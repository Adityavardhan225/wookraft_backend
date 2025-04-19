from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path, File, UploadFile, Form
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv

from routes.security.protected_authorise import get_current_user
from configurations.config import client
import json
from routes.campaign.sending_campaign.services.cloudinary_service import cloudinary_service

# Load environment variables
load_dotenv()

router = APIRouter()
db = client["wookraft_db"]
templates_collection = db["email_templates"]






@router.post("/save_template", response_model=Dict[str, Any])
async def create_email_template(
    name: str = Form(...),
    subject: str = Form(...),
    html_content: str = Form(...),
    variables: str = Form(...),
    description: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    background: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new email template with optional image uploads to Cloudinary
    """
    try:
        variables_dict = json.loads(variables)
        # Upload logo to Cloudinary if provided
        logo_url = None
        if logo:
            logo_public_id = f"{name.lower().replace(' ', '_')}_logo"
            logo_result = await cloudinary_service.upload_image(
                file=logo,
                folder="woopos/email_templates/logo",
                public_id=logo_public_id
            )
            if logo_result.get("success"):
                logo_url = logo_result.get("secure_url")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to upload logo: {logo_result.get('error')}")
        
        # Upload background to Cloudinary if provided
        background_url = None
        if background:
            bg_public_id = f"{name.lower().replace(' ', '_')}_background"
            bg_result = await cloudinary_service.upload_image(
                file=background,
                folder="woopos/email_templates/background",
                public_id=bg_public_id
            )
            if bg_result.get("success"):
                background_url = bg_result.get("secure_url")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to upload background: {bg_result.get('error')}")
        
        # Access user attributes directly instead of using .get()
        # UserOutput object doesn't have a .get() method
        user_id = current_user.id if hasattr(current_user, "id") else ""
        
        # Create template document
        template = {
            "name": name,
            "subject": subject,
            "html_content": html_content,
            "variables": variables_dict, 
            "description": description,
            "logo_url": logo_url,
            "background_url": background_url,
            "created_by": user_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Insert into database
        result = templates_collection.insert_one(template)
        
        # Return created template with ID
        template["_id"] = str(result.inserted_id)
        
        return {
            "status": "success",
            "message": "Email template created successfully",
            "template": template
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create email template: {str(e)}"
        )

@router.get("/", response_model=Dict[str, Any])
async def get_all_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all email templates with pagination
    """
    try:
        # Count total templates
        total = templates_collection.count_documents({})
        
        # Get templates with pagination
        cursor = templates_collection.find().sort("created_at", -1).skip(skip).limit(limit)
        
        # Format templates
        templates = []
        for template in cursor:
            template["_id"] = str(template["_id"])
            templates.append(template)
        
        return {
            "status": "success",
            "total": total,
            "templates": templates
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve email templates: {str(e)}"
        )

@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_template_by_id(
    template_id: str = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific email template by ID
    """
    try:
        # Find template
        template = templates_collection.find_one({"_id": ObjectId(template_id)})
        
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Email template not found"
            )
        
        # Format ID
        template["_id"] = str(template["_id"])
        
        return {
            "status": "success",
            "template": template
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve email template: {str(e)}"
        )

@router.put("/{template_id}", response_model=Dict[str, Any])
async def update_email_template(
    template_id: str = Path(...),
    name: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    html_content: Optional[str] = Form(None),
    variables: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    background: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing email template
    """
    try:
        # Check if template exists
        template = templates_collection.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Email template not found"
            )
        
        # Prepare update data
        update_data = {}
        
        if name:
            update_data["name"] = name
        
        if subject:
            update_data["subject"] = subject
        
        if html_content:
            update_data["html_content"] = html_content

        if variables:
            update_data["variables"] = json.loads(variables)  # Parse variables JSON string
        
        if description:
            update_data["description"] = description
        
        # Upload logo to Cloudinary if provided
        if logo:
            template_name = name if name else template.get('name', 'template')
            logo_public_id = f"{template_name.lower().replace(' ', '_')}_logo"
            
            logo_result = await cloudinary_service.upload_image(
                file=logo,
                folder="woopos/email_templates/logo",
                public_id=logo_public_id,
                overwrite=True
            )
            
            if logo_result.get("success"):
                update_data["logo_url"] = logo_result.get("secure_url")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to upload logo: {logo_result.get('error')}")
        
        # Upload background to Cloudinary if provided
        if background:
            template_name = name if name else template.get('name', 'template')
            bg_public_id = f"{template_name.lower().replace(' ', '_')}_background"
            
            bg_result = await cloudinary_service.upload_image(
                file=background,
                folder="woopos/email_templates/background",
                public_id=bg_public_id,
                overwrite=True
            )
            
            if bg_result.get("success"):
                update_data["background_url"] = bg_result.get("secure_url")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to upload background: {bg_result.get('error')}")
        
        # Add update timestamp
        update_data["updated_at"] = datetime.now()
        update_data["updated_by"] = current_user.get("_id", "")
        
        # Update template
        templates_collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": update_data}
        )
        
        # Get updated template
        updated_template = templates_collection.find_one({"_id": ObjectId(template_id)})
        updated_template["_id"] = str(updated_template["_id"])
        
        return {
            "status": "success",
            "message": "Email template updated successfully",
            "template": updated_template
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update email template: {str(e)}"
        )

