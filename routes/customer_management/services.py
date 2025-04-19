# from datetime import datetime, timedelta
# from typing import List, Dict, Optional, Any
# from bson import ObjectId
# from pymongo.collection import Collection
# from routes.client_intelligence.services import get_collection_for_dataset
# from bson.errors import InvalidId

# import logging

# # Setup logging
# logger = logging.getLogger(__name__)

# # Core Customer Services



# def is_valid_object_id(id_str: str) -> bool:
#     """
#     Check if the ID is a valid identifier (e.g., mobile number or string-based ID).
#     """
#     # Check if it's a valid mobile number (e.g., 10-15 digit number)
#     if id_str.isdigit():
#         print("Valid mobile number")
#         return True

#     # Check if it's a valid MongoDB ObjectId (if applicable)
#     try:
#         ObjectId(id_str)
#         return True
#     except Exception:
#         pass

#     # If none of the above conditions are met, return False
#     return False



# def get_customer_by_id_service(customer_id: str) -> Dict[str, Any]:
#     """
#     Retrieve detailed information for a single customer.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         if not is_valid_object_id(customer_id):
#             raise ValueError("Invalid customer ID format")
        
#         customer = collection.find_one({"_id": customer_id})
#         if not customer:
#             raise ValueError(f"Customer {customer_id} not found")
        
#         customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
#         return customer
#     except Exception as e:
#         logger.error(f"Error retrieving customer by ID: {str(e)}")
#         raise ValueError(str(e))


# def get_customer_orders_service(customer_id: str, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
#     """
#     Retrieve order history for a specific customer.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         if not is_valid_object_id(customer_id):
#             raise ValueError("Invalid customer ID format")
        
#         customer = collection.find_one({"_id": customer_id})
#         if not customer or "orders" not in customer:
#             raise ValueError(f"No orders found for customer {customer_id}")
        
#         orders = customer["orders"][skip: skip + limit]
#         return orders
#     except Exception as e:
#         logger.error(f"Error retrieving customer orders: {str(e)}")
#         raise ValueError(str(e))


# def update_customer_service(customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Modify customer information (contact details, status, tags).
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         if not is_valid_object_id(customer_id):
#             raise ValueError("Invalid customer ID format")
        
#         result = collection.update_one(
#             {"_id": customer_id},
#             {"$set": customer_data}
#         )
#         if result.matched_count == 0:
#             raise ValueError(f"Customer {customer_id} not found")
        
#         updated_customer = collection.find_one({"_id": customer_id})
#         updated_customer["_id"] = str(updated_customer["_id"])  # Convert ObjectId to string
#         return updated_customer
#     except Exception as e:
#         logger.error(f"Error updating customer: {str(e)}")
#         raise ValueError(str(e))


# def delete_customer_service(customer_id: str) -> bool:
#     """
#     Remove a customer from the system.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         if not is_valid_object_id(customer_id):
#             raise ValueError("Invalid customer ID format")
        
#         result = collection.delete_one({"_id": customer_id})
#         if result.deleted_count == 0:
#             raise ValueError(f"Customer {customer_id} not found")
        
#         return True
#     except Exception as e:
#         logger.error(f"Error deleting customer: {str(e)}")
#         raise ValueError(str(e))


# # Additional Customer Data Services

# def add_customer_note_service(customer_id: str, note: Dict[str, Any]) -> List[Dict[str, Any]]:
#     """
#     Attach notes/comments to a customer profile.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         if not is_valid_object_id(customer_id):
#             raise ValueError("Invalid customer ID format")
        
#         note["date"] = datetime.now()  # Add timestamp to the note
#         result = collection.update_one(
#             {"_id": customer_id},
#             {"$push": {"notes": note}}
#         )
#         if result.matched_count == 0:
#             raise ValueError(f"Customer {customer_id} not found")
        
