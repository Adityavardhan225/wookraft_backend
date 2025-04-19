from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os

client = MongoClient(os.getenv('MONGO_URI'), server_api=ServerApi('1')) 

db = client["wookraft_db"]

def get_db():
    
    yield db


# for mail verification
from pydantic_settings import BaseSettings
from pydantic import EmailStr

class Settings(BaseSettings):
    MONGO_URI: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    EMAIL_SENDER: EmailStr
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    BASE_URL: str = os.getenv("FEEDBACK_BASE_URL", "http://localhost:8000")

    class Config:
        env_file = ".env"

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
    