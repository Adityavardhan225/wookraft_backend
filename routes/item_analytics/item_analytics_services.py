from typing import Dict, Any, List, Optional
from bson import ObjectId
import logging
from configurations.config import client
from datetime import datetime, timedelta

# Setup logging
logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
item_analytics_collection = db["item_analytics"]

def is_valid_object_id(id_str: str) -> bool:
    """Check if a string is a valid MongoDB ObjectId"""
    try:
        ObjectId(id_str)
        return True
    except:
        return False

async def get_all_item_analytics(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all item analytics.
    
    Args:
        owner_id: Optional owner ID for data segregation
        
    Returns:
        List of item analytics dictionaries
    """
    try:
        # Build query
        query = {}
        if owner_id:
            query["owner_id"] = owner_id
            
        # Find all items
        cursor = item_analytics_collection.find(query)
        
        # Convert to list and format _id
        items = []
        for item in cursor:
            if "_id" in item and isinstance(item["_id"], ObjectId):
                item["_id"] = str(item["_id"])
            items.append(item)
            
        return items
        
    except Exception as e:
        logger.error(f"Error retrieving all item analytics: {str(e)}")
        raise ValueError(f"Failed to retrieve item analytics: {str(e)}")

async def get_item_analytics_by_id(
    item_id: str,
    owner_id: Optional[str] = None,
    date_range: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve analytics for a specific item by ID.
    
    Args:
        item_id: The ID of the item
        owner_id: Optional owner ID for data segregation
        date_range: Optional date range filter
        
    Returns:
        Item analytics dictionary or None if not found
    """
    try:
        # Build query
        query = {"_id": item_id}  # Item analytics uses string ID format
        if owner_id:
            query["owner_id"] = owner_id
            
        # Find item
        item = item_analytics_collection.find_one(query)
        
        if not item:
            logger.warning(f"No item analytics found for ID: {item_id}")
            return None
            
        # Apply date range filter if needed
        if date_range and date_range in ["today", "week", "month", "year"]:
            item = filter_item_by_date_range(item, date_range)
            
        # Format _id
        if "_id" in item and isinstance(item["_id"], ObjectId):
            item["_id"] = str(item["_id"])
            
        return item
        
    except Exception as e:
        logger.error(f"Error retrieving item analytics by ID: {str(e)}")
        raise ValueError(f"Failed to retrieve item analytics: {str(e)}")

async def get_item_analytics_by_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retrieve item analytics based on filters.
    
    Args:
        filters: Dictionary of filter criteria
        
    Returns:
        List of filtered item analytics
    """
    try:
        # Extract pagination, sorting, and owner_id
        limit = filters.get("limit", 20)
        skip = filters.get("skip", 0)
        sort_by = filters.get("sort_by", "total_revenue")
        sort_order = filters.get("sort_order", "desc")
        owner_id = filters.get("owner_id")
        
        # Build query
        query = {}
        if owner_id:
            query["owner_id"] = owner_id
        
        # # Apply filters
        # if "category" in filters and filters["category"]:
        #     query["category"] = filters["category"]
            
        # if "type" in filters and filters["type"]:
        #     query["type"] = filters["type"]


                # Handle multiple categories using $in operator
        if "category" in filters and filters["category"]:
            categories = filters["category"]
            if isinstance(categories, list) and len(categories) > 0:
                query["category"] = {"$in": categories}
            elif not isinstance(categories, list):
                query["category"] = categories
        
        # Handle multiple types using $in operator
        if "type" in filters and filters["type"]:
            types = filters["type"]
            if isinstance(types, list) and len(types) > 0:
                query["type"] = {"$in": types}
            elif not isinstance(types, list):
                query["type"] = types
            
        if "name" in filters and filters["name"]:
            query["name"] = {"$regex": filters["name"], "$options": "i"}
            
        if "min_orders" in filters and filters["min_orders"] is not None:
            query["total_orders"] = {"$gte": filters["min_orders"]}
            
        if "min_revenue" in filters and filters["min_revenue"] is not None:
            query["total_revenue"] = {"$gte": filters["min_revenue"]}
        
        # Determine sort direction
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        
        # Find items
        cursor = item_analytics_collection.find(query).sort(sort_by, sort_direction).skip(skip).limit(limit)
        
        # Convert to list and format _id
        items = []
        for item in cursor:
            if "_id" in item and isinstance(item["_id"], ObjectId):
                item["_id"] = str(item["_id"])
                
            # Apply date range filter if needed
            if "date_range" in filters and filters["date_range"]:
                item = filter_item_by_date_range(item, filters["date_range"])
                
            items.append(item)
            
        return items
        
    except Exception as e:
        logger.error(f"Error retrieving item analytics by filters: {str(e)}")
        raise ValueError(f"Failed to retrieve item analytics: {str(e)}")

def filter_item_by_date_range(item: Dict[str, Any], date_range: str) -> Dict[str, Any]:
    """
    Filter item data by date range.
    
    Args:
        item: Item analytics dictionary
        date_range: Date range string (today, week, month, year)
        
    Returns:
        Updated item with filtered data
    """
    result = item.copy()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Filter daily sales
    if "daily_sales" in result:
        filtered_sales = []
        
        if date_range == "today":
            filtered_sales = [sale for sale in result["daily_sales"] if sale.get("date") == today]
        elif date_range == "week":
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            filtered_sales = [sale for sale in result["daily_sales"] if sale.get("date") >= week_ago]
        elif date_range == "month":
            current_month = today[:7]  # YYYY-MM format
            filtered_sales = [sale for sale in result["daily_sales"] if sale.get("date", "").startswith(current_month)]
        elif date_range == "year":
            current_year = today[:4]  # YYYY format
            filtered_sales = [sale for sale in result["daily_sales"] if sale.get("date", "").startswith(current_year)]
            
        result["daily_sales"] = filtered_sales
        
        # Update total_revenue and total_quantity based on filtered sales
        if filtered_sales:
            result["total_revenue"] = sum(sale.get("revenue", 0) for sale in filtered_sales)
            result["total_quantity"] = sum(sale.get("quantity", 0) for sale in filtered_sales)
        else:
            result["total_revenue"] = 0
            result["total_quantity"] = 0
            
    # Similarly filter monthly_sales if needed for year range
    if date_range == "year" and "monthly_sales" in result:
        current_year = today[:4]
        result["monthly_sales"] = [
            sale for sale in result["monthly_sales"] 
            if sale.get("month", "").startswith(current_year)
        ]
    
    return result