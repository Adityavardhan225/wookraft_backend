from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path, BackgroundTasks, Form
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
import asyncio
from routes.security.protected_authorise import get_current_user
from configurations.config import client
from routes.campaign.customer_segment_services import get_customers_for_combined_criteria
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
import json
import requests
from jinja2 import Template
from dotenv import load_dotenv
import redis
import uuid
from fastapi.responses import JSONResponse, FileResponse
import pandas as pd
from starlette.background import BackgroundTask

# Load environment variables
load_dotenv()

# Configure Redis for task queue
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost") 
# REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
# REDIS_DB = int(os.getenv("REDIS_DB", "0"))
# REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
print("REDIS_URL", REDIS_URL )
# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
FROM_NAME = os.getenv("FROM_NAME", "WooPOS")

# Setup Redis connection
# redis_client = redis.Redis(
#     host=REDIS_HOST,
#     port=REDIS_PORT,
#     db=REDIS_DB,
#     password=REDIS_PASSWORD,
#     # decode_responses=True
# )

# redis_client = redis.Redis.from_url(REDIS_URL)
redis_client = redis.Redis.from_url(
    REDIS_URL,
    
    health_check_interval=10,  # Check connection health every 10 seconds
    socket_connect_timeout=5,  # Timeout for connecting to the server (in seconds)
    retry_on_timeout=True,     # Retry if a timeout occurs
    socket_keepalive=True,    # Keep the connection 
    decode_responses=True,
    ssl_cert_reqs=None if REDIS_URL.startswith("rediss://") else None  # Disable SSL validation for rediss://
)

# Test Redis connection during startup
try:
    redis_client.ping()
    print("Redis connection successful!")
except Exception as e:
    print(f"Redis connection failed: {e}")
    raise


print("redis_client", redis_client)
router = APIRouter()
db = client["wookraft_db"]
campaigns_collection = db["email_campaigns"]
templates_collection = db["email_templates"]
email_logs_collection = db["email_logs"]

