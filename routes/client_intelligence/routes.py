from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import redis
import json
from bson.errors import InvalidId  

from ..client_intelligence.models import (
    Dashboard, DashboardCreate, DashboardUpdate, DashboardResponse,
    ChartConfig, ChartCreate, ChartUpdate, ChartResponse,
    QueryRequest, QueryResponse,
    Dataset, DatasetResponse,FilterCondition
)





from ..client_intelligence.services import (
    get_dashboard, get_all_dashboards, create_dashboard, update_dashboard, delete_dashboard,
    toggle_dashboard_favorite, get_recent_dashboards, get_favorite_dashboards,
    get_chart, get_all_charts, create_chart, update_chart, delete_chart,
    execute_query, get_datasets, get_dataset,
    generate_insights,generate_export_in_background,get_dashboard_templates,set_default_dashboard, get_default_dashboard,
    get_dashboard_items, update_dashboard_item, 
    delete_dashboard_item, create_dashboard_item,
    set_dashboard_editing_state,get_dashboard_with_data,
    undo_dashboard_change, redo_dashboard_change,get_user_dashboard_permissions,
    set_dashboard_selected_items, get_dashboard_selected_items,
    set_dashboard_focused_item, get_dashboard_focused_item,get_dashboard_history,transform_to_chart_data,



    get_data_source_fields, build_filters, build_mongodb_pipeline, 
    execute_mongodb_pipeline, transform_to_chart_js_format, 
    transform_for_bar_chart, transform_for_line_chart, transform_for_pie_chart,get_sample_data_for_chart_type,get_all_customers,get_collection_for_dataset
)

# Create the router
router = APIRouter()

# Dataset endpoints
@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets():
    """Get all available analytics datasets with metadata"""
    return get_datasets()

@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset_details(dataset_id: str):
    """Get metadata for a specific dataset"""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return dataset

# Query endpoints
@router.post("/query", response_model=QueryResponse)
async def query_data(query_request: QueryRequest):
    """Execute an analytics query with filters, dimensions and measures"""
    try:
        result = execute_query(query_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/insights")
async def get_insights(
    dataset_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = Query(None)
):
    """Generate insights automatically from dataset"""
    try:
        insights = generate_insights(dataset_id, start_date, end_date, dimensions)
        return insights
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Dashboard endpoints
@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    search: Optional[str] = None,
    favorites_only: bool = False,
    limit: int = 100
):
    """Get all dashboards with optional filtering"""
    if favorites_only:
        return get_favorite_dashboards(search, limit)
    return get_all_dashboards(search, limit)

@router.get("/dashboards/recent", response_model=List[DashboardResponse])
async def get_recent_accessed_dashboards(limit: int = 5):
    """Get recently accessed dashboards"""
    return get_recent_dashboards(limit)

@router.get("/dashboards/favorites", response_model=List[DashboardResponse])
async def get_favorite_only_dashboards():
    """Get favorite dashboards"""
    return get_favorite_dashboards()


@router.get("/dashboards/templates", response_model=List[DashboardResponse])
async def get_dashboard_templates():
    """Get pre-defined dashboard templates"""
    return get_dashboard_templates()



# Add this function import
@router.get("/dashboards/default", response_model=DashboardResponse)
async def get_default_dashboard_endpoint():
    """Get the user's default dashboard"""
    dashboard = get_default_dashboard()
    if not dashboard:
        raise HTTPException(status_code=404, detail="No default dashboard set")
    return dashboard

# @router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
# async def get_dashboard_by_id(dashboard_id: str):
#     """Get a specific dashboard with all items and configurations"""
#     dashboard = get_dashboard(dashboard_id)
#     if not dashboard:
#         raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
#     return dashboard

