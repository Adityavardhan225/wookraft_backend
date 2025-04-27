from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from configurations.config import get_db
from routes.security.protected_authorise import get_current_user
from schema.user import UserOutput
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()

class RolePermission(BaseModel):
    role: str
    permissions: Dict[str, List[str]]

@router.post("/roles", status_code=201)
async def add_role_permission(role_permission: RolePermission, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    
    existing_role = db.roles.find_one({"role": role_permission.role})
    if existing_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role already exists")
    
    db.roles.insert_one(role_permission.dict())
    return {"message": "Role permission added successfully"}

@router.put("/roles/{role}", status_code=200)
async def update_role_permission(role: str, role_permission: RolePermission, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    
    db.roles.update_one({"role": role}, {"$set": role_permission.dict()})
    return {"message": "Role permission updated successfully"}

@router.delete("/roles/{role}", status_code=200)
async def delete_role_permission(role: str, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
    
    db.roles.delete_one({"role": role})
    return {"message": "Role permission deleted successfully"}


@router.get("/all-roles", status_code=200)
async def get_all_access_control(db: Database = Depends(get_db)):
    """
    Get all roles and their associated permissions.
    :param db: The database connection.
    :return: List of all roles and their permissions.
    """
    try:
        # Fetch all role documents from the database
        all_roles = list(db.roles.find({}, {"_id": 0}))
        
        if not all_roles:
            return {"message": "No roles found", "roles": []}
            
        return {"roles": all_roles, "count": len(all_roles)}
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve roles: {str(e)}"
        )