@router.post("/create_campaign", response_model=Dict[str, Any])
async def create_email_campaign(
    campaign_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new email campaign
    """
    try:
        # Validate required fields
        required_fields = ["name", "template_id", "segment_ids", "subject"]
        for field in required_fields:
            if field not in campaign_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Verify template exists
        template_id = campaign_data["template_id"]
        template = templates_collection.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Email template not found"
            )
        
        # Create campaign document
        campaign = {
            "name": campaign_data["name"],
            "subject": campaign_data["subject"],
            "template_id": template_id,
            "segment_ids": campaign_data.get("segment_ids", []),
            "custom_filters": campaign_data.get("custom_filters", []),
            "operator": campaign_data.get("operator", "AND"),
            "schedule_time": datetime.fromisoformat(campaign_data["schedule_time"]) 
    if "schedule_time" in campaign_data and campaign_data["schedule_time"] is not None 
    else None,
            "status": "draft",
            "created_by": current_user.id if hasattr(current_user, "id") else "",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "statistics": {
                "total_recipients": 0,
                "sent": 0,
                "delivered": 0,
                "failed": 0
            }
        }
        

        # Insert campaign
        result = campaigns_collection.insert_one(campaign)
        campaign_id = result.inserted_id
        
        # Get preliminary recipient count
        recipient_data = await get_customers_for_combined_criteria(
            segment_ids=campaign["segment_ids"],
            custom_filters=campaign["custom_filters"],
            operator=campaign["operator"],
            limit=0,  # Just get the count
            skip=0
        )
        
        # Update recipient count
        campaigns_collection.update_one(
            {"_id": campaign_id},
            {"$set": {"statistics.total_recipients": recipient_data.get("total", 0)}}
        )
        
        # Get updated campaign
        updated_campaign = campaigns_collection.find_one({"_id": campaign_id})
        updated_campaign["_id"] = str(updated_campaign["_id"])
        
        return {
            "status": "success",
            "message": "Email campaign created successfully",
            "campaign": updated_campaign
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create email campaign: {str(e)}"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_all_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all email campaigns with pagination and optional status filtering
    """
    try:
        # Build query
        query = {}
        if status:
            query["status"] = status
        
        # Count total campaigns
        total = campaigns_collection.count_documents(query)
        
        # Get campaigns with pagination
        cursor = campaigns_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        
        # Format campaigns
        campaigns = []
        for campaign in cursor:
            campaign["_id"] = str(campaign["_id"])
            campaigns.append(campaign)
        
        return {
            "status": "success",
            "total": total,
            "campaigns": campaigns
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve email campaigns: {str(e)}"
        )

@router.get("/{campaign_id}", response_model=Dict[str, Any])
async def get_campaign_by_id(
    campaign_id: str = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific email campaign by ID
    """
    try:
        # Find campaign
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Email campaign not found"
            )
        
        # Format ID
        campaign["_id"] = str(campaign["_id"])
        
        return {
            "status": "success",
            "campaign": campaign
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve email campaign: {str(e)}"
        )

@router.put("/{campaign_id}", response_model=Dict[str, Any])
async def update_email_campaign(
    campaign_id: str = Path(...),
    campaign_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing email campaign
    """
    try:
        # Check if campaign exists
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Email campaign not found"
            )
        
        # Check if campaign can be updated (only draft campaigns can be updated)
        if campaign["status"] not in ["draft"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update campaign with status: {campaign['status']}"
            )
        
        # Prepare update data
        update_data = {k: v for k, v in campaign_data.items() if k not in ["_id", "created_at", "status", "statistics"]}
        update_data["updated_at"] = datetime.now()
        
        # Convert schedule_time from string to datetime
        if "schedule_time" in update_data and update_data["schedule_time"]:
            update_data["schedule_time"] = datetime.fromisoformat(update_data["schedule_time"])
        
        # Update campaign
        campaigns_collection.update_one(
            {"_id": ObjectId(campaign_id)},
            {"$set": update_data}
        )
        
        # Recalculate recipient count if segments or filters changed
        if "segment_ids" in update_data or "custom_filters" in update_data or "operator" in update_data:
            recipient_data = await get_customers_for_combined_criteria(
                segment_ids=update_data.get("segment_ids", campaign["segment_ids"]),
                custom_filters=update_data.get("custom_filters", campaign["custom_filters"]),
                operator=update_data.get("operator", campaign["operator"]),
                limit=0,  # Just get the count
                skip=0
            )
            
            # Update recipient count
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {"statistics.total_recipients": recipient_data.get("total", 0)}}
            )
        
        # Get updated campaign
        updated_campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        updated_campaign["_id"] = str(updated_campaign["_id"])
        
        return {
            "status": "success",
            "message": "Email campaign updated successfully",
            "campaign": updated_campaign
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update email campaign: {str(e)}"
        )

