from fastapi import APIRouter, Depends, HTTPException, Header
from schema.user import UserInCreate, UserWithToken, UserOutput
from configurations.config import get_db
from routes.service.userService import UserService
from pymongo.database import Database
from routes.security.auth import get_current_user_verify
from fastapi.security import OAuth2PasswordRequestForm
from routes.security.auth import create_access_token
from pydantic import BaseModel
from schema.adminUserSchema import CreateUserRequest
from routes.service.adminUserService import AdminUserService
from routes.security.protected_authorise import get_current_user

authRouter = APIRouter()


# Add this to the existing models
class ForgotPasswordRequest(BaseModel):
    email: str
    role: str
    workplace: str

class UserWithToken(BaseModel):
    access_token: str
    token_type: str
    role: str

class VerifyEmailRequest(BaseModel):
    email: str
    otp: str

class EmailRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str

@authRouter.post("/generate-otp", status_code=200)
async def generate_otp(email: str, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.generate_otp(email)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@authRouter.post("/verify-otp-and-signup", status_code=201, response_model=UserOutput)
async def verify_otp_and_signup(signUpDetails: UserInCreate, otp: str, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)

        return user_service.verify_otp_and_signup(user_details=signUpDetails, otp=otp)
    except Exception as error:
        print(error)
        raise HTTPException(status_code=500, detail=str(error))

@authRouter.post("/regenerate-otp", status_code=200)
async def regenerate_otp(email: str, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.regenerate_otp(email)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@authRouter.post("/login", status_code=200, response_model=UserWithToken)
async def login(loginDetails: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        user = user_service.authenticate_user(loginDetails.username, loginDetails.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        access_token = create_access_token(data={"user_id": str(user["_id"])})
        return {"access_token": access_token, "token_type": "bearer","role": user["role"]}
    except Exception as error:
        print(f"error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
    


# role login according to permission

class UserWithPermissions(UserWithToken):
    employee_id: str
    permissions: dict

@authRouter.post("/role-login", status_code=200, response_model=UserWithPermissions)
async def login(loginDetails: OAuth2PasswordRequestForm = Depends(), db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        user = user_service.authenticate_user(loginDetails.username, loginDetails.password)
        print(user)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"user_id": str(user["_id"])})
        
        # Fetch role permissions
        role_permissions = db.roles.find_one({"role": user["role"]})
        permissions = role_permissions.get("permissions", {}) if role_permissions else {}
        
        # Simplify permissions for frontend
        simplified_permissions = {resource: list(actions) for resource, actions in permissions.items()}
        employee_id = user.get("employee_id")
        
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user["role"],
            "employee_id": employee_id,
            "permissions": simplified_permissions
        }
    except Exception as error:
        print(f"error: {error}")
        raise HTTPException(status_code=500, detail=str(error))


@authRouter.get("/me", response_model=UserOutput)
def get_me(current_user: UserOutput = Depends(get_current_user_verify)):
    return current_user

@authRouter.post("/logout")
def logout(authorization: str = Header(...), db: Database = Depends(get_db)):
    token = authorization.split(" ")[1]
    user_service = UserService(db)
    user_service.logout(token)
    return {"message": "Successfully logged out"}

@authRouter.post("/request-password-reset", status_code=200)
async def request_password_reset(email_request: EmailRequest, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.request_password_reset(email_request.email)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
    
@authRouter.post("/forgot-password/request", status_code=200)
async def request_forgot_password(request: ForgotPasswordRequest, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.request_forgot_password(
            email=request.email,
            role=request.role,
            workplace=request.workplace
        )
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@authRouter.post("/verify-reset-otp", status_code=200)
async def verify_reset_otp(verify_email_request: VerifyEmailRequest, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.verify_reset_otp(verify_email_request.email, verify_email_request.otp)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@authRouter.post("/reset-password", status_code=200)
async def reset_password(reset_password_request: ResetPasswordRequest, db: Database = Depends(get_db)):
    try:
        user_service = UserService(db)
        return user_service.reset_password(reset_password_request.email, reset_password_request.new_password)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))
    

@authRouter.post("/verify-otp-and-create-user", status_code=201)
async def verify_otp_and_create_user(create_user_request: CreateUserRequest, otp: str, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    try:

        user_service = AdminUserService(db)
        print(f"Current User: {current_user}")
        print(f"Create User Request: {create_user_request}")
        return user_service.verify_otp_and_create_user(new_user_request=create_user_request, otp=otp, admin_user=current_user)
    except Exception as error:
        print(f"Error: {error}")
        raise HTTPException(status_code=500, detail=str(error))







# First define a model for query parameters (add this to the existing models)
class EmployeeFilters(BaseModel):
    role: str = None
    search: str = None

@authRouter.get("/employees", status_code=200)
async def get_all_employees(
    role: str = None, 
    search: str = None,
    current_user: UserOutput = Depends(get_current_user), 
    db: Database = Depends(get_db)
):
    """Get all employees with their complete information"""
    try:
        # Verify user has admin privileges
        if current_user.role != "admin" and current_user.role != "manager":
            raise HTTPException(status_code=403, detail="Only admins and managers can view all employees")
        
        # Create base query
        query = {}
        if role:
            query["role"] = role
        
        # Get employees from database
        employees = list(db.users.find(query))
        
        # Apply search filter if provided
        if search:
            search_term = search.lower()
            filtered_employees = []
            
            for employee in employees:
                # Check if search term is in name, email or username
                if (
                    search_term in (employee.get("first_name", "") + " " + employee.get("last_name", "")).lower()
                    or search_term in employee.get("email", "").lower()
                    or search_term in employee.get("username", "").lower()
                ):
                    filtered_employees.append(employee)
                    
            employees = filtered_employees
        
        # Process results for response
        for employee in employees:
            if "_id" in employee:
                employee["id"] = str(employee["_id"])
                del employee["_id"]
                
            # Remove sensitive data
            if "password" in employee:
                del employee["password"]
        
        return employees
        
    except HTTPException as e:
        raise e
    except Exception as error:
        print(f"Error retrieving employees: {error}")
        raise HTTPException(status_code=500, detail=str(error))