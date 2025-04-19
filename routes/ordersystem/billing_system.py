
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pymongo.database import Database
from bson import ObjectId
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import traceback
from configurations.config import get_db
from routes.security.protected_authorise import get_current_user
# from routes.ordersystem.order_service import OrderService



router = APIRouter()


def calculate_bill_discounts(order_id: str, total_price: float, discounted_price: Optional[float], coupon_ids: List[str], db: Database) -> Dict:
    """
    Calculate bill discounts for an order based on coupon IDs.
    
    Args:
        order_id: The order identifier
        total_price: The original total price
        discounted_price: The price after item discounts (if any)
        coupon_ids: List of coupon IDs to apply
        db: Database connection
        
    Returns:
        Dict containing discount information
    """
    # Determine base price - use discounted_price if available, otherwise use total_price
    base_price = discounted_price if discounted_price is not None else total_price
    
    print(f"[BILL-DISCOUNT] Order {order_id}: Original total={total_price}, Discounted total={discounted_price}, Using base={base_price}")
    
    # If no coupons provided, return early
    if not coupon_ids:
        print(f"[BILL-DISCOUNT] Order {order_id}: No coupon IDs provided, skipping discount calculation")
        return {
            "bill_discount_amount": 0,
            "applied_bill_discounts": [],
            "final_price_after_discount": base_price
        }
    
    print(f"[BILL-DISCOUNT] Order {order_id}: Processing {len(coupon_ids)} coupons")
    discount_amount = 0
    applied_discounts = []
    
    # Process each coupon
    for coupon_id in coupon_ids:
        print(f"[BILL-DISCOUNT] Order {order_id}: Processing coupon {coupon_id}")
        # Try to find coupon by _id or coupon_id
        coupon = db.coupons.find_one({
            "$or": [
                {"_id": ObjectId(coupon_id) if len(coupon_id) == 24 else coupon_id},
                {"coupon_id": coupon_id}
            ],
            "discount_coupon_type": "BILL"
        })
        
        if not coupon:
            print(f"[BILL-DISCOUNT] Order {order_id}: Coupon {coupon_id} not found")
            continue  # Skip if not found
            
        # Check date/day/time validity
        if not is_coupon_valid_now(coupon):
            print(f"[BILL-DISCOUNT] Order {order_id}: Coupon {coupon_id} not valid at current time")
            continue  # Skip if not valid now
            
        # Check minimum bill amount
        min_bill = coupon.get("min_bill_amount", 0) or 0  # Handle None as 0
        if base_price < min_bill:
            print(f"[BILL-DISCOUNT] Order {order_id}: Base price {base_price} below minimum {min_bill}")
            continue  # Skip if below minimum amount
        
        # Apply percentage discount
        if coupon.get("discount_percentage") is not None:
            percentage = coupon["discount_percentage"]
            if percentage is None or not isinstance(percentage, (int, float)):
                print(f"[BILL-DISCOUNT] Order {order_id}: Invalid percentage value {percentage}")
                continue  # Skip invalid values
                
            print(f"[BILL-DISCOUNT] Order {order_id}: Calculating {percentage}% discount on {base_price}")
            curr_discount = base_price * (percentage / 100)
            
            # Apply max cap if present
            max_value = coupon.get("discount_max_value")
            if max_value is not None and max_value > 0:
                print(f"[BILL-DISCOUNT] Order {order_id}: Applying max cap of {max_value}")
                orig_discount = curr_discount
                curr_discount = min(curr_discount, max_value)
                if curr_discount < orig_discount:
                    print(f"[BILL-DISCOUNT] Order {order_id}: Discount reduced from {orig_discount} to {curr_discount}")
                
            discount_amount += curr_discount
            applied_discounts.append({
                "coupon_id": coupon.get("coupon_id", str(coupon["_id"])),
                "name": coupon.get("discount_coupon_name", "Percentage Discount"),
                "type": "PERCENTAGE",
                "value": percentage,
                "amount": round(curr_discount, 2)
            })
            print(f"[BILL-DISCOUNT] Order {order_id}: Applied {percentage}% discount = {round(curr_discount, 2)}")
            
        # Apply fixed amount discount    
        elif coupon.get("discount_value") is not None:
            fixed_value = coupon["discount_value"]
            if fixed_value is None or not isinstance(fixed_value, (int, float)):
                print(f"[BILL-DISCOUNT] Order {order_id}: Invalid fixed discount value {fixed_value}")
                continue  # Skip invalid values
                
            curr_discount = fixed_value
            discount_amount += curr_discount
            applied_discounts.append({
                "coupon_id": coupon.get("coupon_id", str(coupon["_id"])),
                "name": coupon.get("discount_coupon_name", "Amount Discount"),
                "type": "AMOUNT",
                "value": fixed_value,
                "amount": round(curr_discount, 2)
            })
            print(f"[BILL-DISCOUNT] Order {order_id}: Applied fixed discount = {round(curr_discount, 2)}")
    
    # Ensure discount doesn't exceed the price
    if discount_amount > base_price:
        print(f"[BILL-DISCOUNT] Order {order_id}: Discount {discount_amount} exceeds base price {base_price}, capping")
        discount_amount = base_price
    
    final_price = base_price - discount_amount
    
    print(f"[BILL-DISCOUNT] Order {order_id}: Final calculation - Base: {base_price}, Discount: {round(discount_amount, 2)}, Final: {round(final_price, 2)}")
    
    return {
        "bill_discount_amount": round(discount_amount, 2),
        "applied_bill_discounts": applied_discounts,
        "final_price_after_discount": round(final_price, 2)
    }
    

