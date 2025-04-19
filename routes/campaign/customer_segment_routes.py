# from fastapi import APIRouter, HTTPException, Depends, Query, Path, File, UploadFile, Form
# from typing import List, Dict, Any, Optional
# from pydantic import BaseModel
# import logging
# import json
# from .customer_segment_services import (
#     get_all_segments,
#     get_segment_by_id,
#     create_segment,
#     update_segment,
#     delete_segment,
#     count_customers_for_criteria,
#     get_customers_for_criteria,
#     count_customers_for_combined_criteria,
#     get_customers_for_combined_criteria,
#     get_filter_fields,
#     import_customers_from_csv
# )
# from routes.security.protected_authorise import get_current_user

# router = APIRouter()
# logger = logging.getLogger(__name__)

# # Pydantic models for request validation
# class FilterCondition(BaseModel):
#     field: str
#     operator: str
#     value: Any

# class FilterCriteria(BaseModel):
#     operator: str = "AND"
#     conditions: List[FilterCondition]

# class SegmentCreate(BaseModel):
#     name: str
#     description: Optional[str] = None
#     criteria: FilterCriteria

# class SegmentUpdate(BaseModel):
#     name: Optional[str] = None
#     description: Optional[str] = None
#     criteria: Optional[FilterCriteria] = None

# class CombinedCriteriaRequest(BaseModel):
#     segmentIds: Optional[List[str]] = []
#     customFilters: Optional[List[FilterCondition]] = []
#     operator: str = "AND"

# # Customer Segments Management

# @router.get("/segments", response_model=Dict[str, Any])
# async def get_segments_route(
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Retrieve all customer segments (predefined and custom).
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         segments = await get_all_segments(owner_id)
#         return {"success": True, "data": segments}
        
#     except Exception as e:
#         logger.error(f"Error retrieving segments: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/segments/{segment_id}", response_model=Dict[str, Any])
# async def get_segment_by_id_route(
#     segment_id: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Retrieve a specific segment by ID.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         segment = await get_segment_by_id(segment_id, owner_id)
#         if not segment:
#             raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
#         return {"success": True, "data": segment}
        
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         logger.error(f"Error retrieving segment: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/segments", response_model=Dict[str, Any])
# async def create_segment_route(
#     segment: SegmentCreate,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Create a new customer segment.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         # Convert Pydantic model to dict
#         segment_data = segment.dict()
        
#         created_segment = await create_segment(segment_data, owner_id)
#         return {"success": True, "data": created_segment}
        
#     except Exception as e:
#         logger.error(f"Error creating segment: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.put("/segments/{segment_id}", response_model=Dict[str, Any])
# async def update_segment_route(
#     segment_id: str,
#     segment: SegmentUpdate,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Update an existing customer segment.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         # Convert Pydantic model to dict, excluding None values
#         segment_data = {k: v for k, v in segment.dict().items() if v is not None}
        
#         updated_segment = await update_segment(segment_id, segment_data, owner_id)
#         if not updated_segment:
#             raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
#         return {"success": True, "data": updated_segment}
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"Error updating segment: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.delete("/segments/{segment_id}", response_model=Dict[str, Any])
# async def delete_segment_route(
#     segment_id: str,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Delete a customer segment.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         result = await delete_segment(segment_id, owner_id)
#         if not result:
#             raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
#         return {"success": True, "message": f"Segment {segment_id} deleted successfully"}
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"Error deleting segment: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# # Segmentation Operations

# @router.post("/count", response_model=Dict[str, Any])
# async def count_customers_route(
#     criteria: CombinedCriteriaRequest,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Count customers matching the combined criteria of segments and filters.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         count = await count_customers_for_combined_criteria(
#             segment_ids=criteria.segmentIds,
#             custom_filters=criteria.customFilters,
#             operator=criteria.operator,
#             owner_id=owner_id
#         )
        
#         return {"success": True, "count": count}
        