@router.delete("/{template_id}", response_model=Dict[str, Any])
async def delete_email_template(
    template_id: str = Path(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an email template
    """
    try:
        # Check if template exists
        template = templates_collection.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise HTTPException(
                status_code=404,
                detail="Email template not found"
            )
        
        # # Check if template is being used in campaigns
        # campaign_count = db["email_campaigns"].count_documents({"template_id": template_id})
        # if campaign_count > 0:
        #     raise HTTPException(
        #         status_code=400,
        #         detail=f"Cannot delete template that is being used in {campaign_count} campaigns"
        #     )
        
        # Delete images from Cloudinary if they exist
        if template.get("logo_url"):
            # Extract public_id from URL
            logo_parts = template["logo_url"].split("/")
            logo_filename = logo_parts[-1].split(".")[0]
            
            # Build the full public_id including folder path
            folder_idx = logo_parts.index("woopos")
            logo_public_id = "/".join(logo_parts[folder_idx:len(logo_parts)-1]) + "/" + logo_filename
            
            # Delete from Cloudinary
            delete_result = await cloudinary_service.delete_image(logo_public_id)
            if not delete_result.get("success"):
                # Log the error but continue with deletion
                print(f"Warning: Failed to delete logo image: {delete_result.get('error')}")
        
        if template.get("background_url"):
            # Extract public_id from URL
            bg_parts = template["background_url"].split("/")
            bg_filename = bg_parts[-1].split(".")[0]
            
            # Build the full public_id including folder path
            folder_idx = bg_parts.index("woopos")
            bg_public_id = "/".join(bg_parts[folder_idx:len(bg_parts)-1]) + "/" + bg_filename
            
            # Delete from Cloudinary
            delete_result = await cloudinary_service.delete_image(bg_public_id)
            if not delete_result.get("success"):
                # Log the error but continue with deletion
                print(f"Warning: Failed to delete background image: {delete_result.get('error')}")
        
        # Delete template from database
        result = templates_collection.delete_one({"_id": ObjectId(template_id)})
        
        return {
            "status": "success",
            "message": "Email template deleted successfully"
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete email template: {str(e)}"
        )

@router.post("/preview", response_model=Dict[str, Any])
async def preview_template(
    template_id: str = Body(..., embed=True),
    test_data: Dict[str, Any] = Body({}, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview an email template with test data
    """
    try:
        # Fetch the template by ID
        template = templates_collection.find_one({"_id": ObjectId(template_id)})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Get the HTML content and variables
        html_content = template["html_content"]
        variables = template.get("variables", {})

        # Merge default variables with test data
        merged_data = {**variables, **test_data}

        # Render the template
        from jinja2 import Template
        rendered_html = Template(html_content).render(merged_data)

        return {
            "status": "success",
            "preview_html": rendered_html
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate preview: {str(e)}"
        )