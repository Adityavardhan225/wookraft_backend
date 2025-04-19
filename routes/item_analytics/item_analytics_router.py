from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, List, Optional
from .item_analytics_services import (
    get_all_item_analytics,
    get_item_analytics_by_id,
    get_item_analytics_by_filters
)
from routes.security.protected_authorise import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/items", response_model=List[Dict[str, Any]])
async def get_items_analytics_route(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of items to return"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    category: Optional[List[str]] = Query(None, description="Filter items by category"),
    type: Optional[List[str]] = Query(None, description="Filter items by food type (veg, non-veg, egg, etc.)"),
    name: Optional[str] = Query(None, description="Filter items by name"),
    min_orders: Optional[int] = Query(None, ge=0, description="Minimum number of orders"),
    min_revenue: Optional[float] = Query(None, ge=0, description="Minimum revenue generated"),
    sort_by: Optional[str] = Query("total_revenue", description="Sort by field (total_revenue, total_orders, etc.)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    date_range: Optional[str] = Query(None, description="Date range filter (today, week, month, year)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a list of item analytics with optional filtering.
    """
    try:
        # Get owner_id from current user
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Build filters
        filters = {
            "limit": limit,
            "skip": skip,
            "sort_by": sort_by,
            "sort_order": sort_order,
           
        }
        
        if category:
            filters["category"] = category
        if type:
            filters["type"] = type
        if name:
            filters["name"] = name
        if min_orders is not None:
            filters["min_orders"] = min_orders
        if min_revenue is not None:
            filters["min_revenue"] = min_revenue
        if date_range:
            filters["date_range"] = date_range
        print(f'filters: {filters}')
        # Get item analytics
        item_analytics = await get_item_analytics_by_filters(filters)
        print(f'item_analytics: {item_analytics}')
        return item_analytics
        
    except Exception as e:
        logger.error(f"Error retrieving item analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving item analytics: {str(e)}")

@router.get("/items/{item_id}", response_model=Dict[str, Any])
async def get_item_analytics_by_id_route(
    item_id: str,
    date_range: Optional[str] = Query(None, description="Date range filter (today, week, month, year)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve analytics for a specific item by ID.
    """
    try:
        # Get owner_id from current user
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get item analytics
        item_analytics = await get_item_analytics_by_id(item_id, owner_id, date_range)
        
        if not item_analytics:
            raise HTTPException(status_code=404, detail=f"No item analytics found for ID: {item_id}")
        
        return item_analytics
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving item analytics by ID: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving item analytics: {str(e)}")

@router.get("/categories", response_model=List[str])
async def get_item_categories_route(
    current_user: dict = Depends(get_current_user)
):
    """
    Get a list of all unique item categories for filtering.
    """
    try:
        # Get owner_id from current user
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get all item analytics
        all_items = await get_all_item_analytics(owner_id)
        
        # Extract unique categories
        categories = list(set(item.get("category", "") for item in all_items if item.get("category")))
        return sorted(categories)
        
    except Exception as e:
        logger.error(f"Error retrieving item categories: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving item categories: {str(e)}")

@router.get("/types", response_model=List[str])
async def get_item_types_route(
    current_user: dict = Depends(get_current_user)
):
    """
    Get a list of all unique item types (veg, non-veg, etc.) for filtering.
    """
    try:
        # Get owner_id from current user
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get all item analytics
        all_items = await get_all_item_analytics(owner_id)
        
        # Extract unique types
        types = list(set(item.get("type", "") for item in all_items if item.get("type")))
        return sorted(types)
        
    except Exception as e:
        logger.error(f"Error retrieving item types: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving item types: {str(e)}")

@router.get("/summary", response_model=Dict[str, Any])
async def get_items_summary_route(
    date_range: Optional[str] = Query(None, description="Date range filter (today, week, month, year)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary statistics for all items.
    """
    try:
        # Get owner_id from current user
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get filtered item analytics
        filters = {
            "date_range": date_range,
            "owner_id": owner_id,
            "sort_by": "total_revenue",
            "sort_order": "desc"
        }
        items = await get_item_analytics_by_filters(filters)
        
        # Calculate summary
        total_revenue = sum(item.get("total_revenue", 0) for item in items)
        total_orders = sum(item.get("total_orders", 0) for item in items)
        total_items = len(items)
        
        # Get top items
        top_revenue_items = sorted(items, key=lambda x: x.get("total_revenue", 0), reverse=True)[:5]
        top_ordered_items = sorted(items, key=lambda x: x.get("total_orders", 0), reverse=True)[:5]
        
        # Get category breakdown
        category_breakdown = {}
        for item in items:
            category = item.get("category", "Other")
            if category not in category_breakdown:
                category_breakdown[category] = {
                    "revenue": 0,
                    "orders": 0,
                    "items": 0
                }
            category_breakdown[category]["revenue"] += item.get("total_revenue", 0)
            category_breakdown[category]["orders"] += item.get("total_orders", 0)
            category_breakdown[category]["items"] += 1
        
        return {
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_items": total_items,
            "top_revenue_items": top_revenue_items,
            "top_ordered_items": top_ordered_items,
            "category_breakdown": category_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error retrieving items summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving items summary: {str(e)}")