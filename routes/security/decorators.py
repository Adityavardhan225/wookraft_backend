# from functools import wraps
# from fastapi import HTTPException, Depends
# from routes.security.protected_authorise import get_current_user
# from schema.user import UserOutput

# VALID_ROLES = ["admin", "waiter", "kds", "transaction", "manager"]

# def authorize(roles: list):
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, current_user: UserOutput = Depends(get_current_user), **kwargs):
#             if not current_user or current_user.role not in roles:
#                 raise HTTPException(status_code=403, detail="User is not authorized to access this resource")
#             return await func(*args, current_user=current_user, **kwargs)
#         return wrapper
#     return decorator








from functools import wraps
from fastapi import HTTPException, Depends
from routes.security.protected_authorise import get_current_user
from schema.user import UserOutput
from pymongo.database import Database
from configurations.config import get_db

def authorize(resource: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db), **kwargs):
            if not current_user:
                raise HTTPException(status_code=403, detail="User is not authorized to access this resource")
            
            # Fetch allowed roles for the resource from the database
            access_control = db.access_control.find_one({"resource": resource})
            if not access_control or current_user.role not in access_control["allowed_roles"]:
                raise HTTPException(status_code=403, detail="User is not authorized to access this resource")
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator