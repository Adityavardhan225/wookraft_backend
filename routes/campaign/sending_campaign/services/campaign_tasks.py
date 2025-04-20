from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
import asyncio
import json
import os
from bson import ObjectId
import time
from celery import Celery
import os
# from routes.campaign.sending_campaign.services.celery_app import celery_app
from routes.campaign.sending_campaign.services.email_service import email_service
from configurations.config import client
from routes.campaign.customer_segment_services import get_customers_for_combined_criteria


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

# Create Celery app directly in tasks file
celery_app = Celery(
    'woopos', 
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add this to your campaign_tasks.py
celery_app.conf.beat_schedule = {
    'check-scheduled-campaigns': {
        'task':'routes.campaign.sending_campaign.services.campaign_tasks.check_scheduled_campaigns',
        'schedule': 60.0,  # Run every 60 seconds
    },
    'process-campaign-queue': {
        'task': 'routes.campaign.sending_campaign.services.campaign_tasks.process_campaign_queue',
        'schedule': 30.0,  # Run every 30 seconds
    },
}

# Database collections
db = client["wookraft_db"]
campaigns_collection = db["email_campaigns"]
templates_collection = db["email_templates"]
email_logs_collection = db["email_logs"]

# Queue name for Redis
EMAIL_QUEUE = 'email_campaigns_queue'
SCHEDULED_CAMPAIGNS = 'scheduled_campaigns'

@celery_app.task(name="send_campaign_email")
def send_campaign_email(
    to_email: str,
    to_name: str,
    subject: str,
    template_id: str,
    variables: Dict[str, Any],
    campaign_id: str,
    tracking_enabled: bool = True
) -> Dict[str, Any]:
    """
    Send a single campaign email
    
    Args:
        to_email: Recipient email address
        to_name: Recipient name
        subject: Email subject
        template_id: Template ID
        variables: Variables for the template
        campaign_id: Campaign ID
        tracking_enabled: Whether to enable tracking
        
    Returns:
        Send result
    """
    logger.info(f"Sending campaign email to {to_email}")
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run email service send method
        result = loop.run_until_complete(
            email_service.send_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                template_id=template_id,
                variables=variables,
                campaign_id=campaign_id,
                tracking_enabled=tracking_enabled
            )
        )
        
        # Update campaign statistics
        status_field = "statistics.sent" if result.get("success") else "statistics.failed"
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$inc": {status_field: 1}}
        )
        
        return result
        
    finally:
        # Clean up the event loop
        loop.close()

@celery_app.task(name="send_campaign_batch")
def send_campaign_batch(
    recipients: List[Dict[str, Any]],
    subject: str,
    template_id: str,
    campaign_id: str,
    batch_index: int
) -> Dict[str, Any]:
    """
    Send a batch of campaign emails
    
    Args:
        recipients: List of recipient data
        subject: Email subject
        template_id: Template ID
        campaign_id: Campaign ID
        batch_index: Batch index for tracking
        
    Returns:
        Batch send result
    """
    logger.info(f"Processing batch {batch_index} with {len(recipients)} recipients")
    start_time = time.time()
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run email service batch send method
        result = loop.run_until_complete(
            email_service.send_batch_emails(
                recipients=recipients,
                subject=subject,
                template_id=template_id,
                campaign_id=campaign_id
            )
        )
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Update campaign batch stats
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {
                "$push": {
                    "batches": {
                        "batch_index": batch_index,
                        "total": len(recipients),
                        "sent": result.get("sent_count", 0),
                        "failed": result.get("failed_count", 0),
                        "duration_seconds": duration,
                        "completed_at": datetime.now()
                    }
                }
            }
        )
        
        logger.info(f"Batch {batch_index} completed in {duration:.2f}s: {result.get('sent_count', 0)} sent, {result.get('failed_count', 0)} failed")
        
        return {
            "success": result.get("success", False),
            "batch_index": batch_index,
            "sent_count": result.get("sent_count", 0),
            "failed_count": result.get("failed_count", 0),
            "duration_seconds": duration
        }
        
    finally:
        # Clean up the event loop
        loop.close()