#         customer = collection.find_one({"_id": customer_id})
#         return customer.get("notes", [])
#     except Exception as e:
#         logger.error(f"Error adding customer note: {str(e)}")
#         raise ValueError(str(e))


# def get_customer_statistics_service() -> Dict[str, Any]:
#     """
#     Retrieve aggregated metrics across all customers.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         total_customers = collection.count_documents({})
#         active_customers = collection.count_documents({"status": "active"})
#         new_customers = collection.count_documents({"first_visit": {"$gte": datetime.now() - timedelta(days=30)}})
        
#         return {
#             "total_customers": total_customers,
#             "active_customers": active_customers,
#             "new_customers": new_customers
#         }
#     except Exception as e:
#         logger.error(f"Error retrieving customer statistics: {str(e)}")
#         raise ValueError(str(e))


# # Specialized Filtering Services

# def get_active_customers_service(status: str = "active", limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
#     """
#     Filter customers by status (active, inactive, vip).
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         customers = list(collection.find({"status": status}).skip(skip).limit(limit))
#         for customer in customers:
#             customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
#         return customers
#     except Exception as e:
#         logger.error(f"Error retrieving active customers: {str(e)}")
#         raise ValueError(str(e))


# def get_top_spending_customers_service(limit: int = 10) -> List[Dict[str, Any]]:
#     """
#     Retrieve highest-value customers.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         customers = list(collection.find().sort("total_spent", -1).limit(limit))
#         for customer in customers:
#             customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
#         return customers
#     except Exception as e:
#         logger.error(f"Error retrieving top spending customers: {str(e)}")
#         raise ValueError(str(e))


# def get_most_frequent_customers_service(limit: int = 10) -> List[Dict[str, Any]]:
#     """
#     Retrieve customers with most orders.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         customers = list(collection.find().sort("total_visits", -1).limit(limit))
#         for customer in customers:
#             customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
#         return customers
#     except Exception as e:
#         logger.error(f"Error retrieving most frequent customers: {str(e)}")
#         raise ValueError(str(e))


# def get_customers_by_spending_tier_service(high: float = 1000, medium: float = 500) -> Dict[str, List[Dict[str, Any]]]:
#     """
#     Categorize customers by spending level.
#     """
#     try:
#         collection = get_collection_for_dataset("customer_order_history")
#         if not collection:
#             raise ValueError("Customer dataset not found")
        
#         high_spenders = list(collection.find({"total_spent": {"$gte": high}}))
#         medium_spenders = list(collection.find({"total_spent": {"$gte": medium, "$lt": high}}))
#         low_spenders = list(collection.find({"total_spent": {"$lt": medium}}))
        
#         for customer in high_spenders + medium_spenders + low_spenders:
#             customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        
#         return {
#             "high_spenders": high_spenders,
#             "medium_spenders": medium_spenders,
#             "low_spenders": low_spenders
#         }
#     except Exception as e:
#         logger.error(f"Error retrieving customers by spending tier: {str(e)}")
#         raise ValueError(str(e))



































from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from bson import ObjectId
from pymongo.collection import Collection
from routes.client_intelligence.services import get_collection_for_dataset
from bson.errors import InvalidId

import logging

# Setup logging
logger = logging.getLogger(__name__)

# Core Customer Services

def is_valid_object_id(id_str: str) -> bool:
    """
    Check if the ID is a valid identifier (e.g., mobile number or string-based ID).
    """
    # Check if it's a valid mobile number (e.g., 10-15 digit number)
    if id_str.isdigit() and 10 <= len(id_str) <= 15:
        return True

    # Check if it's a valid MongoDB ObjectId (if applicable)
    try:
        ObjectId(id_str)
        return True
    except Exception:
        pass

    # If none of the above conditions are met, return False
    return False

