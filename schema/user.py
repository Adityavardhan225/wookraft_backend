from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Union ,Optional

class UserInCreate(BaseModel):
    owner_id :Optional[str] = None
    first_name:str
    last_name:str
    email:EmailStr
    password:str
    role: str
    workplace_name: str
    phone_number: str

class UserOutput(BaseModel):
    id: str
    owner_id: str 
    first_name:str
    last_name:str
    email:EmailStr
    role: str
    workplace_name: str
    phone_number: str
    employee_id: str

class UserInUpdate(BaseModel):
    owner_id :str
    first_name:Union[str,None] = None
    last_name:Union[str,None] = None
    email:Union[EmailStr,None] = None
    password:Union[str,None] = None

class UserInLogin(BaseModel):
    email:EmailStr
    password:str
    
class UserWithToken(BaseModel):
    token : str

class VerifyEmailRequest(BaseModel):
    email: str
    otp: str


    