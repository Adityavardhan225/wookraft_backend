from repository.userRepo import UserRepository
from schema.user import UserOutput
from schema.adminUserSchema import CreateUserRequest, AdminUserOutput
from routes.security.hashHelper import HashHelper
from routes.service.userService import UserService
from fastapi import HTTPException
from pymongo.database import Database
import random
import hashlib
import time

class AdminUserService:
    def __init__(self, db: Database):
        self._userRepository = UserRepository(db)
        self.userService = UserService(db)
        self.valid_roles = ["admin", "waiter", "kds", "transaction", "manager"]
        self.db = db

    def send_otp(self, email: str):
        otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        self.db.otps.update_one(
            {"email": email},
            {"$set": {"otp": hashed_otp, "timestamp": time.time()}},
            upsert=True
        )
        self.userService.send_verification_email(email, otp)
        return {"message": "OTP sent to email"}

    def create_user(self, admin_user: UserOutput, new_user_request: CreateUserRequest):
        if new_user_request.role not in self.valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role")

        if self.db.users.find_one({"email": new_user_request.email}):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Send OTP
        return self.send_otp(new_user_request.email)

    def verify_otp_and_create_user(self, new_user_request: CreateUserRequest, otp: str, admin_user: UserOutput):
        otp_record = self.db.otps.find_one({"email": new_user_request.email})
        if not otp_record:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")

        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        if otp_record["otp"] != hashed_otp or (time.time() - otp_record["timestamp"]) > 600:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")

        # Generate a new employee ID
        # last_user = self.db.users.find_one(sort=[("employee_id", -1)])
        # new_employee_id = str(int(last_user["employee_id"]) + 1) if last_user else "1"
        # new_employee_id="1"

        last_user = self.db.users.find_one(sort=[("employee_id", -1)])
        if last_user and "employee_id" in last_user:
            new_employee_id = str(int(last_user["employee_id"]) + 1)
        else:
            new_employee_id = "1"

        hashed_password = HashHelper.hash_password(new_user_request.password)
        user_data = {
            "first_name": new_user_request.first_name,
            "last_name": new_user_request.last_name,
            "email": new_user_request.email,
            "phone_number": new_user_request.phone_number,
            "owner_id": admin_user.owner_id,  # Set owner_id same as admin
            "role": new_user_request.role,
            "workplace_name": admin_user.workplace_name,  # Set workplace_name same as admin
            "password": hashed_password,
            "employee_id": new_employee_id,
            "is_verified": False,
            "email_verified": True  # Email is verified since OTP is correct
        }
        print(f"User Data: {user_data}")

        try:
            result = self.db.users.insert_one(user_data)
            user_data["id"] = str(result.inserted_id)

            # Delete OTP after successful signup
            self.db.otps.delete_one({"email": new_user_request.email})

            return {"message": "User created successfully"}
        except Exception as error:
            print(f"User Creation Error: {error}")
            raise HTTPException(status_code=500, detail="User creation failed")