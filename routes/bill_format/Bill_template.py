from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pymongo.database import Database
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from bson import ObjectId
from configurations.config import get_db
from routes.security.protected_authorise import get_current_user
from datetime import datetime, date, timedelta
import logging
import re
from fastapi.responses import StreamingResponse
import io
import traceback
from routes.bill_format.Bill_storage import BillStorage
from motor.motor_asyncio import AsyncIOMotorClient

# from routes.bill_format.feedback_form import send_feedback_email
from routes.bill_format.feedback_form import send_feedback_email_with_form



# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic Models
class BusinessInfo(BaseModel):
    name: str
    address: str
    phone: str
    gstin: Optional[str] = None
    fssaiNo: Optional[str] = None
    sacCode: Optional[str] = None
    logoIcon: Optional[str] = None
    email: Optional[str] = None

class Styling(BaseModel):
    fontFamily: Optional[str] = "Arial, sans-serif"
    paperWidth: int = 80
    paperPadding: int = 20
    headerFontSize: int = 16
    contentFontSize: int = 12
    footerFontSize: int = 10
    headerAlignment: str = "center"
    contentAlignment: str = "left"
    footerAlignment: str = "center"
    lineSpacing: float = 1.5
    itemSpacing: int = 5
    sectionSpacing: int = 15

class Config(BaseModel):
    showHeader: bool = True
    showBusinessInfo: bool = True
    showLogo: bool = False
    showMetaInfo: bool = True
    showItemsHeader: bool = True
    showItems: bool = True
    showCalculations: bool = True
    showTotal: bool = True
    showPaymentInfo: bool = True
    showFooter: bool = True
    showItemSize:bool = True
    showItemAddons:bool = True
    showItemNotes:bool = True
    businessInfo: BusinessInfo
    footerText: str
    styling: Optional[Styling] = None

class BillTemplate(BaseModel):
    id: Optional[str] = None
    name: str
    templateType: Optional[str] = None
    isActive: bool = False
    config: Config
    htmlContent: Optional[str] = None  # HTML content
    cssContent: Optional[str] = None  # CSS styling content

class BillTemplateSettings(BaseModel):
    templates: List[BillTemplate]
    activeTemplateId: str

@router.post("/selected-bill-template")
async def save_selected_template(
    template: Dict[str, Any] = Body(..., description="The selected template configuration with HTML content"),
    token: str = Body(...),
    db: Database = Depends(get_db)
):
    """Save the selected bill template including HTML/CSS content for the current owner."""
    try:
        # Verify user is authenticated and has admin rights
        current_user = get_current_user(db, token)
        
        # Only allow admin to update templates
        if current_user.role != "admin":  # Note: Changed to ADMIN to match case in your system
            raise HTTPException(status_code=403, detail="Only admin can update bill templates")
            
        owner_id = current_user.owner_id
        logger.info(f"Saving selected bill template for owner_id: {owner_id}")
        
        # Save to MongoDB - using upsert to update if exists or insert if not
        result = db.settings.update_one(
            {"setting_type": "selected_bill_template", "owner_id": owner_id},
            {"$set": {
                "template": template,
                "updated_at": datetime.now().isoformat()
            }},
            upsert=True
        )
        
        logger.info(f"Selected template saved successfully for owner_id: {owner_id}")
        return {"success": True, "message": "Selected template saved successfully"}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error saving selected template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save template: {str(e)}")

@router.get("/selected-bill-template")
async def get_selected_template(
    token: str = Query(..., description="Authentication token"),
    db: Database = Depends(get_db)
):
    """Get the selected bill template for the current owner."""
    try:
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        owner_id = current_user.owner_id
        logger.info(f"Fetching selected template for owner_id: {owner_id}")
        
        # Retrieve from MongoDB
        settings = db.settings.find_one({
            "setting_type": "selected_bill_template",
            "owner_id": owner_id
        })
        
        if not settings or "template" not in settings:
            logger.warning(f"No selected template found for owner_id: {owner_id}")
            return {"success": False, "message": "No selected template found"}
        
        logger.info(f"Retrieved selected template for owner_id: {owner_id}")
        return {"success": True, "template": settings["template"]}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving selected template: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve template: {str(e)}")




