from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from bson import ObjectId
from bson.errors import InvalidId
import json
import redis
import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from fastapi import HTTPException
from configurations.config import client

# Import models
from .models import (
    Dashboard, DashboardCreate, DashboardUpdate, DashboardResponse,
    ChartConfig, ChartCreate, ChartUpdate, ChartResponse,
    QueryRequest, QueryResponse, FilterCondition,
    Dataset, DatasetResponse
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection - replace with your actual DB connection logic
# client = MongoClient("mongodb://localhost:27017/")
# db = client.woopos
db=client["wookraft_db"]
# Redis connection for caching
try:
    redis_client = redis.Redis(host="localhost", port=6379, db=0)
    redis_connected = True
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching disabled.")
    redis_connected = False

# Cache configuration
CACHE_TTL = 60 * 15  # 15 minutes




def is_valid_object_id(id_str: str) -> bool:
    """Check if the ID is a valid MongoDB ObjectId"""
    try:
        ObjectId(id_str)
        return True
    except InvalidId:
        return False

def get_dashboard_query(dashboard_id: str) -> dict:
    """Get the appropriate query for dashboard lookup"""
    if is_valid_object_id(dashboard_id):
        return {"_id": ObjectId(dashboard_id)}
    elif dashboard_id.startswith("dashboard-"):
        return {"custom_id": dashboard_id}
    else:
        # Default to ObjectId (will likely raise InvalidId)
        return {"_id": ObjectId(dashboard_id)}
    


# ======== Dataset Services ========

def get_datasets() -> List[DatasetResponse]:
    """Get all available analytics datasets"""
    # Define the available datasets based on your MongoDB collections
    datasets = [
        {
            "id": "bills",
            "name": "Sales Data",
            "description": "Bill and sales transaction data",
            "last_updated": datetime.now(),
            "record_count": db.bills.count_documents({}),
            "fields": [
                {"name": "date", "type": "date", "description": "Bill date"},
                {"name": "timestamp", "type": "datetime", "description": "Transaction time"},
                {"name": "total_amount", "type": "number", "description": "Total bill amount"},
                {"name": "subtotal", "type": "number", "description": "Subtotal before tax"},
                {"name": "customer.name", "type": "string", "description": "Customer name"},
                {"name": "payment.status", "type": "string", "description": "Payment status"},
                {"name": "table_number", "type": "integer", "description": "Table number"},
                {"name": "items.name", "type": "string", "description": "Item name"},
                {"name": "items.quantity", "type": "integer", "description": "Item quantity"},
                {"name": "items.unit_price", "type": "number", "description": "Item unit price"},
                {"name": "items.category", "type": "string", "description": "Item category"},
            ],
            "available_aggregations": ["sum", "avg", "min", "max", "count"],
            "available_filters": ["date", "timestamp", "customer.name", "payment.status", "table_number", "items.category"]
        },
        {
            "id": "customer_order_history",
            "name": "Customer Data",
            "description": "Customer order history and preferences",
            "last_updated": datetime.now(),
            "record_count": db.customer_order_history.count_documents({}),
            "fields": [
                {"name": "name", "type": "string", "description": "Customer name"},
                {"name": "email", "type": "string", "description": "Customer email"},
                {"name": "first_visit", "type": "date", "description": "First visit date"},
                {"name": "last_visit", "type": "date", "description": "Last visit date"},
                {"name": "total_visits", "type": "integer", "description": "Total visit count"},
                {"name": "total_spent", "type": "number", "description": "Total amount spent"},
                {"name": "favorite_items.name", "type": "string", "description": "Favorite item name"},
                {"name": "favorite_items.count", "type": "integer", "description": "Favorite item order count"},
                {"name": "orders.amount", "type": "number", "description": "Order amount"},
                {"name": "orders.date", "type": "date", "description": "Order date"},
                {"name": "orders.items_count", "type": "integer", "description": "Items per order"},
            ],
            "available_aggregations": ["sum", "avg", "min", "max", "count"],
            "available_filters": ["name", "email", "first_visit", "last_visit", "total_visits", "total_spent"]
        },
        {
            "id": "item_analytics",
            "name": "Menu Performance",
            "description": "Menu item sales and performance",
            "last_updated": datetime.now(),
            "record_count": db.item_analytics.count_documents({}),
            "fields": [
                {"name": "name", "type": "string", "description": "Item name"},
                {"name": "category", "type": "string", "description": "Item category"},
                {"name": "type", "type": "string", "description": "Item type"},
                {"name": "total_orders", "type": "integer", "description": "Total orders"},
                {"name": "total_quantity", "type": "integer", "description": "Total quantity sold"},
                {"name": "total_revenue", "type": "number", "description": "Total revenue"},
                {"name": "daily_sales.date", "type": "date", "description": "Daily sales date"},
                {"name": "daily_sales.quantity", "type": "integer", "description": "Daily quantity sold"},
                {"name": "daily_sales.revenue", "type": "number", "description": "Daily revenue"},
                {"name": "peak_hours.hour", "type": "integer", "description": "Peak sales hour"},
                {"name": "peak_hours.count", "type": "integer", "description": "Sales count in hour"}
            ],
            "available_aggregations": ["sum", "avg", "min", "max", "count"],
            "available_filters": ["name", "category", "type", "total_orders", "total_quantity", "total_revenue"]
        },
        {
            "id": "reservations",
            "name": "Reservation Data",
            "description": "Customer reservations and status",
            "last_updated": datetime.now(),
            "record_count": db.reservations.count_documents({}),
            "fields": [
                {"name": "customer_name", "type": "string", "description": "Customer name"},
                {"name": "party_size", "type": "integer", "description": "Party size"},
                {"name": "reservation_date", "type": "datetime", "description": "Reservation date/time"},
                {"name": "status", "type": "string", "description": "Reservation status"},
                {"name": "expected_duration_minutes", "type": "integer", "description": "Expected duration"},
                {"name": "special_requests", "type": "string", "description": "Special requests"},
                {"name": "table_ids", "type": "array", "description": "Assigned table IDs"},
                {"name": "check_in_time", "type": "datetime", "description": "Check-in time"},
                {"name": "completion_time", "type": "datetime", "description": "Completion time"},
            ],
            "available_aggregations": ["sum", "avg", "min", "max", "count"],
            "available_filters": ["customer_name", "party_size", "reservation_date", "status"]
        },
        {
            "id": "tables",
            "name": "Table Data",
            "description": "Restaurant tables and occupancy",
            "last_updated": datetime.now(),
            "record_count": db.tables.count_documents({}),
            "fields": [
                {"name": "table_number", "type": "integer", "description": "Table number"},
                {"name": "capacity", "type": "integer", "description": "Table capacity"},
                {"name": "section", "type": "string", "description": "Restaurant section"},
                {"name": "status", "type": "string", "description": "Table status"},
                {"name": "customer_count", "type": "integer", "description": "Current customer count"},
                {"name": "occupied_since", "type": "datetime", "description": "Occupied since time"},
                {"name": "floor_id", "type": "string", "description": "Floor ID"},
            ],
            "available_aggregations": ["sum", "avg", "min", "max", "count"],
            "available_filters": ["table_number", "capacity", "section", "status"]
        }
    ]
    
    return datasets

def get_dataset(dataset_id: str) -> Optional[DatasetResponse]:
    """Get metadata for a specific dataset"""
    datasets = get_datasets()
    for dataset in datasets:
        if dataset["id"] == dataset_id:
            return dataset
    return None

# ======== Query Services ========

def execute_query(query: QueryRequest) -> QueryResponse:
    """Execute an analytics query based on the request"""
    try:
        # Try to get cached result
        if redis_connected:
            cache_key = f"query:{hash(frozenset(query.dict().items()))}"
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
        
        # Get the appropriate collection
        collection = get_collection_for_dataset(query.dataset_id)
        if not collection:
            raise ValueError(f"Dataset not found: {query.dataset_id}")
        
        # Build the aggregation pipeline
        pipeline = build_aggregation_pipeline(query)
        
        # Execute the query
        result = list(collection.aggregate(pipeline))
        
        # Format the result
        response = {
            "data": result,
            "count": len(result),
            "query": query.dict()
        }
        
        # Cache the result
        if redis_connected:
            redis_client.setex(
                cache_key,
                CACHE_TTL,
                json.dumps(response, default=str)
            )
        
        return response
    
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise ValueError(f"Query execution failed: {str(e)}")

def get_collection_for_dataset(dataset_id: str) -> Optional[Collection]:
    """Get the MongoDB collection for a dataset"""
    dataset_to_collection = {
        "bills": db.bills,
        "customer_order_history": db.customer_order_history,
        "item_analytics": db.item_analytics,
        "reservations": db.reservations,
        "tables": db.tables
    }
    print(444)
    print(dataset_to_collection.get(dataset_id))
    
    return dataset_to_collection.get(dataset_id)

def build_aggregation_pipeline(query: QueryRequest) -> List[Dict]:
    """Build MongoDB aggregation pipeline from query request"""
    pipeline = []
    
    # Add match stage if filters exist
    if query.filters:
        match_conditions = {}
        for filter_condition in query.filters:
            field = filter_condition.field
            operator = filter_condition.operator
            value = filter_condition.value
            
            # Convert operators to MongoDB syntax
            if operator == "eq":
                match_conditions[field] = value
            elif operator == "gt":
                match_conditions[field] = {"$gt": value}
            elif operator == "gte":
                match_conditions[field] = {"$gte": value}
            elif operator == "lt":
                match_conditions[field] = {"$lt": value}
            elif operator == "lte":
                match_conditions[field] = {"$lte": value}
            elif operator == "in":
                match_conditions[field] = {"$in": value}
            elif operator == "contains":
                match_conditions[field] = {"$regex": value, "$options": "i"}
        
        pipeline.append({"$match": match_conditions})
    
    # Build group stage
    group_stage = {"_id": {}}
    for dimension in query.dimensions:
        field = dimension.field
        group_stage["_id"][field.replace(".", "_")] = f"${field}"
    
    # Add measures to group stage
    for measure in query.measures:
        field = measure.field
        aggregation = measure.aggregation
        
        if aggregation == "sum":
            group_stage[f"{field}_{aggregation}"] = {"$sum": f"${field}"}
        elif aggregation == "avg":
            group_stage[f"{field}_{aggregation}"] = {"$avg": f"${field}"}
        elif aggregation == "min":
            group_stage[f"{field}_{aggregation}"] = {"$min": f"${field}"}
        elif aggregation == "max":
            group_stage[f"{field}_{aggregation}"] = {"$max": f"${field}"}
        elif aggregation == "count":
            group_stage[f"{field}_{aggregation}"] = {"$sum": 1}
    
    # If we have dimensions or measures, add the group stage
    if query.dimensions or query.measures:
        pipeline.append({"$group": group_stage})
    
    # Add sort stage if order_by exists
    if query.order_by:
        sort_stage = {}
        for order in query.order_by:
            field = order.field
            direction = -1 if order.direction == "desc" else 1
            sort_stage[field] = direction
        
        pipeline.append({"$sort": sort_stage})
    
    # Add limit stage if limit exists
    if query.limit:
        pipeline.append({"$limit": query.limit})
    
    # Add project stage to flatten the response
    project_stage = {}
    if query.dimensions:
        for dimension in query.dimensions:
            field = dimension.field
            project_stage[field.replace(".", "_")] = f"$_id.{field.replace('.', '_')}"
    
    if query.measures:
        for measure in query.measures:
            field = measure.field
            aggregation = measure.aggregation
            project_stage[f"{field}_{aggregation}"] = 1
    
    if project_stage:
        pipeline.append({"$project": project_stage})
    
    return pipeline

def generate_insights(dataset_id: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, 
                      dimensions: Optional[List[str]] = None) -> Dict:
    """Generate automated insights from dataset"""
    try:
        # This is a simplified version - a real implementation would be more sophisticated
        collection = get_collection_for_dataset(dataset_id)
        if not collection:
            raise ValueError(f"Dataset not found: {dataset_id}")
        
        insights = {"dataset_id": dataset_id, "insights": []}
        
        # Example insights based on dataset
        if dataset_id == "bills":
            # Total sales
            total_sales = collection.aggregate([
                {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
            ])
            total_sales_result = next(total_sales, {"total": 0})
            insights["insights"].append({
                "type": "metric",
                "name": "Total Sales",
                "value": total_sales_result["total"]
            })
            
            # Sales by day
            sales_by_day = collection.aggregate([
                {"$group": {"_id": "$date", "total": {"$sum": "$total_amount"}}},
                {"$sort": {"_id": 1}},
                {"$limit": 7}
            ])
            insights["insights"].append({
                "type": "trend",
                "name": "Sales Trend",
                "data": list(sales_by_day)
            })
            
        elif dataset_id == "customer_order_history":
            # Customer count
            customer_count = collection.count_documents({})
            insights["insights"].append({
                "type": "metric",
                "name": "Total Customers",
                "value": customer_count
            })
            
            # Top customers
            top_customers = collection.aggregate([
                {"$sort": {"total_spent": -1}},
                {"$limit": 5},
                {"$project": {"_id": 0, "name": 1, "total_spent": 1, "total_visits": 1}}
            ])
            insights["insights"].append({
                "type": "ranking",
                "name": "Top Customers",
                "data": list(top_customers)
            })
            
        elif dataset_id == "item_analytics":
            # Top menu items
            top_items = collection.aggregate([
                {"$sort": {"total_revenue": -1}},
                {"$limit": 5},
                {"$project": {"_id": 0, "name": 1, "total_revenue": 1, "total_quantity": 1}}
            ])
            insights["insights"].append({
                "type": "ranking",
                "name": "Top Menu Items",
                "data": list(top_items)
            })
            
            # Sales by category
            sales_by_category = collection.aggregate([
                {"$group": {"_id": "$category", "total": {"$sum": "$total_revenue"}}},
                {"$sort": {"total": -1}}
            ])
            insights["insights"].append({
                "type": "breakdown",
                "name": "Sales by Category",
                "data": list(sales_by_category)
            })
        
        return insights
    
    except Exception as e:
        logger.error(f"Insight generation error: {str(e)}")
        raise ValueError(f"Failed to generate insights: {str(e)}")

# ======== Dashboard Services ========

def get_all_dashboards(search: Optional[str] = None, limit: int = 100) -> List[DashboardResponse]:
    """Get all dashboards with optional search"""
    query = {}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    dashboards = list(db.dashboards.find(query).limit(limit))
    return [format_dashboard(dashboard) for dashboard in dashboards]

# def get_dashboard(dashboard_id: str) -> Optional[DashboardResponse]:
#     """Get a specific dashboard by ID"""
#     try:
#         dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
#         if dashboard:
#             # Update last accessed time
#             db.dashboards.update_one(
#                 {"_id": ObjectId(dashboard_id)},
#                 {"$set": {"last_accessed": datetime.now()}}
#             )
#             return format_dashboard(dashboard)
#         return None
#     except Exception as e:
#         logger.error(f"Error getting dashboard {dashboard_id}: {str(e)}")
#         return None


# Modify existing get_dashboard function
def get_dashboard(dashboard_id: str) -> Optional[DashboardResponse]:
    """Get a dashboard by ID with support for custom IDs"""
    try:
        if dashboard_id.startswith("dashboard-"):
            dashboard = db.dashboards.find_one({"custom_id": dashboard_id})
            if dashboard:
                # Found in database, format and return
                result = format_dashboard(dashboard)
                # Ensure we use the custom_id as the ID
                result["id"] = dashboard_id
                return result
                
            # Only return mock if not found in database
            return {
                "id": dashboard_id,
                "name": f"Dashboard {dashboard_id}",
                "description": "Mock dashboard for development",
                "items": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_favorite": False,
                "is_template": False,
                "tags": [],
                "last_accessed": datetime.now(),
                "settings": {}
            }
            
        # Normal case - use MongoDB ObjectId
        query = {"_id": ObjectId(dashboard_id)}
        dashboard = db.dashboards.find_one(query)

        if not dashboard:
            return None
            
        # Format response
        # return {
        #     "id": str(dashboard["_id"]),
        #     "name": dashboard.get("name", "Untitled Dashboard"),
        #     "description": dashboard.get("description", ""),
        #     "items": dashboard.get("items", []),
        #     "created_at": dashboard.get("created_at", datetime.now()),
        #     "updated_at": dashboard.get("updated_at", datetime.now()),
        #     "is_favorite": dashboard.get("is_favorite", False),
        #     "is_template": dashboard.get("is_template", False),
        #     "tags": dashboard.get("tags", []),
        #     "last_accessed": dashboard.get("last_accessed", datetime.now()),
        #     "settings": dashboard.get("settings", {})
        # }

        return format_dashboard(dashboard)
    except Exception as e:
        print(f"Error getting dashboard {dashboard_id}: {str(e)}")
        return None

# def create_dashboard(dashboard: DashboardCreate) -> DashboardResponse:
#     """Create a new dashboard"""
#     dashboard_dict = dashboard.dict()
#     dashboard_dict["created_at"] = datetime.now()
#     dashboard_dict["updated_at"] = datetime.now()
#     dashboard_dict["last_accessed"] = datetime.now()
    
#     result = db.dashboards.insert_one(dashboard_dict)
#     return get_dashboard(str(result.inserted_id))




def create_dashboard(dashboard: DashboardCreate) -> DashboardResponse:
    """Create a new dashboard"""
    dashboard_dict = dashboard.dict()
    dashboard_dict["created_at"] = datetime.now()
    dashboard_dict["updated_at"] = datetime.now()
    dashboard_dict["last_accessed"] = datetime.now()
    
    # Handle custom ID properly
    custom_id = None
    if "id" in dashboard_dict and dashboard_dict["id"] and isinstance(dashboard_dict["id"], str):
        custom_id = dashboard_dict["id"]
        # Store the custom ID in a separate field
        dashboard_dict["custom_id"] = custom_id
        # Remove id to let MongoDB generate an _id
        del dashboard_dict["id"]
    print('dashboard_dict',dashboard_dict)
    
    # Insert the dashboard into the database
    result = db.dashboards.insert_one(dashboard_dict)
    print('result',result)
    # Return with the custom ID if provided, otherwise use MongoDB ID
    if custom_id:
        return get_dashboard(custom_id)
    else:
        return get_dashboard(str(result.inserted_id))





def update_dashboard(dashboard_id: str, dashboard: DashboardUpdate) -> Optional[DashboardResponse]:
    """Update an existing dashboard"""
    try:
        # For custom dashboard IDs with "dashboard-" prefix
        if dashboard_id.startswith("dashboard-"):
            update_data = dashboard.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.now()
            
            # Try to update by custom_id
            result = db.dashboards.update_one(
                {"custom_id": dashboard_id},
                {"$set": update_data}
            )
            
            # If the dashboard with this custom_id exists, update it
            if result.matched_count > 0:
                return get_dashboard(dashboard_id)
                
            # If dashboard doesn't exist with this custom_id, create it
            dashboard_dict = update_data.copy()
            dashboard_dict["custom_id"] = dashboard_id
            dashboard_dict["created_at"] = datetime.now()
            dashboard_dict["last_accessed"] = datetime.now()
            
            db.dashboards.insert_one(dashboard_dict)
            return get_dashboard(dashboard_id)
            
        # Normal case - try MongoDB ObjectId
        update_data = dashboard.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        result = db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return get_dashboard(dashboard_id)
        return None
    except Exception as e:
        logger.error(f"Error updating dashboard {dashboard_id}: {str(e)}")
        return None

def delete_dashboard(dashboard_id: str) -> bool:
    """Delete a dashboard"""
    try:
        result = db.dashboards.delete_one({"_id": ObjectId(dashboard_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting dashboard {dashboard_id}: {str(e)}")
        return False

def toggle_dashboard_favorite(dashboard_id: str) -> Optional[DashboardResponse]:
    """Toggle favorite status for a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
        
        is_favorite = dashboard.get("is_favorite", False)
        
        db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {"$set": {"is_favorite": not is_favorite, "updated_at": datetime.now()}}
        )
        
        return get_dashboard(dashboard_id)
    except Exception as e:
        logger.error(f"Error toggling favorite for dashboard {dashboard_id}: {str(e)}")
        return None

def get_recent_dashboards(limit: int = 5) -> List[DashboardResponse]:
    """Get recently accessed dashboards"""
    dashboards = list(db.dashboards.find().sort("last_accessed", -1).limit(limit))
    return [format_dashboard(dashboard) for dashboard in dashboards]

def get_favorite_dashboards(search: Optional[str] = None, limit: int = 100) -> List[DashboardResponse]:
    """Get favorite dashboards"""
    query = {"is_favorite": True}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    dashboards = list(db.dashboards.find(query).limit(limit))
    return [format_dashboard(dashboard) for dashboard in dashboards]

def format_dashboard(dashboard: Dict) -> DashboardResponse:
    """Format dashboard for API response"""
    dashboard["id"] = str(dashboard["_id"])
    del dashboard["_id"]
    return dashboard

# ======== Chart Services ========

def get_all_charts() -> List[ChartResponse]:
    """Get all chart configurations"""
    charts = list(db.charts.find())
    return [format_chart(chart) for chart in charts]

def get_chart(chart_id: str) -> Optional[ChartResponse]:
    """Get a specific chart configuration"""
    try:
        chart = db.charts.find_one({"_id": ObjectId(chart_id)})
        if chart:
            return format_chart(chart)
        return None
    except Exception as e:
        logger.error(f"Error getting chart {chart_id}: {str(e)}")
        return None

def create_chart(chart: ChartCreate) -> ChartResponse:
    """Create a new chart configuration"""
    chart_dict = chart.dict()
    chart_dict["created_at"] = datetime.now()
    chart_dict["updated_at"] = datetime.now()
    
    result = db.charts.insert_one(chart_dict)
    return get_chart(str(result.inserted_id))

def update_chart(chart_id: str, chart: ChartUpdate) -> Optional[ChartResponse]:
    """Update an existing chart configuration"""
    try:
        update_data = chart.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        result = db.charts.update_one(
            {"_id": ObjectId(chart_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return get_chart(chart_id)
        return None
    except Exception as e:
        logger.error(f"Error updating chart {chart_id}: {str(e)}")
        return None

def delete_chart(chart_id: str) -> bool:
    """Delete a chart configuration"""
    try:
        result = db.charts.delete_one({"_id": ObjectId(chart_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting chart {chart_id}: {str(e)}")
        return False

def format_chart(chart: Dict) -> ChartResponse:
    """Format chart for API response"""
    chart["id"] = str(chart["_id"])
    del chart["_id"]
    return chart

# Helper function to generate exports in background
def generate_export_in_background(job_id: str, query: QueryRequest, format: str):
    """Generate export file in background"""
    try:
        # Execute the query
        result = execute_query(query)
        
        # Generate export file based on format
        if format == "csv":
            # CSV export logic
            pass
        elif format == "excel":
            # Excel export logic
            pass
        elif format == "pdf":
            # PDF export logic
            pass
        elif format == "json":
            # JSON export logic
            pass
        
        # Update job status in Redis
        if redis_connected:
            redis_client.setex(
                f"export_job:{job_id}",
                60 * 60 * 24,  # 24 hour TTL
                json.dumps({"status": "completed", "download_url": f"/api/analytics/downloads/{job_id}.{format}"})
            )
    
    except Exception as e:
        logger.error(f"Export generation error: {str(e)}")
        if redis_connected:
            redis_client.setex(
                f"export_job:{job_id}",
                60 * 60,  # 1 hour TTL
                json.dumps({"status": "failed", "error": str(e)})
            )




# Add these functions to services.py

# ======== Dashboard Templates ========

def get_dashboard_templates() -> List[DashboardResponse]:
    """Get pre-defined dashboard templates"""
    # Query dashboards with is_template=True
    templates = list(db.dashboards.find({"is_template": True}))
    return [format_dashboard(template) for template in templates]

# ======== Default Dashboard Management ========

def set_default_dashboard(dashboard_id: str) -> bool:
    """Set a dashboard as the default dashboard"""
    try:
        # Validate dashboard exists
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return False
        
        # Clear any existing default dashboards
        db.user_preferences.update_one(
            {"user_id": "current_user"},  # Replace with actual user ID
            {"$set": {"default_dashboard_id": None}},
            upsert=True
        )
        
        # Set new default dashboard
        result = db.user_preferences.update_one(
            {"user_id": "current_user"},  # Replace with actual user ID
            {"$set": {"default_dashboard_id": dashboard_id}}
        )
        
        return True
    except Exception as e:
        logger.error(f"Error setting default dashboard {dashboard_id}: {str(e)}")
        return False
    

import logging
logger = logging.getLogger(__name__)

def is_db_connected():
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")
        return False

# def get_default_dashboard() -> Optional[DashboardResponse]:
#     """Get the user's default dashboard"""
#     try:

#         if not is_db_connected():
#             # Return mock default dashboard
#             return {
#                 "id": "default-dashboard-id",
#                 "name": "Default Dashboard (Mock)",
#                 "description": "This is a mock default dashboard",
#                 "items": [],
#                 "created_at": datetime.now(),
#                 "updated_at": datetime.now(),
#                 "is_favorite": True,
#                 "tags": ["default", "mock"]
#             }
#         # Get default dashboard ID from user preferences
#         preferences = db.user_preferences.find_one({"user_id": "current_user"})
#         if not preferences or not preferences.get("default_dashboard_id"):
#             return None
        
#         # Get the dashboard
#         return get_dashboard(preferences["default_dashboard_id"])
#     except Exception as e:
#         logger.error(f"Error getting default dashboard: {str(e)}")
#         return None







# def get_all_customers(search: Optional[str] = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
#     """
#     Get all customer information from the customer_order_history dataset.
#     Supports optional search, pagination, and filtering.
#     """
#     try:
#         # Get the collection for customer_order_history
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         # Build the query
#         query = {}
#         if search:
#             query["name"] = {"$regex": search, "$options": "i"}  # Search by customer name
        
#         # Fetch customer data with optional limit and skip for pagination
#         customers = list(collection.find(query).skip(skip).limit(limit))
        
#         # Convert ObjectId to string for JSON serialization
#         for customer in customers:
#             customer["_id"] = str(customer["_id"])
        
#         return customers
#     except Exception as e:
#         logger.error(f"Error fetching customer data: {str(e)}")
#         raise ValueError(f"Error fetching customer data: {str(e)}")
    
def get_all_customers(search: Optional[str] = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Get all customer information from the customer_order_history dataset.
    Supports optional search, pagination, and filtering.
    """
    try:
        # Get the collection for customer_order_history
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        # Build the query
        query = {}
        if search:
            query["name"] = {"$regex": search, "$options": "i"}  # Search by customer name
        
        # Fetch customer data with optional limit and skip for pagination
        customers = list(collection.find(query).skip(skip).limit(limit))
        
        # Convert ObjectId to string for JSON serialization
        for customer in customers:
            customer["_id"] = str(customer["_id"])
        
        return customers
    except Exception as e:
        logger.error(f"Error fetching customer data: {str(e)}")
        raise ValueError(f"Error fetching customer data: {str(e)}")







def get_default_dashboard() -> Optional[DashboardResponse]:
    """Get the user's default dashboard with all its details and data"""
    try:
        if not is_db_connected():
            # Return mock default dashboard with all details
            return {
                "id": "default-dashboard-id",
                "name": "Default Dashboard (Mock)",
                "description": "This is a mock default dashboard",
                "items": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_favorite": True,
                "tags": ["default", "mock"],
                "settings": {},
                "data": {}  # Mock data
            }
        
        # Get default dashboard ID from user preferences
        preferences = db.user_preferences.find_one({"user_id": "current_user"})
        if not preferences or not preferences.get("default_dashboard_id"):
            return None
        
        # Get the dashboard with all its data
        default_dashboard_id = preferences["default_dashboard_id"]
        return get_dashboard_with_data(default_dashboard_id)
    
    except Exception as e:
        logger.error(f"Error getting default dashboard: {str(e)}")
        return None

# ======== Dashboard Items Management ========

def get_dashboard_items(dashboard_id: str) -> Optional[List[Dict]]:
    """Get all items in a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
        
        return dashboard.get("items", [])
    except Exception as e:
        logger.error(f"Error getting dashboard items {dashboard_id}: {str(e)}")
        return None

def update_dashboard_item(dashboard_id: str, item_id: str, item: Dict) -> Optional[Dict]:
    """Update a specific item in a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
        
        items = dashboard.get("items", [])
        
        # Find and update the item
        updated_items = []
        found = False
        for i in items:
            if i.get("id") == item_id:
                updated_items.append({**i, **item})
                found = True
            else:
                updated_items.append(i)
        
        if not found:
            return None
        
        # Save the updated dashboard
        db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$set": {
                    "items": updated_items,
                    "updated_at": datetime.now()
                }
            }
        )
        
        # Return the updated item
        for i in updated_items:
            if i.get("id") == item_id:
                return i
                
        return None
    except Exception as e:
        logger.error(f"Error updating dashboard item {item_id}: {str(e)}")
        return None

def create_dashboard_item(dashboard_id: str, item: Dict) -> Optional[Dict]:
    """Add a new item to a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
        
        # Generate ID if not provided
        if "id" not in item:
            item["id"] = str(ObjectId())
        
        # Update the dashboard
        db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$push": {"items": item},
                "$set": {"updated_at": datetime.now()}
            }
        )
        
        return item
    except Exception as e:
        logger.error(f"Error creating dashboard item: {str(e)}")
        return None

def delete_dashboard_item(dashboard_id: str, item_id: str) -> bool:
    """Delete an item from a dashboard"""
    try:
        result = db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {
                "$pull": {"items": {"id": item_id}},
                "$set": {"updated_at": datetime.now()}
            }
        )
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error deleting dashboard item {item_id}: {str(e)}")
        return False

# ======== Editing State Management ========

def set_dashboard_editing_state(dashboard_id: str, is_editing: bool) -> bool:
    """Set dashboard editing state"""
    try:
        # Store editing state in Redis
        if redis_connected:
            key = f"dashboard:{dashboard_id}:editing"
            
            if is_editing:
                # Set editing state with TTL
                redis_client.setex(
                    key,
                    60 * 15,  # 15 minutes TTL
                    "true"
                )
            else:
                # Clear editing state
                redis_client.delete(key)
                
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error setting dashboard editing state {dashboard_id}: {str(e)}")
        return False

# ======== Dashboard Data Loading ========

# def get_dashboard_with_data(dashboard_id: str) -> Optional[Dict]:
#     """Get a dashboard with all its chart data preloaded"""
#     try:
#         dashboard = get_dashboard(dashboard_id)
#         if not dashboard:
#             return None
        
#         # Process each item to include data
#         for item in dashboard.get("items", []):
#             if item.get("type") == "chart" and item.get("config"):
#                 # Get chart data
#                 config = item.get("config", {})
                
#                 # Create a query from the chart configuration
#                 try:
#                     query = QueryRequest(
#                         dataset_id=config.get("data_source", {}).get("id"),
#                         dimensions=config.get("dimensions", []),
#                         measures=config.get("measures", []),
#                         filters=config.get("filters", []),
#                         limit=config.get("limit", 1000)
#                     )
                    
#                     # Execute the query
#                     result = execute_query(query)
                    
#                     # Add data to the item
#                     item["data"] = result.get("data", [])
#                 except Exception as e:
#                     logger.error(f"Error getting data for chart in dashboard {dashboard_id}: {str(e)}")
#                     item["data"] = []
#                     item["error"] = str(e)
        
#         return dashboard
#     except Exception as e:
#         logger.error(f"Error getting dashboard with data {dashboard_id}: {str(e)}")
#         return None
    
# ======== Dashboard Data Loading ========

def get_dashboard_with_data(dashboard_id: str) -> Optional[Dict]:
    """Get a dashboard with all its chart data preloaded"""
    try:
        # Handle special dashboard IDs
        if dashboard_id == "default":
            dashboard = get_default_dashboard()
        elif dashboard_id == "default-dashboard-id" or dashboard_id.startswith("dashboard-"):
            # Return mock data for special IDs
            return {
                "id": dashboard_id,
                "name": f"Dashboard {dashboard_id}",
                "description": "Mock dashboard with data for development",
                "items": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_favorite": False,
                "data": {}  # Mock data
            }
        else:
            # Check database connection for regular IDs
            if not is_db_connected():
                logger.warning(f"MongoDB not connected, returning mock data for dashboard {dashboard_id}")
                return {
                    "id": dashboard_id,
                    "name": f"Dashboard {dashboard_id} (Mock)",
                    "description": "Mock dashboard - Database unavailable",
                    "items": [],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "is_favorite": False,
                    "data": {}
                }
            
            # Validate ObjectId format
            try:
                # Just validate - don't store
                object_id = ObjectId(dashboard_id)
            except InvalidId:
                logger.error(f"Invalid ObjectId format: {dashboard_id}")
                return None
                
            dashboard = get_dashboard(dashboard_id)
        
        if not dashboard:
            return None
        
        # Process each item to include data
        for item in dashboard.get("items", []):
            if item.get("type") == "chart" and item.get("config"):
                # Get chart data
                config = item.get("config", {})
                
                # Create a query from the chart configuration
                try:
                    query = QueryRequest(
                        dataset_id=config.get("data_source", {}).get("id"),
                        dimensions=config.get("dimensions", []),
                        measures=config.get("measures", []),
                        filters=config.get("filters", []),
                        limit=config.get("limit", 1000)
                    )
                    
                    # Execute the query
                    result = execute_query(query)
                    
                    # Add data to the item
                    item["data"] = result.get("data", [])
                except Exception as e:
                    logger.error(f"Error getting data for chart in dashboard {dashboard_id}: {str(e)}")
                    item["data"] = []
                    item["error"] = str(e)
        
        return dashboard
    except Exception as e:
        logger.error(f"Error getting dashboard with data {dashboard_id}: {str(e)}")
        return None

# ======== Undo/Redo Functionality ========

def undo_dashboard_change(dashboard_id: str) -> Optional[Dict]:
    """Undo the last change to a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
            
        history = dashboard.get("version_history", [])
        
        if not history or len(history) < 2:  # Need at least 2 versions to undo
            return None
            
        # Get the previous version
        current_version = history[-1]
        previous_version = history[-2]
        
        # Apply the previous version state
        update_data = previous_version.get("snapshot", {})
        update_data["version_history"] = history[:-1]  # Remove the current version
        update_data["updated_at"] = datetime.now()
        
        db.dashboards.update_one(
            {"_id": ObjectId(dashboard_id)},
            {"$set": update_data}
        )
        
        return get_dashboard(dashboard_id)
    except Exception as e:
        logger.error(f"Error undoing dashboard change {dashboard_id}: {str(e)}")
        return None

def redo_dashboard_change(dashboard_id: str) -> Optional[Dict]:
    """Redo a previously undone change to a dashboard"""
    try:
        # To implement redo, we need to store undone changes
        # For simplicity, we could use Redis to temporarily store them
        if redis_connected:
            redo_key = f"dashboard:{dashboard_id}:redo"
            redo_data = redis_client.get(redo_key)
            
            if not redo_data:
                return None
                
            redo_version = json.loads(redo_data)
            
            # Apply the redo version
            dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
            if not dashboard:
                return None
                
            # Get current history and append redo version
            history = dashboard.get("version_history", [])
            history.append(redo_version)
            
            # Apply the redo version state
            update_data = redo_version.get("snapshot", {})
            update_data["version_history"] = history
            update_data["updated_at"] = datetime.now()
            
            db.dashboards.update_one(
                {"_id": ObjectId(dashboard_id)},
                {"$set": update_data}
            )
            
            # Clear the redo data
            redis_client.delete(redo_key)
            
            return get_dashboard(dashboard_id)
        
        return None
    except Exception as e:
        logger.error(f"Error redoing dashboard change {dashboard_id}: {str(e)}")
        return None

def get_dashboard_history(dashboard_id: str) -> Optional[List[Dict]]:
    """Get change history for a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
            
        history = dashboard.get("version_history", [])
        
        # Return simplified history (without full snapshots)
        return [
            {
                "timestamp": h.get("timestamp"),
                "user": h.get("user"),
                "action": h.get("action", "update")
            }
            for h in history
        ]
    except Exception as e:
        logger.error(f"Error getting dashboard history {dashboard_id}: {str(e)}")
        return None

# ======== Permission Checking ========

def get_user_dashboard_permissions(dashboard_id: str) -> Optional[Dict]:
    """Get the current user's permissions for a dashboard"""
    try:
        dashboard = db.dashboards.find_one({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None
            
        # In a real app, check permissions against user roles
        # For now, simple implementation
        return {
            "can_view": True,
            "can_edit": True,
            "can_delete": True,
            "can_share": True
        }
    except Exception as e:
        logger.error(f"Error getting dashboard permissions {dashboard_id}: {str(e)}")
        return None

# ======== Selected Items Management ========

def set_dashboard_selected_items(dashboard_id: str, item_ids: List[str]) -> bool:
    """Set the selected items for a dashboard"""
    try:
        if redis_connected:
            key = f"dashboard:{dashboard_id}:selected_items"
            redis_client.setex(
                key,
                60 * 15,  # 15 minutes TTL
                json.dumps(item_ids)
            )
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting selected dashboard items {dashboard_id}: {str(e)}")
        return False

def get_dashboard_selected_items(dashboard_id: str) -> Optional[List[str]]:
    """Get the selected items for a dashboard"""
    try:
        if redis_connected:
            key = f"dashboard:{dashboard_id}:selected_items"
            selected_items = redis_client.get(key)
            
            if selected_items:
                return json.loads(selected_items)
            return []
        return []
    except Exception as e:
        logger.error(f"Error getting selected dashboard items {dashboard_id}: {str(e)}")
        return None

def set_dashboard_focused_item(dashboard_id: str, item_id: Optional[str]) -> bool:
    """Set the focused item for a dashboard"""
    try:
        if redis_connected:
            key = f"dashboard:{dashboard_id}:focused_item"
            
            if item_id:
                redis_client.setex(
                    key,
                    60 * 15,  # 15 minutes TTL
                    item_id
                )
            else:
                redis_client.delete(key)
                
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting focused dashboard item {dashboard_id}: {str(e)}")
        return False

def get_dashboard_focused_item(dashboard_id: str) -> Optional[str]:
    """Get the focused item for a dashboard"""
    try:
        if redis_connected:
            key = f"dashboard:{dashboard_id}:focused_item"
            focused_item = redis_client.get(key)
            
            if focused_item:
                return focused_item.decode('utf-8')
            return None
        return None
    except Exception as e:
        logger.error(f"Error getting focused dashboard item {dashboard_id}: {str(e)}")
        return None
    


# Add this function in routes.py (outside any route)
def handle_dashboard_id(dashboard_id: str):
    """Common handler for dashboard ID validation and special cases"""
    # Handle "default" dashboard
    if dashboard_id == "default":
        dashboard = get_default_dashboard()
        if not dashboard:
            raise HTTPException(status_code=404, detail="No default dashboard found")
        return dashboard
    
    # Handle custom dashboard IDs with prefix
    if dashboard_id.startswith("dashboard-"):
        # For now, return a mock response for custom IDs
        return {
            "id": dashboard_id,
            "name": f"Dashboard {dashboard_id}",
            "description": "Mock dashboard for development",
            "items": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "is_favorite": False
        }
    
    # Normal case - MongoDB ObjectId
    try:
        # Validate it's a proper ObjectId
        object_id = ObjectId(dashboard_id)
        dashboard = get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        return dashboard
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")
    


# Add this utility function
def transform_to_chart_data(data, chart_type="bar"):
    """Transform MongoDB data into Chart.js format"""
    if not data:
        return {
            "labels": [],
            "datasets": [{
                "label": "No Data",
                "data": [],
                "backgroundColor": "#4f46e5"
            }]
        }
    
    # Extract all unique dimension values to use as labels
    labels = []
    series_data = {}
    
    for item in data:
        # Get first non-measure field as dimension (usually _id or category)
        dimension_field = next((k for k in item.keys() if not k.endswith("_sum") and 
                               not k.endswith("_avg") and not k.endswith("_count") and
                               not k.endswith("_min") and not k.endswith("_max")), None)
        
        if dimension_field:
            dimension_value = item[dimension_field]
            
            # Add to labels if not already there
            if dimension_value not in labels:
                labels.append(dimension_value)
            
            # Process measures (fields that end with aggregation suffix)
            for field, value in item.items():
                if field != dimension_field:
                    if field not in series_data:
                        series_data[field] = []
                    
                    # Add value to corresponding position
                    position = labels.index(dimension_value)
                    
                    # Fill with zeros for missing positions
                    while len(series_data[field]) < position:
                        series_data[field].append(0)
                    
                    # Add the value
                    series_data[field].append(value)
    
    # Build datasets for Chart.js
    datasets = []
    colors = ["#4f46e5", "#16a34a", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4"]
    
    for i, (field, values) in enumerate(series_data.items()):
        # Ensure all series have same length as labels
        while len(values) < len(labels):
            values.append(0)
            
        datasets.append({
            "label": field.replace("_sum", "").replace("_avg", " (avg)").replace("_count", " (count)"),
            "data": values,
            "backgroundColor": colors[i % len(colors)]
        })
    
    return {
        "labels": labels,
        "datasets": datasets
    }






# Add these imports if not already present
from pymongo import MongoClient
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any, Optional
import re

# Add these service functions

def get_data_source_fields(data_source: str) -> Dict[str, Any]:
    """
    Get available fields for a specific data source with metadata
    """
    # Define field mappings for each data source
    field_mappings = {
        "bills": {
            "dimensions": [
                {"id": "date", "name": "Date", "type": "date"},
                {"id": "time", "name": "Time", "type": "string"},
                {"id": "customer.name", "name": "Customer Name", "type": "string"},
                {"id": "table_number", "name": "Table Number", "type": "number"},
                {"id": "payment.status", "name": "Payment Status", "type": "string"},
                {"id": "payment.methods.method", "name": "Payment Method", "type": "string"},
                {"id": "employee_id", "name": "Server", "type": "string"},
                {"id": "items.category", "name": "Item Category", "type": "string"},
                {"id": "items.name", "name": "Item Name", "type": "string"},
                {"id": "feedback.overall_rating", "name": "Rating", "type": "number"},
            ],
            "measures": [
                {"id": "total_amount", "name": "Total Amount", "type": "number", "aggregations": ["sum", "avg", "min", "max"]},
                {"id": "subtotal", "name": "Subtotal", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "total_discount", "name": "Total Discount", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "items.quantity", "name": "Item Quantity", "type": "number", "aggregations": ["sum", "avg", "count"]},
                {"id": "items.total_price", "name": "Item Price", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "payment.paid_amount", "name": "Paid Amount", "type": "number", "aggregations": ["sum", "avg"]}
            ]
        },
        "customer_order_history": {
            "dimensions": [
                {"id": "name", "name": "Customer Name", "type": "string"},
                {"id": "first_visit", "name": "First Visit Date", "type": "date"},
                {"id": "last_visit", "name": "Last Visit Date", "type": "date"},
                {"id": "orders.date", "name": "Order Date", "type": "date"},
                {"id": "orders.table_number", "name": "Table Number", "type": "number"},
                {"id": "favorite_items.name", "name": "Favorite Item", "type": "string"}
            ],
            "measures": [
                {"id": "total_visits", "name": "Total Visits", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "total_spent", "name": "Total Spent", "type": "number", "aggregations": ["sum", "avg", "min", "max"]},
                {"id": "orders.amount", "name": "Order Amount", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "orders.items_count", "name": "Items Count", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "favorite_items.count", "name": "Item Order Count", "type": "number", "aggregations": ["sum", "avg"]}
            ]
        },
        "item_analytics": {
            "dimensions": [
                {"id": "name", "name": "Item Name", "type": "string"},
                {"id": "category", "name": "Category", "type": "string"},
                {"id": "type", "name": "Type", "type": "string"},
                {"id": "daily_sales.date", "name": "Sale Date", "type": "date"},
                {"id": "monthly_sales.month", "name": "Sale Month", "type": "string"},
                {"id": "peak_hours.hour", "name": "Hour of Day", "type": "number"},
                {"id": "addon_popularity.name", "name": "Addon Name", "type": "string"},
                {"id": "size_distribution.size", "name": "Size", "type": "string"}
            ],
            "measures": [
                {"id": "total_orders", "name": "Total Orders", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "total_quantity", "name": "Total Quantity", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "total_revenue", "name": "Total Revenue", "type": "number", "aggregations": ["sum", "avg", "min", "max"]},
                {"id": "daily_sales.quantity", "name": "Daily Quantity", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "daily_sales.revenue", "name": "Daily Revenue", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "monthly_sales.quantity", "name": "Monthly Quantity", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "monthly_sales.revenue", "name": "Monthly Revenue", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "peak_hours.count", "name": "Hour Count", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "addon_popularity.total_quantity", "name": "Addon Quantity", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "addon_popularity.revenue_contribution", "name": "Addon Revenue", "type": "number", "aggregations": ["sum", "avg"]},
                {"id": "size_distribution.count", "name": "Size Count", "type": "number", "aggregations": ["sum", "avg"]}
            ]
        }
    }
    
    # Return fields for the requested data source
    if data_source in field_mappings:
        return field_mappings[data_source]
    else:
        return None
    



def get_sample_data_for_chart_type(chart_type: str, fields: Dict = None) -> Dict:
    """Return sample data based on chart type"""
    if chart_type in ["bar", "line", "area"]:
        return {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
            "datasets": [{
                "label": "Sample Data",
                "data": [65, 59, 80, 81, 56],
                "backgroundColor": "#4f46e5"
            }]
        }
    elif chart_type in ["pie", "doughnut"]:
        return {
            "labels": ["Red", "Blue", "Yellow", "Green", "Purple"],
            "datasets": [{
                "data": [12, 19, 3, 5, 2],
                "backgroundColor": ["#f87171", "#60a5fa", "#fbbf24", "#4ade80", "#a78bfa"]
            }]
        }
    elif chart_type == "scatter":
        return {
            "datasets": [{
                "label": "Sample Scatter",
                "data": [
                    {"x": 10, "y": 20}, {"x": 15, "y": 10}, 
                    {"x": 20, "y": 30}, {"x": 25, "y": 15}, 
                    {"x": 30, "y": 25}
                ],
                "backgroundColor": "#4f46e5"
            }]
        }
    elif chart_type == "bubble":
        return {
            "datasets": [{
                "label": "Sample Bubble",
                "data": [
                    {"x": 10, "y": 20, "r": 5}, {"x": 15, "y": 10, "r": 8}, 
                    {"x": 20, "y": 30, "r": 12}, {"x": 25, "y": 15, "r": 6}, 
                    {"x": 30, "y": 25, "r": 10}
                ],
                "backgroundColor": "#4f46e5"
            }]
        }
    elif chart_type == "radar":
        return {
            "labels": ["Speed", "Handling", "Comfort", "Safety", "Efficiency"],
            "datasets": [{
                "label": "Car A",
                "data": [80, 70, 85, 90, 75],
                "backgroundColor": "rgba(79, 70, 229, 0.2)",
                "borderColor": "#4f46e5"
            }]
        }
    elif chart_type == "heatmap":
        return {
            "data": {
                "datasets": [{
                    "data": [
                        {"x": "Mon", "y": "Morning", "v": 12},
                        {"x": "Mon", "y": "Afternoon", "v": 8},
                        {"x": "Tue", "y": "Morning", "v": 15},
                        {"x": "Tue", "y": "Afternoon", "v": 20}
                    ]
                }]
            }
        }
    
    elif chart_type == "treemap":
        return {
            "data": {
                "datasets": [{
                    "tree": [
                        {"id": "root", "name": "Root"},
                        {"id": "A", "name": "Category A", "parent": "root", "value": 40},
                        {"id": "B", "name": "Category B", "parent": "root", "value": 30},
                        {"id": "C", "name": "Category C", "parent": "root", "value": 20}
                    ],
                    "key": "value",
                    "groups": ["name"],
                    "spacing": 0.5
                }]
            }
        }
    
    elif chart_type.lower() == "counter":
        return {
            "type": "counter",
            "data": {
                "current": 5280,
                "previous": 4750,
                "percentChange": 11.2,
                "label": "Total Sales"
            }
        }
    # Default sample data for other chart types
    return {
        "labels": ["Sample"],
        "datasets": [{
            "label": f"Sample {chart_type} Data",
            "data": [50],
            "backgroundColor": "#4f46e5"
        }]
    }




def build_filters(filters: List[Dict], time_range: str, data_source: str = None) -> Dict:
    """
    Build MongoDB filters from UI filter configuration and time range
    Parameters:
        filters: List of filter objects from UI
        time_range: String time range selector
        data_source: The collection/data source being queried
    """
    mongo_filters = {}
    
    # Define UI-only parameters that should be excluded from MongoDB query
    ui_only_params = ["compareEnabled", "compareType", "timeRange"]
    
    # Define date field mapping based on data source
    date_field_mapping = {
        "bills": "date",
        "customer_order_history": "orders.date",  # Date is in the orders array
        "item_analytics": "daily_sales.date",     # Date is in the daily_sales array
        "items": "daily_sales.date"               # Alias for item_analytics
    }
    
    # Get the appropriate date field for this data source
    date_field = date_field_mapping.get(data_source, "date")
    
    # Special handling for item_analytics - we can't filter directly on array fields
    # This will be handled in the pipeline construction by unwinding first
    needs_special_pipeline = data_source in ["item_analytics", "items"] and date_field == "daily_sales.date"
    
    # Process time range filter if we don't need special pipeline handling
    if time_range and not needs_special_pipeline:
        now = datetime.now()
        
        if time_range == "today":
            mongo_filters[date_field] = now.strftime("%Y-%m-%d")
        elif time_range == "yesterday":
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            mongo_filters[date_field] = yesterday
        elif time_range == "last7Days":
            start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            mongo_filters[date_field] = {"$gte": start_date}
        elif time_range == "last30Days":
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            mongo_filters[date_field] = {"$gte": start_date}
        elif time_range == "thisMonth":
            start_date = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
            mongo_filters[date_field] = {"$gte": start_date}
        elif time_range == "lastMonth":
            last_month = now.month - 1 if now.month > 1 else 12
            last_month_year = now.year if now.month > 1 else now.year - 1
            start_date = datetime(last_month_year, last_month, 1).strftime("%Y-%m-%d")
            end_date = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
            mongo_filters[date_field] = {"$gte": start_date, "$lt": end_date}
    
    # Store time range for special pipeline handling
    time_range_filter = None
    if time_range and needs_special_pipeline:
        now = datetime.now()
        
        if time_range == "today":
            time_range_filter = now.strftime("%Y-%m-%d")
        elif time_range == "yesterday":
            time_range_filter = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif time_range == "last7Days":
            time_range_filter = {"$gte": (now - timedelta(days=7)).strftime("%Y-%m-%d")}
        elif time_range == "last30Days":
            time_range_filter = {"$gte": (now - timedelta(days=30)).strftime("%Y-%m-%d")}
        elif time_range == "thisMonth":
            time_range_filter = {"$gte": datetime(now.year, now.month, 1).strftime("%Y-%m-%d")}
        elif time_range == "lastMonth":
            last_month = now.month - 1 if now.month > 1 else 12
            last_month_year = now.year if now.month > 1 else now.year - 1
            start_date = datetime(last_month_year, last_month, 1).strftime("%Y-%m-%d")
            end_date = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
            time_range_filter = {"$gte": start_date, "$lt": end_date}
    
    # Process custom filters
    array_filters = {}  # Special handling for array fields
    
    for f in filters:
        if not isinstance(f, dict) or "field" not in f or "operator" not in f or "value" not in f:
            continue
            
        field = f.get("field")
        operator = f.get("operator")
        value = f.get("value")
        
        # Skip UI-only parameters
        if field in ui_only_params:
            continue
            
        # Handle custom date range
        if field == "customDateRange" and isinstance(value, dict):
            start_date = value.get("startDate")
            end_date = value.get("endDate")
            
            if start_date and end_date:
                # Convert ISO strings to date strings
                if isinstance(start_date, str) and "T" in start_date:
                    start_date = start_date.split("T")[0]
                if isinstance(end_date, str) and "T" in end_date:
                    end_date = end_date.split("T")[0]
                
                # For regular collections
                if not needs_special_pipeline:
                    mongo_filters[date_field] = {"$gte": start_date, "$lte": end_date}
                else:
                    # Store for special handling
                    time_range_filter = {"$gte": start_date, "$lte": end_date}
                    
            continue
        
        # Check if this is a field inside an array
        is_array_field = False
        array_field_name = None
        
        # Define which fields are inside arrays for each data source
        array_field_mapping = {
            "bills": {
                "items.": "items",
                "payment.methods.": "payment.methods"
            },
            "customer_order_history": {
                "orders.": "orders",
                "favorite_items.": "favorite_items"
            },
            "item_analytics": {
                "daily_sales.": "daily_sales",
                "monthly_sales.": "monthly_sales",
                "peak_hours.": "peak_hours",
                "size_distribution.": "size_distribution",
                "common_customizations.": "common_customizations",
                "addon_popularity.": "addon_popularity",
                "addon_combinations.": "addon_combinations"
            }
        }
        
        # Check if field is in an array
        if data_source in array_field_mapping:
            for prefix, array_name in array_field_mapping[data_source].items():
                if field.startswith(prefix):
                    is_array_field = True
                    array_field_name = array_name
                    break
        
        # Apply operators based on whether field is in array or not
        filter_value = None
        
        # Map operator to MongoDB operator
        if operator == "eq":
            filter_value = value
        elif operator == "ne":
            filter_value = {"$ne": value}
        elif operator == "gt":
            filter_value = {"$gt": value}
        elif operator == "gte":
            filter_value = {"$gte": value}
        elif operator == "lt":
            filter_value = {"$lt": value}
        elif operator == "lte":
            filter_value = {"$lte": value}
        elif operator == "in":
            filter_value = {"$in": value if isinstance(value, list) else [value]}
        elif operator == "not_in":
            filter_value = {"$nin": value if isinstance(value, list) else [value]}
        elif operator == "contains":
            filter_value = {"$regex": value, "$options": "i"}
        elif operator == "not_contains":
            filter_value = {"$not": {"$regex": value, "$options": "i"}}
        
        # Apply filter
        if is_array_field:
            # For array fields, track separately for pipeline optimization
            if array_field_name not in array_filters:
                array_filters[array_field_name] = {}
            array_filters[array_field_name][field] = filter_value
        else:
            # Normal field
            mongo_filters[field] = filter_value
    
    # Store metadata for pipeline construction
    if time_range_filter or array_filters:
        mongo_filters["__pipeline_metadata__"] = {
            "time_range_filter": time_range_filter,
            "array_filters": array_filters,
            "date_field": date_field,
            "needs_special_pipeline": needs_special_pipeline
        }
    
    return mongo_filters





def build_mongodb_pipeline(data_source: str, dimensions: List, measures: List, 
                          filters: Dict = None, fields: Dict = None, chart_type: str = "bar") -> List[Dict]:
    """Build MongoDB aggregation pipeline with support for enhanced field mappings"""
    pipeline = []

    if not dimensions and fields and 'dimension' in fields:
        dimensions = [fields['dimension']]
    
    if not measures and fields and 'measure' in fields:
        measures = [{'field': fields['measure'], 'aggregation': 'sum'}]
        
    # Special handling for table charts with dimension and measure in fields
    if chart_type == "table" and not dimensions and not measures:
        if fields and 'dimension' in fields:
            dimensions = [fields['dimension']]
        if fields and 'measure' in fields:
            measures = [{'field': fields['measure'], 'aggregation': 'sum'}]
    
    # Extract pipeline metadata if present
    pipeline_metadata = None
    if filters and "__pipeline_metadata__" in filters:
        pipeline_metadata = filters.pop("__pipeline_metadata__")
    
    # For array fields, we need to unwind
    array_fields = {
        "bills": ["items", "payment.methods"],
        "customer_order_history": ["orders", "favorite_items"],
        "item_analytics": ["daily_sales", "monthly_sales", "peak_hours", 
                          "size_distribution", "common_customizations", 
                          "addon_popularity", "addon_combinations"]
    }
    
    # Special handling for item_analytics date filtering
    if pipeline_metadata and pipeline_metadata.get("needs_special_pipeline"):
        # First filter on non-array fields
        if filters:
            pipeline.append({"$match": filters})
        
        # For item_analytics, unwinding daily_sales first is required for date filtering
        if data_source in ["item_analytics", "items"] and pipeline_metadata.get("date_field") == "daily_sales.date":
            pipeline.append({"$unwind": "$daily_sales"})
            
            # Apply date filter if present
            time_range_filter = pipeline_metadata.get("time_range_filter")
            if time_range_filter:
                pipeline.append({"$match": {"daily_sales.date": time_range_filter}})
        
        # Handle other array filters
        array_filters = pipeline_metadata.get("array_filters", {})
        for array_field, field_filters in array_filters.items():
            # Unwind this array
            if array_field not in pipeline_metadata.get("already_unwound", []):
                pipeline.append({"$unwind": f"${array_field}"})
            
            # Apply filters for this array
            pipeline.append({"$match": field_filters})
    else:
        # Standard filtering
        if filters:
            pipeline.append({"$match": filters})
    
    # Process fields to get effective dimensions and measures based on chart type
    effective_dimensions = list(dimensions) if dimensions else []
    effective_measures = list(measures) if measures else []
    
    # Use field mappings if provided
    if fields:
        # Special handling for scatter/bubble charts
        if chart_type in ["scatter", "bubble", "quadrantChart"]:
            # For scatter, both x and y are typically measures
            x_field = fields.get("x")
            y_field = fields.get("y")
            if x_field and x_field not in effective_measures:
                effective_measures.append({"field": x_field, "aggregation": "avg"})
                # Remove from dimensions if it was added there
                effective_dimensions = [d for d in effective_dimensions if d != x_field]
            if y_field and y_field not in effective_measures:
                effective_measures.append({"field": y_field, "aggregation": "avg"})
                # Remove from dimensions if it was added there
                effective_dimensions = [d for d in effective_dimensions if d != y_field]
        
        # Special handling for pie/doughnut charts
        elif chart_type in ["pie", "doughnut"]:
            labels_field = fields.get("labels")
            values_field = fields.get("values")
            if labels_field and labels_field not in effective_dimensions:
                effective_dimensions.append(labels_field)
            if values_field and values_field not in effective_measures:
                effective_measures.append({"field": values_field, "aggregation": "sum"})
        
        # Special handling for treemap
        elif chart_type == "treemap":
            hierarchy_field = fields.get("hierarchy")
            size_field = fields.get("size")
            if hierarchy_field and hierarchy_field not in effective_dimensions:
                effective_dimensions.append(hierarchy_field)
            if size_field and size_field not in effective_measures:
                effective_measures.append({"field": size_field, "aggregation": "sum"})
        
        # Special handling for heatmap
        elif chart_type == "heatmap":
            rows_field = fields.get("rows")
            columns_field = fields.get("columns")
            values_field = fields.get("values")
            if rows_field and rows_field not in effective_dimensions:
                effective_dimensions.append(rows_field)
            if columns_field and columns_field not in effective_dimensions:
                effective_dimensions.append(columns_field)
            if values_field and values_field not in effective_measures:
                effective_measures.append({"field": values_field, "aggregation": "sum"})
    
    # Check if we need to unwind arrays based on dimensions and measures
    if data_source in array_fields:
        for array_field in array_fields[data_source]:
            # Check if any dimension or measure uses this array field
            needs_unwind = False
            for dim in effective_dimensions:
                dim_field = dim if isinstance(dim, str) else dim.get("field")
                if dim_field and dim_field.startswith(array_field + "."):
                    needs_unwind = True
                    break
                    
            if not needs_unwind:
                for measure in effective_measures:
                    measure_field = measure if isinstance(measure, str) else measure.get("field")
                    if measure_field and measure_field.startswith(array_field + "."):
                        needs_unwind = True
                        break
            
            if needs_unwind:
                pipeline.append({"$unwind": f"${array_field}"})
    
    # Prepare group stage
    group_stage = {
        "_id": {} if effective_dimensions else None
    }
    
    # Add dimensions to group _id
    for dim in effective_dimensions:
        dim_field = dim if isinstance(dim, str) else dim.get("field")
        if not dim_field:
            continue
            
        # Handle date formatting
        if dim_field.endswith("_date") or dim_field == "date" or dim_field.endswith(".date"):
            group_stage["_id"][dim_field] = {"$substr": [f"${dim_field}", 0, 10]}  # YYYY-MM-DD format
        else:
            group_stage["_id"][dim_field] = f"${dim_field}"
    
    # Add measures to group with aggregations
    for measure in effective_measures:
        field = measure if isinstance(measure, str) else measure.get("field")
        aggregation = measure.get("aggregation", "sum") if isinstance(measure, dict) else "sum"
        
        if not field:
            continue
            
        # Create field alias based on aggregation
        alias = f"{field.replace('.', '_')}_{aggregation}"
        
        # Add appropriate aggregation
        if aggregation == "sum":
            group_stage[alias] = {"$sum": f"${field}"}
        elif aggregation == "avg":
            group_stage[alias] = {"$avg": f"${field}"}
        elif aggregation == "min":
            group_stage[alias] = {"$min": f"${field}"}
        elif aggregation == "max":
            group_stage[alias] = {"$max": f"${field}"}
        elif aggregation == "count":
            group_stage[alias] = {"$sum": 1}
    
    # Add group stage to pipeline
    pipeline.append({"$group": group_stage})
    
    # Add sort stage if dimensions are specified
    if effective_dimensions:
        dim_field = effective_dimensions[0] if isinstance(effective_dimensions[0], str) else effective_dimensions[0].get("field")
        if dim_field:
            pipeline.append({"$sort": {"_id." + dim_field: 1}})
    


    project_stage = {"$project": {"_id": 0}}

    if effective_dimensions:
        for dim in effective_dimensions:
            dim_field = dim if isinstance(dim, str) else dim.get("field")
            if dim_field:
                if len(group_stage["_id"]) > 1:
                    project_stage["$project"][dim_field] = f"$_id.{dim_field}"
                else:
                    # When there's only one dimension field in _id, extract just that field's value
                    if group_stage["_id"] and dim_field in group_stage["_id"]:
                        project_stage["$project"][dim_field] = f"$_id.{dim_field}"
                    else:
                        # This is a fallback that shouldn't normally be needed
                        project_stage["$project"][dim_field] = "$_id"
    
    # Include all aggregated measures
    for measure in effective_measures:
        field = measure if isinstance(measure, str) else measure.get("field")
        aggregation = measure.get("aggregation", "sum") if isinstance(measure, dict) else "sum"
        if field:
            alias = f"{field.replace('.', '_')}_{aggregation}"
            project_stage["$project"][alias] = 1
    
    pipeline.append(project_stage)
    
    return pipeline



def execute_mongodb_pipeline(data_source: str, pipeline: List[Dict]) -> List[Dict]:
    """
    Execute MongoDB aggregation pipeline on the specified collection
    """
    # Get MongoDB client and database
    try:
 # Replace with your actual database name
        print(f"data_source {data_source} ,{pipeline}")
        # Map data source to collection name
        collection_mapping = {
            "bills": "bills",
            "customer_order_history": "customer_order_history",
            "item_analytics": "item_analytics",
            "items": "item_analytics" 
        }
        
        collection_name = collection_mapping.get(data_source, data_source)
        collection = db[collection_name]
        
        # Execute aggregation
        print(f"[MONGODB] Executing pipeline on {collection_name}: {json.dumps(pipeline)}")
        result = list(collection.aggregate(pipeline))
        print(f"[MONGODB] Query returned {len(result)} documents")
        print(f'[MONGODB] Result: {result}')
                # If the result is empty, return fallback data
        if not result:
            print(f"[MONGODB] Empty result set, using fallback data for {data_source}")
            return _generate_fallback_data(data_source, pipeline)
        
        return result
        
    except Exception as e:
        import traceback
        print(f"[ERROR] MongoDB query error: {str(e)}\n{traceback.format_exc()}")
        return _generate_fallback_data(data_source, pipeline)
    




def transform_for_area_chart(data: List[Dict], dimensions: List, measures: List, 
                           colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for area charts (similar to line but with fill)"""
    line_data = transform_for_line_chart(data, dimensions, measures, colors, fields)
    
    # Update styling for area chart - add fill
    for dataset in line_data["datasets"]:
        dataset["fill"] = True
        dataset["backgroundColor"] = dataset["borderColor"].replace(")", ", 0.2)")
    
    return line_data

def transform_for_scatter_chart(data: List[Dict], dimensions: List, measures: List, 
                              colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for scatter charts"""
    # Get field mappings or use defaults
    x_field = fields.get("x") if fields else (measures[0] if measures else None)
    y_field = fields.get("y") if fields else (measures[1] if len(measures) > 1 else None)
    label_field = fields.get("label") if fields else (dimensions[0] if dimensions else None)
    
    # Extract field names
    x_field_name = x_field if isinstance(x_field, str) else (x_field.get("field") if x_field else None)
    y_field_name = y_field if isinstance(y_field, str) else (y_field.get("field") if y_field else None)
    label_field_name = label_field if isinstance(label_field, str) else (label_field.get("field") if label_field else None)
    
    # Check for required fields
    if not x_field_name or not y_field_name:
        return {
            "datasets": [{
                "label": "Missing x/y configuration",
                "data": [],
                "backgroundColor": "#ef4444"
            }]
        }
    
    # Format x/y field names for data lookup (they include aggregation in MongoDB result)
    x_agg = "avg" if isinstance(x_field, dict) and x_field.get("aggregation") else "sum"
    y_agg = "avg" if isinstance(y_field, dict) and y_field.get("aggregation") else "sum"
    x_lookup = f"{x_field_name.replace('.', '_')}_{x_agg}"
    y_lookup = f"{y_field_name.replace('.', '_')}_{y_agg}"
    
    # Group data by label if provided
    datasets = []
    
    if label_field_name:
        # Group data by label
        grouped_data = {}
        for item in data:
            label = str(item.get(label_field_name, "Unknown"))
            if label not in grouped_data:
                grouped_data[label] = []
            
            # Only add points with both x and y values
            if x_lookup in item and y_lookup in item:
                grouped_data[label].append({
                    "x": item[x_lookup],
                    "y": item[y_lookup]
                })
        
        # Create a dataset for each label
        for idx, (label, points) in enumerate(grouped_data.items()):
            color = colors[idx % len(colors)]
            datasets.append({
                "label": label,
                "data": points,
                "backgroundColor": color
            })
    else:
        # Single dataset with all points
        points = []
        for item in data:
            if x_lookup in item and y_lookup in item:
                points.append({
                    "x": item[x_lookup],
                    "y": item[y_lookup]
                })
        
        datasets.append({
            "label": f"{x_field_name} vs {y_field_name}",
            "data": points,
            "backgroundColor": colors[0]
        })
    
    return {"datasets": datasets}

def transform_for_bubble_chart(data: List[Dict], dimensions: List, measures: List, 
                             colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for bubble charts (scatter with size)"""
    # Get field mappings or use defaults
    x_field = fields.get("x") if fields else (measures[0] if measures else None)
    y_field = fields.get("y") if fields else (measures[1] if len(measures) > 1 else None)
    size_field = fields.get("size") if fields else (measures[2] if len(measures) > 2 else None)
    label_field = fields.get("label") if fields else (dimensions[0] if dimensions else None)
    
    # Extract field names
    x_field_name = x_field if isinstance(x_field, str) else (x_field.get("field") if x_field else None)
    y_field_name = y_field if isinstance(y_field, str) else (y_field.get("field") if y_field else None)
    size_field_name = size_field if isinstance(size_field, str) else (size_field.get("field") if size_field else None)
    label_field_name = label_field if isinstance(label_field, str) else (label_field.get("field") if label_field else None)
    
    # Check for required fields
    if not x_field_name or not y_field_name:
        return {
            "datasets": [{
                "label": "Missing x/y configuration",
                "data": [],
                "backgroundColor": "#ef4444"
            }]
        }
    
    # Format field names for data lookup (they include aggregation in MongoDB result)
    x_agg = "avg" if isinstance(x_field, dict) and x_field.get("aggregation") else "sum"
    y_agg = "avg" if isinstance(y_field, dict) and y_field.get("aggregation") else "sum"
    size_agg = "avg" if isinstance(size_field, dict) and size_field.get("aggregation") else "sum"
    x_lookup = f"{x_field_name.replace('.', '_')}_{x_agg}"
    y_lookup = f"{y_field_name.replace('.', '_')}_{y_agg}"
    size_lookup = f"{size_field_name.replace('.', '_')}_{size_agg}" if size_field_name else None
    
    # Group data by label if provided
    datasets = []
    
    if label_field_name:
        # Group data by label
        grouped_data = {}
        for item in data:
            label = str(item.get(label_field_name, "Unknown"))
            if label not in grouped_data:
                grouped_data[label] = []
            
            # Only add points with required values
            if x_lookup in item and y_lookup in item:
                point = {
                    "x": item[x_lookup],
                    "y": item[y_lookup]
                }
                
                # Add size if available
                if size_lookup and size_lookup in item:
                    # Scale size to reasonable bubble radius (1-40)
                    raw_size = item[size_lookup]
                    point["r"] = min(40, max(1, int(raw_size / 10)))
                else:
                    point["r"] = 10  # Default radius
                
                grouped_data[label].append(point)
        
        # Create a dataset for each label
        for idx, (label, points) in enumerate(grouped_data.items()):
            color = colors[idx % len(colors)]
            datasets.append({
                "label": label,
                "data": points,
                "backgroundColor": color.replace(")", ", 0.7)")
            })
    else:
        # Single dataset with all points
        points = []
        for item in data:
            if x_lookup in item and y_lookup in item:
                point = {
                    "x": item[x_lookup],
                    "y": item[y_lookup]
                }
                
                # Add size if available
                if size_lookup and size_lookup in item:
                    # Scale size to reasonable bubble radius (1-40)
                    raw_size = item[size_lookup]
                    point["r"] = min(40, max(1, int(raw_size / 10)))
                else:
                    point["r"] = 10  # Default radius
                
                points.append(point)
        
        datasets.append({
            "label": f"{x_field_name} vs {y_field_name}",
            "data": points,
            "backgroundColor": colors[0].replace(")", ", 0.7)")
        })
    
    return {"datasets": datasets}

def transform_for_radar_chart(data: List[Dict], dimensions: List, measures: List, 
                            colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for radar charts"""
    # Get field mappings or use defaults
    categories_field = fields.get("categories") if fields else (dimensions[0] if dimensions else None)
    values_field = fields.get("values") if fields else (measures[0] if measures else None)
    series_field = fields.get("series") if fields else (dimensions[1] if len(dimensions) > 1 else None)
    
    # Extract field names
    categories_field_name = categories_field if isinstance(categories_field, str) else (categories_field.get("field") if categories_field else None)
    values_field_name = values_field if isinstance(values_field, str) else (values_field.get("field") if values_field else None)
    series_field_name = series_field if isinstance(series_field, str) else (series_field.get("field") if series_field else None)
    
    if not categories_field_name or not values_field_name:
        return {
            "labels": [],
            "datasets": [{
                "label": "Missing configuration",
                "data": [],
                "backgroundColor": "#ef4444"
            }]
        }
    
    # Format values field name for data lookup
    values_agg = "avg" if isinstance(values_field, dict) and values_field.get("aggregation") else "sum"
    values_lookup = f"{values_field_name.replace('.', '_')}_{values_agg}"
    
    # Get unique categories
    categories = []
    for item in data:
        category = item.get(categories_field_name)
        if category and category not in categories:
            categories.append(category)
    
    # Sort categories
    categories.sort()
    
    datasets = []
    
    if series_field_name:
        # Multi-series radar chart
        series_values = set(item.get(series_field_name) for item in data if series_field_name in item)
        
        for idx, series_value in enumerate(sorted(series_values)):
            # Filter data for this series
            series_data = [next((item.get(values_lookup, 0) for item in data 
                              if item.get(series_field_name) == series_value and 
                              item.get(categories_field_name) == category), 0)
                          for category in categories]
            
            color = colors[idx % len(colors)]
            
            datasets.append({
                "label": str(series_value),
                "data": series_data,
                "backgroundColor": color.replace(")", ", 0.2)"),
                "borderColor": color,
                "pointBackgroundColor": color
            })
    else:
        # Single series radar chart
        values = [next((item.get(values_lookup, 0) for item in data 
                     if item.get(categories_field_name) == category), 0)
                 for category in categories]
        
        datasets.append({
            "label": values_field_name,
            "data": values,
            "backgroundColor": colors[0].replace(")", ", 0.2)"),
            "borderColor": colors[0],
            "pointBackgroundColor": colors[0]
        })
    
    return {
        "labels": categories,
        "datasets": datasets
    }

def transform_for_heatmap_chart(data: List[Dict], dimensions: List, measures: List, 
                              colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for heatmap charts"""
    # Get field mappings or use defaults
    rows_field = fields.get("rows") if fields else (dimensions[0] if dimensions else None)
    columns_field = fields.get("columns") if fields else (dimensions[1] if len(dimensions) > 1 else None)
    values_field = fields.get("values") if fields else (measures[0] if measures else None)
    
    # Extract field names
    rows_field_name = rows_field if isinstance(rows_field, str) else (rows_field.get("field") if rows_field else None)
    columns_field_name = columns_field if isinstance(columns_field, str) else (columns_field.get("field") if columns_field else None)
    values_field_name = values_field if isinstance(values_field, str) else (values_field.get("field") if values_field else None)
    
    if not rows_field_name or not columns_field_name or not values_field_name:
        return {
            "data": {
                "datasets": [{
                    "label": "Missing configuration",
                    "data": []
                }]
            }
        }
    
    # Format values field name for data lookup
    values_agg = "avg" if isinstance(values_field, dict) and values_field.get("aggregation") else "sum"
    values_lookup = f"{values_field_name.replace('.', '_')}_{values_agg}"
    
    # Convert data to heatmap format
    heatmap_data = []
    
    for item in data:
        if rows_field_name in item and columns_field_name in item and values_lookup in item:
            heatmap_data.append({
                "x": item[columns_field_name],
                "y": item[rows_field_name],
                "v": item[values_lookup]
            })
    
    return {
        "data": {
            "datasets": [{
                "label": values_field_name,
                "data": heatmap_data
            }]
        }
    }

def transform_for_treemap_chart(data: List[Dict], dimensions: List, measures: List, 
                              colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for treemap charts"""
    # Get field mappings or use defaults
    hierarchy_field = fields.get("hierarchy") if fields else (dimensions[0] if dimensions else None)
    size_field = fields.get("size") if fields else (measures[0] if measures else None)
    color_field = fields.get("color") if fields else (measures[1] if len(measures) > 1 else None)
    
    # Extract field names
    hierarchy_field_name = hierarchy_field if isinstance(hierarchy_field, str) else (hierarchy_field.get("field") if hierarchy_field else None)
    size_field_name = size_field if isinstance(size_field, str) else (size_field.get("field") if size_field else None)
    color_field_name = color_field if isinstance(color_field, str) else (color_field.get("field") if color_field else None)
    
    if not hierarchy_field_name or not size_field_name:
        return {
            "data": {
                "datasets": [{
                    "label": "Missing configuration",
                    "tree": []
                }]
            }
        }
    
    # Format field names for data lookup
    size_agg = "sum" if isinstance(size_field, dict) and size_field.get("aggregation") else "sum"
    color_agg = "avg" if isinstance(color_field, dict) and color_field.get("aggregation") else "sum"
    size_lookup = f"{size_field_name.replace('.', '_')}_{size_agg}"
    color_lookup = f"{color_field_name.replace('.', '_')}_{color_agg}" if color_field_name else None
    
    # Prepare treemap data
    tree_items = [{"id": "root", "name": "Root"}]
    
    for item in data:
        if hierarchy_field_name in item and size_lookup in item:
            category = item[hierarchy_field_name]
            tree_items.append({
                "id": category,
                "name": category,
                "parent": "root",
                "value": item[size_lookup],
                **({"color": item[color_lookup]} if color_lookup and color_lookup in item else {})
            })
    
    return {
        "data": {
            "datasets": [{
                "tree": tree_items,
                "key": "value",
                "groups": ["name"],
                "spacing": 0.5
            }]
        }
    }



def transform_for_counter_chart(data: List[Dict], dimensions: List, measures: List, 
                              colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for counter/KPI charts with current value and optional comparison"""
    # Get field mappings or use defaults
    value_field = fields.get("value") if fields else (measures[0] if measures else None)
    comparison_field = fields.get("comparison") if fields else (measures[1] if len(measures) > 1 else None)
    label_field = fields.get("label") if fields else (dimensions[0] if dimensions else None)
    
    # Extract field names
    value_field_name = value_field if isinstance(value_field, str) else (value_field.get("field") if value_field else None)
    comparison_field_name = comparison_field if isinstance(comparison_field, str) else (comparison_field.get("field") if comparison_field else None)
    label_field_name = label_field if isinstance(label_field, str) else (label_field.get("field") if label_field else None)
    
    # Format fields for lookup (include aggregation in MongoDB result)
    value_agg = "sum" if isinstance(value_field, dict) and value_field.get("aggregation") else "sum"
    comparison_agg = "sum" if isinstance(comparison_field, dict) and comparison_field.get("aggregation") else "sum"
    
    value_lookup = f"{value_field_name.replace('.', '_')}_{value_agg}" if value_field_name else None
    comparison_lookup = f"{comparison_field_name.replace('.', '_')}_{comparison_agg}" if comparison_field_name else None
    
    # Default values
    current_value = 0
    comparison_value = 0
    label = "Value"
    
    # Extract values from data
    if data and len(data) > 0:
        # If we have label field, use the first item's label
        if label_field_name and label_field_name in data[0]:
            label = str(data[0][label_field_name])
        
        # For counter, we often aggregate to a single value
        if value_lookup and value_lookup in data[0]:
            current_value = data[0][value_lookup]
        
        # Get comparison value if available
        if comparison_lookup and comparison_lookup in data[0]:
            comparison_value = data[0][comparison_lookup]
    
    # Calculate percentage change if both values are present
    percent_change = None
    if comparison_value and current_value:
        percent_change = ((current_value - comparison_value) / comparison_value) * 100
    
    return {
        "type": "counter",
        "data": {
            "current": current_value,
            "previous": comparison_value,
            "percentChange": percent_change,
            "label": label
        }
    }


def transform_to_chart_js_format(data: List[Dict], dimensions: List, measures: List, 
                                chart_type: str = "bar", fields: Dict = None) -> Dict:
    """Transform MongoDB aggregation results to Chart.js format with enhanced chart type support"""
    if not data:
        return {
            "labels": [],
            "datasets": [{
                "label": "No Data",
                "data": [],
                "backgroundColor": "#4f46e5"
            }]
        }
    
    # Define color palette for charts
    colors = [
        "#4f46e5", "#16a34a", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4",
        "#ec4899", "#84cc16", "#14b8a6", "#f97316", "#6366f1", "#0ea5e9"
    ]
    
    # Handle different chart types
    if chart_type in ["pie", "doughnut"]:
        return transform_for_pie_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "line":
        return transform_for_line_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "area":
        return transform_for_area_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "scatter":
        return transform_for_scatter_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "bubble":
        return transform_for_bubble_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "radar":
        return transform_for_radar_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "heatmap":
        return transform_for_heatmap_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "treemap":
        return transform_for_treemap_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "table":  # Add this case for table charts
        return transform_to_chart_data(data, "table") 
    elif chart_type == "counter":
        return transform_for_counter_chart(data, dimensions, measures, colors, fields)
    elif chart_type == "number":  # Also handle 'number' type similarly to counter
        return transform_for_counter_chart(data, dimensions, measures, colors, fields)
    else:  # Default to bar chart
        return transform_for_bar_chart(data, dimensions, measures, colors, fields)



def _generate_fallback_data(data_source: str, pipeline: List[Dict]) -> List[Dict]:
    """Generate fallback sample data when MongoDB is unavailable"""
    print(f"[FALLBACK] Generating sample data for {data_source}")
    
    # Default fallback data based on data source

    if data_source == "customers":
        return [
            {"name": "John Doe", "total_orders": 12, "total_spent": 980.50, "last_visit": "2025-03-01"},
            {"name": "Alice Smith", "total_orders": 8, "total_spent": 640.75, "last_visit": "2025-03-05"},
            {"name": "Bob Johnson", "total_orders": 15, "total_spent": 1250.25, "last_visit": "2025-02-28"},
            {"name": "Emma Davis", "total_orders": 5, "total_spent": 320.80, "last_visit": "2025-03-10"},
            {"name": "Michael Wilson", "total_orders": 10, "total_spent": 780.60, "last_visit": "2025-03-12"}
        ]
    elif data_source == "bills":
        return [
            {"date": "2025-03-01", "total_amount_sum": 1250.75, "items_quantity_sum": 45, "payment_methods_count": 12},
            {"date": "2025-03-02", "total_amount_sum": 980.50, "items_quantity_sum": 32, "payment_methods_count": 8},
            {"date": "2025-03-03", "total_amount_sum": 1500.25, "items_quantity_sum": 57, "payment_methods_count": 15},
            {"date": "2025-03-04", "total_amount_sum": 850.30, "items_quantity_sum": 28, "payment_methods_count": 7},
            {"date": "2025-03-05", "total_amount_sum": 1100.80, "items_quantity_sum": 41, "payment_methods_count": 10}
        ]
    elif data_source == "customer_order_history":
        return [
            {"name": "John Doe", "total_visits": 12, "total_spent_sum": 980.50},
            {"name": "Alice Smith", "total_visits": 8, "total_spent_sum": 640.75},
            {"name": "Bob Johnson", "total_visits": 15, "total_spent_sum": 1250.25},
            {"name": "Emma Davis", "total_visits": 5, "total_spent_sum": 320.80},
            {"name": "Michael Wilson", "total_visits": 10, "total_spent_sum": 780.60}
        ]
    elif data_source == "item_analytics":
        return [
            {"name": "Chicken Curry", "category": "Main Course", "total_revenue_sum": 2500.50, "total_quantity_sum": 125},
            {"name": "Vegetable Biryani", "category": "Rice", "total_revenue_sum": 1800.75, "total_quantity_sum": 95},
            {"name": "Paneer Tikka", "category": "Appetizer", "total_revenue_sum": 950.25, "total_quantity_sum": 65},
            {"name": "Mango Lassi", "category": "Beverage", "total_revenue_sum": 580.50, "total_quantity_sum": 110},
            {"name": "Gulab Jamun", "category": "Dessert", "total_revenue_sum": 450.80, "total_quantity_sum": 90}
        ]
    else:
        # Generic fallback data
        return [
            {"dimension1": "Category A", "metric1": 100, "metric2": 200},
            {"dimension1": "Category B", "metric1": 150, "metric2": 250},
            {"dimension1": "Category C", "metric1": 120, "metric2": 220},
            {"dimension1": "Category D", "metric1": 180, "metric2": 280},
            {"dimension1": "Category E", "metric1": 90, "metric2": 190}
        ]

def transform_for_bar_chart(data: List[Dict], dimensions: List, measures: List, 
                          colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for bar charts with enhanced field support"""
    # Get field mappings or use defaults
    x_field = fields.get("x") if fields else None
    y_field = fields.get("y") if fields else None
    series_field = fields.get("series") if fields else None
    
    # If fields are specified, use them; otherwise use dimensions and measures
    primary_dim = x_field if x_field else (dimensions[0] if dimensions else None)
    primary_measure = y_field if y_field else (measures[0] if measures else None)
    secondary_dim = series_field if series_field else (dimensions[1] if len(dimensions) > 1 else None)
    
    # Extract field names
    primary_dim_name = primary_dim if isinstance(primary_dim, str) else (primary_dim.get("field") if primary_dim else None)
    secondary_dim_name = secondary_dim if isinstance(secondary_dim, str) else (secondary_dim.get("field") if secondary_dim else None)
    
    # Get labels from primary dimension
    labels = []
    if primary_dim_name:
        # Extract unique values for the primary dimension
        labels = sorted(list(set(item.get(primary_dim_name, "") for item in data if primary_dim_name in item)))
    else:
        # If no dimensions, use indices as labels
        labels = [str(i+1) for i in range(len(data))]
    
    # Create datasets
    datasets = []
    
    # Process each measure
    for i, measure in enumerate(measures):
        measure_field = measure if isinstance(measure, str) else measure.get("field")
        aggregation = measure.get("aggregation", "sum") if isinstance(measure, dict) else "sum"
        
        if not measure_field:
            continue
            
        measure_alias = f"{measure_field.replace('.', '_')}_{aggregation}"
        measure_label = f"{measure_field.split('.')[-1]} ({aggregation})"
        
        # For single dimension, create one dataset per measure
        if not secondary_dim_name:
            data_points = []
            for label in labels:
                # Find the value for this label
                if primary_dim_name:
                    value = next((item.get(measure_alias, 0) for item in data 
                                if item.get(primary_dim_name) == label), 0)
                else:
                    # No primary dimension, use index
                    idx = labels.index(label)
                    value = data[idx].get(measure_alias, 0) if idx < len(data) else 0
                
                data_points.append(value)
            
            # Create dataset
            datasets.append({
                "label": measure_label,
                "data": data_points,
                "backgroundColor": colors[i % len(colors)]
            })
        else:
            # With secondary dimension, create a dataset for each combination
            sec_dim_values = sorted(list(set(item.get(secondary_dim_name, "") 
                                          for item in data if secondary_dim_name in item)))
            
            for j, sec_value in enumerate(sec_dim_values):
                # Filter data for this secondary value
                sec_data = [item for item in data if item.get(secondary_dim_name) == sec_value]
                
                # Map to primary dimension
                data_points = []
                for label in labels:
                    value = next((item.get(measure_alias, 0) for item in sec_data 
                                 if item.get(primary_dim_name) == label), 0)
                    data_points.append(value)
                
                # Create dataset for this combination
                datasets.append({
                    "label": f"{sec_value} - {measure_label}",
                    "data": data_points,
                    "backgroundColor": colors[(i * len(sec_dim_values) + j) % len(colors)]
                })
    
    return {
        "labels": labels,
        "datasets": datasets
    }

def transform_for_line_chart(data: List[Dict], dimensions: List, measures: List, 
                           colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for line charts with enhanced field support"""
    # Get the base bar chart data
    bar_data = transform_for_bar_chart(data, dimensions, measures, colors, fields)
    
    # Update styling for line chart
    for dataset in bar_data["datasets"]:
        dataset["borderColor"] = dataset.pop("backgroundColor", colors[0])
        dataset["backgroundColor"] = "rgba(0,0,0,0.1)"
        dataset["fill"] = False
        dataset["tension"] = 0.1  # Add some curve to the lines
    
    return bar_data

def transform_for_pie_chart(data: List[Dict], dimensions: List, measures: List, 
                          colors: List[str], fields: Dict = None) -> Dict:
    """Transform data for pie/doughnut charts with enhanced field support"""
    # Get field mappings or use defaults
    labels_field = fields.get("labels") if fields else None
    values_field = fields.get("values") if fields else None
    
    # If fields are specified, use them; otherwise use dimensions and measures
    primary_dim = labels_field if labels_field else (dimensions[0] if dimensions else None)
    primary_measure = values_field if values_field else (measures[0] if measures else None)
    
    # Extract field names
    primary_dim_name = primary_dim if isinstance(primary_dim, str) else (primary_dim.get("field") if primary_dim else None)
    measure_field = primary_measure if isinstance(primary_measure, str) else (primary_measure.get("field") if primary_measure else None)
    aggregation = primary_measure.get("aggregation", "sum") if isinstance(primary_measure, dict) else "sum"
    
    # Check for required fields
    if not primary_dim_name or not measure_field:
        return {
            "labels": [],
            "datasets": [{
                "label": "Missing configuration",
                "data": [],
                "backgroundColor": colors
            }]
        }
    
    # Format measure field for lookup
    measure_alias = f"{measure_field.replace('.', '_')}_{aggregation}"
    
    # Get labels and values
    pie_data = [(item.get(primary_dim_name, "Unknown"), item.get(measure_alias, 0)) 
               for item in data if primary_dim_name in item and measure_alias in item]
    
    # Sort by value descending for better visualization
    pie_data.sort(key=lambda x: x[1], reverse=True)
    
    # Prepare chart data
    labels = [item[0] for item in pie_data]
    values = [item[1] for item in pie_data]
    
    return {
        "labels": labels,
        "datasets": [{
            "data": values,
            "backgroundColor": colors[:len(values)]
        }]
    }

def transform_to_chart_data(data, chart_type="bar"):
    """Transform MongoDB data into Chart.js format"""
    # Enhanced implementation that accepts MongoDB data and converts to Chart.js format
    
    if not data:
        return {
            "labels": [],
            "datasets": [{
                "label": "No Data",
                "data": [],
                "backgroundColor": "#4f46e5"
            }]
        }
    
    # Colors for the chart
    colors = ["#4f46e5", "#16a34a", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4"]
    
    # Extract keys for dimensions and measures
    keys = list(data[0].keys())
    # Remove _id if it exists
    if "_id" in keys:
        keys.remove("_id")
    
    # Assume first non-numeric field is dimension (label)
    dimension_key = None
    measure_keys = []
    
    for key in keys:
        if isinstance(data[0][key], (int, float)) or (isinstance(data[0][key], str) and data[0][key].replace('.', '').isdigit()):
            measure_keys.append(key)
        elif not dimension_key:  # First non-numeric is dimension
            dimension_key = key
    
    # If no dimension found, use an index
    labels = []
    if dimension_key:
        labels = [item[dimension_key] for item in data]
    else:
        labels = [f"Item {i+1}" for i in range(len(data))]
    
    # Create datasets for each measure
    datasets = []
    for i, measure_key in enumerate(measure_keys):
        # Clean up measure name for display
        measure_name = measure_key.replace('_', ' ').title()
        if '_' in measure_key:
            # Extract aggregation if present (e.g., total_amount_sum -> Total Amount (Sum))
            parts = measure_key.split('_')
            if parts[-1] in ['sum', 'avg', 'min', 'max', 'count']:
                measure_name = ' '.join(parts[:-1]).title() + f" ({parts[-1].title()})"
        
        dataset = {
            "label": measure_name,
            "data": [float(item[measure_key]) if measure_key in item else 0 for item in data],
            "backgroundColor": colors[i % len(colors)]
        }
        
        # Adjust styling for line charts
        if chart_type == "line":
            dataset["borderColor"] = dataset["backgroundColor"]
            dataset["backgroundColor"] = "rgba(0,0,0,0.1)"
            dataset["fill"] = False
            dataset["tension"] = 0.1
        
        datasets.append(dataset)
    
    return {
        "labels": labels,
        "datasets": datasets
    }
