@router.get("/order_details")
async def get_order_details(
    order_id: Optional[str] = Query(None),
    table_number: Optional[int] = Query(None),
    token: str = Query(None),
    db: Database = Depends(get_db)
):
    try:
        print("Verifying user authentication")
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        print(f"Authenticated user: {current_user}")

        # Check if at least one parameter is provided
        if not order_id and table_number is None:
            raise HTTPException(
                status_code=400, 
                detail="Either order_id or table_number must be provided"
            )
        
        # Query to find the order
        query = {"owner_id": current_user.owner_id}
        if order_id:
            query["_id"] = ObjectId(order_id)
        elif table_number is not None:
            query["table_number"] = table_number
            query["status"] = "active"  # For table_number, get the active order
        
        print(f"Querying database with: {query}")
        # Find the order
        order_data = db.orders.find_one(query)
        if not order_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Order not found for {'order_id: ' + order_id if order_id else 'table: ' + str(table_number)}"
            )
        
        print(f"Order data found: {order_data}")
        # Extract basic order information
        order_result = {
            "order_id": str(order_data["_id"]),
            "table_number": order_data["table_number"],
            "employee_id": order_data["employee_id"],
            "status": order_data["status"],
            "timestamp": order_data["timestamp"],
            "items": [],
            "total_price": 0,
            "total_discounted_price": 0,
            "overall_customization": order_data.get("overall_customization", "")
        }
        
        # Process each item in the order
        for item in order_data.get("items", []):
            item_details = {
                "name": item["name"],
                "quantity": item["quantity"],
                "food_type": item.get("food_type", ""),
                "food_category": item.get("food_category", ""),
                "prepared": item.get("prepared_items", False),
                "base_price": item["price"] / item["quantity"] if item["quantity"] > 0 else 0,
                "total_price": item["price"],
                "total_discounted_price": item.get("discounted_price", item["price"]),
                "customization_details": {
                    "text": "",
                    "size": None,
                    "addons": []
                }
            }
            
            # Process customization information
            if "customization" in item:
                if isinstance(item["customization"], dict):
                    # New consolidated format
                    item_details["customization_details"]["text"] = item["customization"].get("text", "")
                    
                    # Process size information
                    if item["customization"].get("size"):
                        size_info = item["customization"]["size"]
                        item_details["customization_details"]["size"] = {
                            "name": size_info.get("size_name", ""),
                            "price": size_info.get("price", 0)
                        }
                    
                    # Process addons
                    addons = []
                    addon_total_price = 0
                    
                    for addon in item["customization"].get("addons", []):
                        addon_name = addon.get("addon_name", "")
                        addon_qty = addon.get("quantity", 1)
                        addon_price = addon.get("price", 0)
                        addon_total = addon_price * addon_qty
                        addon_total_price += addon_total
                        
                        addons.append({
                            "name": addon_name,
                            "quantity": addon_qty,
                            "unit_price": addon_price,
                            "total_price": addon_total
                        })
                    
                    item_details["customization_details"]["addons"] = addons
                    item_details["customization_details"]["addon_total_price"] = addon_total_price
                    
                else:
                    # Old format (string)
                    item_details["customization_details"]["text"] = item["customization"] if item["customization"] else ""
            
            # Process promotion information
            if "promotion" in item and item["promotion"]:
                item_details["is_promotion_item"] = True
                item_details["promotion_details"] = {
                    "buy_item_name": item["promotion"].get("buy_item_name", ""),
                    "buy_quantity": item["promotion"].get("buy_quantity", 0),
                    "discounted_price": item["promotion"].get("discounted_price", 0)
                }
            else:
                item_details["is_promotion_item"] = False
            
            # Add item to result
            order_result["items"].append(item_details)
            
            # Update order totals
            order_result["total_price"] += item["price"]
            order_result["total_discounted_price"] += item.get("discounted_price", item["price"])
            temp_customer = db.customer_temporary_details.find_one({"order_id": order_id})
            coupon_ids = temp_customer.get("selected_coupon_ids", []) if temp_customer else []
        
        # Process bill discounts if present
        # if coupon_ids := order_data.get("coupon_ids", []):
        if  coupon_ids:
            # Calculate bill discounts
            bill_discount_info = calculate_bill_discounts(
                order_id=str(order_data["_id"]),
                total_price=order_result["total_price"],
                discounted_price=order_result.get("total_discounted_price"),
                coupon_ids=coupon_ids,
                db=db
            )
            
            # Add bill discount information to result
            order_result["bill_discount_amount"] = bill_discount_info["bill_discount_amount"]
            order_result["applied_bill_discounts"] = bill_discount_info["applied_bill_discounts"]
            
            # Adjust the final price after all discounts
            order_result["final_price"] = bill_discount_info["final_price_after_discount"]
        else:
            # No bill discounts
            order_result["bill_discount_amount"] = 0
            order_result["applied_bill_discounts"] = []
            order_result["final_price"] = order_result["total_discounted_price"]
        
        print(f"Final order result: {order_result}")
        return order_result
        
    except HTTPException as http_ex:
        print(f"HTTPException: {http_ex.detail}")
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        print(f"[ERROR] Error retrieving order details: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")




