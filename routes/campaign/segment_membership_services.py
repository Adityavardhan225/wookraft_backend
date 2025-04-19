from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from bson import ObjectId
from configurations.config import client

# Setup logging
logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
customer_collection = db["customer_order_history"]
segment_collection = db["customer_segments"]
segment_membership_collection = db["segment_membership"]
customer_segment_membership_collection = db["customer_segment_membership"]

async def get_materialized_segment_customers(
    segment_id: str,
    page: int = 0,
    page_size: int = 20
) -> Dict[str, Any]:
    """
    Get customers in a segment from materialized membership data.
    
    Args:
        segment_id: ID of the segment
        page: Page number for pagination
        page_size: Number of customers per page
        
    Returns:
        Dictionary with segment info and customer list
    """
    try:
        # Check if materialized data exists
        membership = segment_membership_collection.find_one({"segment_id": segment_id})
        
        if not membership:
            logger.warning(f"No materialized data for segment {segment_id}")
            return {
                "segment_id": segment_id,
                "customer_count": 0,
                "customers": [],
                "is_stale": True,
                "last_refreshed": None
            }
            
        # Get segment metadata
        segment = segment_collection.find_one({"id": segment_id})
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")
            
        # Format ObjectId
        if "_id" in segment and isinstance(segment["_id"], ObjectId):
            segment["_id"] = str(segment["_id"])
            
        # For smaller segments with inline customer_ids
        if "customer_ids" in membership and isinstance(membership["customer_ids"], list):
            # Calculate offset and limit
            offset = page * page_size
            end_idx = min(offset + page_size, len(membership["customer_ids"]))
            
            page_customer_ids = membership["customer_ids"][offset:end_idx] if offset < len(membership["customer_ids"]) else []
            
            # Get customer details for ids in this page
            customers = []
            for customer_id in page_customer_ids:
                customer = customer_collection.find_one({"_id": customer_id})
                if customer:
                    if "_id" in customer and isinstance(customer["_id"], ObjectId):
                        customer["_id"] = str(customer["_id"])
                    customers.append(customer)
        
        # For larger segments using pagination
        else:
            # TODO: Implement retrieval from chunked storage
            customers = []
            
        # Check if membership is stale based on refresh settings
        is_stale = False
        if segment.get("refresh_settings") and segment["refresh_settings"].get("frequency") != "manual":
            last_refresh = membership.get("refreshed_at")
            if not last_refresh:
                is_stale = True
            else:
                # Check if it's stale based on frequency
                frequency = segment["refresh_settings"]["frequency"]
                now = datetime.now()
                
                if frequency == "hourly" and (now - last_refresh).total_seconds() > 3600:
                    is_stale = True
                elif frequency == "daily" and (now - last_refresh).total_seconds() > 86400:
                    is_stale = True
                elif frequency == "weekly" and (now - last_refresh).total_seconds() > 604800:
                    is_stale = True
        
        return {
            "segment_id": segment_id,
            "segment_name": segment.get("name", ""),
            "customer_count": membership.get("customer_count", 0),
            "customers": customers,
            "page": page,
            "page_size": page_size,
            "total_pages": (membership.get("customer_count", 0) + page_size - 1) // page_size,
            "is_stale": is_stale,
            "last_refreshed": membership.get("refreshed_at")
        }
        
    except Exception as e:
        logger.error(f"Error retrieving materialized segment customers: {str(e)}")
        raise ValueError(f"Failed to retrieve segment customers: {str(e)}")

async def get_customer_segment_membership(customer_id: str) -> Dict[str, Any]:
    """
    Get segments a customer belongs to from materialized membership data.
    
    Args:
        customer_id: ID of the customer
        
    Returns:
        Dictionary with customer's segment membership
    """
    try:
        # Check if materialized data exists
        membership = customer_segment_membership_collection.find_one({"customer_id": customer_id})
        
        if not membership:
            logger.warning(f"No materialized membership data for customer {customer_id}")
            return {
                "customer_id": customer_id,
                "segment_ids": [],
                "refreshed_at": None
            }
            
        # Format ObjectId
        if "_id" in membership and isinstance(membership["_id"], ObjectId):
            membership["_id"] = str(membership["_id"])
            
        return membership
        
    except Exception as e:
        logger.error(f"Error retrieving customer segment membership: {str(e)}")
        raise ValueError(f"Failed to retrieve customer segment membership: {str(e)}")

async def update_segment_membership(
    segment_id: str,
    customer_ids: List[str],
    customer_count: int = None
) -> Dict[str, Any]:
    """
    Update the materialized segment membership.
    
    Args:
        segment_id: ID of the segment
        customer_ids: List of customer IDs in the segment
        customer_count: Total count of customers (for large segments)
        
    Returns:
        Updated membership document
    """
    try:
        now = datetime.now()
        
        # If customer_count is not provided, use length of customer_ids
        if customer_count is None:
            customer_count = len(customer_ids)
            
        # Update segment membership
        membership_data = {
            "segment_id": segment_id,
            "customer_ids": customer_ids if len(customer_ids) <= 1000 else [],  # Only store inline for small segments
            "refreshed_at": now,
            "calculation_duration_ms": 0,  # Will be updated by the calculation process
            "customer_count": customer_count
        }
        
        # Update or insert
        result = segment_membership_collection.update_one(
            {"segment_id": segment_id},
            {"$set": membership_data},
            upsert=True
        )
        
        # Update customer_segment_membership for each customer
        for customer_id in customer_ids:
            customer_segment_membership_collection.update_one(
                {"customer_id": customer_id},
                {
                    "$addToSet": {"segment_ids": segment_id},
                    "$set": {"refreshed_at": now}
                },
                upsert=True
            )
            
        # Update segment statistics
        segment_collection.update_one(
            {"id": segment_id},
            {
                "$set": {
                    "statistics.customer_count": customer_count,
                    "refresh_settings.last_refresh": now
                }
            }
        )
        
        return membership_data
        
    except Exception as e:
        logger.error(f"Error updating segment membership: {str(e)}")
        raise ValueError(f"Failed to update segment membership: {str(e)}")

async def remove_customer_from_segments(customer_id: str, segment_ids: List[str] = None) -> bool:
    """
    Remove a customer from segments.
    
    Args:
        customer_id: ID of the customer
        segment_ids: List of segment IDs to remove from (None for all segments)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # If segment_ids is None, remove from all segments
        if segment_ids is None:
            # Get all segments the customer belongs to
            membership = await get_customer_segment_membership(customer_id)
            segment_ids = membership.get("segment_ids", [])
            
        # Remove customer from each segment
        for segment_id in segment_ids:
            # Update segment membership
            segment_membership_collection.update_one(
                {"segment_id": segment_id},
                {"$pull": {"customer_ids": customer_id}}
            )
            
            # Update segment count
            segment_membership_collection.update_one(
                {"segment_id": segment_id},
                {"$inc": {"customer_count": -1}}
            )
            
            # Update segment statistics
            segment_collection.update_one(
                {"id": segment_id},
                {"$inc": {"statistics.customer_count": -1}}
            )
            
        # Update customer segment membership
        if segment_ids:
            customer_segment_membership_collection.update_one(
                {"customer_id": customer_id},
                {
                    "$pull": {"segment_ids": {"$in": segment_ids}},
                    "$set": {"refreshed_at": datetime.now()}
                }
            )
            
        return True
        
    except Exception as e:
        logger.error(f"Error removing customer from segments: {str(e)}")
        return False