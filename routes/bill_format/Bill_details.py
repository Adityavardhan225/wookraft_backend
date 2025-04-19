from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo.database import Database
from typing import Dict, Optional, List
from bson import ObjectId
from configurations.config import get_db
from routes.security.protected_authorise import get_current_user
from datetime import datetime
import logging

router = APIRouter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RestaurantDetails:
    """Model for restaurant details"""
    restaurant_name: str
    address: str
    phone_number: str
    gstin: str
    cgst: float
    sgst: float
    service_tax: float
    fssai_number: str
    sac_code: str
    owner_id: str  # Add owner_id to the model
    

@router.post("/restaurant-details")
async def create_restaurant_details(
    restaurant_name: str = Body(..., description="Restaurant name"),
    address: str = Body(..., description="Restaurant address"),
    phone_number: str = Body(..., description="Restaurant phone number"),
    gstin: str = Body(..., description="GSTIN number"),
    cgst: float = Body(..., description="CGST percentage"),
    sgst: float = Body(..., description="SGST percentage"),
    service_tax: float = Body(..., description="Service tax percentage"),
    fssai_number: str = Body(..., description="FSSAI license number"),
    sac_code: str = Body(..., description="SAC code"),
    token: str = Body(...),
    db: Database = Depends(get_db)
):
    """Create restaurant details. Only one record allowed per owner."""
    try:
        # Verify user is authenticated and has admin rights
        current_user = get_current_user(db, token)
        
        # Only allow admin to create restaurant details
        if current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only admin can create restaurant details")
            
        owner_id = current_user.owner_id
        logger.info(f"Creating restaurant details for owner_id: {owner_id}")
        
        # Check if restaurant details already exist for this owner
        existing = db.restaurant_details.find_one({"owner_id": owner_id})
        if existing:
            logger.warning(f"Restaurant details already exist for owner_id: {owner_id}")
            raise HTTPException(
                status_code=400, 
                detail="Restaurant details already exist. Use the update endpoint."
            )
            
        # Create restaurant details document
        restaurant_data = {
            "owner_id": owner_id,
            "restaurant_name": restaurant_name,
            "address": address,
            "phone_number": phone_number,
            "gstin": gstin,
            "cgst": cgst,
            "sgst": sgst,
            "service_tax": service_tax,
            "fssai_number": fssai_number,
            "sac_code": sac_code,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Insert into database
        result = db.restaurant_details.insert_one(restaurant_data)
        logger.info(f"Restaurant details created with ID: {result.inserted_id} for owner_id: {owner_id}")
        
        # Include owner_id explicitly in the response
        return {
            "message": "Restaurant details created successfully",
            "id": str(result.inserted_id),
            "owner_id": owner_id,
            "data": {**restaurant_data, "_id": str(result.inserted_id)}
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creating restaurant details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.put("/restaurant-details")
async def update_restaurant_details(
    restaurant_name: Optional[str] = Body(None),
    address: Optional[str] = Body(None),
    phone_number: Optional[str] = Body(None),
    gstin: Optional[str] = Body(None),
    cgst: Optional[float] = Body(None),
    sgst: Optional[float] = Body(None),
    service_tax: Optional[float] = Body(None),
    fssai_number: Optional[str] = Body(None),
    sac_code: Optional[str] = Body(None),
    token: str = Body(...),
    db: Database = Depends(get_db)
):
    """Update existing restaurant details."""
    try:
        # Verify user is authenticated and has admin rights
        current_user = get_current_user(db, token)
        
        # Only allow admin to update restaurant details
        if current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only admin can update restaurant details")
            
        owner_id = current_user.owner_id
        logger.info(f"Updating restaurant details for owner_id: {owner_id}")
        
        # Check if restaurant details exist
        existing = db.restaurant_details.find_one({"owner_id": owner_id})
        if not existing:
            logger.warning(f"Restaurant details not found for owner_id: {owner_id}")
            raise HTTPException(status_code=404, detail="Restaurant details not found")
            
        # Build update data with only provided fields
        update_data = {}
        if restaurant_name is not None:
            update_data["restaurant_name"] = restaurant_name
        if address is not None:
            update_data["address"] = address
        if phone_number is not None:
            update_data["phone_number"] = phone_number
        if gstin is not None:
            update_data["gstin"] = gstin
        if cgst is not None:
            update_data["cgst"] = cgst
        if sgst is not None:
            update_data["sgst"] = sgst
        if service_tax is not None:
            update_data["service_tax"] = service_tax
        if fssai_number is not None:
            update_data["fssai_number"] = fssai_number
        if sac_code is not None:
            update_data["sac_code"] = sac_code
            
        # Add updated timestamp
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Update the database
        db.restaurant_details.update_one(
            {"owner_id": owner_id},
            {"$set": update_data}
        )
        logger.info(f"Updated restaurant details for owner_id: {owner_id}")
        
        # Get the updated document
        updated = db.restaurant_details.find_one({"owner_id": owner_id})
        updated["_id"] = str(updated["_id"])  # Convert ObjectId to string
        
        # Include owner_id explicitly in the response
        return {
            "message": "Restaurant details updated successfully",
            "owner_id": owner_id,
            "data": updated
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error updating restaurant details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.get("/restaurant-details")
async def get_restaurant_details(
    token: str,
    db: Database = Depends(get_db)
):
    """Get restaurant details for the current owner."""
    try:
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        owner_id = current_user.owner_id
        logger.info(f"Fetching restaurant details for owner_id: {owner_id}")
        
        # Retrieve restaurant details
        details = db.restaurant_details.find_one({"owner_id": owner_id})
        if not details:
            logger.warning(f"Restaurant details not found for owner_id: {owner_id}")
            raise HTTPException(status_code=404, detail="Restaurant details not found")
            
        # Convert ObjectId to string
        details["_id"] = str(details["_id"])
        
        # Ensure owner_id is in response (it should be, but let's be explicit)
        if "owner_id" not in details:
            details["owner_id"] = owner_id
            
        return details
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving restaurant details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.delete("/restaurant-details")
async def delete_restaurant_details(
    token: str = Body(...),
    db: Database = Depends(get_db)
):
    """Delete restaurant details."""
    try:
        # Verify user is authenticated and has admin rights
        current_user = get_current_user(db, token)
        
        # Only allow admin to delete restaurant details
        if current_user.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Only admin can delete restaurant details")
            
        owner_id = current_user.owner_id
        logger.info(f"Deleting restaurant details for owner_id: {owner_id}")
        
        # Check if restaurant details exist
        existing = db.restaurant_details.find_one({"owner_id": owner_id})
        if not existing:
            logger.warning(f"Restaurant details not found for owner_id: {owner_id}")
            raise HTTPException(status_code=404, detail="Restaurant details not found")
            
        # Delete the document
        result = db.restaurant_details.delete_one({"owner_id": owner_id})
        logger.info(f"Deleted {result.deleted_count} restaurant details for owner_id: {owner_id}")
        
        # Include owner_id explicitly in the response
        return {
            "message": "Restaurant details deleted successfully",
            "owner_id": owner_id
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error deleting restaurant details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")