from fastapi import Depends, HTTPException, status
from functools import wraps
from pymongo.database import Database
from configurations.config import get_db
from routes.security.protected_authorise import get_current_user
from schema.user import UserOutput
import inspect

def dynamic_authorize(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_user: UserOutput = kwargs.get('current_user')
            db: Database = kwargs.get('db')
            if current_user is None or db is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Authentication Credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            print(f"Current User: {current_user}")
            print(f"Resource: {resource}, Action: {action}")

            if current_user.role == "admin":
                print("Admin access granted")
                return await func(*args, **kwargs)
            
            role_permissions = db.roles.find_one({"role": current_user.role})
            print(f"Role Permissions: {role_permissions}")
            
            if not role_permissions or action not in role_permissions.get("permissions", {}).get(resource, []):
                print(f"Permission Denied for role: {current_user.role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to perform this action"
                )
            return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            current_user: UserOutput = kwargs.get('current_user')
            db: Database = kwargs.get('db')
            if current_user is None or db is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Authentication Credentials",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            print(f"Current User: {current_user}")
            print(f"Resource: {resource}, Action: {action}")

            if current_user.role == "admin":
                print("Admin access granted")
                return func(*args, **kwargs)
            
            role_permissions = db.roles.find_one({"role": current_user.role})
            print(f"Role Permissions: {role_permissions}")
            
            if not role_permissions or action not in role_permissions.get("permissions", {}).get(resource, []):
                print(f"Permission Denied for role: {current_user.role}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to perform this action"
                )
            return func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

