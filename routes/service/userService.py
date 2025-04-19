from repository.userRepo import UserRepository
from schema.user import UserOutput, UserInCreate, UserInLogin, UserWithToken
from routes.security.hashHelper import HashHelper
from routes.security.authHandler import AuthHandler
from fastapi import HTTPException, status
import uuid
from pymongo.database import Database
from bson import ObjectId
import random
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from configurations.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import time
from configurations.config import get_db


conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USERNAME,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAIL_SENDER,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)


class UserService:
    def __init__(self, db: Database):
        self._userRepository = UserRepository(db)
        self._hashHelper = HashHelper()
        self._authHandler = AuthHandler()
        self.valid_roles = ["admin", "waiter", "kds", "transaction", "manager"]
        self.db=db
        


    # async def send_verification_email(self, email: str, otp: str):
    #     message = MessageSchema(
    #         subject="Email Verification OTP",
    #         recipients=[email],
    #         body=f"Your OTP for email verification is: {otp}",
    #         subtype="plain"
    #     )
    #     fm = FastMail(conf)
    #     await fm.send_message(message)



    def send_verification_email(self, email: str, otp: str):
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_SENDER
        msg['To'] = email
        msg['Subject'] = "Email Verification OTP"
        
        body = f"Your OTP for email verification is: {otp}"
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(settings.EMAIL_SENDER, email, text)
            server.quit()
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: {e.smtp_code} - {e.smtp_error}")
            raise HTTPException(status_code=500, detail="SMTP Authentication Error")
        except Exception as e:
            print(f"Error sending email: {e}")
            raise HTTPException(status_code=500, detail="Error sending email")


    # async def signup(self,user_details:UserInCreate) -> UserOutput:
    #     try:
    #         if self.db.users.find_one({"email": user_details.email}):
    #             raise HTTPException(status_code=400, detail="Email already registered")
    #         hashed_password = HashHelper.hash_password(user_details.password)
    #         user_details.password = hashed_password
    #         user_id = str(uuid.uuid4())
    #         user_details.owner_id = user_id  # Set owner_id
    #         user_data = user_details.dict()
    #         user_data["is_verified"] = False  # Set initial verification status to False
    #         user_data["email_verified"] = False  # Set initial email verification status to False
    #         otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
    #         user_data["otp"] = otp  # Store OTP in the database
    #         result = self.db.users.insert_one(user_data)
    #         user_data["id"] = str(result.inserted_id)

    #         self.send_verification_email(user_data["email"], otp)
            
    #         return UserOutput(
    #             id=user_data["id"],
    #             email=user_data["email"],
    #             first_name=user_data["first_name"],
    #             last_name=user_data["last_name"],
    #             workplace_name=user_data["workplace_name"],
    #             phone_number=user_data["phone_number"],
    #             role=user_data["role"],
    #             owner_id=user_data["owner_id"]
    #         )
    #     except Exception as error:
    #         print(f"Signup Error: {error}")
    #         raise HTTPException(status_code=500, detail="Signup failed")

    # not used logn in place of this authenticated user is used

    def generate_otp(self, email: str):
        if self.db.users.find_one({"email": email}):
            raise HTTPException(status_code=400, detail="Your account already exists")
        
        otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        self.db.otps.update_one(
            {"email": email},
            {"$set": {"otp": hashed_otp, "timestamp": time.time()}},
            upsert=True
        )
        self.send_verification_email(email, otp)
        return {"message": "OTP sent to email"}


    def verify_otp_and_signup(self, user_details: UserInCreate, otp: str) -> UserOutput:
        if user_details.role not in self.valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role")

        otp_record = self.db.otps.find_one({"email": user_details.email})
        if not otp_record:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        if otp_record["otp"] != hashed_otp or (time.time() - otp_record["timestamp"]) > 600:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")
        if self.db.users.find_one({"email": user_details.email}):
            raise HTTPException(status_code=400, detail="Your account already exists. Please login.")

        try:
            if self.db.users.find_one({"email": user_details.email}):
                raise HTTPException(status_code=400, detail="Email already registered")
            hashed_password = HashHelper.hash_password(user_details.password)
            user_details.password = hashed_password
            user_id = str(uuid.uuid4())
            user_details.owner_id = user_id  # Set owner_id
            user_data = user_details.dict()
            user_data["is_verified"] = False  # Set initial verification status to False
            user_data["email_verified"] = True  # Email is verified since OTP is correct
            result = self.db.users.insert_one(user_data)
            user_data["id"] = str(result.inserted_id)

            self.db.otps.delete_one({"email": user_details.email})  # Delete OTP after successful signup

            return UserOutput(
                id=user_data["id"],
                email=user_data["email"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                workplace_name=user_data["workplace_name"],
                phone_number=user_data["phone_number"],
                role=user_data["role"],
                owner_id=user_data["owner_id"]
            )
        except Exception as error:
            print(f"Signup Error: {error}")
            raise HTTPException(status_code=500, detail="Signup failed")
        

    def regenerate_otp(self, email: str):
        otp_record = self.db.otps.find_one({"email": email})
        if otp_record and (time.time() - otp_record["timestamp"]) < 60:
            raise HTTPException(status_code=400, detail="Cannot regenerate OTP yet")
        
        otp = str(random.randint(100000, 999999))  # Generate a new 6-digit OTP
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        self.db.otps.update_one(
            {"email": email},
            {"$set": {"otp": hashed_otp, "timestamp": time.time()}},
            upsert=True
        )
        self.send_verification_email(email, otp)
        return {"message": "New OTP sent to email"}

    def cleanup_expired_otps(self):
        while True:
            time.sleep(60)
            current_time = time.time()
            self.db.otps.delete_many({"timestamp": {"$lt": current_time - 600}})
        

    
    def login(self,login_details:UserInLogin) -> UserWithToken:
        if not self._userRepository.user_exist_by_email(email=login_details.email):
            raise HTTPException(status_code=400,detail="User does not exist.")
        if not user.get("is_verified"):
            raise HTTPException(status_code=400, detail="Your account will be verified within 48 hours. Please contact our customer support for any reference.")
        user = self._userRepository.get_user_by_email(email=login_details.email)
        if HashHelper.verify_password(plain_password=login_details.password,hashed_password=user['password']):
            print(user['_id'])
            token = AuthHandler.sign_jwt(user_id=user['_id'])
            if token:
                return UserWithToken(token=token)
            raise HTTPException(status_code=500,detail="Token creation failed.")
        raise HTTPException(status_code=400,detail="Invalid password.Please Check your credentials.")
    
    
    def get_user_by_email(self, email: str) -> dict:
        user = self._userRepository.get_user_by_email(email)
        print(user)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    

    def verify_email(self, email: str, otp: str):
        user = self.db.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user["otp"] != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        self.db.users.update_one({"email": email}, {"$set": {"email_verified": True}})
        return {"message": "Email verified successfully"}

    def authenticate_user(self, username: str, password: str):
        user = self.db.users.find_one({"email": username})
        if not user.get("is_verified"):
            raise HTTPException(status_code=400, detail="Your account will be verified within 48 hours. Please contact our customer support for any reference.")
        if not user.get("email_verified"):
            raise HTTPException(status_code=400, detail="Please verify your email address.")
        if user and HashHelper.verify_password(password, user["password"]):
            print(user)
            return user


        return None

   
    def get_user_by_id(self, user_id: str):
        return self.db.users.find_one({"_id": ObjectId(user_id)})
    
    def logout(self, token: str):
        AuthHandler.invalidate_token(token)


    def request_password_reset(self, email: str):
        user = self.db.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=400, detail="Email does not exist.")
        
        otp = str(random.randint(100000, 999999))  # Generate a 6-digit OTP
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        self.db.otps.update_one(
            {"email": email},
            {"$set": {"otp": hashed_otp, "timestamp": time.time()}},
            upsert=True
        )
        self.send_verification_email(email, otp)
        return {"message": "OTP sent to email"}

    def verify_reset_otp(self, email: str, otp: str):
        otp_record = self.db.otps.find_one({"email": email})
        if not otp_record:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        if otp_record["otp"] != hashed_otp or (time.time() - otp_record["timestamp"]) > 600:
            raise HTTPException(status_code=400, detail="OTP expired or invalid")
        
        return {"message": "OTP verified"}
    
    def reset_password(self, email: str, new_password: str):
        user = self.db.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=400, detail="Email does not exist.")
        
        hashed_password = HashHelper.hash_password(new_password)
        self.db.users.update_one(
            {"email": email},
            {"$set": {"password": hashed_password}}
        )
        self.db.otps.delete_one({"email": email})  # Delete OTP after successful password reset
        return {"message": "Password reset successful"}


# Start the cleanup thread
import threading
db=next(get_db())
user_service=UserService(db)
cleanup_thread = threading.Thread(target=user_service.cleanup_expired_otps)
cleanup_thread.daemon = True
cleanup_thread.start()
    
