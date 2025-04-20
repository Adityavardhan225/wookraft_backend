from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGO_URI'), server_api=ServerApi('1')) 

db = client["wookraft_db"]

def get_db():
    
    yield db


# for mail verification
from pydantic_settings import BaseSettings
from pydantic import EmailStr

# class Settings(BaseSettings):
#     MONGO_URI: str
#     JWT_SECRET: str
#     JWT_ALGORITHM: str
#     EMAIL_SENDER: EmailStr
#     SMTP_SERVER: str
#     SMTP_PORT: int
#     SMTP_USERNAME: str
#     SMTP_PASSWORD: str
#     ACCESS_TOKEN_EXPIRE_MINUTES: int

#         # Cloudinary Configuration
#     CLOUDINARY_CLOUD_NAME: str
#     CLOUDINARY_API_KEY: str
#     CLOUDINARY_API_SECRET: str

#     REDIS_URL: str
#     BASE_URL: str = os.getenv("FEEDBACK_BASE_URL", "http://localhost:8000")

#     class Config:
#         env_file = ".env"


class Settings(BaseSettings):
    MONGO_URI: str = os.getenv("MONGO_URI")
    JWT_SECRET: str = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")
    EMAIL_SENDER: EmailStr = os.getenv("EMAIL_SENDER")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET")

    REDIS_URL: str = os.getenv("REDIS_URL")
    BASE_URL: str = os.getenv("FEEDBACK_BASE_URL", "http://localhost:8000")

settings = Settings()



from fastapi_mail import ConnectionConfig, FastMail

mail_conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USERNAME,
    MAIL_PASSWORD=settings.SMTP_PASSWORD,
    MAIL_FROM=settings.EMAIL_SENDER,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)
    