#     except Exception as e:
#         logger.error(f"Error counting customers: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/preview", response_model=Dict[str, Any])
# async def preview_customers_route(
#     criteria: CombinedCriteriaRequest,
#     limit: int = Query(5, ge=1, le=100),
#     offset: int = Query(0, ge=0),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Preview customers matching the combined criteria of segments and filters.
#     """
#     try:
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         result = await get_customers_for_combined_criteria(
#             segment_ids=criteria.segmentIds,
#             custom_filters=criteria.customFilters,
#             operator=criteria.operator,
#             limit=limit,
#             skip=offset,
#             owner_id=owner_id
#         )
        
#         return {
#             "success": True,
#             "total": result["total"],
#             "customers": result["customers"]
#         }
        
#     except Exception as e:
#         logger.error(f"Error previewing customers: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/filter-fields", response_model=Dict[str, Any])
# async def get_filter_fields_route(
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Get available customer fields for filtering.
#     """
#     try:
#         fields = await get_filter_fields()
#         return {"success": True, "fields": fields}
        
#     except Exception as e:
#         logger.error(f"Error retrieving filter fields: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/import", response_model=Dict[str, Any])
# async def import_customers_route(
#     file: UploadFile = File(...),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Import customers from a CSV file.
#     """
#     try:
#         # Validate file type
#         if not file.filename.endswith('.csv'):
#             raise HTTPException(status_code=400, detail="File must be a CSV")
        
#         # Get owner_id from current user
#         owner_id = None
#         if hasattr(current_user, 'owner_id'):
#             owner_id = current_user.owner_id
#         elif isinstance(current_user, dict) and "owner_id" in current_user:
#             owner_id = current_user["owner_id"]
        
#         result = await import_customers_from_csv(file, owner_id)
#         return result
        
#     except Exception as e:
#         logger.error(f"Error importing customers: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))















































from fastapi import APIRouter, HTTPException, Depends, Query, Path, File, UploadFile, Form, BackgroundTasks
from typing import List, Dict, Any, Optional
import logging
import json
from .customer_segment_models import (
    FilterCondition,
    FilterCriteria,
    SegmentCreate,
    SegmentUpdate,
    CombinedCriteriaRequest,
    RefreshSettings
)
from .customer_segment_services import (
    get_all_segments,
    get_segment_by_id,
    create_segment,
    update_segment,
    delete_segment,
    count_customers_for_criteria,
    get_customers_for_criteria,
    count_customers_for_combined_criteria,
    get_customers_for_combined_criteria,
    get_filter_fields,
    import_customers_from_csv,
    is_valid_object_id
)
from .segment_membership_services import (
    get_materialized_segment_customers,
    get_customer_segment_membership,
    remove_customer_from_segments
)
from .segment_scheduler import (
    refresh_segment_membership,
    get_segment_refresh_job
)
from routes.security.protected_authorise import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Customer Segments Management

@router.get("/segments", response_model=Dict[str, Any])
async def get_segments_route(
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve all customer segments (predefined and custom).
    """
    try:
        segments = await get_all_segments()
        return {"success": True, "data": segments}
        
    except Exception as e:
        logger.error(f"Error retrieving segments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/segments/{segment_id}", response_model=Dict[str, Any])
async def get_segment_by_id_route(
    segment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific segment by ID.
    """
    try:
        segment = await get_segment_by_id(segment_id)
        if not segment:
            raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
        return {"success": True, "data": segment}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/segments", response_model=Dict[str, Any])
async def create_segment_route(
    segment: SegmentCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new customer segment.
    """
    try:
        # Convert Pydantic model to dict
        segment_data = segment.dict()
        
        created_segment = await create_segment(segment_data)
        return {"success": True, "data": created_segment}
        
    except Exception as e:
        logger.error(f"Error creating segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/segments/{segment_id}", response_model=Dict[str, Any])
async def update_segment_route(
    segment_id: str,
    segment: SegmentUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing customer segment.
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        segment_data = {k: v for k, v in segment.dict().items() if v is not None}
        
        updated_segment = await update_segment(segment_id, segment_data)
        if not updated_segment:
            raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
        return {"success": True, "data": updated_segment}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/segments/{segment_id}", response_model=Dict[str, Any])
async def delete_segment_route(
    segment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a customer segment.
    """
    try:
        result = await delete_segment(segment_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
        
        return {"success": True, "message": f"Segment {segment_id} deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Segment Membership Operations

@router.post("/segments/{segment_id}/refresh", response_model=Dict[str, Any])
async def refresh_segment_route(
    segment_id: str,
    background_tasks: BackgroundTasks,
    full_refresh: bool = Query(False, description="Whether to do a full refresh of all customer data"),
    wait: bool = Query(False, description="Whether to wait for refresh to complete"),
    current_user: dict = Depends(get_current_user)
):
    """
    Start a segment membership refresh.
    """
    try:
        # Check if segment exists
        segment = await get_segment_by_id(segment_id)
        if not segment:
            raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
            
        if wait:
            # Execute synchronously
            result = await refresh_segment_membership(segment_id, full_refresh)
            return {
                "success": True,
                "data": result
            }
        else:
            # Schedule as background task
            background_tasks.add_task(refresh_segment_membership, segment_id, full_refresh)
            return {
                "success": True,
                "message": f"Refresh for segment {segment_id} scheduled",
                "data": {
                    "segment_id": segment_id,
                    "status": "scheduled"
                }
            }
            
    except Exception as e:
        logger.error(f"Error refreshing segment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/segments/{segment_id}/customers", response_model=Dict[str, Any])
async def get_segment_customers_route(
    segment_id: str,
    page: int = Query(0, ge=0, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    refresh: bool = Query(False, description="Whether to refresh membership data first"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """
    Get customers in a segment.
    """
    try:
        # Check if segment exists
        segment = await get_segment_by_id(segment_id)
        if not segment:
            raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
            
        # If refresh requested, schedule in background
        if refresh:
            background_tasks.add_task(refresh_segment_membership, segment_id)
            
        # Get customers from materialized data
        result = await get_materialized_segment_customers(
            segment_id=segment_id,
            page=page,
            page_size=page_size
        )
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error retrieving segment customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers/{customer_id}/segments", response_model=Dict[str, Any])
async def get_customer_segments_route(
    customer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get segments a customer belongs to.
    """
    try:
        # Get customer segment membership
        membership = await get_customer_segment_membership(customer_id)
        
        # Get full segment details
        segments = []
        for segment_id in membership.get("segment_ids", []):
            segment = await get_segment_by_id(segment_id)
            if segment:
                segments.append(segment)
                
        return {
            "success": True,
            "data": {
                "customer_id": customer_id,
                "segments": segments
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving customer segments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/customers/{customer_id}/segments", response_model=Dict[str, Any])
async def remove_customer_from_segments_route(
    customer_id: str,
    segment_ids: List[str] = Query(None, description="Segment IDs to remove from (empty for all)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Remove a customer from segments.
    """
    try:
        result = await remove_customer_from_segments(customer_id, segment_ids)
        
        return {
            "success": result,
            "message": f"Customer {customer_id} removed from segments"
        }
        
    except Exception as e:
        logger.error(f"Error removing customer from segments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Segmentation Operations

@router.post("/count", response_model=Dict[str, Any])
async def count_customers_route(
    criteria: CombinedCriteriaRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Count customers matching the combined criteria of segments and filters.
    """
    try:
        count = await count_customers_for_combined_criteria(
            segment_ids=criteria.segmentIds,
            custom_filters=criteria.customFilters,
            operator=criteria.operator
        )
        
        return {"success": True, "count": count}
        
    except Exception as e:
        logger.error(f"Error counting customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preview", response_model=Dict[str, Any])
async def preview_customers_route(
    criteria: CombinedCriteriaRequest,
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview customers matching the combined criteria of segments and filters.
    """
    try:
        print(f'criteria: {criteria}')
        result = await get_customers_for_combined_criteria(
            segment_ids=criteria.segmentIds,
            custom_filters=criteria.customFilters,
            operator=criteria.operator,
            limit=limit,
            skip=offset
        )
        print(f'result: {result}')
        return {
            "success": True,
            "total": result["total"],
            "customers": result["customers"]
        }
        
    except Exception as e:
        logger.error(f"Error previewing customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/filter-fields", response_model=Dict[str, Any])
async def get_filter_fields_route(
    current_user: dict = Depends(get_current_user)
):
    """
    Get available customer fields for filtering.
    """
    try:
        fields = await get_filter_fields()
        print(f'fields: {fields}')
        return {"success": True, "fields": fields}
        
    except Exception as e:
        logger.error(f"Error retrieving filter fields: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import", response_model=Dict[str, Any])
async def import_customers_route(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Import customers from a CSV file.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        result = await import_customers_from_csv(file)
        return result
        
    except Exception as e:
        logger.error(f"Error importing customers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/refresh-jobs/{job_id}", response_model=Dict[str, Any])
async def get_refresh_job_route(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of a segment refresh job.
    """
    try:
        job = await get_segment_refresh_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
            
        return {"success": True, "data": job}
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    





# Add this import at the top:
from .segment_templates import get_template_definitions, get_template_by_id, build_segment_from_template

# Add these new routes to the file:

@router.get("/templates", response_model=Dict[str, Any])
async def get_segment_templates_route(
    current_user: dict = Depends(get_current_user)
):
    """
    Get all available segment templates.
    """
    try:
        templates = get_template_definitions()
        
        # Group templates by category
        categories = {}
        for template in templates:
            category = template.get("category", "other")
            if category not in categories:
                categories[category] = []
            categories[category].append(template)
        
        return {
            "success": True,
            "data": {
                "templates": templates,
                "categories": categories
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving segment templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_segment_template_by_id_route(
    template_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get segment template by ID.
    """
    try:
        template = get_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
        
        return {
            "success": True,
            "data": template
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving segment template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/segments/from-template", response_model=Dict[str, Any])
async def create_segment_from_template_route(
    template_id: str = Form(...),
    params: str = Form("{}"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a segment from a template.
    """
    try:
        # Parse params
        params_dict = json.loads(params)
        
        # Build segment from template
        segment_data = await build_segment_from_template(template_id, params_dict)
        
        # Create segment
        created_segment = await create_segment(segment_data)
        
        return {
            "success": True,
            "data": created_segment
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating segment from template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    



# Add this import at the top:
from .segment_analytics import analyze_segment_overlap, analyze_customer_lifecycle

# Add these new routes to the file:

@router.post("/analyze/overlap", response_model=Dict[str, Any])
async def analyze_segment_overlap_route(
    segment_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze overlap between segments.
    """
    try:
        # Validate segment IDs
        for segment_id in segment_ids:
            segment = await get_segment_by_id(segment_id)
            if not segment:
                raise HTTPException(status_code=404, detail=f"Segment with ID {segment_id} not found")
                
        # Analyze overlap
        result = await analyze_segment_overlap(segment_ids)
        
        return {
            "success": True,
            "data": result
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error analyzing segment overlap: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/customers/{customer_id}/lifecycle", response_model=Dict[str, Any])
async def analyze_customer_lifecycle_route(
    customer_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze customer lifecycle and spending patterns.
    """
    try:
        # Validate customer ID
        if not customer_id or not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID")
            
        # Analyze lifecycle
        result = await analyze_customer_lifecycle(customer_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing customer lifecycle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))