def is_coupon_valid_now(coupon: Dict) -> bool:
    """Check if coupon is valid at the current time"""
    # If no duration constraints, coupon is valid
    if not coupon.get("discount_duration"):
        return True
    
    now = datetime.now()
    duration = coupon.get("discount_duration", {})
    
    # Check days constraint
    if duration.get("days"):
        current_day = now.strftime("%A").lower()  # e.g. "monday"
        if current_day not in [day.lower() for day in duration["days"]]:
            return False
    
    # Check dates constraint
    if duration.get("dates"):
        current_date = now.date()
        date_valid = False
        
        for date_range in duration["dates"]:
            # Handle both string and datetime objects
            if isinstance(date_range["start_date"], str):
                start_date = datetime.fromisoformat(date_range["start_date"]).date()
            else:
                start_date = date_range["start_date"]
                
            if isinstance(date_range["end_date"], str):
                end_date = datetime.fromisoformat(date_range["end_date"]).date()
            else:
                end_date = date_range["end_date"]
            
            if start_date <= current_date <= end_date:
                date_valid = True
                break
                
        if not date_valid:
            return False
    
    # Check times constraint
    if duration.get("times"):
        current_time = now.time()
        time_valid = False
        
        for time_range in duration["times"]:
            # Handle both string and datetime objects
            if isinstance(time_range["start_time"], str):
                start_time = datetime.fromisoformat(time_range["start_time"]).time()
            else:
                start_time = time_range["start_time"]
                
            if isinstance(time_range["end_time"], str):
                end_time = datetime.fromisoformat(time_range["end_time"]).time()
            else:
                end_time = time_range["end_time"]
            
            if start_time <= current_time <= end_time:
                time_valid = True
                break
                
        if not time_valid:
            return False
    
    # All constraints passed
    return True






