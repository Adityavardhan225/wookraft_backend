# from fastapi import APIRouter, Depends, HTTPException
# from pymongo.database import Database
# from configurations.config import get_db
# from routes.security.decorators import authorize

# adminRouter = APIRouter()

# @adminRouter.post("/access-control", status_code=201)
# async def add_access_control(resource: str, allowed_roles: list, db: Database = Depends(get_db)):
#     print(f"Adding access control for resource: {resource} with roles: {allowed_roles}")
#     db.access_control.update_one(
#         {"resource": resource},
#         {"$set": {"allowed_roles": allowed_roles}},
#         upsert=True
#     )
#     return {"message": "Access control updated"}

# @adminRouter.get("/access-control", status_code=200)
# async def get_access_control(resource: str, db: Database = Depends(get_db)):
#     access_control = db.access_control.find_one({"resource": resource})
#     if not access_control:
#         raise HTTPException(status_code=404, detail="Resource not found")
#     return access_control

















from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from configurations.config import get_db
from routes.security.decorators import authorize

adminRouter = APIRouter()

@adminRouter.post("/access-control", status_code=201)
async def add_access_control(role: str, resources: dict, db: Database = Depends(get_db)):
    """
    Add access control for a role with multiple resources and actions.
    :param role: The role to add access control for.
    :param resources: A dictionary where keys are resource names and values are lists of actions.
    :param db: The database connection.
    """
    print(f"Adding access control for role: {role} with resources: {resources}")
    
    # Fetch existing role permissions
    role_permissions = db.roles.find_one({"role": role})
    
    if not role_permissions:
        # If the role does not exist, create a new entry
        role_permissions = {"role": role, "permissions": {}}
    
    # Update the permissions with new resources and actions
    for resource, actions in resources.items():
        if resource not in role_permissions["permissions"]:
            role_permissions["permissions"][resource] = []
        for action in actions:
            if action not in role_permissions["permissions"][resource]:
                role_permissions["permissions"][resource].append(action)
    
    # Update the role permissions in the database
    db.roles.update_one(
        {"role": role},
        {"$set": {"permissions": role_permissions["permissions"]}},
        upsert=True
    )
    
    return {"message": "Access control updated"}

@adminRouter.get("/access-control", status_code=200)
async def get_access_control(role: str, db: Database = Depends(get_db)):
    """
    Get access control for a role.
    :param role: The role to get access control for.
    :param db: The database connection.
    """
    role_permissions = db.roles.find_one({"role": role})
    if not role_permissions:
        raise HTTPException(status_code=404, detail="Role not found")
    return role_permissions


@adminRouter.get("/roles", status_code=200)
async def get_all_roles(search: str = None, db: Database = Depends(get_db)):
    """
    Get all roles from the database with optional search filter.
    """
    try:
        # Get all roles
        roles = list(db.roles.find({}))
        
        # Process _id to string
        for role in roles:
            if "_id" in role:
                role["id"] = str(role["_id"])
                del role["_id"]
        
        # Apply search filter if provided
        if search:
            search_term = search.lower()
            roles = [
                role for role in roles 
                if search_term in role.get("role", "").lower()
            ]
        
        return roles
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve roles: {str(e)}")