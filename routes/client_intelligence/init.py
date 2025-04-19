# from fastapi import FastAPI
# from .routes import router as analytics_router
# from .cache import cache_manager
# import logging

# # Setup logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def init_client_intelligence(app: FastAPI, prefix: str = "/api/analytics", redis_host: str = "localhost", redis_port: int = 6379):
#     """
#     Initialize client intelligence module
    
#     Args:
#         app: FastAPI application instance
#         prefix: API route prefix
#         redis_host: Redis host for caching
#         redis_port: Redis port for caching
#     """
#     # Configure Redis connection if needed
#     if redis_host != "localhost" or redis_port != 6379:
#         from .cache import CacheManager
#         global cache_manager
#         cache_manager = CacheManager(host=redis_host, port=redis_port)
    
#     # Include router
#     app.include_router(analytics_router, prefix=prefix, tags=["Analytics"])
    
#     logger.info(f"Client intelligence module initialized with prefix: {prefix}")
#     logger.info(f"Redis cache: {'Connected' if cache_manager.connected else 'Disconnected'}")
    
#     # Return the router for reference
#     return analytics_router

# # Expose key components
# from .models import (
#     Dashboard, DashboardCreate, DashboardUpdate, DashboardResponse,
#     ChartConfig, ChartCreate, ChartUpdate, ChartResponse,
#     QueryRequest, QueryResponse,
#     Dataset, DatasetResponse
# )

# from .services import (
#     get_dashboard, get_all_dashboards, create_dashboard, update_dashboard, delete_dashboard,
#     toggle_dashboard_favorite, get_recent_dashboards, get_favorite_dashboards,
#     get_chart, get_all_charts, create_chart, update_chart, delete_chart,
#     execute_query, get_datasets, get_dataset,
#     generate_insights
# )

# # Version information
# __version__ = "0.1.0"














from fastapi import FastAPI
from .routes import router as analytics_router
from .cache import cache_manager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_client_intelligence(app: FastAPI, prefix: str = "/api/analytics", redis_host: str = "localhost", redis_port: int = 6379):
    """
    Initialize client intelligence module
    
    Args:
        app: FastAPI application instance
        prefix: API route prefix
        redis_host: Redis host for caching
        redis_port: Redis port for caching
    """
    # Configure Redis connection if needed
    if redis_host != "localhost" or redis_port != 6379:
        from .cache import CacheManager
        global cache_manager
        cache_manager = CacheManager(host=redis_host, port=redis_port)
    
    # Include router
    app.include_router(analytics_router, prefix=prefix, tags=["Analytics"])
    
    logger.info(f"Client intelligence module initialized with prefix: {prefix}")
    logger.info(f"Redis cache: {'Connected' if cache_manager.connected else 'Disconnected'}")
    
    # Return the router for reference
    return analytics_router

# Expose key components
from .models import (
    Dashboard, DashboardCreate, DashboardUpdate, DashboardResponse,
    ChartConfig, ChartCreate, ChartUpdate, ChartResponse,
    QueryRequest, QueryResponse,
    Dataset, DatasetResponse
)

from .services import (
    # Existing exports
    get_dashboard, get_all_dashboards, create_dashboard, update_dashboard, delete_dashboard,
    toggle_dashboard_favorite, get_recent_dashboards, get_favorite_dashboards,
    get_chart, get_all_charts, create_chart, update_chart, delete_chart,
    execute_query, get_datasets, get_dataset,
    generate_insights,
    
    # New dashboard template functions
    get_dashboard_templates,
    
    # Default dashboard functions
    set_default_dashboard, get_default_dashboard,
    
    # Dashboard items management
    get_dashboard_items, update_dashboard_item, create_dashboard_item, delete_dashboard_item,
    
    # Editing state management
    set_dashboard_editing_state,
    
    # Dashboard with data
    get_dashboard_with_data,
    
    # Undo/Redo functions
    undo_dashboard_change, redo_dashboard_change, get_dashboard_history,
    
    # Permission checking
    get_user_dashboard_permissions,
    
    # Selected/Focused items management
    set_dashboard_selected_items, get_dashboard_selected_items,
    set_dashboard_focused_item, get_dashboard_focused_item
)

# Version information
__version__ = "0.1.0"