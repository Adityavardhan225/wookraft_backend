import os
from routes.campaign.sending_campaign.services import celery_app
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'celery.log'), 'a')
    ]
)

# Ensure logs directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'logs'), exist_ok=True)

logger = logging.getLogger('celery_worker')

# Make sure all task modules are imported so tasks are registered with Celery
import routes.campaign.sending_campaign.services.campaign_tasks

# This file is the entry point for Celery workers
if __name__ == '__main__':
    logger.info("Starting Celery worker...")
    celery_app.worker_main(['worker', '--loglevel=info'])