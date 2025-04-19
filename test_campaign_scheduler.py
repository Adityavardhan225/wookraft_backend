import redis
import os
from datetime import datetime, timedelta
from bson import ObjectId
from dotenv import load_dotenv
import time
import uuid

# Load environment variables
load_dotenv()

# MongoDB connection
from configurations.config import client
db = client["wookraft_db"]
campaigns_collection = db["email_campaigns"]
templates_collection = db["email_templates"]

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost") 
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD
)

def test_campaign_scheduling():
    # Try to get any existing campaign
    campaign = campaigns_collection.find_one({})
    
    if not campaign:
        print("No campaign found. Creating a test campaign...")
        # Find a template
        template = templates_collection.find_one({})
        if not template:
            print("Error: No email templates found in database")
            return
        
        # Create test campaign
        campaign = {
            "name": f"Test Campaign {uuid.uuid4().hex[:8]}",
            "subject": "Test Email Subject",
            "template_id": str(template["_id"]),
            "segment_ids": [],
            "custom_filters": [],
            "operator": "AND",
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "statistics": {
                "total_recipients": 0,
                "sent": 0,
                "delivered": 0,
                "failed": 0
            }
        }
        
        result = campaigns_collection.insert_one(campaign)
        campaign_id = str(result.inserted_id)
        print(f"Created new test campaign: {campaign_id}")
    else:
        campaign_id = str(campaign["_id"])
        print(f"Using existing campaign: {campaign_id}")
    
    # Schedule for 2 minutes from now
    schedule_time = datetime.now() + timedelta(minutes=2)
    schedule_time_ts = int(schedule_time.timestamp())
    
    print(f"Current time: {datetime.now()}")
    print(f"Scheduling for: {schedule_time} (unix timestamp: {schedule_time_ts})")
    
    # Update the campaign in MongoDB
    campaigns_collection.update_one(
        {"_id": ObjectId(campaign_id)},
        {"$set": {
            "schedule_time": schedule_time,
            "status": "scheduled",
            "scheduled_at": datetime.now()
        }}
    )
    
    # Add to Redis scheduled queue
    task_id = f"campaign:{campaign_id}"
    redis_client.zadd("scheduled_campaigns", {task_id: schedule_time_ts})
    
    print(f"Campaign scheduled successfully. Task ID: {task_id}")
    
    # Check what's in the Redis queue
    all_scheduled = redis_client.zrange("scheduled_campaigns", 0, -1, withscores=True)
    print("\nAll scheduled campaigns:")
    for campaign_key, score in all_scheduled:
        c_id = campaign_key.decode().split(":")[-1]
        due_time = datetime.fromtimestamp(score)
        print(f"- Campaign {c_id}: scheduled for {due_time} (timestamp: {int(score)})")
    
    print("\nWaiting for scheduler to pick up the campaign...")
    print("Make sure your scheduler is running with:")
    print("celery -A routes.campaign.sending_campaign.services.campaign_tasks beat -l info")
    print("And your worker with:")
    print("celery -A routes.campaign.sending_campaign.services.campaign_tasks worker -l info -Q campaigns,scheduler,emails")

if __name__ == "__main__":
    test_campaign_scheduling()