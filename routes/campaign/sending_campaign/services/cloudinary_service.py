import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, Any, Optional, Union
from fastapi import UploadFile
import logging
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
        cloud_name = 'dl91gwshv', 
        api_key = '392761399558392', 
        api_secret = 'N8dW3ksMCt41qCfzFeobTh701hM',
        secure=True
)



# Setup logging
logger = logging.getLogger(__name__)

class CloudinaryService:
    """
    Service for handling Cloudinary image uploads and management
    """
    
    @staticmethod
    async def upload_image(
        file: UploadFile,
        folder: str = "woopos/email_templates",
        public_id: Optional[str] = None,
        overwrite: bool = True,
        resource_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary
        
        Args:
            file: The UploadFile to upload
            folder: Cloudinary folder path
            public_id: Optional public ID for the asset
            overwrite: Whether to overwrite existing images with the same ID
            resource_type: Type of resource (image, raw, video)
            
        Returns:
            Dictionary containing upload result
        """
        try:
            # Read file content
            file_content = await file.read()
            
            # Generate public_id if not provided
            if not public_id:
                file_ext = file.filename.split('.')[-1] if file.filename else "png"
                public_id = f"{uuid.uuid4().hex}"
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_content,
                folder=folder,
                public_id=public_id,
                overwrite=overwrite,
                resource_type=resource_type
            )
            
            return {
                "success": True,
                "public_id": upload_result.get("public_id"),
                "secure_url": upload_result.get("secure_url"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height"),
                "format": upload_result.get("format"),
                "resource_type": upload_result.get("resource_type")
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def upload_from_url(
        image_url: str,
        folder: str = "woopos/email_templates",
        public_id: Optional[str] = None,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        Upload an image to Cloudinary from a URL
        
        Args:
            image_url: URL of the image to upload
            folder: Cloudinary folder path
            public_id: Optional public ID for the asset
            overwrite: Whether to overwrite existing images with the same ID
            
        Returns:
            Dictionary containing upload result
        """
        try:
            # Generate public_id if not provided
            if not public_id:
                public_id = f"{uuid.uuid4().hex}"
            
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_url,
                folder=folder,
                public_id=public_id,
                overwrite=overwrite
            )
            
            return {
                "success": True,
                "public_id": upload_result.get("public_id"),
                "secure_url": upload_result.get("secure_url"),
                "width": upload_result.get("width"),
                "height": upload_result.get("height"),
                "format": upload_result.get("format")
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image from URL to Cloudinary: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def delete_image(
        public_id: str,
        resource_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Delete an image from Cloudinary
        
        Args:
            public_id: Public ID of the image to delete
            resource_type: Type of resource (image, raw, video)
            
        Returns:
            Dictionary containing deletion result
        """
        try:
            # Delete from Cloudinary
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            
            if result.get("result") == "ok":
                return {
                    "success": True,
                    "message": f"Image {public_id} deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to delete image {public_id}",
                    "result": result
                }
            
        except Exception as e:
            logger.error(f"Failed to delete image from Cloudinary: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def create_image_tag(
        public_id: str,
        alt: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
        transformations: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate an HTML image tag for a Cloudinary image
        
        Args:
            public_id: Public ID of the image
            alt: Alt text for the image
            width: Optional width for the image
            height: Optional height for the image
            transformations: Optional transformations to apply
            
        Returns:
            HTML image tag string
        """
        try:
            # Build transformation options
            options = {}
            
            if width:
                options["width"] = width
            
            if height:
                options["height"] = height
            
            if transformations:
                options.update(transformations)
            
            # Generate image tag
            return cloudinary.CloudinaryImage(public_id).image(
                alt=alt,
                **options
            )
            
        except Exception as e:
            logger.error(f"Failed to create image tag: {str(e)}")
            return f'<img src="{cloudinary.CloudinaryImage(public_id).build_url()}" alt="{alt}">'
    
    @staticmethod
    async def get_upload_signature(
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a signature for client-side uploading
        
        Args:
            params: Additional parameters for the signature
            
        Returns:
            Dictionary containing timestamp, signature, and API key
        """
        try:
            timestamp = cloudinary.utils.now()
            
            # Default params
            default_params = {
                "timestamp": timestamp,
                "folder": "woopos/email_templates"
            }
            
            # Merge with provided params
            if params:
                default_params.update(params)
            
            # Generate signature
            signature = cloudinary.utils.api_sign_request(
                default_params,
                cloudinary.config().api_secret
            )
            
            return {
                "success": True,
                "timestamp": timestamp,
                "signature": signature,
                "api_key": cloudinary.config().api_key,
                "params": default_params
            }
            
        except Exception as e:
            logger.error(f"Failed to generate upload signature: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Create a singleton instance
cloudinary_service = CloudinaryService()