@celery_app.task(name="process_campaign")
def process_campaign(campaign_id: str) -> Dict[str, Any]:
    """
    Process a campaign by retrieving recipients and sending in batches
    
    Args:
        campaign_id: Campaign ID to process
        
    Returns:
        Processing result
    """
    logger.info(f"Processing campaign {campaign_id}")
    
    # Create event loop for async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Update campaign status to processing
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "processing", 
                "processing_started": datetime.now(),
                "batches": []
            }}
        )
        
        # Get campaign details
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            return {
                "success": False,
                "message": f"Campaign {campaign_id} not found"
            }
        
        # Get template
        template = templates_collection.find_one({"_id": ObjectId(campaign.get("template_id"))})
        if not template:
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "status": "failed", 
                    "error": "Template not found",
                    "failed_at": datetime.now()
                }}
            )
            return {
                "success": False,
                "message": "Template not found"
            }
        
        # Get recipients from segments
        recipient_data = loop.run_until_complete(
            get_customers_for_combined_criteria(
                segment_ids=campaign.get("segment_ids", []),
                custom_filters=campaign.get("custom_filters", []),
                operator=campaign.get("operator", "AND"),
                limit=0,  # Get all recipients
                skip=0
            )
        )
        
        recipients = recipient_data.get("customers", [])
        total_recipients = recipient_data.get("total", 0)
        
        if not recipients:
            logger.warning(f"No recipients found for campaign {campaign_id}")
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "status": "completed", 
                    "error": "No recipients found",
                    "completed_at": datetime.now(),
                    "statistics.total_recipients": 0
                }}
            )
            return {
                "success": True,
                "message": "Campaign completed - no recipients found"
            }
        
        # Update recipient count
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {"statistics.total_recipients": total_recipients}}
        )
        
        # Process in batches (max 50 recipients per batch)
        batch_size = 50
        batches = [recipients[i:i+batch_size] for i in range(0, len(recipients), batch_size)]
        
        logger.info(f"Campaign {campaign_id} has {len(batches)} batches with {total_recipients} total recipients")
        
        # Queue batch sending tasks
        for i, batch in enumerate(batches):
            # Prepare recipients with variables
            prepared_recipients = []
            for recipient in batch:
                # Basic variables
                variables = {
                    "customer_name": recipient.get("name", ""),
                    "email": recipient.get("email", ""),
                    "total_spent": recipient.get("totalSpent", 0),
                    "purchase_count": recipient.get("purchaseCount", 0)
                }
                
                # Add campaign custom variables
                if campaign.get("custom_variables"):
                    variables.update(campaign.get("custom_variables", {}))
                
                prepared_recipients.append({
                    "email": recipient.get("email"),
                    "name": recipient.get("name", ""),
                    "variables": variables
                })
            
            # Queue the batch
            send_campaign_batch.apply_async(
                args=[
                    prepared_recipients,
                    campaign.get("subject", ""),
                    str(template["_id"]),
                    campaign_id,
                    i
                ],
                countdown=i * 3  # Space out batches by 3 seconds
            )
        
        # Update campaign status
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "sending",
                "total_batches": len(batches)
            }}
        )
        
        return {
            "success": True,
            "message": f"Campaign processing started with {total_recipients} recipients in {len(batches)} batches"
        }
        
    except Exception as e:
        logger.error(f"Error processing campaign {campaign_id}: {str(e)}")
        
        # Update campaign with error
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now()
            }}
        )
        
        return {
            "success": False,
            "message": f"Failed to process campaign: {str(e)}"
        }
        
    finally:
        # Clean up the event loop
        loop.close()