@router.post("/{campaign_id}/send", response_model=Dict[str, Any])
async def send_campaign(
    campaign_id: str = Path(...),
    list_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Send an email campaign immediately or schedule it
    """
    try:
        # Check if campaign exists
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Email campaign not found"
            )
        print(f'campaign: {campaign}')
        # Check if campaign can be sent
        if campaign["status"] not in ["draft"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send campaign with status: {campaign['status']}"
            )
        print(f'list_id: {list_id}')
        
        if list_id:
            # Verify the list exists and belongs to the user
            recipient_list = recipient_lists_collection.find_one({
                "_id": ObjectId(list_id),
                "created_by": current_user.id  # Security check
            })
            
            if not recipient_list:
                raise HTTPException(
                    status_code=404,
                    detail="Recipient list not found or access denied"
                )
            
            # Update campaign to use ONLY this recipient list - clear any other recipient sources
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "recipient_list_id": list_id,
                    "recipient_source": "recipient_list",
                    "statistics.total_recipients": recipient_list["total_recipients"],
                    # Clear any segment-based targeting to ensure only the list is used
                    "segment_ids": [],
                    "custom_filters": []
                }}
            )
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})


        print(f'campaign 1: {campaign}')
        
        # Schedule for future or send now
        if campaign.get("schedule_time") and campaign["schedule_time"] > datetime.now():
            # Set status to scheduled
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {"status": "scheduled", "scheduled_at": datetime.now()}}
            )
            print(f"Campaign {campaign_id} scheduled for {campaign['schedule_time']}")
            
            # Add to scheduled tasks in Redis
            schedule_time_ts = int(campaign["schedule_time"].timestamp())
            dt_local = datetime.fromtimestamp(schedule_time_ts)
            print(f"Scheduling campaign {campaign_id} for {campaign['schedule_time']} (timestamp: {schedule_time_ts} (date and time : {dt_local}))")
            task_id = f"campaign:{campaign_id}"
            redis_client.zadd("scheduled_campaigns", {task_id: schedule_time_ts})
            
            return {
                "status": "success",
                "message": f"Campaign scheduled for {campaign['schedule_time'].isoformat()}"
            }
        else:
            # Start processing immediately
            # Set status to processing
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {"status": "processing", "started_at": datetime.now()}}
            )
            
            # Queue the campaign for processing
            task_id = str(uuid.uuid4())
            campaign_data = {
                "campaign_id": str(campaign["_id"]),
                "task_id": task_id
            }
            print(f"campaign_data: {campaign_data}")
            # Add to the processing queue
            # redis_client.lpush("email_campaigns_queue", json.dumps(campaign_data))
            try:
                redis_client.lpush("email_campaigns_queue", json.dumps(campaign_data))
                print("Campaign data pushed to Redis successfully!")
            except Exception as e:
                print(f"Failed to push campaign data to Redis: {e}")
                raise e
            print(122333999)
            # Start a background worker process to handle the queue
            # In a real implementation, you'd have a separate worker process
            # Here we're using background tasks as a simplified example
            if background_tasks:
                background_tasks.add_task(process_campaign_queue)
            
            return {
                "status": "success",
                "message": "Campaign processing started",
                "task_id": task_id
            }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email campaign: {str(e)}"
        )

@router.post("/{campaign_id}/test", response_model=Dict[str, Any])
async def send_test_email(
    campaign_id: str = Path(...),
    
    test_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Send a test email for the campaign
    """
    try:
        # Check required fields
        if "email" not in test_data:
            raise HTTPException(
                status_code=400,
                detail="Test recipient email is required"
            )
        
        # Get campaign
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Email campaign not found"
            )
        
        # Get template
        template = templates_collection.find_one({"_id": ObjectId(campaign["template_id"])})
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Email template not found"
            )
        

        variables = template.get("variables", {})
        variables.update(test_data.get("variables", {}))
        
        # Send test email
        result = await send_single_email(
            to_email=test_data["email"],
            to_name=test_data.get("name", "Test Recipient"),
            subject=campaign["subject"],
            template=template,
            variables=test_data.get("variables", {})
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to send test email")
            )
        
        return {
            "status": "success",
            "message": f"Test email sent to {test_data['email']}"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send test email: {str(e)}"
        )