@router.post("/dashboards", response_model=DashboardResponse)
async def create_new_dashboard(dashboard: DashboardCreate):
    """Create a new dashboard"""
    try:
        created_dashboard = create_dashboard(dashboard)
        return created_dashboard
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_existing_dashboard(dashboard_id: str, dashboard: DashboardUpdate):
    """Update an existing dashboard"""
    try:
        # Use the existing update_dashboard function that now handles custom IDs
        updated_dashboard = update_dashboard(dashboard_id, dashboard)
        if not updated_dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        return updated_dashboard
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")
    

@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard_by_id(dashboard_id: str):
    """Get a specific dashboard with all items and configurations"""
    # Special case handling
    if dashboard_id == "default":
        # Get the default dashboard via a different method
        dashboard = get_default_dashboard()
        if not dashboard:
            raise HTTPException(status_code=404, detail="No default dashboard found")
        return dashboard
    
    # Handle custom dashboard IDs that aren't ObjectIds
    if dashboard_id.startswith("dashboard-"):
        # Add logic to handle custom ID format
        # For example, look up by a different field
        pass
        
    # Normal case - try to get dashboard by MongoDB ObjectId
    try:
        # Validate it's a proper ObjectId
        object_id = ObjectId(dashboard_id)
        dashboard = get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        return dashboard
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")



# @router.put("/dashboards/{dashboard_id}", response_model=DashboardResponse)
# async def update_existing_dashboard(dashboard_id: str, dashboard: DashboardUpdate):
#     """Update an existing dashboard"""
#     updated_dashboard = update_dashboard(dashboard_id, dashboard)
#     if not updated_dashboard:
#         raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
#     return updated_dashboard




@router.delete("/dashboards/{dashboard_id}")
async def delete_existing_dashboard(dashboard_id: str):
    """Delete a dashboard"""
    success = delete_dashboard(dashboard_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"message": f"Dashboard {dashboard_id} deleted successfully"}

@router.post("/dashboards/{dashboard_id}/favorite")
async def toggle_favorite_dashboard(dashboard_id: str):
    """Toggle favorite status for a dashboard"""
    dashboard = toggle_dashboard_favorite(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"message": f"Favorite status toggled for dashboard {dashboard_id}"}

@router.get("/charts", response_model=List[ChartResponse])
async def list_charts():
    """Get all saved chart configurations"""
    return get_all_charts()


