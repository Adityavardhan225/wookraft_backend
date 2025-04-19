from fastapi import APIRouter, Depends, HTTPException, Request, Form
from pymongo.database import Database
from configurations.config import get_db, settings
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import json
from bson import ObjectId
from datetime import datetime, timedelta
from fastapi.responses import HTMLResponse, JSONResponse
import logging
from routes.bill_format.Bill_storage import BillStorage
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

router = APIRouter()

# Models for validation
class FeedbackData(BaseModel):
    order_id: str
    bill_id: str
    customer_email: str
    overall_rating: int
    item_ratings: Dict[str, int] = {}
    comments: str = ""

def get_feedback_email_template(customer_name, restaurant_name, order_id, bill_id, email, items):
    """
    Returns a simplified HTML template for feedback email
    
    Args:
        customer_name: Customer name for personalization
        restaurant_name: Restaurant name
        order_id: Order ID
        bill_id: Bill ID
        email: Customer email
        items: List of order items
    
    Returns:
        str: HTML email template with overall rating options
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
                color: white;
                padding: 25px 20px;
                text-align: center;
            }}
            .header h2 {{
                margin: 0 0 5px;
                font-weight: 600;
                font-size: 24px;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
            }}
            .header p {{
                margin: 0;
                opacity: 0.9;
                font-size: 14px;
            }}
            .content {{
                padding: 25px;
                background-color: #ffffff;
            }}
            .feedback-section {{
                margin: 20px 0;
                padding-bottom: 20px;
                border-bottom: 1px solid #edf2f7;
            }}
            .feedback-section:last-child {{
                border-bottom: none;
                padding-bottom: 0;
            }}
            .feedback-section h3 {{
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 18px;
                color: #4a5568;
                font-weight: 500;
            }}
            .emoji-rating {{
                display: table;
                width: 100%;
                margin: 15px 0;
                border-collapse: collapse;
            }}
            .emoji-btn {{
                display: block;
                width: 100%;
                padding: 12px 5px;
                text-decoration: none;
                background-color: #fff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin: 0 2px;
            }}
            .emoji {{
                font-size: 24px;
                display: block;
                margin-bottom: 5px;
                line-height: 1.2;
            }}
            .rating-value {{
                font-size: 12px;
                color: #4a5568;
                display: block;
            }}
            .detailed-btn {{
                display: block;
                width: 80%;
                margin: 20px auto;
                background-color: #4299e1;
                color: white;
                padding: 15px 0;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                text-align: center;
                font-size: 16px;
                transition: all 0.2s;
            }}
            .detailed-btn:hover {{
                background-color: #3182ce;
            }}
            .footer {{
                font-size: 12px;
                color: #777;
                text-align: center;
                margin-top: 20px;
                padding: 15px;
                background-color: #f9fafb;
                border-top: 1px solid #edf2f7;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{restaurant_name}</h2>
                <p>Order #{order_id}</p>
            </div>
            <div class="content">
                <p>Hello {customer_name},</p>
                
                <p>Thank you for your recent order! We hope you enjoyed your experience with us.</p>
                
                <p>We value your feedback and would love to hear what you thought about your meal.</p>
                
                <div class="feedback-section">
                    <h3>How was your overall experience?</h3>
                    <table class="emoji-rating" cellspacing="0" cellpadding="0" border="0" width="100%">
                        <tr>
                            <td align="center" width="20%">
                                <a href="{settings.BASE_URL}/feedback/quick-submit?order_id={order_id}&bill_id={bill_id}&rating=1&email={email}" class="emoji-btn" target="_blank">
                                    <span class="emoji">😞</span>
                                    <span class="rating-value">Poor</span>
                                </a>
                            </td>
                            <td align="center" width="20%">
                                <a href="{settings.BASE_URL}/feedback/quick-submit?order_id={order_id}&bill_id={bill_id}&rating=2&email={email}" class="emoji-btn" target="_blank">
                                    <span class="emoji">😐</span>
                                    <span class="rating-value">Fair</span>
                                </a>
                            </td>
                            <td align="center" width="20%">
                                <a href="{settings.BASE_URL}/feedback/quick-submit?order_id={order_id}&bill_id={bill_id}&rating=3&email={email}" class="emoji-btn" target="_blank">
                                    <span class="emoji">🙂</span>
                                    <span class="rating-value">Good</span>
                                </a>
                            </td>
                            <td align="center" width="20%">
                                <a href="{settings.BASE_URL}/feedback/quick-submit?order_id={order_id}&bill_id={bill_id}&rating=4&email={email}" class="emoji-btn" target="_blank">
                                    <span class="emoji">😊</span>
                                    <span class="rating-value">Very Good</span>
                                </a>
                            </td>
                            <td align="center" width="20%">
                                <a href="{settings.BASE_URL}/feedback/quick-submit?order_id={order_id}&bill_id={bill_id}&rating=5&email={email}" class="emoji-btn" target="_blank">
                                    <span class="emoji">😃</span>
                                    <span class="rating-value">Excellent</span>
                                </a>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div class="feedback-section">
                    <a href="{settings.BASE_URL}/feedback/detailed/{order_id}/{bill_id}/{email}" class="detailed-btn" target="_blank">Rate Individual Items</a>
                </div>
                
                <p>Thank you for choosing {restaurant_name}. We look forward to serving you again soon!</p>
            </div>
            <div class="footer">
                <p>If you have any questions, please contact our customer support.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_detailed_feedback_form_template(order_id, bill_id, email, items_html, restaurant_name):
    """
    Returns the HTML template for the detailed feedback form with individual item ratings
    
    Args:
        order_id: Order ID
        bill_id: Bill ID
        email: Customer email
        items_html: Pre-generated HTML for the items section
        restaurant_name: Restaurant name
    
    Returns:
        str: Enhanced HTML detailed feedback form template
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Order Feedback | {restaurant_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                padding: 20px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 0 0 8px 8px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }}
            textarea {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-sizing: border-box;
                resize: vertical;
                min-height: 80px;
                font-family: inherit;
            }}
            .item {{
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                background-color: #f9f9fb;
            }}
            .item-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .quantity-badge {{
                background-color: #e2e8f0;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
                color: #4a5568;
            }}
            .rating-container {{
                display: flex;
                justify-content: center;
                margin: 10px 0;
            }}
            .star {{
                font-size: 24px;
                cursor: pointer;
                color: #ddd;
                margin: 0 5px;
            }}
            .star.selected {{
                color: gold;
            }}
            .issues-container {{
                margin-top: 15px;
            }}
            .issues-title {{
                font-size: 14px;
                color: #4a5568;
                margin-bottom: 8px;
            }}
            .issues-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 15px;
            }}
            .issue-chip {{
                display: flex;
                align-items: center;
                gap: 5px;
                padding: 8px 12px;
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 20px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }}
            .issue-chip:hover {{
                background-color: #f7fafc;
            }}
            .issue-chip.selected {{
                background-color: #ebf8ff;
                border-color: #63b3ed;
            }}
            .issue-emoji {{
                font-size: 16px;
            }}
            .comment-box {{
                display: none;
                margin-top: 10px;
            }}
            .comment-box.visible {{
                display: block;
            }}
            .button {{
                display: inline-block;
                background-color: #4299e1;
                color: white;
                padding: 12px 20px;
                text-decoration: none;
                border-radius: 8px;
                margin: 5px;
                font-weight: bold;
                border: none;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
                transition: background-color 0.2s;
            }}
            .button:hover {{
                background-color: #3182ce;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Order Feedback</h2>
                <p>Order #: {order_id}</p>
            </div>
            <div class="content">
                <form action="/feedback/submit-detailed" method="post">
                    <input type="hidden" name="order_id" value="{order_id}">
                    <input type="hidden" name="bill_id" value="{bill_id}">
                    <input type="hidden" name="email" value="{email}">
                    
                    <div class="form-group">
                        <label>How was your overall experience?</label>
                        <div class="rating-container">
                            <span class="star" onclick="setOverallRating(1)">★</span>
                            <span class="star" onclick="setOverallRating(2)">★</span>
                            <span class="star" onclick="setOverallRating(3)">★</span>
                            <span class="star" onclick="setOverallRating(4)">★</span>
                            <span class="star" onclick="setOverallRating(5)">★</span>
                        </div>
                        <input type="hidden" name="overall_rating" id="overall_rating" value="0">
                    </div>
                    
                    <div class="form-group">
                        <label>General Comments:</label>
                        <textarea name="comments" placeholder="Tell us about your overall experience..."></textarea>
                    </div>
                    
                    <h3>Rate Your Items</h3>
                    
                    {items_html}
                    
                    <button type="submit" class="button">Submit Feedback</button>
                </form>
            </div>
        </div>
        
        <script>
            function setOverallRating(rating) {{
                document.getElementById('overall_rating').value = rating;
                const stars = document.querySelectorAll('.form-group:first-of-type .star');
                stars.forEach((star, index) => {{
                    if (index < rating) {{
                        star.classList.add('selected');
                    }} else {{
                        star.classList.remove('selected');
                    }}
                }});
            }}
            
            function setItemRating(itemId, rating) {{
                const fieldId = 'item_rating_' + itemId;
                document.getElementById(fieldId).value = rating;
                const itemDiv = document.getElementById('item_' + itemId);
                const stars = itemDiv.querySelectorAll('.star');
                stars.forEach((star, index) => {{
                    if (index < rating) {{
                        star.classList.add('selected');
                    }} else {{
                        star.classList.remove('selected');
                    }}
                }});
            }}
            
            function toggleIssue(itemId, issueId) {{
                const issueChip = document.getElementById('issue_' + itemId + '_' + issueId);
                issueChip.classList.toggle('selected');
                
                // Get the comment box for this item
                const commentBox = document.getElementById('comment_box_' + itemId);
                
                // Check if any issues are selected for this item
                const itemIssues = document.querySelectorAll('#item_' + itemId + ' .issue-chip.selected');
                if (itemIssues.length > 0) {{
                    commentBox.classList.add('visible');
                }} else {{
                    commentBox.classList.remove('visible');
                }}
                
                // Update hidden field with selected issues
                const selectedIssues = Array.from(itemIssues).map(chip => chip.dataset.issue);
                document.getElementById('item_issues_' + itemId).value = selectedIssues.join(',');
            }}
        </script>
    </body>
    </html>
    """

@router.get("/feedback/detailed/{order_id}/{bill_id}/{email}", response_class=HTMLResponse)
async def serve_detailed_feedback_form(
    order_id: str,
    bill_id: str,
    email: str,
    db: Database = Depends(get_db)
):
    """Serve a detailed feedback form"""
    try:
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return HTMLResponse(get_error_template("Bill not found"))
            
        # Get items from the bill
        all_items = bill.get("items", [])
        restaurant_name = "WooPOS Restaurant"  # Define this variable
        
        # FIXED ISSUE 2: Deduplicate items by name
        unique_items = {}
        for item in all_items:
            item_name = item.get('name', '')
            if item_name:
                if item_name not in unique_items:
                    unique_items[item_name] = item
                else:
                    # If duplicate, update quantity
                    unique_items[item_name]['quantity'] = unique_items[item_name].get('quantity', 1) + item.get('quantity', 1)
        
        print(f"[DEBUG] Found {len(all_items)} total items, {len(unique_items)} unique items")
        
        # Build the items HTML dynamically for unique items only
        items_html = ""
        for item_name, item in unique_items.items():
            # FIXED ISSUE 1: Consistent item ID normalization
            # Create a clean ID from item name (remove spaces and special characters)
            item_id = ''.join(c for c in item_name if c.isalnum() or c == '_').lower()
            item_quantity = item.get('quantity', 1)
            
            print(f"[DEBUG] Adding item to form: {item_name} (ID: {item_id})")
            
            items_html += f"""
            <div id="item_{item_id}" class="item">
                <div class="item-header">
                    <h4 style="margin: 0; font-weight: 500;">{item_name}</h4>
                    <span class="quantity-badge">Qty: {item_quantity}</span>
                </div>
                
                <div class="rating-container">
                    <span class="star" onclick="setItemRating('{item_id}', 1)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 2)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 3)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 4)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 5)">★</span>
                </div>
                <input type="hidden" name="item_rating_{item_id}" id="item_rating_{item_id}" value="0">
                
                <div class="issues-container">
                    <div class="issues-title">Any issues with this item?</div>
                    <div class="issues-grid">
                        <div id="issue_{item_id}_cold" class="issue-chip" onclick="toggleIssue('{item_id}', 'cold')" data-issue="cold">
                            <span class="issue-emoji">❄️</span>
                            <span>Cold</span>
                        </div>
                        <div id="issue_{item_id}_small" class="issue-chip" onclick="toggleIssue('{item_id}', 'small')" data-issue="small">
                            <span class="issue-emoji">📏</span>
                            <span>Small portion</span>
                        </div>
                        <div id="issue_{item_id}_taste" class="issue-chip" onclick="toggleIssue('{item_id}', 'taste')" data-issue="taste">
                            <span class="issue-emoji">👅</span>
                            <span>Taste</span>
                        </div>
                        <div id="issue_{item_id}_quality" class="issue-chip" onclick="toggleIssue('{item_id}', 'quality')" data-issue="quality">
                            <span class="issue-emoji">👎</span>
                            <span>Quality</span>
                        </div>
                        <div id="issue_{item_id}_spicy" class="issue-chip" onclick="toggleIssue('{item_id}', 'spicy')" data-issue="spicy">
                            <span class="issue-emoji">🌶️</span>
                            <span>Too spicy</span>
                        </div>
                    </div>
                    <input type="hidden" name="item_issues_{item_id}" id="item_issues_{item_id}" value="">
                </div>
                
                <div id="comment_box_{item_id}" class="comment-box">
                    <textarea name="item_comment_{item_id}" placeholder="Tell us more about the issues with {item_name}..."></textarea>
                </div>
            </div>
            """
        
        # Now return the complete template with unique items only
        return HTMLResponse(
            get_detailed_feedback_form_template(
                order_id=order_id,
                bill_id=bill_id,
                email=email,
                items_html=items_html,
                restaurant_name=restaurant_name
            )
        )
        
    except Exception as e:
        print(f"[ERROR] Error serving detailed form: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return HTMLResponse(get_error_template())
    

    
def get_thank_you_template(item=None, rating=None):
    """
    Returns the HTML template for the thank you page
    
    Args:
        item: Optional item name that was rated
        rating: Optional rating value
    
    Returns:
        str: HTML thank you template
    """
    stars_html = ""
    if rating:
        stars_html = f"""<div class="stars">{"★" * rating}{"☆" * (5 - rating)}</div>"""
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Thank You for Your Feedback</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                text-align: center;
                padding: 40px 20px;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .thank-you {{
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                margin: 0 auto;
                padding: 30px 20px;
            }}
            .success-icon {{
                width: 60px;
                height: 60px;
                background-color: #48bb78;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
                margin: 0 auto 20px;
            }}
            .stars {{
                color: gold;
                font-size: 24px;
                margin: 10px 0;
            }}
        </style>
    </head>
    <body>
        <div class="thank-you">
            <div class="success-icon">✓</div>
            <h2>Thank You!</h2>
            <p>Your {item or 'order'} feedback has been submitted successfully.</p>
            {stars_html}
            <p>We appreciate your time and value your opinion!</p>
        </div>
    </body>
    </html>
    """






def get_error_template(message="Something went wrong"):
    """
    Returns the HTML template for error messages
    
    Args:
        message: Error message to display
    
    Returns:
        str: HTML error template
    """
    return f"""
    <html>
    <head>
        <title>Error</title>
        <style>
            body {{
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                text-align: center;
                padding: 40px 20px;
                background-color: #f5f5f5;
                line-height: 1.6;
            }}
            .error-container {{
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
                max-width: 500px;
                margin: 0 auto;
                padding: 30px 20px;
            }}
            .error-icon {{
                width: 60px;
                height: 60px;
                background-color: #e53e3e;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 32px;
                margin: 0 auto 20px;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-icon">✕</div>
            <h1>{message}</h1>
            <p>We encountered an error processing your request.</p>
        </div>
    </body>
    </html>
    """



# Add this new helper function after other helper functions (around line 600)
def update_item_analytics_with_feedback(db, bill_id, feedback_data):
    """
    Update item analytics collection with feedback data using existing fields
    
    Args:
        db: Database connection
        bill_id: Bill ID
        feedback_data: Formatted feedback data
    """
    try:
        print(f"[DEBUG] Starting update_item_analytics_with_feedback for bill: {bill_id}")
        print(f"[DEBUG] Feedback data items: {feedback_data.get('items', {}).keys()}")
        
        # Get bill to access item details
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill or "items" not in bill:
            print(f"[ERROR] Bill {bill_id} not found or has no items")
            return
        
        print(f"[DEBUG] Found bill with {len(bill['items'])} items")
        
        # Create a map of normalized item names to actual bill item names
        # This helps handle inconsistencies like "paneer tikka" vs "paneertikka"
        bill_item_map = {}
        for bill_item in bill["items"]:
            item_name = bill_item.get("name", "")
            normalized_name = item_name.replace(" ", "").lower()
            bill_item_map[normalized_name] = item_name
        
        print(f"[DEBUG] Bill item map: {bill_item_map}")
        
        # Process each item in the feedback data
        for feedback_item_name, item_feedback in feedback_data.get("items", {}).items():
            print(f"[DEBUG] Processing feedback item: {feedback_item_name}")
            
            # Normalize feedback item name for matching
            normalized_feedback_name = feedback_item_name.replace(" ", "").lower()
            
            # Try to find the matching bill item
            actual_item_name = None
            if normalized_feedback_name in bill_item_map:
                actual_item_name = bill_item_map[normalized_feedback_name]
                print(f"[DEBUG] Matched to bill item: {actual_item_name}")
            else:
                # Try a more flexible match if exact match fails
                for bill_norm_name, bill_name in bill_item_map.items():
                    if normalized_feedback_name in bill_norm_name or bill_norm_name in normalized_feedback_name:
                        actual_item_name = bill_name
                        print(f"[DEBUG] Partial match to bill item: {actual_item_name}")
                        break
            
            # Skip if no matching item found
            if not actual_item_name:
                print(f"[DEBUG] No matching bill item found for: {feedback_item_name}")
                continue
                
            # Get item feedback data
            rating = item_feedback.get("rating", 0)
            issues = item_feedback.get("issues", [])
            print(f"[DEBUG] Found feedback for {actual_item_name}: rating={rating}, issues={issues}")
            
            # Process items even with zero ratings if they have issues or comments
            # This addresses the zero rating issue
            has_issues_or_comments = len(issues) > 0 or (item_feedback.get("comments", "") != "")
            if rating <= 0 and not has_issues_or_comments:
                print(f"[DEBUG] Skipping {actual_item_name} - no valid rating or feedback")
                continue
                
            # Get item_id from menu collection or generate if not found
            menu_item = db.menu.find_one({"name": actual_item_name})
            item_id = str(menu_item.get("_id")) if menu_item else f"item-{actual_item_name.lower().replace(' ', '-')}"
            print(f"[DEBUG] Using item_id: {item_id} for {actual_item_name}")
            
            # Only update rating metrics if rating > 0
            if rating > 0:
                print(f"[DEBUG] Updating rating metrics for {actual_item_name}")
                db.item_analytics.update_one(
                    {"_id": item_id},
                    {
                        "$inc": {
                            "rating_count": 1,
                            "rating_sum": rating
                        },
                        "$set": {
                            "last_feedback_date": datetime.now()
                        }
                    },
                    upsert=True
                )
                print(f"[DEBUG] Updated core ratings for {actual_item_name}")
                
                # Update rating distribution - use existing structure
                print(f"[DEBUG] Updating rating distribution for {actual_item_name} with rating {rating}")
                result1 = db.item_analytics.update_one(
                    {"_id": item_id, "rating_distribution.rating": rating},
                    {"$inc": {"rating_distribution.$.count": 1}}
                )
                print(f"[DEBUG] Update distribution match result: {result1.matched_count}")
                
                # If rating doesn't exist in distribution, add it
                if result1.matched_count == 0:
                    print(f"[DEBUG] Rating {rating} not found in distribution, adding it")
                    result2 = db.item_analytics.update_one(
                        {"_id": item_id, "rating_distribution.rating": {"$ne": rating}},
                        {"$push": {"rating_distribution": {"rating": rating, "count": 1}}}
                    )
                    print(f"[DEBUG] Added new rating: {result2.modified_count}")
            
            # Update issues frequency in common_issues field (always process issues if present)
            for issue in issues:
                if not issue:  # Skip empty issues
                    continue
                print(f"[DEBUG] Processing issue: '{issue}' for {actual_item_name}")
                    
                # Update existing issue
                result3 = db.item_analytics.update_one(
                    {"_id": item_id, "common_issues.issue": issue},
                    {"$inc": {"common_issues.$.count": 1}}
                )
                print(f"[DEBUG] Update issue match result: {result3.matched_count}")
                
                # If issue doesn't exist, add it
                if result3.matched_count == 0:
                    print(f"[DEBUG] Issue '{issue}' not found, adding it")
                    result4 = db.item_analytics.update_one(
                        {"_id": item_id, "common_issues.issue": {"$ne": issue}},
                        {"$push": {"common_issues": {"issue": issue, "count": 1}}}
                    )
                    print(f"[DEBUG] Added new issue: {result4.modified_count}")
            
            # Recalculate average rating
            if rating > 0:
                print(f"[DEBUG] Recalculating average rating for {actual_item_name}")
                analytics = db.item_analytics.find_one({"_id": item_id})
                if analytics and "rating_sum" in analytics and "rating_count" in analytics:
                    rating_sum = analytics["rating_sum"]
                    rating_count = analytics["rating_count"]
                    print(f"[DEBUG] Found rating_sum={rating_sum}, rating_count={rating_count}")
                    if rating_count > 0:
                        avg_rating = round(rating_sum / rating_count, 1)
                        db.item_analytics.update_one(
                            {"_id": item_id},
                            {"$set": {"avg_rating": avg_rating}}
                        )
                        print(f"[DEBUG] Set avg_rating={avg_rating} for {actual_item_name}")
            
            print(f"[DEBUG] Completed feedback processing for {actual_item_name}")
                    
    except Exception as e:
        print(f"[ERROR] Error updating item analytics with feedback: {str(e)}")
        import traceback
        print(traceback.format_exc())




def send_feedback_email_with_form(email: str, customer_name: str, order_id: str, bill_id: str, items: List[Dict], restaurant_name: str = None):
    """
    Sends an email with embedded feedback form to the customer
    
    Args:
        email: Customer's email address
        customer_name: Customer's name for personalization
        order_id: Order ID for reference
        bill_id: ID of the bill in the database
        items: List of order items
        restaurant_name: Name of the restaurant
    """
    if not restaurant_name:
        restaurant_name = "WooPOS Restaurant"
        
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = email
    msg['Subject'] = f"We'd love your feedback on your order from {restaurant_name}"
    
    # Use the template function
    html = get_feedback_email_template(
        customer_name=customer_name,
        restaurant_name=restaurant_name,
        order_id=order_id,
        bill_id=bill_id,
        email=email,
        items=items
    )
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.EMAIL_SENDER, email, text)
        server.quit()
        logging.info(f"Feedback email sent successfully to {email} for order {order_id}")
        return True
    except Exception as e:
        logging.error(f"Error sending feedback email: {e}")
        return False

@router.post("/feedback/send")
async def send_feedback_email(
    bill_id: str,
    order_id: str,
    customer_email: str,
    customer_name: str = None,
    restaurant_name: str = None,
    db: Database = Depends(get_db)
):
    """Send a feedback email with embedded form"""
    try:
        # Check if bill exists
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
            
        # Get items from bill
        items = bill.get("items", [])
            
        # Send email with form
        email_sent = send_feedback_email_with_form(
            email=customer_email,
            customer_name=customer_name or "Valued Customer",
            order_id=order_id,
            bill_id=bill_id,
            items=items,
            restaurant_name=restaurant_name
        )
        
        return {"status": "success", "email_sent": email_sent}
        
    except Exception as e:
        logging.error(f"Error sending feedback email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Replace the quick_submit_feedback function (around line 750)

# Replace the quick_submit_feedback function

@router.get("/feedback/quick-submit")
async def quick_submit_feedback(
    order_id: str,
    bill_id: str,
    rating: int,
    email: str,
    item: str = None,
    issue: str = None,
    db: Database = Depends(get_db)
):
    """Handle quick feedback submission from email link clicks"""
    try:
        # Validate bill exists
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return HTMLResponse(get_error_template("Bill not found"))
            
        # Format feedback data using the existing structure
        if item:
            # This is an item rating
            item_feedbacks = {
                item: {
                    "rating": rating,
                    "issues": [issue] if issue else [],
                    "comments": ""
                }
            }
            
            formatted_feedback = {
                "items": item_feedbacks,
                "submitted_at": datetime.now(),
                "email": email
            }
        else:
            # This is an overall rating
            formatted_feedback = {
                "overall_rating": rating,
                "comments": "",
                "items": {},
                "submitted_at": datetime.now(),
                "email": email
            }
        
        # Get bill storage instance
        bill_storage = BillStorage(db)
        
        # Update feedback using BillStorage
        bill_storage.update_customer_feedback(bill_id, formatted_feedback)
        print('debug formatted_feedback',formatted_feedback)
        # Update item analytics for item-specific feedback
        if item:
            update_item_analytics_with_feedback(db, bill_id, formatted_feedback)
        
        # Return thank you page using template
        return HTMLResponse(get_thank_you_template(item=item, rating=rating))
        
    except Exception as e:
        logging.error(f"Error in quick submit: {str(e)}")
        return HTMLResponse(get_error_template())




@router.get("/feedback/detailed/{order_id}/{bill_id}/{email}", response_class=HTMLResponse)
async def serve_detailed_feedback_form(
    order_id: str,
    bill_id: str,
    email: str,
    db: Database = Depends(get_db)
):
    """Serve a detailed feedback form"""
    try:
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return HTMLResponse(get_error_template("Bill not found"))
            
        # Get items from the bill
        items = bill.get("items", [])
        restaurant_name = "WooPOS Restaurant"  # Define this variable
        
        # Build the items HTML separately to avoid complex nested f-strings
        items_html = ""
        for item in items:
            item_name = item.get('name', '')
            item_quantity = item.get('quantity', 1)
            item_id = item_name.replace(' ', '_')
            
            items_html += f"""
            <div class="item">
                <h4>{item_name} (Qty: {item_quantity})</h4>
                <div class="rating-container">
                    <span class="star" onclick="setItemRating('{item_id}', 1)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 2)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 3)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 4)">★</span>
                    <span class="star" onclick="setItemRating('{item_id}', 5)">★</span>
                </div>
                <input type="hidden" name="item_rating_{item_id}" id="item_rating_{item_id}" value="0">
                <textarea name="item_comment_{item_id}" placeholder="Comments about {item_name}..."></textarea>
            </div>
            """
        
        # Now return the full template using template function
        return HTMLResponse(
            get_detailed_feedback_form_template(
                order_id=order_id,
                bill_id=bill_id,
                email=email,
                items_html=items_html,
                restaurant_name=restaurant_name
            )
        )
        
    except Exception as e:
        logging.error(f"Error serving detailed form: {str(e)}")
        return HTMLResponse(get_error_template())

# Replace the submit_detailed_feedback function (around line 919)

# Replace the submit_detailed_feedback function

@router.post("/feedback/submit-detailed")
async def submit_detailed_feedback(
    request: Request,
    db: Database = Depends(get_db)
):
    """Process submitted detailed feedback form"""
    try:
        form_data = await request.form()
        bill_id = form_data.get('bill_id')
        order_id = form_data.get('order_id')
        email = form_data.get('email')
        overall_rating = int(form_data.get('overall_rating', 0))
        comments = form_data.get('comments', '')
        
        # Get bill
        bill = db.bills.find_one({"_id": ObjectId(bill_id)})
        if not bill:
            return HTMLResponse(get_error_template("Bill not found"))
        
        # Process item feedback - collect ratings, issues and comments
        item_feedbacks = {}
        
        # Go through form data to extract all item feedback
        for key, value in form_data.items():
            if key.startswith('item_rating_'):
                item_id = key[len('item_rating_'):]
                item_name = item_id.replace('_', ' ')
                
                # Initialize item feedback structure if not exists
                if item_name not in item_feedbacks:
                    item_feedbacks[item_name] = {
                        "rating": 0,
                        "issues": [],
                        "comments": ""
                    }
                
                try:
                    rating = int(value)
                    if rating > 0:
                        item_feedbacks[item_name]["rating"] = rating
                except ValueError:
                    pass
                    
            elif key.startswith('item_issues_'):
                item_id = key[len('item_issues_'):]
                item_name = item_id.replace('_', ' ')
                
                # Initialize item feedback structure if not exists
                if item_name not in item_feedbacks:
                    item_feedbacks[item_name] = {
                        "rating": 0,
                        "issues": [],
                        "comments": ""
                    }
                
                # Process comma-separated issues
                if value:
                    item_feedbacks[item_name]["issues"] = value.split(',')
                    
            elif key.startswith('item_comment_'):
                item_id = key[len('item_comment_'):]
                item_name = item_id.replace('_', ' ')
                
                # Initialize item feedback structure if not exists
                if item_name not in item_feedbacks:
                    item_feedbacks[item_name] = {
                        "rating": 0,
                        "issues": [],
                        "comments": ""
                    }
                
                if value:
                    item_feedbacks[item_name]["comments"] = value
        
        # Format complete feedback data
        formatted_feedback = {
            "overall_rating": overall_rating,
            "comments": comments,
            "items": item_feedbacks,
            "submitted_at": datetime.now(),
            "email": email
        }
        
        # Get bill storage instance
        bill_storage = BillStorage(db)
        
        # Update bill and customer feedback history
        bill_storage.update_customer_feedback(bill_id, formatted_feedback)
        print('debug formatted_feedback',formatted_feedback)
        # Update item analytics with feedback data 
        update_item_analytics_with_feedback(db, bill_id, formatted_feedback)
        
        # Return thank you page
        return HTMLResponse(get_thank_you_template())
        
    except Exception as e:
        logging.error(f"Error submitting detailed feedback: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return HTMLResponse(get_error_template())
    
    