from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
from bson import ObjectId
from .services import (
    get_collection_for_dataset,
    is_valid_object_id,
    send_email_with_cloudinary_attachments,
    get_bill_details_by_order_id,
    is_valid_object_id_st,
    get_bill_details_by_order_id,
    get_bill_details_by_bill_number,
    get_all_bills
)

from routes.client_intelligence.services import get_all_customers



from fastapi import APIRouter, HTTPException, Form, UploadFile, File, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import cloudinary.uploader
import asyncio
import logging
import os
import uuid
from datetime import datetime
from .services import get_collection_for_dataset, is_valid_object_id, send_email_with_cloudinary_attachments
from routes.security.protected_authorise import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Define email response model
class EmailResponse(BaseModel):
    message: str
    details: Dict[str, Any]







@router.get("/customers/statistics", response_model=Dict[str, Any])
async def get_customer_statistics():
    """
    Retrieve aggregated metrics across all customers.
    """
    try:
        print('Fetching customer statistics...')
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            print("Customer dataset not found")
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        print("Customer dataset found")    
        total_customers = collection.count_documents({})
        print(f"total_customers: {total_customers}")
        active_customers = collection.count_documents({"status": "active"})
        print(f"active_customers: {active_customers}")
        new_customers = collection.count_documents({"first_visit": {"$gte": datetime.now() - timedelta(days=30)}})
        print(f"total_customers: {total_customers}, active_customers: {active_customers}, new_customers: {new_customers}")
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "new_customers": new_customers
        }
    except Exception as e:
        
        raise HTTPException(status_code=500, detail="An error occurred while fetching customer statistics.")


# Specialized Filtering APIs

@router.get("/customers/active", response_model=List[Dict[str, Any]])
async def get_active_customers(status: str = "active", limit: int = 100, skip: int = 0):
    """
    Filter customers by status (active, inactive, vip).
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        customers = list(collection.find({"status": status}).skip(skip).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/top-spenders", response_model=List[Dict[str, Any]])
async def get_top_spending_customers(limit: int = 10):
    """
    Retrieve highest-value customers.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        customers = list(collection.find().sort("total_spent", -1).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/frequent", response_model=List[Dict[str, Any]])
async def get_most_frequent_customers(limit: int = 10):
    """
    Retrieve customers with most orders.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        customers = list(collection.find().sort("total_visits", -1).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/spending-tiers", response_model=Dict[str, List[Dict[str, Any]]])
async def get_customers_by_spending_tier(high: float = 1000, medium: float = 500):
    """
    Categorize customers by spending level.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        high_spenders = list(collection.find({"total_spent": {"$gte": high}}))
        medium_spenders = list(collection.find({"total_spent": {"$gte": medium, "$lt": high}}))
        low_spenders = list(collection.find({"total_spent": {"$lt": medium}}))
        
        for customer in high_spenders + medium_spenders + low_spenders:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        
        return {
            "high_spenders": high_spenders,
            "medium_spenders": medium_spenders,
            "low_spenders": low_spenders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



# @router.get("/customers", response_model=List[Dict[str, Any]])
# async def get_all_customers_route(
#     search: Optional[str] = None,
#     limit: int = 100,
#     skip: int = 0
# ):
#     """
#     Get all customer information from the customer_order_history dataset.
#     Supports optional search, pagination, and filtering.
#     """
#     try:
#         customers = get_all_customers(search=search, limit=limit, skip=skip)
#         print(f'customers: {customers}')
#         return customers
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))
    