def get_valid_bill_discounts(db: Database, current_time: datetime) -> List[Dict]:
    """Get valid bill discounts based on current time."""
    bill_discounts = db.coupons.find({"discount_coupon_type": "BILL"})
    valid_discounts = []
    
    for discount in bill_discounts:
        # Check time validity
        discount_duration = discount.get("discount_duration", {})
        days = discount_duration.get("days", [])
        dates = discount_duration.get("dates", [])
        times = discount_duration.get("times", [])
        
        # Check day, date, and time validity in a single condition
        if (days and current_time.weekday() + 1 not in days):
            continue
            
        if (dates and not any(
            datetime.fromisoformat(date_range["start_date"]).date() <= current_time.date() <= 
            datetime.fromisoformat(date_range["end_date"]).date() for date_range in dates)):
            continue
            
        if (times and not any(
            datetime.fromisoformat(time_range["start_time"]).time() <= current_time.time() <= 
            datetime.fromisoformat(time_range["end_time"]).time() for time_range in times)):
            continue
        
        # Discount is valid - create a clean copy with default values
        clean_discount = {
            "_id": str(discount["_id"]),
            "coupon_id": discount.get("coupon_id", str(discount["_id"])),  
            "discount_value": discount.get("discount_value", 0.0),
            "discount_percentage": discount.get("discount_percentage", 0.0),
            "discount_coupon_name": discount.get("discount_coupon_name", ""),
            "discount_coupon_type": discount.get("discount_coupon_type", "BILL"),
            "discount_type": discount.get("discount_type", ""),
            "discount_max_value": discount.get("discount_max_value", 0.0),
            "min_bill_amount": discount.get("min_bill_amount", 0.0),
            "buy_x_get_y": discount.get("buy_x_get_y", {}),
            "buy_x_get_y_diff": discount.get("buy_x_get_y_diff", {}),
            "buy_x_get_percentage_off": discount.get("buy_x_get_percentage_off", {}),
            "buy_x_get_y_at_z_price": discount.get("buy_x_get_y_at_z_price", {}),
            "message": discount.get("message", ""),
            "loyalty_points_required": discount.get("loyalty_points_required", 0),
            "combo_items": discount.get("combo_items", []),
            "addons": discount.get("addons", []),
            "can_apply_with_other_coupons": discount.get("can_apply_with_other_coupons", False),
            "details_required": discount.get("details_required", {})
        }
        valid_discounts.append(clean_discount)
    
    return valid_discounts

@router.get("/valid_bill_discounts", response_model=None)
async def fetch_valid_bill_discounts(db: Database = Depends(get_db)):
    """Fetch all valid bill discounts based on current time."""
    try:
        valid_discounts = get_valid_bill_discounts(db, datetime.now())
        return valid_discounts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")













@router.post("/apply_bill_discounts")
async def apply_selected_bill_discounts(
    order_id: str = Body(..., description="Order ID to apply discounts to"),
    coupon_ids: List[str] = Body(..., description="List of coupon IDs to apply"),
    token: str = Body(..., description="Authentication token"),
    db: Database = Depends(get_db)
) -> Dict[str, Any]:
    try:
        # Verify user is authenticated
        current_user = get_current_user(db, token)
        
        # Find the order
        order_data = db.orders.find_one({"_id": ObjectId(order_id), "owner_id": current_user.owner_id})
        if not order_data:
            raise HTTPException(status_code=404, detail="Order not found")
        
        temp_customer = db.customer_temporary_details.find_one({"order_id": order_id})

        if temp_customer:
            # Update existing record
            db.customer_temporary_details.update_one(
                {"order_id": order_id},
                {"$set": {"selected_coupon_ids": coupon_ids}}
            )
        else:
            # Create new record
            db.customer_temporary_details.insert_one({
                "order_id": order_id,
                "selected_coupon_ids": coupon_ids
            })
        
        # Update the order with the selected coupon IDs
        db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"coupon_ids": coupon_ids}}
        )
        
        # Get the updated order details
        # This will automatically calculate the discounts
        updated_order = await get_order_details(
            order_id=order_id,
            token=token,
            db=db
        )
        
        return {
            "success": True,
            "message": "Bill discounts applied successfully",
            "order_details": updated_order
        }
        
    except Exception as e:
        print(f"[ERROR] Error applying bill discounts: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")