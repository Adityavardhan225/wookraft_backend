import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables first
load_dotenv()

# Import the celery application
from routes.campaign.sending_campaign.services.celery_app import celery_app

# IMPORTANT: Import tasks to register them with celery
import routes.campaign.sending_campaign.services.campaign_tasks

# This is required for Celery to find the app
app = celery_app