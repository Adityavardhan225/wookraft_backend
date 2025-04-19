from pydantic import BaseModel, EmailStr
from typing import Optional

class CreateUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: str
    phone_number: str

class AdminUserOutput(BaseModel):
    id: str
    owner_id: str
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    workplace_name: str
    phone_number: str
    employee_id: str
    is_verified: bool
    email_verified: bool