@router.delete("/{campaign_id}", response_model=Dict[str, Any])
async def delete_email_campaign(
    campaign_id: str = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an email campaign
    """
    try:
        # Check if campaign exists
        campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
        if not campaign:
            raise HTTPException(
                status_code=404,
                detail="Email campaign not found"
            )
        
        # Check if campaign can be deleted (can't delete campaigns that are in progress)
        if campaign["status"] in ["processing", "sending"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete campaign with status: {campaign['status']}"
            )
        
        # If scheduled, remove from Redis scheduled queue
        if campaign["status"] == "scheduled":
            task_id = f"campaign:{campaign_id}"
            redis_client.zrem("scheduled_campaigns", task_id)
        
        # Delete campaign
        result = campaigns_collection.delete_one({"_id": ObjectId(campaign_id)})
        
        return {
            "status": "success",
            "message": "Email campaign deleted successfully"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete email campaign: {str(e)}"
        )

# Helper function to send a single email
async def send_single_email(
    to_email: str,
    to_name: str,
    subject: str,
    template: Dict[str, Any],
    variables: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Send a single email using the template
    """
    try:
        # Create email message
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = f"{to_name} <{to_email}>"
                # Add embedded images
        if template.get("logo_url"):
            variables['logo_img']=template.get("logo_url")
        if template.get("background_url"):
            variables['banner_img']=template.get("background_url")
            # Download image from Cloudinary
        html_content = template["html_content"]
        print(f"variables: {variables}")
        # for key, value in variables.items():
        #     html_content = html_content.replace(f"{{{{{key}}}}}", str(value))

        rendered_html = Template(html_content).render(variables)
        # Prepare HTML content with variable replacement
        print(1)
        
        print(2)
        print(f"html_content: {html_content}")
        print(3)
        print(f"variables: {variables}")
        print(4)
        # Replace variables in format {{variable_name}}

        
        # Add HTML part
        html_part = MIMEMultipart('alternative')
        html_part.attach(MIMEText(rendered_html, 'html'))
        msg.attach(html_part)
        

        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        # Log email
        email_logs_collection.insert_one({
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "template_id": str(template["_id"]),
            "variables": variables,
            "status": "sent",
            "sent_at": datetime.now()
        })
        
        return {
            "success": True,
            "message": f"Email sent to {to_email}"
        }
    
    except Exception as e:
        # Log failure
        email_logs_collection.insert_one({
            "to_email": to_email,
            "to_name": to_name,
            "subject": subject,
            "template_id": str(template["_id"]) if template else None,
            "variables": variables,
            "status": "failed",
            "error": str(e),
            "sent_at": datetime.now()
        })
        
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }

# Helper function to process the campaign queue
async def process_campaign_queue():
    """
    Process the campaign queue (worker process)
    
    Note: In a production system, this would be a separate worker process
    """
    while True:
        # Get campaign task from queue
        campaign_data = redis_client.rpop("email_campaigns_queue")
        if not campaign_data:
            break
        
        campaign_data = json.loads(campaign_data)
        campaign_id = campaign_data["campaign_id"]
        
        try:
            # Get campaign
            campaign = campaigns_collection.find_one({"_id": ObjectId(campaign_id)})
            if not campaign:
                continue
            
            # Get template
            template = templates_collection.find_one({"_id": ObjectId(campaign["template_id"])})
            if not template:
                continue
            
            if campaign.get("recipient_source") == "recipient_list" and campaign.get("recipient_list_id"):
                # Get recipients from a list
                recipient_list = recipient_lists_collection.find_one({"_id": ObjectId(campaign["recipient_list_id"])})
                if not recipient_list or "recipients" not in recipient_list:
                    # Mark campaign as failed
                    campaigns_collection.update_one(
                        {"_id": ObjectId(campaign_id)},
                        {"$set": {
                            "status": "failed",
                            "error": "Recipient list not found or empty",
                            "failed_at": datetime.now()
                        }}
                    )
                    continue
                    
                recipients = recipient_list["recipients"]
                total_recipients = len(recipients)
            else:
            # Get recipients
                recipient_data = await get_customers_for_combined_criteria(
                    segment_ids=campaign["segment_ids"],
                    custom_filters=campaign["custom_filters"],
                    operator=campaign["operator"],
                    limit=1000,  # Process in batches of 1000
                    skip=0
                )
                
                recipients = recipient_data.get("customers", [])
                total_recipients = recipient_data.get("total", 0)
            
            # Update campaign status
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "status": "sending",
                    "statistics.total_recipients": total_recipients
                }}
            )
            
            # Send emails in batches
            sent_count = 0
            failed_count = 0
            
            # Break into smaller batches (e.g., 50 per batch) to not overwhelm SMTP
            batch_size = 50

           

 
                    # Add campaign custom variables

            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i+batch_size]
                
                for recipient in batch:
                    # Prepare variables
                    variables = {
                        "customer_name": recipient.get("name", ""),
                        "email": recipient.get("email", ""),
                        "total_spent": recipient.get("totalSpent", 0),
                        "purchase_count": recipient.get("purchaseCount", 0)
                    }

                    if template.get("variables"):
                        variables.update(template["variables"])

                    if campaign.get("custom_variables"):
                        variables.update(campaign["custom_variables"])
                    # Send email
                    result = await send_single_email(
                        to_email=recipient.get("email", ""),
                        to_name=recipient.get("name", ""),
                        subject=campaign["subject"],
                        template=template,
                        variables=variables
                    )
                    
                    if result.get("success"):
                        sent_count += 1
                    else:
                        failed_count += 1
                    
                    # Update campaign statistics
                    campaigns_collection.update_one(
                        {"_id": ObjectId(campaign_id)},
                        {"$set": {
                            "statistics.sent": sent_count,
                            "statistics.failed": failed_count
                        }}
                    )
                
                # Pause between batches to not overwhelm SMTP server
                await asyncio.sleep(1)
            
            # Complete campaign
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.now()
                }}
            )
            
        except Exception as e:
            # Log error and mark campaign as failed
            campaigns_collection.update_one(
                {"_id": ObjectId(campaign_id)},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.now()
                }}
            )







