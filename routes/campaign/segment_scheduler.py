from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import time
from bson import ObjectId
from configurations.config import client
from .customer_segment_services import build_query_from_criteria, get_segment_by_id
from .segment_membership_services import update_segment_membership

# Setup logging
logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
customer_collection = db["customer_order_history"]
segment_collection = db["customer_segments"]
job_collection = db["segment_jobs"]

async def refresh_segment_membership(segment_id: str, full_refresh: bool = False) -> Dict[str, Any]:
    """
    Background job that updates segment membership.
    
    Args:
        segment_id: ID of the segment to refresh
        full_refresh: Whether to do a full refresh of membership data
        
    Returns:
        Job results dictionary
    """
    try:
        start_time = time.time()
        
        # Record job start
        job_id = str(ObjectId())
        job_data = {
            "_id": job_id,
            "segment_id": segment_id,
            "type": "refresh_membership",
            "status": "running",
            "start_time": datetime.now(),
            "end_time": None,
            "duration_ms": None,
            "full_refresh": full_refresh,
            "customer_count": None,
            "error": None
        }
        job_collection.insert_one(job_data)
        
        # Get segment
        segment = await get_segment_by_id(segment_id)
        if not segment:
            # Update job status
            job_collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "failed",
                        "end_time": datetime.now(),
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "error": f"Segment {segment_id} not found"
                    }
                }
            )
            return {"success": False, "error": f"Segment {segment_id} not found"}
            
        # Build query from segment criteria
        query = build_query_from_criteria(segment.get("criteria", {}))
        
        # Find matching customers
        cursor = customer_collection.find(query)
        
        # Get customer IDs
        customer_ids = []
        customer_count = 0
        for customer in cursor:
            customer_count += 1
            customer_ids.append(str(customer["_id"]))
            
            # For large segments, we might not store all IDs in memory
            if len(customer_ids) >= 10000 and not full_refresh:
                break
        
        # Update materialized view
        await update_segment_membership(
            segment_id=segment_id,
            customer_ids=customer_ids,
            customer_count=customer_count
        )
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update job status
        job_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "end_time": datetime.now(),
                    "duration_ms": duration_ms,
                    "customer_count": customer_count
                }
            }
        )
        
        # Update segment with average duration
        segment_collection.update_one(
            {"id": segment_id},
            {
                "$set": {
                    "refresh_settings.average_duration_ms": duration_ms,
                    "refresh_settings.last_refresh": datetime.now(),
                    "refresh_settings.next_scheduled": calculate_next_scheduled(segment.get("refresh_settings", {}))
                }
            }
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "segment_id": segment_id,
            "customer_count": customer_count,
            "duration_ms": duration_ms
        }
        
    except Exception as e:
        logger.error(f"Error refreshing segment membership: {str(e)}")
        
        # Update job status
        job_collection.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "end_time": datetime.now(),
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "error": str(e)
                }
            }
        )
        
        raise ValueError(f"Failed to refresh segment membership: {str(e)}")

def calculate_next_scheduled(refresh_settings: Dict[str, Any]) -> datetime:
    """
    Calculate the next scheduled refresh time based on frequency.
    
    Args:
        refresh_settings: Dictionary with refresh settings
        
    Returns:
        Next scheduled refresh time
    """
    now = datetime.now()
    frequency = refresh_settings.get("frequency", "daily")
    
    if frequency == "hourly":
        return now + timedelta(hours=1)
    elif frequency == "daily":
        return now + timedelta(days=1)
    elif frequency == "weekly":
        return now + timedelta(weeks=1)
    else:
        return now + timedelta(days=1)  # Default to daily

async def schedule_due_segment_refreshes():
    """
    Check for segments due for refresh and schedule them.
    This should be run on a regular interval, e.g., every hour.
    """
    try:
        now = datetime.now()
        
        # Find segments due for refresh
        due_segments = segment_collection.find({
            "refresh_settings.frequency": {"$ne": "manual"},
            "refresh_settings.next_scheduled": {"$lte": now}
        })
        
        # Schedule refresh for each due segment
        for segment in due_segments:
            segment_id = segment.get("id")
            if segment_id:
                # Schedule in background
                asyncio.create_task(refresh_segment_membership(segment_id))
                logger.info(f"Scheduled refresh for segment {segment_id}")
                
    except Exception as e:
        logger.error(f"Error scheduling segment refreshes: {str(e)}")

async def get_segment_refresh_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get details of a segment refresh job.
    
    Args:
        job_id: ID of the job
        
    Returns:
        Job details or None if not found
    """
    try:
        job = job_collection.find_one({"_id": job_id})
        
        if not job:
            return None
            
        return job
        
    except Exception as e:
        logger.error(f"Error retrieving job details: {str(e)}")
        raise ValueError(f"Failed to retrieve job details: {str(e)}")