@router.post("/charts", response_model=ChartResponse)
async def create_new_chart(chart: ChartCreate):
    """Create a new chart configuration"""
    try:
        created_chart = create_chart(chart)
        return created_chart
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/charts/preview")
async def preview_chart(chart_config: ChartConfig):
    """Generate preview data for a chart configuration"""
    try:
        # Create a query from the chart configuration
        query = QueryRequest(
            dataset_id=chart_config.data_source.id,
            dimensions=chart_config.dimensions,
            measures=chart_config.measures,
            filters=chart_config.filters,
            order_by=chart_config.order_by if hasattr(chart_config, 'order_by') else None,
            limit=chart_config.limit if hasattr(chart_config, 'limit') else 1000
        )
        # Execute the query to get preview data
        result = execute_query(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Chart endpoints


@router.get("/charts/{chart_id}", response_model=ChartResponse)
async def get_chart_by_id(chart_id: str):
    """Get a specific chart configuration"""
    chart = get_chart(chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
    return chart


@router.put("/charts/{chart_id}", response_model=ChartResponse)
async def update_existing_chart(chart_id: str, chart: ChartUpdate):
    """Update an existing chart configuration"""
    updated_chart = update_chart(chart_id, chart)
    if not updated_chart:
        raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
    return updated_chart

@router.delete("/charts/{chart_id}")
async def delete_existing_chart(chart_id: str):
    """Delete a chart configuration"""
    success = delete_chart(chart_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
    return {"message": f"Chart {chart_id} deleted successfully"}



# Export endpoints
@router.post("/export")
async def export_data(
    query_request: QueryRequest,
    format: str = "csv",
    background_tasks: BackgroundTasks = None
):
    """Export query results in various formats (CSV, Excel, PDF, JSON)"""
    try:
        if format not in ["csv", "excel", "pdf", "json"]:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        
        # For larger exports, use background tasks
        if background_tasks and query_request.estimate_size() > 1000:
            # Generate export in background and return a job ID
            job_id = f"export_{ObjectId()}"
            background_tasks.add_task(
                generate_export_in_background, 
                job_id, 
                query_request, 
                format
            )
            return {"job_id": job_id, "status": "processing"}
        
        # For smaller exports, generate immediately
        result = execute_query(query_request)
        
        # Format based on requested export type
        if format == "json":
            return result
        elif format == "csv":
            # CSV formatting logic here
            return {"download_url": f"/api/analytics/downloads/{job_id}.csv"}
        elif format == "excel":
            # Excel formatting logic here
            return {"download_url": f"/api/analytics/downloads/{job_id}.xlsx"}
        elif format == "pdf":
            # PDF formatting logic here
            return {"download_url": f"/api/analytics/downloads/{job_id}.pdf"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Additional utility endpoints
@router.get("/user/preferences")
async def get_user_preferences():
    """Get user preferences for analytics"""
    # Implementation depends on your user management system
    return {
        "color_scheme": "default",
        "date_format": "MM/DD/YYYY",
        "number_format": {"decimal_places": 2, "thousands_separator": ","}
    }

@router.put("/user/preferences")
async def update_user_preferences(preferences: Dict[str, Any]):
    """Update user preferences for analytics"""
    # Implementation depends on your user management system
    return {"message": "Preferences updated successfully"}


# Add this route for widget data


# Add this function import
# from ..client_intelligence.services import get_dashboard_templates



@router.post("/dashboards/{dashboard_id}/default")
async def set_default_dashboard_endpoint(dashboard_id: str):
    """Set a dashboard as the default dashboard"""
    success = set_default_dashboard(dashboard_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"message": f"Dashboard {dashboard_id} set as default"}







@router.get("/dashboards/{dashboard_id}/items")
async def get_dashboard_items_endpoint(dashboard_id: str):
    """Get all items in a dashboard"""
    items = get_dashboard_items(dashboard_id)
    if items is None:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return items

@router.put("/dashboards/{dashboard_id}/items/{item_id}")
async def update_dashboard_item_endpoint(dashboard_id: str, item_id: str, item: Dict):
    """Update a specific item in a dashboard"""
    updated_item = update_dashboard_item(dashboard_id, item_id, item)
    if not updated_item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found in dashboard {dashboard_id}")
    return updated_item

@router.post("/dashboards/{dashboard_id}/items")
async def create_dashboard_item_endpoint(dashboard_id: str, item: Dict):
    """Add a new item to a dashboard"""
    new_item = create_dashboard_item(dashboard_id, item)
    if not new_item:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return new_item

@router.delete("/dashboards/{dashboard_id}/items/{item_id}")
async def delete_dashboard_item_endpoint(dashboard_id: str, item_id: str):
    """Delete an item from a dashboard"""
    success = delete_dashboard_item(dashboard_id, item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found in dashboard {dashboard_id}")
    return {"message": f"Item {item_id} deleted from dashboard {dashboard_id}"}




@router.post("/dashboards/{dashboard_id}/editing")
async def set_dashboard_editing_state_endpoint(dashboard_id: str, is_editing: bool = False):
    """Set dashboard editing state"""
    result = set_dashboard_editing_state(dashboard_id, is_editing)
    if not result:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"dashboard_id": dashboard_id, "is_editing": is_editing}







@router.get("/dashboards/{dashboard_id}/with-data")
async def get_dashboard_with_data_endpoint(dashboard_id: str):
    """Get a dashboard with all its chart data preloaded"""
    # Use common handler for dashboard ID
    if dashboard_id.startswith("dashboard-"):
        # Special handling for custom dashboard IDs
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
        
    dashboard_with_data = get_dashboard_with_data(dashboard_id)
    if not dashboard_with_data:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return dashboard_with_data





@router.post("/dashboards/{dashboard_id}/undo")
async def undo_dashboard_change_endpoint(dashboard_id: str):
    """Undo the last change to a dashboard"""
    result = undo_dashboard_change(dashboard_id)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot undo any further")
    return result

@router.post("/dashboards/{dashboard_id}/redo")
async def redo_dashboard_change_endpoint(dashboard_id: str):
    """Redo a previously undone change to a dashboard"""
    result = redo_dashboard_change(dashboard_id)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot redo any further")
    return result

@router.get("/dashboards/{dashboard_id}/history")
async def get_dashboard_history_endpoint(dashboard_id: str):
    """Get change history for a dashboard"""
    history = get_dashboard_history(dashboard_id)
    if history is None:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return history





@router.get("/dashboards/{dashboard_id}/permissions")
async def get_dashboard_permissions_endpoint(dashboard_id: str):
    """Get the current user's permissions for a dashboard"""
    permissions = get_user_dashboard_permissions(dashboard_id)
    if permissions is None:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return permissions



# Add these function imports

@router.post("/dashboards/{dashboard_id}/selected-items")
async def set_selected_items_endpoint(dashboard_id: str, item_ids: List[str]):
    """Set the selected items for a dashboard"""
    result = set_dashboard_selected_items(dashboard_id, item_ids)
    if not result:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"dashboard_id": dashboard_id, "selected_items": item_ids}

@router.get("/dashboards/{dashboard_id}/selected-items")
async def get_selected_items_endpoint(dashboard_id: str):
    """Get the selected items for a dashboard"""
    items = get_dashboard_selected_items(dashboard_id)
    if items is None:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"dashboard_id": dashboard_id, "selected_items": items}

@router.post("/dashboards/{dashboard_id}/focused-item")
async def set_focused_item_endpoint(dashboard_id: str, item_id: Optional[str] = None):
    """Set the focused item for a dashboard"""
    result = set_dashboard_focused_item(dashboard_id, item_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"dashboard_id": dashboard_id, "focused_item": item_id}

@router.get("/dashboards/{dashboard_id}/focused-item")
async def get_focused_item_endpoint(dashboard_id: str):
    """Get the focused item for a dashboard"""
    item = get_dashboard_focused_item(dashboard_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
    return {"dashboard_id": dashboard_id, "focused_item": item}






@router.post("/analytics/widget-data")
async def get_widget_data(request: Dict[str, Any]):
    """Get data for a specific widget based on its configuration"""
    try:
        widget_id = request.get("widgetId")
        config = request.get("config", {})
        
        # Extract data source and chart type
        data_source = config.get("dataSource")
        chart_type = config.get("chartType", "bar")
        
        # For "empty" data source, return sample data for development
        if not data_source or data_source == "empty":
            return {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May"],
                "datasets": [{
                    "label": "Sample Data",
                    "data": [65, 59, 80, 81, 56],
                    "backgroundColor": "#4f46e5"
                }]
            }
        
        # Process filters
        filters = []
        for f in config.get("filters", []):
            if isinstance(f, dict) and "field" in f and "operator" in f and "value" in f:
                # Map frontend operator names to backend enum values
                operator_mapping = {
                    "equals": "eq",
                    "notEquals": "ne",
                    "greaterThan": "gt",
                    "greaterThanOrEqual": "gte",
                    "lessThan": "lt",
                    "lessThanOrEqual": "lte",
                    "in": "in",
                    "notIn": "not_in",
                    "contains": "contains",
                    "notContains": "not_contains",
                    "between": "between"
                }
                
                # Get correct operator value
                operator = operator_mapping.get(f.get("operator"), "eq")
                
                filters.append({
                    "field": f.get("field"),
                    "operator": operator,
                    "value": f.get("value")
                })
        
        # Create query parameters
        dimensions = config.get("dimensions", [])
        measures = config.get("measures", [])
        
        # Format dimensions and measures for the query
        formatted_dimensions = [{"field": d} for d in dimensions] if dimensions else []
        formatted_measures = [
            {"field": m.get("field"), "aggregation": m.get("aggregation", "sum")} 
            for m in measures
        ] if measures else []
        
        # Create the query request
        query_params = {
            "dataset_id": data_source,
            "filters": filters,
            "limit": config.get("limit", 1000)
        }
        
        if formatted_dimensions:
            query_params["dimensions"] = formatted_dimensions
            
        if formatted_measures:
            query_params["measures"] = formatted_measures
            
        # Execute the query
        query_request = QueryRequest(**query_params)
        result = execute_query(query_request)
        
        # Transform to Chart.js format and return
        data = result.get("data", [])
        chart_data = transform_to_chart_data(data, chart_type)
        
        return chart_data
        
    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        print(f"Widget data error: {str(e)}\n{trace}")
        
        # Return empty Chart.js structure
        return {
            "labels": [],
            "datasets": [{
                "label": "Error",
                "data": [],
                "backgroundColor": "#ef4444"
            }]
        }





# Add after your imports section:
import hashlib
import json
from redis import Redis
from datetime import datetime, timedelta
from ..client_intelligence.services import redis_client as services_redis_client, redis_connected
# Initialize Redis client for caching
# Updated Redis handling
redis_client = services_redis_client
redis_available = redis_connected

# Add these new endpoints to your existing router

@router.get("/analytics/available-fields/{data_source}")
async def get_available_fields(data_source: str):
    """Get available fields (dimensions and measures) for a specific data source"""
    try:
        # Get field metadata for the specified data source
        fields = get_data_source_fields(data_source)
        if not fields:
            raise HTTPException(status_code=404, detail=f"Data source {data_source} not found")
        return fields
    except Exception as e:
        import traceback
        print(f"[ERROR] Getting fields for {data_source}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=str(e))




# Update the chart-data endpoint to handle the new fields structure
@router.post("/analytics/chart-data")
async def get_chart_data(config: Dict[str, Any]):
    """Get chart data based on configuration with enhanced field mapping support"""
    try:
        # Extract config parameters
        data_source = config.get("dataSource")
        dimensions = config.get("dimensions", [])
        measures = config.get("measures", [])
        filters = config.get("filters", [])
        time_range = config.get("timeRange", "last30Days")
        chart_type = config.get("chartType", "bar")
        fields = config.get("fields", {})  # New field mappings structure
        question_id = config.get("questionId")  # Support for question-based queries
        
        # Check for required parameters
        if not data_source or data_source == "empty":
            # Return sample data for development or when no data source
            return get_sample_data_for_chart_type(chart_type, fields)
        
        cache_key = None
        print(f"Fields: {fields}")
        print(f"filters: {filters}")
        print(f"time_range: {time_range}")
        print(f"chart_type: {chart_type}")
        print(f"question_id: {question_id}")
        print(f"dimensions: {dimensions}")
        print(f"measures: {measures}")
        print(f"data_source: {data_source}")
        # Try to get from cache if Redis is available
        if redis_available:
            # Create a hash of the config for cache key
            config_str = json.dumps({
                "dataSource": data_source,
                "dimensions": dimensions,
                "measures": measures,
                "filters": filters,
                "timeRange": time_range,
                "chartType": chart_type,
                "fields": fields,
                "questionId": question_id
            }, sort_keys=True)
            cache_key = f"chart-data:{hashlib.md5(config_str.encode()).hexdigest()}"
            
            try:
                cached_data = redis_client.get(cache_key)
                if cached_data:
                    print(f"[CACHE] Hit for {cache_key}")
                    return json.loads(cached_data)
            except Exception as redis_err:
                print(f"[REDIS] Error reading cache: {str(redis_err)}")
        
        # Process filters to MongoDB format
        mongo_filters = build_filters(filters, time_range, data_source=data_source)
        
        # Build MongoDB aggregation pipeline with enhanced field support
        pipeline = build_mongodb_pipeline(data_source, dimensions, measures, mongo_filters, fields, chart_type)
        
        # Execute MongoDB query
        result = execute_mongodb_pipeline(data_source, pipeline)
        
        # Transform result to Chart.js format with enhanced chart type support
        chart_data = transform_to_chart_js_format(result, dimensions, measures, chart_type, fields)
        
        # Cache the result if Redis is available
        if redis_available:
            try:
                redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(chart_data)
                )
                print(f"[CACHE] Stored result in {cache_key}")
            except Exception as redis_err:
                print(f"[REDIS] Error setting cache: {str(redis_err)}")
        
        return chart_data
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Chart data error: {str(e)}\n{traceback.format_exc()}")
        
        return {
            "labels": [],
            "datasets": [{
                "label": f"Error: {str(e)}",
                "data": [],
                "backgroundColor": "#ef4444"
            }]
        }




@router.post("/analytics/invalidate-cache")
async def invalidate_analytics_cache(pattern: str = "chart-data:*"):
    """Invalidate analytics cache entries"""
    if not redis_available:
        return {"message": "Redis not available", "invalidated": 0}
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            count = redis_client.delete(*keys)
            return {"message": f"Invalidated {count} cache entries", "invalidated": count}
        return {"message": "No matching cache entries found", "invalidated": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache invalidation error: {str(e)}")









@router.post("/analytics/dashboard-config")
async def save_dashboard_configuration(config: Dict[str, Any]):
    """Save dashboard configuration - create new or update existing"""
    try:
        # Check if widgets are in a nested config object
        if "config" in config and isinstance(config["config"], dict):
            # Extract from nested config
            dashboard_config = config["config"]
            dashboard_id = dashboard_config.get("id")
            widgets = dashboard_config.get("widgets", [])
            layouts = {layout["i"]: layout for layout in dashboard_config.get("layouts", [])}
            name = config.get("name") or dashboard_config.get("name", "New Dashboard")
            description = config.get("description", "")
            settings = config.get("settings", {}) or dashboard_config.get("settings", {})
            is_favorite = config.get("is_favorite", False)
            tags = config.get("tags", [])
        else:
            # Original structure (top-level properties)
            dashboard_id = config.get("id")
            widgets = config.get("widgets", [])
            layouts = {layout["i"]: layout for layout in config.get("layouts", [])}
            name = config.get("name", "New Dashboard")
            description = config.get("description", "")
            settings = config.get("settings", {})
            is_favorite = config.get("is_favorite", False)
            tags = config.get("tags", [])
        
        # Transform widgets to dashboard items
        items = []
        for widget in widgets:
            widget_id = widget.get("id")
            position = layouts.get(widget_id, {})
            if "position" in widget:
                position = widget["position"]
            
            item = {
                "id": widget_id,
                "type": widget.get("type", "chart"),
                "component_id": widget_id,
                "x": position.get("x", 0),
                "y": position.get("y", 0),
                "w": position.get("w", 4),
                "h": position.get("h", 4),
                "config": widget  # Store the full widget config
            }
            items.append(item)

        # NEW CODE: Check if dashboard actually exists before updating
        existing_dashboard = None
        if dashboard_id:
            # Try to get the dashboard from the database
            existing_dashboard = get_dashboard(dashboard_id)
            print(f"Dashboard ID from request: {dashboard_id}, exists: {existing_dashboard is not None}")
        
        if dashboard_id and existing_dashboard:
            # Update existing dashboard that was found in the database
            print(f"Updating existing dashboard: {dashboard_id}")
            update_data = DashboardUpdate(
                name=name,
                description=description,
                items=items,
                settings=settings,
                is_favorite=is_favorite,
                tags=tags
            )
            
            updated_dashboard = update_dashboard(dashboard_id, update_data)
            if not updated_dashboard:
                raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
            
            return {
                "success": True,
                "dashboard": updated_dashboard
            }
        else:
            # Create new dashboard - either no ID provided or ID not found in database
            if not dashboard_id:
                # Generate a new ID if none provided
                timestamp = int(datetime.now().timestamp() * 1000)
                dashboard_id = f"dashboard-{timestamp}"
                print(f"Creating new dashboard with generated ID: {dashboard_id}")
            else:
                print(f"Creating new dashboard with provided ID: {dashboard_id}")
            
            create_data = DashboardCreate(
                id=dashboard_id,
                name=name,
                description=description,
                items=items,
                settings=settings,
                is_favorite=is_favorite,
                tags=tags
            )
            
            new_dashboard = create_dashboard(create_data)
            
            return {
                "success": True,
                "dashboard": new_dashboard
            }
    
    except Exception as e:
        print(f"Error saving dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save dashboard configuration: {str(e)}")

@router.get("/analytics/dashboard-config/{dashboard_id}")
async def load_dashboard_configuration(dashboard_id: str):
    """Load a dashboard configuration by ID"""
    try:
        # Handle custom dashboard IDs
        if dashboard_id.startswith("dashboard-"):
            # Return mock data for development with custom IDs
            return {
                "success": True,
                "dashboard": {
                    "id": dashboard_id,
                    "name": f"Dashboard {dashboard_id}",
                    "description": "Mock dashboard for development",
                    "items": [],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                    "is_favorite": False,
                    "data": {}  # Empty data object
                }
            }
        
        # Normal case - try MongoDB ObjectId
        dashboard = get_dashboard_with_data(dashboard_id)
        print(f"dashboard identifying: {dashboard}")
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard configuration {dashboard_id} not found")
            
        return {
            "success": True,
            "dashboard": dashboard
        }
    
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard configuration: {str(e)}")

@router.delete("/analytics/dashboard-config/{dashboard_id}")
async def delete_dashboard_configuration(dashboard_id: str):
    """Delete a dashboard configuration by ID"""
    try:
        # For custom dashboard IDs, just return success (mock implementation)
        if dashboard_id.startswith("dashboard-"):
            return {
                "success": True,
                "message": f"Dashboard configuration {dashboard_id} deleted successfully"
            }
        
        # Normal case - try MongoDB ObjectId
        result = delete_dashboard(dashboard_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Dashboard configuration {dashboard_id} not found")
            
        return {
            "success": True,
            "message": f"Dashboard configuration {dashboard_id} deleted successfully"
        }
    
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid dashboard ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete dashboard configuration: {str(e)}")
    




@router.post("/analytics/dashboard-config/{dashboard_id}/set-default")
async def set_default_dashboard_route(dashboard_id: str):
    """Set a dashboard as the default dashboard"""
    try:
        # Validate if the dashboard exists
        dashboard = get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        
        # Call the service function to set the default dashboard
        success = set_default_dashboard(dashboard_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set default dashboard")
        
        return {"success": True, "message": f"Dashboard {dashboard_id} set as default"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error setting default dashboard: {str(e)}")
    





@router.get("/dashboards/default")
async def get_default_dashboard_route():
    """Get the default dashboard"""
    try:
        # Call the service function to get the default dashboard
        default_dashboard = get_default_dashboard()
        if not default_dashboard:
            raise HTTPException(status_code=404, detail="Default dashboard not found")
        
        return {"success": True, "dashboard": default_dashboard}
    
    except Exception as e:
        print(f"Error retrieving default dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving default dashboard: {str(e)}")




















@router.get("/customers", response_model=List[Dict[str, Any]])
async def get_all_customers_route(
    search: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """
    Get all customer information from the customer_order_history dataset.
    Supports optional search, pagination, and filtering.
    """
    try:
        customers = get_all_customers(search=search, limit=limit, skip=skip)
        return customers
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))