from fastapi import UploadFile, File

# 1. Create a new collection for recipient lists
recipient_lists_collection = db["email_recipient_lists"]

# 2. Add endpoints for managing recipient lists

@router.get("/recipient-lists/", response_model=Dict[str, Any])
async def get_recipient_lists(
    current_user: dict = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
):
    """Get all recipient lists for the current user"""
    lists = list(recipient_lists_collection.find(
        {"created_by": current_user.id},
        {"recipients": 0}  # Exclude the actual recipients for the list endpoint
    ).skip(skip).limit(limit))
    
    return {
        "total": recipient_lists_collection.count_documents({"created_by": current_user.id}),
        "lists": json.loads(json.dumps(lists, default=str))
    }

@router.get("/recipients/download-template", response_class=FileResponse)
async def download_recipient_template(background_tasks: BackgroundTasks):
    """Download a template Excel file for email recipients"""
    # Create an empty DataFrame with specified columns
    df = pd.DataFrame(columns=["name", "email", "phone"])
    
    # Create a temporary file path for the Excel
    file_path = f'recipient_template_{uuid.uuid4()}.xlsx'
    
    # Write the DataFrame to Excel
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Recipients', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Recipients']
        
        # Add some formatting
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})
        for col_num, column in enumerate(df.columns):
            worksheet.write(0, col_num, column, header_format)
            worksheet.set_column(col_num, col_num, 20)
    
    # Return the Excel file and clean up afterwards
    return FileResponse(
        file_path, 
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
        filename='email_recipients_template.xlsx',
        background=BackgroundTask(lambda: os.remove(file_path))
    )

@router.post("/recipient-lists/upload", response_model=Dict[str, Any])
async def upload_recipient_list(
    list_name: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload an Excel file and create a new recipient list
    """
    try:
        # Read Excel file
        df = pd.read_excel(file.file)
        
        # Check required columns exist
        required_columns = ["name", "email"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Filter out invalid rows
        original_count = len(df)
        
        # Remove rows with missing required fields
        df = df.dropna(subset=["name", "email"])
        
        # Remove rows with invalid email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        df = df[df['email'].str.match(email_pattern)]
        
        # Convert DataFrame to list of recipients
        recipients = df.to_dict(orient='records')
        
        if len(recipients) == 0:
            return {
                "status": "warning",
                "message": "No valid recipients found in the file"
            }
        
        # Create a new recipient list
        new_list = {
            "name": list_name,
            "recipients": recipients,
            "total_recipients": len(recipients),
            "created_by": current_user.id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = recipient_lists_collection.insert_one(new_list)
        
        # Calculate total removed rows
        total_removed = original_count - len(recipients)
        
        return {
            "status": "success",
            "message": f"Created recipient list '{list_name}' with {len(recipients)} contacts. {total_removed} invalid entries were removed.",
            "list_id": str(result.inserted_id),
            "total_recipients": len(recipients)
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload recipients: {str(e)}"
        )

@router.get("/recipient-lists/{list_id}", response_model=Dict[str, Any])
async def get_recipient_list(
    list_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific recipient list"""
    recipient_list = recipient_lists_collection.find_one({"_id": ObjectId(list_id)})
    if not recipient_list:
        raise HTTPException(status_code=404, detail="Recipient list not found")
    
    return json.loads(json.dumps(recipient_list, default=str))