def get_customer_by_id_service(customer_id: str) -> Dict[str, Any]:
    """
    Retrieve detailed information for a single customer.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise ValueError("Invalid customer ID format")
        
        customer = collection.find_one({"_id": customer_id})
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customer
    except Exception as e:
        logger.error(f"Error retrieving customer by ID: {str(e)}")
        raise ValueError(str(e))

def get_customer_orders_service(customer_id: str, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve order history for a specific customer.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise ValueError("Invalid customer ID format")
        
        customer = collection.find_one({"_id": customer_id})
        if not customer or "orders" not in customer:
            raise ValueError(f"No orders found for customer {customer_id}")
        
        orders = customer["orders"][skip: skip + limit]
        return orders
    except Exception as e:
        logger.error(f"Error retrieving customer orders: {str(e)}")
        raise ValueError(str(e))

def update_customer_service(customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify customer information (contact details, status, tags).
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise ValueError("Invalid customer ID format")
        
        result = collection.update_one(
            {"_id": customer_id},
            {"$set": customer_data}
        )
        if result.matched_count == 0:
            raise ValueError(f"Customer {customer_id} not found")
        
        updated_customer = collection.find_one({"_id": customer_id})
        updated_customer["_id"] = str(updated_customer["_id"])  # Convert ObjectId to string
        return updated_customer
    except Exception as e:
        logger.error(f"Error updating customer: {str(e)}")
        raise ValueError(str(e))

def delete_customer_service(customer_id: str) -> bool:
    """
    Remove a customer from the system.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise ValueError("Invalid customer ID format")
        
        result = collection.delete_one({"_id": customer_id})
        if result.deleted_count == 0:
            raise ValueError(f"Customer {customer_id} not found")
        
        return True
    except Exception as e:
        logger.error(f"Error deleting customer: {str(e)}")
        raise ValueError(str(e))

# Additional Customer Data Services

