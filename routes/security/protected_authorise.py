from routes.service.userService import UserService
from fastapi import Depends, HTTPException, status
from pymongo.database import Database
from routes.security.authHandler import AuthHandler
from configurations.config import get_db
from schema.user import UserOutput
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(
        db: Database = Depends(get_db), 

        token: str = Depends(oauth2_scheme)
) -> UserOutput:
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Authentication hjh Credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    payload = AuthHandler.decode_jwt(token=token)
    print("Payload: ", payload)

    if payload and payload.get("user_id"):
        try:
            user = UserService(db=db).get_user_by_id(payload["user_id"])
            print("User: ", user)
            return UserOutput(
                owner_id=str(user["owner_id"]),
                first_name=user["first_name"],
                last_name=user["last_name"],
                email=user["email"],
                workplace_name=user["workplace_name"],
                phone_number=user["phone_number"],
                role=user["role"],
                employee_id=user["employee_id"],
                id=str(user["_id"])
            )
        except Exception as error:
            print(f"Error: {error}")
            raise auth_exception
    print("No Payload")
    raise auth_exception

