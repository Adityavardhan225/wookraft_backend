import os
import logging
from typing import Dict, List, Any, Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import requests
from datetime import datetime
from dotenv import load_dotenv
import asyncio
from bson import ObjectId
from configurations.config import client
import re
import uuid
from jinja2 import Template

# Load environment variables
load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
FROM_NAME = os.getenv("FROM_NAME", "WooPOS")

# Setup logging
logger = logging.getLogger(__name__)

# Database collections
db = client["wookraft_db"]
templates_collection = db["email_templates"]
email_logs_collection = db["email_logs"]

class EmailService:
    """
    Service for sending emails with templates and tracking
    """
    
    @staticmethod
    async def send_email(
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        variables: Dict[str, Any] = {},
        campaign_id: Optional[str] = None,
        tracking_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Send an email using a template
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            template_id: ID of the template to use
            variables: Variables to replace in the template
            campaign_id: Optional ID of the campaign
            tracking_enabled: Whether to include tracking pixels
            
        Returns:
            Dictionary containing send result
        """
        try:
            # Get template
            template = templates_collection.find_one({"_id": ObjectId(template_id)})
            if not template:
                return {
                    "success": False,
                    "message": "Template not found"
                }
            
            # Create unique tracking ID
            tracking_id = str(uuid.uuid4()) if tracking_enabled else None
            
            # Add tracking ID to email log
            log_id = email_logs_collection.insert_one({
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "template_id": template_id,
                "campaign_id": campaign_id,
                "tracking_id": tracking_id,
                "variables": variables,
                "status": "processing",
                "created_at": datetime.now()
            }).inserted_id
            
            # Create email message
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email


            print(f'html_content: {template.get("html_content", "")}')
            if template.get("variables"):
                        variables.update(template["variables"])
            print(111111)
            print(f'variables 123: {variables}')
            # Prepare HTML content with variable replacement
            
            # html_content = Template(template.get("html_content", "")).render(variables)

            # Embed images in the email
            # html_content, embedded_images = EmailService._embed_images(html_content, variables)


            # original_html = html_content
            # Replace variables in format {{variable_name}}
            # for key, value in variables.items():
            #     html_content = html_content.replace(f"{{{{ {key} }}}}", str(value))

            # html_content = Template(html_content).render(variables)
            
            


            # Add tracking pixel if enabled

            
            # Create HTML part

            
            # Add embedded images
            if template.get("logo_url"):
                variables['logo_img']=template.get("logo_url")
            if template.get("background_url"):
                variables['banner_img']=template.get("background_url")

            template_obj = Template(template.get("html_content", ""))
            html_content = template_obj.render(**variables)  
            print(222222)
            print(f'html_content after template: {html_content}')
            print(333333)
            # html_content = Template(template.get("html_content", "")).render(variables)
            html_part = MIMEText(html_content, 'html')
            
            # Create multipart alternative container
            alternative = MIMEMultipart('alternative')
            alternative.attach(html_part)
            
            # Attach multipart alternative to the message
            msg.attach(alternative)

            if tracking_enabled and tracking_id:
                tracking_pixel = f'<img src="{os.getenv("API_BASE_URL", "http://localhost:8000")}/email/tracking/open/{tracking_id}" width="1" height="1" alt="" style="display:none;width:1px;height:1px;" />'
                
                # Add tracking pixel at the end of HTML
                if "</body>" in html_content:
                    html_content = html_content.replace("</body>", f"{tracking_pixel}</body>")
                else:
                    html_content = f"{html_content}{tracking_pixel}"
                
                # Add tracking to links
                html_content = await EmailService._add_link_tracking(html_content, tracking_id)
            # Connect to SMTP server and send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            
            # Update email log
            email_logs_collection.update_one(
                {"_id": log_id},
                {
                    "$set": {
                        "status": "sent",
                        "sent_at": datetime.now()
                    }
                }
            )
            
            return {
                "success": True,
                "message": f"Email sent to {to_email}",
                "tracking_id": tracking_id
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            
            # Update email log with error
            if 'log_id' in locals():
                email_logs_collection.update_one(
                    {"_id": log_id},
                    {
                        "$set": {
                            "status": "failed",
                            "error": str(e),
                            "failed_at": datetime.now()
                        }
                    }
                )
            
            return {
                "success": False,
                "message": f"Failed to send email: {str(e)}"
            }
    
    @staticmethod
    async def send_batch_emails(
        recipients: List[Dict[str, Any]],
        subject: str,
        template_id: str,
        campaign_id: Optional[str] = None,
        tracking_enabled: bool = True,
        batch_size: int = 50,
        delay_seconds: float = 1.0
    ) -> Dict[str, Any]:
        """
        Send emails to multiple recipients in batches
        
        Args:
            recipients: List of recipient dictionaries with email, name, and variables
            subject: Email subject
            template_id: ID of the template to use
            campaign_id: Optional ID of the campaign
            tracking_enabled: Whether to include tracking pixels
            batch_size: Number of emails to send in each batch
            delay_seconds: Delay between batches
            
        Returns:
            Dictionary containing send result
        """
        try:
            # Counters
            sent_count = 0
            failed_count = 0
            
            # Send emails in batches
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i+batch_size]
                
                # Process each recipient
                for recipient in batch:
                    # Send email
                    result = await EmailService.send_email(
                        to_email=recipient.get("email"),
                        to_name=recipient.get("name", ""),
                        subject=subject,
                        template_id=template_id,
                        variables=recipient.get("variables", {}),
                        campaign_id=campaign_id,
                        tracking_enabled=tracking_enabled
                    )
                    
                    # Update counters
                    if result.get("success"):
                        sent_count += 1
                    else:
                        failed_count += 1
                
                # Delay between batches to avoid rate limiting
                if i + batch_size < len(recipients):
                    await asyncio.sleep(delay_seconds)
            
            return {
                "success": True,
                "message": f"Sent {sent_count} emails, failed {failed_count}",
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_count": len(recipients)
            }
            
        except Exception as e:
            logger.error(f"Failed to send batch emails: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to send batch emails: {str(e)}",
                "sent_count": sent_count,
                "failed_count": failed_count,
                "total_count": len(recipients)
            }
    
    @staticmethod
    async def track_email_open(tracking_id: str) -> bool:
        """
        Track email open event
        
        Args:
            tracking_id: Tracking ID of the email
            
        Returns:
            True if tracking was successful
        """
        try:
            # Update email log
            result = email_logs_collection.update_one(
                {"tracking_id": tracking_id},
                {
                    "$set": {
                        "opened": True,
                        "opened_at": datetime.now()
                    }
                }
            )
            
            # Update campaign stats if campaign_id exists
            email_log = email_logs_collection.find_one({"tracking_id": tracking_id})
            if email_log and email_log.get("campaign_id"):
                db["email_campaigns"].update_one(
                    {"_id": ObjectId(email_log["campaign_id"])},
                    {
                        "$inc": {"statistics.opened": 1}
                    }
                )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to track email open: {str(e)}")
            return False
    
    @staticmethod
    async def track_email_click(tracking_id: str, link_id: str) -> Dict[str, Any]:
        """
        Track email link click event
        
        Args:
            tracking_id: Tracking ID of the email
            link_id: ID of the clicked link
            
        Returns:
            Dictionary with success status and redirect URL
        """
        try:
            # Find the email log
            email_log = email_logs_collection.find_one({"tracking_id": tracking_id})
            if not email_log:
                return {
                    "success": False,
                    "message": "Email tracking ID not found"
                }
            
            # Get link destination
            if "tracked_links" not in email_log:
                return {
                    "success": False,
                    "message": "No tracked links found"
                }
            
            # Find the link
            for link in email_log.get("tracked_links", []):
                if link.get("id") == link_id:
                    destination_url = link.get("url")
                    
                    # Record click
                    email_logs_collection.update_one(
                        {"tracking_id": tracking_id},
                        {
                            "$push": {
                                "clicks": {
                                    "link_id": link_id,
                                    "url": destination_url,
                                    "clicked_at": datetime.now()
                                }
                            },
                            "$set": {
                                "clicked": True,
                                "first_clicked_at": email_log.get("first_clicked_at", datetime.now())
                            }
                        }
                    )
                    
                    # Update campaign stats if campaign_id exists
                    if email_log.get("campaign_id"):
                        db["email_campaigns"].update_one(
                            {"_id": ObjectId(email_log["campaign_id"])},
                            {
                                "$inc": {"statistics.clicked": 1}
                            }
                        )
                    
                    return {
                        "success": True,
                        "destination_url": destination_url
                    }
            
            return {
                "success": False,
                "message": "Link ID not found"
            }
            
        except Exception as e:
            logger.error(f"Failed to track email click: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to track email click: {str(e)}"
            }
    
    @staticmethod
    async def _add_link_tracking(html_content: str, tracking_id: str) -> str:
        """
        Add tracking to links in HTML content
        
        Args:
            html_content: HTML content with links
            tracking_id: Tracking ID to add to links
            
        Returns:
            HTML content with tracking links
        """
        try:
            # Find all links in HTML
            link_pattern = r'<a\s+(?:[^>]*?\s+)?href=(["\'])(.*?)\1'
            links = re.findall(link_pattern, html_content)
            
            # Tracked links to save
            tracked_links = []
            
            # Replace each link with tracking link
            for quote, url in links:
                # Skip anchor links, javascript, mailto, etc.
                if url.startswith("#") or url.startswith("javascript:") or url.startswith("mailto:"):
                    continue
                
                # Generate unique ID for this link
                link_id = str(uuid.uuid4())
                
                # Create tracking URL
                tracking_url = f"{os.getenv('API_BASE_URL', 'http://localhost:8000')}/email/tracking/click/{tracking_id}/{link_id}"
                
                # Replace in HTML
                html_content = html_content.replace(
                    f'href={quote}{url}{quote}',
                    f'href={quote}{tracking_url}{quote}'
                )
                
                # Add to tracked links
                tracked_links.append({
                    "id": link_id,
                    "url": url
                })
            
            # Save tracked links to email log
            if tracked_links:
                email_logs_collection.update_one(
                    {"tracking_id": tracking_id},
                    {
                        "$set": {
                            "tracked_links": tracked_links
                        }
                    }
                )
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to add link tracking: {str(e)}")
            return html_content

# Create a singleton instance
email_service = EmailService()