@router.get("/customers", response_model=Dict[str, Any])
async def get_all_customers_route(
    search: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    filters: Optional[str] = Query(None)
):
    """
    Get all customer information with pagination and filtering.
    """
    try:
        # Calculate skip from page
        skip = (page - 1) * limit
        
        # Parse filters if provided
        filter_obj = {}
        if filters and filters != "[object Object]":
            try:
                filter_obj = json.loads(filters)
            except:
                pass
        
        customers = get_all_customers(search=search, limit=limit, skip=skip)
        total = len(customers)  # Or get total count from service
        
        return {
            "success": True,
            "data": customers,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/customers/{customer_id}", response_model=Dict[str, Any])
async def get_customer_by_id(customer_id: str):
    """
    Retrieve detailed information for a single customer.
    """

    print(f'customer_id: {customer_id}')
    try:
        print(1)
        collection = get_collection_for_dataset("customer_order_history")
        print(f'collection is  {collection}')
        if collection is None:
            print(22)
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        print(2)
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
        print(3)
        customer = collection.find_one({"_id": customer_id})
        print(f'customer: {customer}')
        if customer is None:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        print(4)
        customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers/{customer_id}/orders", response_model=List[Dict[str, Any]])
async def get_customer_orders(customer_id: str, limit: int = 10, skip: int = 0):
    """
    Retrieve order history for a specific customer.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
        
        customer = collection.find_one({"_id": customer_id})
        if not customer or "orders" not in customer:
            raise HTTPException(status_code=404, detail=f"No orders found for customer {customer_id}")
        
        orders = customer["orders"][skip: skip + limit]
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/customers/{customer_id}", response_model=Dict[str, Any])
async def update_customer(customer_id: str, customer_data: Dict[str, Any]):
    """
    Modify customer information (contact details, status, tags).
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
        
        result = collection.update_one(
            {"_id": customer_id},
            {"$set": customer_data}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        
        updated_customer = collection.find_one({"_id": customer_id})
        updated_customer["_id"] = str(updated_customer["_id"])  # Convert ObjectId to string
        return updated_customer
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/customers/{customer_id}")
async def delete_customer(customer_id: str):
    """
    Remove a customer from the system.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
        
        result = collection.delete_one({"_id": customer_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        
        return {"message": f"Customer {customer_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Additional Customer Data APIs

@router.post("/customers/{customer_id}/notes", response_model=List[Dict[str, Any]])
async def add_customer_note(customer_id: str, note: Dict[str, Any]):
    """
    Attach notes/comments to a customer profile.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
        
        note["date"] = datetime.now()  # Add timestamp to the note
        result = collection.update_one(
            {"_id": customer_id},
            {"$push": {"notes": note}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
        
        customer = collection.find_one({"_id": customer_id})
        return customer.get("notes", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# @router.post("/customers/{customer_id}/email", response_model=Dict[str, Any])
# async def send_email_to_customer(customer_id: str, email_data: EmailRequest):
#     """
#     Send an email to a customer.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if collection is None:
#             raise HTTPException(status_code=404, detail="Customer dataset not found")
            
#         if not is_valid_object_id(customer_id):
#             raise HTTPException(status_code=400, detail="Invalid customer ID format")
            
#         customer = collection.find_one({"_id": customer_id})
#         if customer is None:
#             raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
            
#         if "email" not in customer or not customer["email"]:
#             raise HTTPException(status_code=400, detail="Customer does not have an email address")
            
#         result = await send_email_to_customer_service(
#             customer["email"], 
#             email_data.subject, 
#             email_data.body, 
#             email_data.attachments
#         )
#         return {"message": "Email sent successfully", "details": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))









@router.post("/customers/{customer_id}/email", response_model=EmailResponse)
async def send_email_to_customer(
    customer_id: str,
    subject: str = Form(...),
    body: str = Form(...),
    attachments: List[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Send an email to a customer with optional attachments.
    Attachments are temporarily stored in Cloudinary before being included in the email.
    """
    try:
        # 1. Get customer from database
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:
            raise HTTPException(status_code=404, detail="Customer dataset not found")
            
        if not is_valid_object_id(customer_id):
            raise HTTPException(status_code=400, detail="Invalid customer ID format")
            
        customer = collection.find_one({"_id": customer_id})
        if not customer:
            raise HTTPException(status_code=404, detail=f"Customer with ID {customer_id} not found")
            
        if "email" not in customer or not customer["email"]:
            raise HTTPException(status_code=400, detail="Customer does not have an email address")
        

                # Debug logging
        print(f"Sending email to {customer['email']}")
        print(f"Subject: {subject}")
        print(f"Attachments: {len(attachments) if attachments else 0}")
            
        # 2. Send email using service with cloudinary attachments
        result = await send_email_with_cloudinary_attachments(
            recipient_email=customer["email"],
            subject=subject,
            body=body,
            attachments=attachments if attachments else [],
            user_id=current_user.owner_id,
        )
        
        return {
            "message": "Email sent successfully",
            "details": result
        }
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    








# Router implementation for bill endpoints
from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Dict, Any, List, Optional
from .services import (
    get_bill_details_by_order_id,
    get_bill_details_by_bill_number,
    get_all_bills,
    is_valid_object_id_st
)
from routes.security.protected_authorise import get_current_user
import logging



@router.get("/bills", response_model=List[Dict[str, Any]])
async def get_bills_route(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of bills to return"),
    skip: int = Query(0, ge=0, description="Number of bills to skip"),
    start_date: Optional[str] = Query(None, description="Filter bills by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter bills by end date (YYYY-MM-DD)"),
    customer_name: Optional[str] = Query(None, description="Filter bills by customer name"),
    customer_phone: Optional[str] = Query(None, description="Filter bills by customer phone"),
    table_number: Optional[int] = Query(None, description="Filter bills by table number"),
    employee_id: Optional[str] = Query(None, description="Filter bills by employee ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a list of bills with optional filtering.
    """
    try:
        # Build filter criteria
        filters = {}
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if customer_name:
            filters["customer_name"] = customer_name
        if customer_phone:
            filters["customer_phone"] = customer_phone
        if table_number:
            filters["table_number"] = table_number
        if employee_id:
            filters["employee_id"] = employee_id
            
        # Get owner_id from current user
        # Handle both dictionary and object access
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        print(f'owner_id: {owner_id}')
        print(f'filters: {filters}')
        print(f'limit: {limit}')
        print(f'skip: {skip}')
        bills = await get_all_bills(limit=limit, skip=skip, filters=filters)
        print(f'bills: {bills}')
        return bills
        
    except Exception as e:
        logger.error(f"Error retrieving bills: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bills")

@router.get("/orders/{order_id}/bill", response_model=Dict[str, Any])
async def get_bill_by_order_id_route(
    order_id: str = Path(..., description="Order ID to fetch bill details for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve bill details by order ID.
    """
    try:
        # Get owner_id from current user, handling both object and dict types
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get bill details from service
        bill_details = await get_bill_details_by_order_id(
            order_id=order_id,
            
        )
        
        if not bill_details:
            raise HTTPException(status_code=404, detail=f"No bill found for order ID: {order_id}")
            
        return bill_details
        
    except ValueError as e:
        logger.error(f"Error retrieving bill details: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving bill details: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bill details")

@router.get("/bills/{bill_number}", response_model=Dict[str, Any])
async def get_bill_by_number_route(
    bill_number: str = Path(..., description="Bill number to fetch (e.g., INV-c8ebdc)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve bill details by bill number.
    """
    try:
        # Get owner_id from current user, handling both object and dict types
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        # Get bill details from service
        bill_details = await get_bill_details_by_bill_number(
            bill_number=bill_number,
            
        )
        
        if not bill_details:
            raise HTTPException(status_code=404, detail=f"No bill found with number: {bill_number}")
            
        return bill_details
        
    except ValueError as e:
        logger.error(f"Error retrieving bill details: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error retrieving bill details: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving bill details")

@router.get("/employee/{employee_id}/bills", response_model=List[Dict[str, Any]])
async def get_bills_by_employee_route(
    employee_id: str = Path(..., description="Employee ID to fetch bills for"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of bills to return"),
    skip: int = Query(0, ge=0, description="Number of bills to skip"),
    start_date: Optional[str] = Query(None, description="Filter bills by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter bills by end date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve bills handled by a specific employee.
    """
    try:
        # Build filter criteria
        filters = {
            "employee_id": employee_id
        }
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
            
        # Get owner_id from current user, handling both object and dict types
        owner_id = None
        if hasattr(current_user, 'owner_id'):
            owner_id = current_user.owner_id
        elif isinstance(current_user, dict) and "owner_id" in current_user:
            owner_id = current_user["owner_id"]
        
        bills = await get_all_bills(limit=limit, skip=skip, filters=filters)
        return bills
        
    except Exception as e:
        logger.error(f"Error retrieving bills for employee {employee_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving employee bills")