def add_customer_note_service(customer_id: str, note: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Attach notes/comments to a customer profile.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        if not is_valid_object_id(customer_id):
            raise ValueError("Invalid customer ID format")
        
        note["date"] = datetime.now()  # Add timestamp to the note
        result = collection.update_one(
            {"_id": customer_id},
            {"$push": {"notes": note}}
        )
        if result.matched_count == 0:
            raise ValueError(f"Customer {customer_id} not found")
        
        customer = collection.find_one({"_id": customer_id})
        return customer.get("notes", [])
    except Exception as e:
        logger.error(f"Error adding customer note: {str(e)}")
        raise ValueError(str(e))

def get_customer_statistics_service() -> Dict[str, Any]:
    """
    Retrieve aggregated metrics across all customers.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        total_customers = collection.count_documents({})
        active_customers = collection.count_documents({"status": "active"})
        new_customers = collection.count_documents({"first_visit": {"$gte": datetime.now() - timedelta(days=30)}})
        
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "new_customers": new_customers
        }
    except Exception as e:
        logger.error(f"Error retrieving customer statistics: {str(e)}")
        raise ValueError(str(e))

# Specialized Filtering Services

def get_active_customers_service(status: str = "active", limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Filter customers by status (active, inactive, vip).
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        customers = list(collection.find({"status": status}).skip(skip).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        logger.error(f"Error retrieving active customers: {str(e)}")
        raise ValueError(str(e))

def get_top_spending_customers_service(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve highest-value customers.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        customers = list(collection.find().sort("total_spent", -1).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        logger.error(f"Error retrieving top spending customers: {str(e)}")
        raise ValueError(str(e))

def get_most_frequent_customers_service(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve customers with most orders.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        customers = list(collection.find().sort("total_visits", -1).limit(limit))
        for customer in customers:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        return customers
    except Exception as e:
        logger.error(f"Error retrieving most frequent customers: {str(e)}")
        raise ValueError(str(e))

def get_customers_by_spending_tier_service(high: float = 1000, medium: float = 500) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize customers by spending level.
    """
    try:
        collection = get_collection_for_dataset("customer_order_history")
        if collection is None:  # Explicitly check for None
            raise ValueError("Customer dataset not found")
        
        high_spenders = list(collection.find({"total_spent": {"$gte": high}}))
        medium_spenders = list(collection.find({"total_spent": {"$gte": medium, "$lt": high}}))
        low_spenders = list(collection.find({"total_spent": {"$lt": medium}}))
        
        for customer in high_spenders + medium_spenders + low_spenders:
            customer["_id"] = str(customer["_id"])  # Convert ObjectId to string
        
        return {
            "high_spenders": high_spenders,
            "medium_spenders": medium_spenders,
            "low_spenders": low_spenders
        }
    except Exception as e:
        logger.error(f"Error retrieving customers by spending tier: {str(e)}")
        raise ValueError(str(e))
    














# from datetime import datetime, timedelta
# from typing import List, Dict, Optional, Any
# from bson import ObjectId
# from pymongo.collection import Collection
# from routes.client_intelligence.services import get_collection_for_dataset
# from bson.errors import InvalidId
# import base64
# import logging
# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
# from configurations.config import settings
# from pydantic import EmailStr

# # Import or define the ConnectionConfig
# conf = ConnectionConfig(
#     MAIL_USERNAME=settings.SMTP_USERNAME,
#     MAIL_PASSWORD=settings.SMTP_PASSWORD,
#     MAIL_FROM=settings.EMAIL_SENDER,
#     MAIL_PORT=settings.SMTP_PORT,
#     MAIL_SERVER=settings.SMTP_SERVER,
#     MAIL_STARTTLS=True,
#     MAIL_SSL_TLS=False,
#     USE_CREDENTIALS=True
# )

# # Setup logging
# logger = logging.getLogger(__name__)


# async def send_email_to_customer_service(
#     recipient_email: str,
#     subject: str,
#     body: str,
#     attachments: Optional[List[Dict[str, str]]] = None
# ) -> Dict[str, Any]:
#     """
#     Send an email to a customer with optional attachments using FastAPI-Mail.
    
#     Args:
#         recipient_email: Customer's email address
#         subject: Email subject
#         body: Email body content (plain text)
#         attachments: Optional list of attachments [{"filename": "name.pdf", "content": "base64_content"}]
        
#     Returns:
#         Dict with status information
#     """
#     try:
#         # Prepare attachments if provided
#         files = []
#         if attachments:
#             for attachment in attachments:
#                 filename = attachment.get("filename")
#                 content_base64 = attachment.get("content")
                
#                 if filename and content_base64:
#                     # Decode base64 content
#                     try:
#                         file_content = base64.b64decode(content_base64)
#                         # Create temp file to attach
#                         with open(filename, "wb") as f:
#                             f.write(file_content)
#                         files.append(filename)
#                     except Exception as e:
#                         logger.error(f"Error processing attachment {filename}: {str(e)}")
        
#         # Create message schema
#         message = MessageSchema(
#             subject=subject,
#             recipients=[recipient_email],
#             body=body,
#             subtype="plain",
#             attachments=files
#         )
        
#         # Send email
#         fm = FastMail(conf)
#         await fm.send_message(message)
        
#         logger.info(f"Email sent successfully to {recipient_email}")
#         return {
#             "recipient": recipient_email,
#             "subject": subject,
#             "timestamp": datetime.now().isoformat(),
#             "attachments_count": len(files)
#         }
        
#     except Exception as e:
#         logger.error(f"Error sending email: {str(e)}")
#         raise ValueError(f"Error sending email: {str(e)}")






























from fastapi import UploadFile
from fastapi_mail import FastMail, MessageSchema
from typing import List, Dict, Optional, Any
import cloudinary.uploader
import os
import uuid
import tempfile
from datetime import datetime
import logging
import asyncio
from configurations.config import mail_conf
from configurations.config import client

# Setup logging and database
logger = logging.getLogger(__name__)
db = client["wookraft_db"]
temp_attachments_collection = db["temp_email_attachments"]

# Configure cloudinary (should be already configured in your app)
# cloudinary.config(
#     cloud_name = 'dl91gwshv', 
#     api_key = '392761399558392', 
#     api_secret = 'N8dW3ksMCt41qCfzFeobTh701hM' 
# )

async def send_email_with_cloudinary_attachments(
    recipient_email: str,
    subject: str,
    body: str,
    attachments: List[UploadFile],
    user_id: str
) -> Dict[str, Any]:
    """
    Send email with attachments using Cloudinary for temporary storage.
    Uses the global Cloudinary configuration already set elsewhere.
    """
    cloudinary_ids = []
    email_attachments = []
    temp_files = []
    
    try:
        # Process attachments if any
        if attachments:
            for attachment in attachments:
                try:
                    # Reset file cursor position before reading
                    await attachment.seek(0)
                    
                    # Create a unique ID for this attachment
                    unique_id = f"email_att_{user_id}_{uuid.uuid4().hex}"
                    
                    # Upload to Cloudinary - using the globally configured settings
                    result = cloudinary.uploader.upload(
                        attachment.file, 
                        folder="email_attachments", 
                        public_id=unique_id,
                        resource_type="auto"
                    )
                    
                    transformed_url = result.get("secure_url")  # Use secure_url for HTTPS
                    public_id = result.get("public_id")
                    
                    # Store reference in MongoDB
                    attachment_data = {
                        "name": attachment.filename,
                        "url": transformed_url,
                        "public_id": public_id,
                        "owner_id": user_id,
                        "created_at": datetime.now(),
                        "temp_for_email": True  # Mark as temporary for email
                    }
                    
                    temp_attachments_collection.insert_one(attachment_data)
                    cloudinary_ids.append(public_id)
                    
                    # Create temporary file for the email attachment
                    temp_file_path = os.path.join(tempfile.gettempdir(), f"{unique_id}_{attachment.filename}")
                    
                    # Download from Cloudinary to temp file
                    import urllib.request
                    urllib.request.urlretrieve(transformed_url, temp_file_path)
                    
                    # Add to email attachments list
                    email_attachments.append({
                        "file": temp_file_path,
                        "filename": attachment.filename
                    })
                    
                    temp_files.append(temp_file_path)
                    
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment.filename}: {str(e)}")
                    raise ValueError(f"Error processing attachment: {str(e)}")
        
        # Create email message
        message = MessageSchema(
            subject=subject,
            recipients=[recipient_email],
            body=body,
            subtype="plain",
            attachments=email_attachments
        )
        
        # Send email
        fm = FastMail(mail_conf)
        await fm.send_message(message)
        
        return {
            "recipient": recipient_email,
            "subject": subject,
            "attachments_count": len(email_attachments),
            "timestamp": datetime.now().isoformat()
        }
    
    finally:
        # Clean up temporary files
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error removing temporary file {file_path}: {str(e)}")
        
        # Clean up Cloudinary resources
        for public_id in cloudinary_ids:
            try:
                # Delete from Cloudinary
                cloudinary.uploader.destroy(public_id)
                
                # Delete from MongoDB
                temp_attachments_collection.delete_one({"public_id": public_id})
            except Exception as e:
                logger.error(f"Error cleaning up Cloudinary resource {public_id}: {str(e)}")