@celery_app.task(name="routes.campaign.sending_campaign.services.campaign_tasks.check_scheduled_campaigns")
def check_scheduled_campaigns() -> Dict[str, Any]:
    """Check for campaigns scheduled to run now"""
    logger.info("Checking for scheduled campaigns")
    
    try:
        # Get Redis connection
        from redis import Redis
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD')
        )
        
        # Test Redis connection
        try:
            redis_client.ping()
            print("Redis connection successful")
        except Exception as redis_error:
            logger.error(f"Failed to connect to Redis: {str(redis_error)}")
            return {
                "success": False,
                "message": f"Redis connection error: {str(redis_error)}"
            }
        
        # Current timestamp
        now = int(datetime.now().timestamp())
        print(f"Current timestamp: {now} ({datetime.fromtimestamp(now)})")
        
        # Log all campaigns in Redis
        all_campaigns = redis_client.zrange("scheduled_campaigns", 0, -1, withscores=True)
        print(f"All scheduled campaigns in Redis: {[(key.decode(), score) for key, score in all_campaigns]}")
        
        # Get due campaigns from Redis sorted set
        due_campaigns = redis_client.zrangebyscore("scheduled_campaigns", 0, now)
        print(f"Found {len(due_campaigns)} due campaigns: {due_campaigns}")
        
        processed_count = 0
        
        # Process each due campaign
        for campaign_key in due_campaigns:
            try:
                campaign_id = campaign_key.decode().split(":")[-1]
                print(f"Processing campaign {campaign_id}")
                
                # Queue campaign processing
                print(f"Queuing campaign {campaign_id} for processing")
                process_campaign.apply_async(args=[campaign_id])
                
                # Remove from scheduled set
                removed = redis_client.zrem("scheduled_campaigns", campaign_key)
                if removed:
                    print(f"Removed campaign {campaign_id} from Redis")
                else:
                    print(f"Failed to remove campaign {campaign_id} from Redis")
                
                processed_count += 1
            except Exception as e:
                logger.error(f"Error processing campaign {campaign_id}: {str(e)}")
        
        if processed_count > 0:
            print(f"Queued {processed_count} scheduled campaigns for processing")
        
        return {
            "success": True,
            "processed_count": processed_count
        }
        
    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {str(e)}")
        return {
            "success": False, 
            "message": f"Failed to check scheduled campaigns: {str(e)}"
        }
    
    
@celery_app.task(name="routes.campaign.sending_campaign.services.campaign_tasks.process_campaign_queue")
def process_campaign_queue() -> Dict[str, Any]:
    """
    Process the campaign queue from Redis
    
    Returns:
        Processing result
    """
    logger.info("Processing campaign queue")
    
    try:
        # Get Redis connection
        from redis import Redis
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD')
        )
        
        # Get campaigns from queue (up to 5 at a time)
        processed_count = 0
        max_to_process = 5
        
        for _ in range(max_to_process):
            # Try to get campaign from queue
            campaign_data = redis_client.rpop(EMAIL_QUEUE)
            if not campaign_data:
                break
            
            # Parse campaign data
            campaign_info = json.loads(campaign_data)
            campaign_id = campaign_info.get("campaign_id")
            print(f"Processing campaign {campaign_id} from queue")
            if campaign_id:
                # Queue campaign processing
                process_campaign.apply_async(args=[campaign_id])
                processed_count += 1
        print(f"Processed {processed_count} campaigns from queue")
        if processed_count > 0:
            logger.info(f"Queued {processed_count} campaigns from Redis queue")
        
        return {
            "success": True,
            "processed_count": processed_count
        }
        
    except Exception as e:
        logger.error(f"Error processing campaign queue: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to process campaign queue: {str(e)}"
        }

@celery_app.task(name="check_campaign_completion")
def check_campaign_completion() -> Dict[str, Any]:
    """
    Check for campaigns that should be marked as completed
    
    Returns:
        Check result
    """
    logger.info("Checking for completed campaigns")
    
    try:
        # Find campaigns in sending status
        campaigns = campaigns_collection.find({
            "status": "sending"
        })
        
        completed_count = 0
        
        # Process each campaign
        for campaign in campaigns:
            campaign_id = campaign["_id"]
            total_batches = campaign.get("total_batches", 0)
            completed_batches = len(campaign.get("batches", []))
            
            # If all batches are complete or campaign has been sending for over 24 hours
            time_limit = datetime.now() - timedelta(hours=24)
            processing_started = campaign.get("processing_started", datetime.now())
            
            if (completed_batches >= total_batches) or (processing_started < time_limit):
                # Update sent and failed counts from batch data
                sent_count = sum(batch.get("sent", 0) for batch in campaign.get("batches", []))
                failed_count = sum(batch.get("failed", 0) for batch in campaign.get("batches", []))
                
                # Mark campaign as completed
                campaigns_collection.update_one(
                    {"_id": campaign_id},
                    {"$set": {
                        "status": "completed",
                        "completed_at": datetime.now(),
                        "statistics.sent": sent_count,
                        "statistics.failed": failed_count
                    }}
                )
                
                completed_count += 1
        
        if completed_count > 0:
            logger.info(f"Marked {completed_count} campaigns as completed")
        
        return {
            "success": True,
            "completed_count": completed_count
        }
        
    except Exception as e:
        logger.error(f"Error checking campaign completion: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to check campaign completion: {str(e)}"
        }