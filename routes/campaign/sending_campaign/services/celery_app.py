from celery import Celery
import os
from dotenv import load_dotenv
import logging
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

# Import task modules explicitly to ensure registration

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis configuration
# REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
# REDIS_PORT = os.getenv('REDIS_PORT', '6379')
# REDIS_DB = os.getenv('REDIS_DB', '0')
# REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')

# # Build Redis URL
# if REDIS_PASSWORD:
#     REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
# else:
#     REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Use REDIS_URL for deployment
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# try:
#     from routes.campaign.sending_campaign.services.campaign_tasks import celery_app
# except ImportError:
#     # Create a backup app if import fails
#     celery_app = Celery('woopos', broker=REDIS_URL, backend=REDIS_URL)

# Log configuration
logger.info(f"Celery configured with broker: {REDIS_URL}")
# Create Celery app
celery_app = Celery(
    'woopos',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Load task modules
celery_app.conf.imports = [
    'routes.campaign.sending_campaign.services.campaign_tasks'
]

import ssl
if REDIS_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE  # Disable certificate validation
    }
    celery_app.conf.redis_backend_use_ssl = {
        "ssl_cert_reqs": ssl.CERT_NONE  # Disable certificate validation
    }


# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',  # Set to your local timezone
    enable_utc=False,   
    
    # Task execution settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,  # Adjust based on server capabilities
    task_acks_late=True,   # Tasks acknowledged after execution
    
    # Task time limits
    task_time_limit=3600,  # 1 hour task time limit
    task_soft_time_limit=3000,  # 50 minutes soft time limit
    
    # Retry settings
    task_default_rate_limit='150/m',  # Default task rate limit
    
    # Result backend settings
    result_expires=86400,  # Results expire after 1 day
    
    # Scheduled tasks
    beat_schedule={
        'check-scheduled-campaigns': {
            'task': 'routes.campaign.sending_campaign.services.campaign_tasks.check_scheduled_campaigns',
            'schedule': 60.0,  # Run every 60 seconds
        },
        'process-campaign-queue': {
            'task': 'routes.campaign.sending_campaign.services.campaign_tasks.process_campaign_queue',
            'schedule': 30.0,  # Run every 30 seconds
        },
    }
)

# Task routing
celery_app.conf.task_routes = {

    'routes.campaign.sending_campaign.services.campaign_tasks.check_scheduled_campaigns': {'queue': 'scheduler'},
    'routes.campaign.sending_campaign.services.campaign_tasks.process_campaign_queue': {'queue': 'scheduler'},
    'routes.campaign.sending_campaign.services.campaign_tasks.send_campaign_email': {'queue': 'emails'},
    'routes.campaign.sending_campaign.services.campaign_tasks.send_campaign_batch': {'queue': 'emails'},
    'routes.campaign.sending_campaign.services.campaign_tasks.process_campaign': {'queue': 'campaigns'},
}

# Log Celery configuration
logger.info(f"Celery configured with broker: {REDIS_URL}")
logger.info(f"Available task queues: {list(celery_app.conf.task_routes.keys())}")

__all__ = ['celery_app']