from typing import Dict, Any, List, Optional
from bson import ObjectId
import logging
from configurations.config import client

# Setup logging
logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
billing_collection = db["bills"]  # Your billing collection

def is_valid_object_id_st(id_str: str) -> bool:
    """Check if a string is a valid MongoDB ObjectId"""
    try:
        ObjectId(id_str)
        return True
    except:
        return False

async def get_bill_details_by_order_id(
    order_id: str,
    owner_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete bill details for a specific order ID.
    
    Args:
        order_id: The ID of the order to fetch bill details for
        owner_id: Optional owner ID for data segregation
        
    Returns:
        Dictionary containing bill details or None if no bill is found
    """
    try:
        # Build query for order_id
        query = {"order_id": order_id}
        
        # Add owner_id if provided
        if owner_id:
            query["owner_id"] = owner_id
            
        # Find bill by order_id (primary search)
        bill = billing_collection.find_one(query)
        
        if not bill:
            logger.warning(f"No bill found for order ID: {order_id}")
            return None
            
        # Convert ObjectId to string for JSON serialization
        if "_id" in bill and isinstance(bill["_id"], ObjectId):
            bill["_id"] = str(bill["_id"])
            
        return bill
        
    except Exception as e:
        logger.error(f"Error retrieving bill details: {str(e)}")
        raise ValueError(f"Failed to retrieve bill details: {str(e)}")

async def get_bill_details_by_bill_number(
    bill_number: str, 
    owner_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve bill details by bill number.
    
    Args:
        bill_number: The bill number to search for (e.g., INV-c8ebdc)
        owner_id: Optional owner ID for data segregation
        
    Returns:
        Bill details dictionary or None if not found
    """
    try:
        # Build query
        query = {"bill_number": bill_number}
        if owner_id:
            query["owner_id"] = owner_id
            
        # Find bill by bill_number
        bill = billing_collection.find_one(query)
            
        if not bill:
            logger.warning(f"No bill found with bill_number: {bill_number}")
            return None
            
        # Convert ObjectId to string
        if "_id" in bill and isinstance(bill["_id"], ObjectId):
            bill["_id"] = str(bill["_id"])
            
        return bill
        
    except Exception as e:
        logger.error(f"Error retrieving bill by bill_number: {str(e)}")
        raise ValueError(f"Failed to retrieve bill details: {str(e)}")

async def get_all_bills(
    limit: int = 10,
    skip: int = 0,
    filters: Optional[Dict[str, Any]] = None,
    owner_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve a list of bills with optional filtering.
    
    Args:
        limit: Maximum number of bills to return
        skip: Number of bills to skip (for pagination)
        filters: Optional filters for querying bills
        owner_id: Optional owner ID for data segregation
        
    Returns:
        List of bill dictionaries
    """
    try:
        # Build query
        query = {}
        
        # Add owner_id for data segregation if provided
        if owner_id:
            query["owner_id"] = owner_id
        
        # Apply filters if provided
        if filters:
            # Date range filtering
            if "start_date" in filters or "end_date" in filters:
                date_query = {}
                if "start_date" in filters:
                    date_query["$gte"] = filters["start_date"]
                if "end_date" in filters:
                    date_query["$lte"] = filters["end_date"]
                if date_query:
                    query["date"] = date_query
            
            # Customer name filtering
            if "customer_name" in filters and filters["customer_name"]:
                query["customer.name"] = {"$regex": filters["customer_name"], "$options": "i"}
            
            # Customer phone filtering
            if "customer_phone" in filters and filters["customer_phone"]:
                query["customer.phone"] = {"$regex": filters["customer_phone"], "$options": "i"}
            
            # Table number filtering
            if "table_number" in filters and filters["table_number"] is not None:
                query["table_number"] = filters["table_number"]
                
            # Employee ID filtering
            if "employee_id" in filters and filters["employee_id"]:
                query["employee_id"] = filters["employee_id"]
        print(f'query {query}')
        # Find bills with the query
        cursor = billing_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)

        # Convert cursor to list and format _id fields
        bills = []
        for bill in cursor:
            if "_id" in bill and isinstance(bill["_id"], ObjectId):
                bill["_id"] = str(bill["_id"])
            bills.append(bill)
        
        return bills
        
    except Exception as e:
        logger.error(f"Error retrieving bills: {str(e)}")
        raise ValueError(f"Failed to retrieve bills: {str(e)}")