# Add these imports at the top of your file
from playwright.async_api import async_playwright
import asyncio
@router.get("/generate-bill-pdf/{order_id}")
async def generate_bill_pdf(
    order_id: str,
    token: str = Query(...),
    db: Database = Depends(get_db)
):
    """
    Generate a PDF bill for an order using the stored template.
    Supports enhanced features including discounts and addon details.
    """
    try:
        # Get complete order details using existing endpoint
        print(f"[DEBUG] Getting complete order details for order: {order_id}")
        from routes.ordersystem.billing_system import get_order_details
        
        # Get full order details with all customizations, discounts, etc.
        order_details = await get_order_details(
            order_id=order_id,
            token=token,
            db=db
        )
        
        # Verify user is authenticated and get template
        current_user = get_current_user(db, token)
        owner_id = current_user.owner_id
        
        settings = db.settings.find_one({
            "setting_type": "selected_bill_template",
            "owner_id": owner_id
        })
        
        if not settings or "template" not in settings:
            raise HTTPException(status_code=404, detail="No bill template found")
            
        template = settings["template"]
        
        # Extract styling and content
        html_content = template.get("htmlContent", "")
        css_content = template.get("cssContent", "")
        
        # Extract CSS from the HTML content if available
        embedded_css = ""
        css_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
        if css_match:
            embedded_css = css_match.group(1)
            html_content = re.sub(r'<style>.*?</style>', '', html_content, flags=re.DOTALL)
        
        if embedded_css:
            css_content = embedded_css
        
        # Extract styling and business info
        styling = {}
        if "config" in template and "styling" in template["config"]:
            styling = template["config"]["styling"]
        elif "styling" in template:
            styling = template["styling"]
        
        paper_width = styling.get("paperWidth", 80)
        paper_padding = styling.get("paperPadding", 20)
        font_family = styling.get("fontFamily", "Arial, sans-serif")
        
        business_info = {}
        footer_text = ""
        
        if "config" in template and "businessInfo" in template["config"]:
            business_info = template["config"]["businessInfo"]
        elif "businessInfo" in template:
            business_info = template["businessInfo"]
            
        if "config" in template and "footerText" in template["config"]:
            footer_text = template["config"]["footerText"]
        elif "footerText" in template:
            footer_text = template["footerText"]
        
        # Create enhanced bill items from complete order details
        bill_items = []
        total_discount = 0
        
        for item in order_details["items"]:
            # Calculate if the item has a discount
            original_price = item.get("original_price", item["base_price"])
            has_discount = original_price > item["base_price"]
            if has_discount:
                total_discount += (original_price - item["base_price"]) * item["quantity"]
            
            # Format the item name with customizations
            item_name = item["name"]
            
            # Add size information if available
            size_info = item["customization_details"].get("size")
            if size_info:
                item_name += f" ({size_info['name']})"
            
            # Handle customization text
            custom_text = item["customization_details"].get("text", "").strip()
            if custom_text:
                item_name += f" - {custom_text}"
            
            # Create the base item with discount information
            bill_item = {
                "name": item_name,
                "qty": item["quantity"],
                "price": item["base_price"],
                "originalPrice": original_price if has_discount else None,
                "amount": item["total_price"],
                "size": size_info["name"] if size_info else None,
                "notes": custom_text if custom_text else None,
                "addons": []
            }
            # Add addon items directly to the parent item's addons array
            for addon in item["customization_details"].get("addons", []):
                bill_item["addons"].append({
                    "name": addon["name"],
                    "price": addon["unit_price"]
                    
                    # No qty or amount - matching the desired format
                })

            print(f'bill_item: {bill_item}')
            bill_items.append(bill_item)
            
            # Add addon items with more details
            # for addon in item["customization_details"].get("addons", []):
            #     addon_item = {
            #         "name": f"  + {addon['name']}",
            #         "qty": addon["quantity"],
            #         "price": addon["unit_price"],
            #         "amount": addon["total_price"],
            #         "is_addon": True,
            #         "parent_item": item_name
            #     }
            #     bill_items.append(addon_item)
            #     bill_item["addons"].append({
            #         "name": addon["name"],
            #         "price": addon["unit_price"],
            #         "qty": addon["quantity"]
            #     })
        
        # Create calculations for discounts
        calculations = []
        
        # Item level discounts
        item_discount = order_details["total_price"] - order_details["total_discounted_price"]
        if item_discount > 0:
            calculations.append({
                "label": "Item Discounts",
                "amount": -item_discount
            })
            total_discount += item_discount
        
        # Bill level discounts
        if "bill_discount_amount" in order_details and order_details["bill_discount_amount"] > 0:
            calculations.append({
                "label": "Bill Discount",
                "amount": -order_details["bill_discount_amount"]
            })
            total_discount += order_details["bill_discount_amount"]

        temp_customer = db.customer_temporary_details.find_one({"order_id": order_id})
        if temp_customer:
            customer_name = temp_customer.get("name", "")
            customer_phone = temp_customer.get("phone", "")
            customer_email = temp_customer.get("email", "")
        print(f'temp_customer: {temp_customer}')
        
        # Create bill data structure for template
        bill_data = {
            "date": datetime.now().strftime("%d/%m/%Y"),
            "time": datetime.now().strftime("%H:%M"),
            "billNo": f"ORD-{order_id[-6:]}",
            "customerName": customer_name,
            "customerPhone": customer_phone,
            "paymentMode": order_details.get("payment_method", "Cash"),
            "server": order_details.get("employee_name", ""),
            "table": order_details.get("table_number", ""),
            "items": bill_items,
            "subtotal": {
                "qty": sum(item["quantity"] for item in order_details["items"]),
                "amount": order_details["total_price"]
            },
            "calculations": calculations,
            "totalDiscount": total_discount,  # Add total discount value
            "total": order_details["final_price"],
            "payments": {
                "cash": order_details["final_price"],
                "cashTendered": order_details["final_price"]
            },
            "currentYear": datetime.now().year
        }
        
        # Replace variables in template
        rendered_html = html_content
        
        # Replace simple fields
        for key, value in bill_data.items():
            if isinstance(value, (str, int, float)):
                rendered_html = re.sub(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', str(value), rendered_html)
                rendered_html = re.sub(r'\{\{\s*data\.' + re.escape(key) + r'\s*\}\}', str(value), rendered_html)
        
        # Process nested objects
        if "subtotal" in bill_data:
            for key, value in bill_data["subtotal"].items():
                pattern = r'\{\{\s*data\.subtotal\.' + re.escape(key) + r'\s*\}\}'
                rendered_html = re.sub(pattern, str(value), rendered_html)
                
        if "payments" in bill_data:
            for key, value in bill_data["payments"].items():
                pattern = r'\{\{\s*data\.payments\.' + re.escape(key) + r'\s*\}\}'
                rendered_html = re.sub(pattern, str(value), rendered_html)
        
        # Process business info
        if business_info:
            for key, value in business_info.items():
                if isinstance(value, (str, int, float, bool)):
                    rendered_html = re.sub(r'\{\{\s*businessInfo\.' + re.escape(key) + r'\s*\}\}', str(value), rendered_html)
        
        # Replace footer text
        if footer_text:
            rendered_html = re.sub(r'\{\{\s*footerText\s*\}\}', footer_text, rendered_html)
            
        # Handle special placeholders
        rendered_html = re.sub(r'\{\{\s*data\.totalDiscount\s*\}\}', str(total_discount), rendered_html)
        
        # Check for change_amount placeholder
        if "change_amount" in rendered_html:
            change_html = ""
            if bill_data["payments"]["cashTendered"] > bill_data["total"]:
                change = bill_data["payments"]["cashTendered"] - bill_data["total"]
                change_html = f"Change: Rs {change:.2f}"
            rendered_html = re.sub(r'\{\{\s*data\.change_amount\s*\}\}', change_html, rendered_html)
        
        # Enhanced items_table replacement with discounted prices and addon details
        items_placeholder = re.search(r'\{\{\s*items_table\s*\}\}', rendered_html)
        if items_placeholder:
            items_html = ""
            current_item_name = ""
            
            for item in bill_data["items"]:
                # Display items with discount if applicable
                price_html = ""
                if item.get("originalPrice") and item["originalPrice"] > item["price"]:
                    price_html = f"""
                    <span class="item-price">
                        <span class="strike-price">{item['originalPrice']:.2f}</span>
                        <span class="discounted-price">{item['price']:.2f}</span>
                    </span>
                    """
                else:
                    price_html = f"""<span class="item-price">{item['price']:.2f}</span>"""
                
                # Main item row
                items_html += f"""
                <div class="receipt-row item-row">
                    <div class="col col-name">{item['name']}</div>
                    <div class="col col-qty">{item['qty']}</div>
                    {price_html}
                    <div class="col col-amount">{item['amount']:.2f}</div>
                </div>
                """
                
                # Add item detail rows if needed
                if item.get("size") and not item.get("is_addon"):
                    items_html += f"""
                    <div class="item-detail-row">Size: {item['size']}</div>
                    """
                
                if item.get("notes") and not item.get("is_addon"):
                    items_html += f"""
                    <div class="item-detail-row">Note: {item['notes']}</div>
                    """

                        # Add addon details - THIS IS THE MISSING PART
                if item.get("addons") and len(item["addons"]) > 0:
                    addons_text = ", ".join([f"{addon['name']} (+{addon['price']:.2f})" for addon in item["addons"]])
                    items_html += f"""
                    <div class="item-detail-row">Addons: {addons_text}</div>
                    """
            
            rendered_html = re.sub(r'\{\{\s*items_table\s*\}\}', items_html, rendered_html)
        
        # Enhanced calculations_table replacement
        calc_placeholder = re.search(r'\{\{\s*calculations_table\s*\}\}', rendered_html)
        if calc_placeholder:
            calcs_html = ""
            for calc in bill_data["calculations"]:
                calcs_html += f"""
                <div class="receipt-row calc-row">
                    <div class="col col-name">{calc['label']}</div>
                    <div class="col col-qty"></div>
                    <div class="col col-price"></div>
                    <div class="col col-amount discount-value">{calc['amount']:.2f}</div>
                </div>
                """
            rendered_html = re.sub(r'\{\{\s*calculations_table\s*\}\}', calcs_html, rendered_html)
        
        # Create full HTML with CSS
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                {css_content}
                
                /* Ensure proper dimensions */
                body {{
                    width: {paper_width}mm;
                    margin: 0 auto;
                    padding: 0;
                    font-family: {font_family};
                }}
                
                @page {{
                    margin: {paper_padding}mm;
                }}
                
                /* New styles for enhanced features */
                .receipt-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 5px;
                }}
                
                .item-row, .calc-row, .header-row {{
                    display: grid;
                    grid-template-columns: 40% 20% 20% 20%;
                    padding: 5px 0;
                    border-bottom: 1px solid #f5f5f5;
                }}
                
                .total-row {{
                    display: grid;
                    grid-template-columns: 60% 40%;
                    padding: 8px 0;
                    border-top: 1px dashed #000;
                    border-bottom: 1px dashed #000;
                    font-weight: bold;
                    margin-top: 10px;
                }}
                
                .meta-grid {{
                    display: grid;
                    grid-template-columns: 50% 50%;
                }}
                
                .col-name {{ text-align: left; }}
                .col-qty, .col-price, .col-amount {{ text-align: right; }}
                
                .item-detail-row {{
                    font-size: 90%;
                    color: #666;
                    margin-left: 10px;
                    margin-bottom: 5px;
                    padding-left: 5px;
                    border-left: 1px solid #f0f0f0;
                }}
                
                .strike-price {{
                    text-decoration: line-through;
                    color: #999;
                    margin-right: 5px;
                    font-size: 90%;
                }}
                
                .discounted-price {{
                    color: #e53935;
                }}
                
                .discount-value {{
                    color: #e53935;
                }}
            </style>
        </head>
        <body>
            {rendered_html}
        </body>
        </html>
        """
        
        # Generate PDF using Playwright
        width_px = int(paper_width * 3.8)
        
        pdf_data = await generate_pdf_with_playwright(
            html_content=full_html,
            width=width_px,
            margins={
                "top": f"{paper_padding}mm",
                "right": f"{paper_padding}mm",
                "bottom": f"{paper_padding}mm",
                "left": f"{paper_padding}mm"
            }
        )
        
        filename = f"bill_{bill_data['billNo'].replace('/', '-')}.pdf"

            # Initialize BillStorage
                # Get MongoDB URI from settings or environment
        # In generate_bill_pdf function
        bill_storage = BillStorage(db)
        storage_result = bill_storage.store_bill(
            order_details=order_details,
            bill_items=bill_items,
            calculations=calculations,
            total_amount=bill_data["total"]
        )
        print(f"[BILL] Stored bill data: {storage_result}")
        
        # Log the result
        print(f"[BILL] Stored bill data: {storage_result}")

        if storage_result and storage_result.get("bill_id"):
            bill_id = storage_result.get("bill_id")
            
            # Get business/restaurant name
            restaurant_name = business_info.get("business_name", "WooPOS Restaurant")
            
            # Send feedback email if customer email is available
            if customer_email:
                name_to_use = customer_name if customer_name else "Valued Customer"
                
                # This sends an email with embedded feedback stars directly in the email
                try:
                    email_sent = send_feedback_email_with_form(
                        email=customer_email,
                        customer_name=name_to_use,
                        order_id=order_id,
                        bill_id=str(bill_id),
                        items=bill_items,
                        restaurant_name=restaurant_name
                    )
                    
                    if email_sent:
                        logging.info(f"Feedback email with direct ratings sent to {customer_email} for order {order_id}")
                        
                        # Update the bill record to indicate feedback email was sent
                        db.bills.update_one(
                            {"_id": ObjectId(bill_id)},
                            {"$set": {
                                "feedback_email_sent": True,
                                "feedback_email_sent_at": datetime.now()
                            }}
                        )
                    else:
                        logging.warning(f"Failed to send feedback email to {customer_email} for order {order_id}")
                except Exception as e:
                    logging.error(f"Error sending feedback email: {str(e)}")
            else:
                logging.info(f"No customer email available for order {order_id}, skipping feedback email")





        # Update table status to vacant after billing
        if order_details.get("table_number"):
            try:
                table_number = order_details.get("table_number")
                print(f"[TABLE] Marking table {table_number} as vacant after billing")
                
                # Get the table_id by table_number
                table = db.tables.find_one({"table_number": table_number})
                if table:
                    from routes.table_management.table_management_model import TableStatus
                    
                    # Update table status to vacant
                    result = db.tables.update_one(
                        {"_id": table["_id"]},
                        {"$set": {"status": TableStatus.VACANT}}
                    )
                    
                    # Broadcast table status update to all clients
                    if result.modified_count > 0:
                        # Import needed only if table was found
                        import asyncio
                        from routes.table_management.table_management import manager, serialize_for_json
                        
                        # Get updated table
                        updated_table = db.tables.find_one({"_id": table["_id"]})
                        if updated_table:
                            # Broadcast update
                            asyncio.create_task(manager.broadcast({
                                "type": "table_status_updated",
                                "data": serialize_for_json(updated_table)
                            }))
                            print(f"[TABLE] Successfully marked table {table_number} as vacant")
            except Exception as table_err:
                print(f"[TABLE] Error updating table status: {str(table_err)}")
                # Don't raise the exception - we don't want to fail bill generation if table update fails        



        
        return StreamingResponse(
            io.BytesIO(pdf_data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to generate bill: {str(e)}")


# Add this helper function to generate PDFs using Playwright
async def generate_pdf_with_playwright(html_content, width=800, margins=None):
    """
    Generate PDF from HTML content using Playwright.
    
    Args:
        html_content: The HTML content to render
        width: Page width in pixels (default 800px)
        margins: Dictionary with top, right, bottom, left margins
        
    Returns:
        PDF file content as bytes
    """
    if margins is None:
        margins = {"top": "20mm", "right": "20mm", "bottom": "20mm", "left": "20mm"}
        
    try:
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch()
            
            # Create a new page
            page = await browser.new_page(viewport={"width": width, "height": 800})
            
            # Set the HTML content
            await page.set_content(html_content, wait_until="networkidle")
            
            # Allow time for any fonts or styles to load
            await asyncio.sleep(0.5)
            
            # Generate PDF
            pdf_data = await page.pdf(
                format="A4",  # This will be overridden by width and height if provided
                width=f"{width}px",
                print_background=True,
                margin=margins
            )
            
            # Close the browser
            await browser.close()
            
            return pdf_data
    except Exception as e:
        print(f"[ERROR] Playwright PDF generation failed: {str(e)}")
        print(traceback.format_exc())
        raise e
    










class CustomerDetails(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[str] = None
    address: Optional[str] = None
    table_number: Optional[int] = None
    order_id: str = Field(..., description="Required to link details to order")
    waiter_no: Optional[str] = None

@router.post("/save-customer-details")
async def save_customer_details(
    details: CustomerDetails,
    token: str = Query(...),
    db: Database = Depends(get_db)
):
    """
    Save basic customer details for a bill in a dedicated temporary collection.
    """
    try:
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        
        # Verify the order exists
        if not db.orders.find_one({"_id": ObjectId(details.order_id)}):
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Prepare data for storage
        customer_data = {
            "name": details.name,
            "phone": details.phone,
            "order_id": details.order_id,
            "table_number": details.table_number,
            "waiter_no": details.waiter_no,
            "created_at": datetime.now(),
            "owner_id": current_user.owner_id
        }
        
        # Add optional fields if provided
        if details.email:
            customer_data["email"] = details.email
        
        if details.address:
            customer_data["address"] = details.address
        
        # First, remove any existing details for this order
        db.customer_temporary_details.delete_many({"order_id": details.order_id})
        
        # Then insert the new details
        result = db.customer_temporary_details.insert_one(customer_data)
        
        if not result.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to save customer details")
            
        return {
            "status": "success", 
            "message": "Customer details saved",
            "detail_id": str(result.inserted_id)
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[ERROR] Failed to save customer details: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/get-customer-details/{order_id}")
async def get_customer_details(
    order_id: str,
    token: str = Query(...),
    db: Database = Depends(get_db)
):
    """Get customer details for an order from temporary storage"""
    try:
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        
        # Get the customer details
        details = db.customer_temporary_details.find_one({"order_id": order_id})
        
        if not details:
            return {
                "name": "",
                "phone": "",
                "email": None,
                "address": None,
                "table_number": None,
                "waiter_no": None,
                "order_id": order_id
            }
        
        # Convert ObjectId to string
        details["_id"] = str(details["_id"])
        
        # Return the details
        return details
        
    except Exception as e:
        print(f"[ERROR] Failed to get customer details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve customer details")

@router.delete("/delete-customer-details/{order_id}")
async def delete_customer_details(
    order_id: str,
    token: str = Query(...),
    db: Database = Depends(get_db)
):
    """Delete temporary customer details after bill generation"""
    try:
        # Verify user is authenticated
        get_current_user(db, token)
        
        # Delete the customer details
        result = db.customer_temporary_details.delete_many({"order_id": order_id})
        
        return {
            "status": "success",
            "deleted_count": result.deleted_count
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to delete customer details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete customer details")