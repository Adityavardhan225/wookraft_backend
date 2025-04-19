from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, Body
from typing import List, Dict, Optional, Any
from pymongo.database import Database
from bson import ObjectId
from configurations.config import get_db
from schema.orderSystemSchema import UserOutput, Order, OrderItem
from routes.menu_manage.menu_filter import get_menu_items as filter_menu_items
from routes.security.custom_authorize import dynamic_authorize
from routes.security.protected_authorise import get_current_user
import json
from datetime import datetime, date, time, timedelta
import asyncio
import traceback
from .websocket_handler import websocket_handler, manager, update_filter_criteria
from configurations.custom_json_encoder import CustomJSONEncoder

router = APIRouter()




# @router.post("/place_order", response_model=Order)
# async def place_order(
#     token: str = Query(None),
#     table_number: int = Query(...),
#     overall_customization: str = Query(...),
#     item_quantities: Dict[str, int] = Body(...),
#     item_customizations: Dict[str, str] = Body(...),
#     item_food_types: Dict[str, str] = Body(...),  # New parameter for food types
#     item_food_categories: Dict[str, str] = Body(...),  # New parameter for food categories
#     item_prices: Dict[str, float] = Body(...),
#     item_discounted_prices: Dict[str, Optional[float]] = Body({}),  # Optional discounted prices
#     db: Database = Depends(get_db)
# ):
#     current_user = get_current_user(db, token)
#     order_data = db.orders.find_one({"table_number": table_number, "status": "active", "owner_id": current_user.owner_id})
#     print(f"Current User: {current_user}")
#     print("Order data retrieved from database:", order_data) 
#     if not order_data:
#         order = Order(id=str(ObjectId()), table_number=table_number, items=[], status="active", employee_id=current_user.employee_id, owner_id=current_user.owner_id, overall_customization=overall_customization)
#     else:
#         # Ensure that the items are correctly structured
#         order_items = []
#         for item in order_data.get("items", []):
#             print("Processing item:", item) 
#             if not item:  # Check for empty item
#                 continue
#             # menu_item_data = item.get("menu_item")
#             # if not menu_item_data:
#             #     raise HTTPException(status_code=400, detail="Invalid order data: missing menu_item")
#             # menu_item = MenuItem(**menu_item_data)
#             total_price = item.get("price", 0) * item.get("quantity", 0)
#             total_discounted_price = item.get("discounted_price") * item.get("quantity", 0)
#             order_item = OrderItem(
#                 name=item.get("name"),
#                 quantity=item.get("quantity"), 
#                 customization=item.get("customization"), 
#                 food_type=item.get("food_type"), 
#                 food_category=item.get("food_category"), 
#                 prepared_items=item.get("prepared", False),
#                 price=total_price,
#                 discounted_price=total_discounted_price 
#             )
#             order_items.append(order_item)
#             print("Order item added:", order_item.dict())
#         order = Order(
#             id=str(order_data["_id"]),  # Convert ObjectId to string
#             table_number=order_data["table_number"],
#             items=order_items,
#             status=order_data["status"],
#             employee_id=order_data["employee_id"],
#             owner_id=order_data["owner_id"],
#             overall_customization=overall_customization,
#             received=False,
#             timestamp=datetime.now(),
#             prepared=order_data.get("prepared", False)
#         )
#     for item_name, quantity in item_quantities.items():
#         # Create OrderItem with food_type and food_category
        
#         order_item = OrderItem(
#             name=item_name,
#             quantity=quantity, 
#             customization=item_customizations.get(item_name, ""), 
#             food_type=item_food_types.get(item_name, ""),  # Include food_type
#             food_category=item_food_categories.get(item_name, ""),  # Include food_category
#             prepared_items=False,
#             price=item_prices[item_name]*quantity,
#             discounted_price=item_discounted_prices.get(item_name)*quantity  # Optional
#         )
#         order.items.append(order_item)
#     db.orders.update_one({"_id": ObjectId(order.id)}, {"$set": order.dict()}, upsert=True)
#     print(f'Order placed successfully: {order.dict()}')
#     try:
#         await manager.broadcast(json.dumps({'type': 'order_placed', 'order': order.dict()}, cls=CustomJSONEncoder), roles=["kds","waiter"])
#     except RuntimeError as e:
#         print(f"Error broadcasting order but order placed sccessfully: {e}")

#     return order















def validate_promotion(
    db: Database,
    buy_item_name: str,
    get_item_name: str,
    buy_quantity: int,
    get_quantity: int,
    discounted_price: float
) -> tuple:

        # Get buy item from database
    buy_item = db.menu_items.find_one({"name": buy_item_name})
    if not buy_item:
        return False, f"Buy item '{buy_item_name}' not found in menu"
    
    # Check for promotion rules
    discount_rules = buy_item.get("buy_x_get_y_at_z_price", [])
    valid_rule = None
    print("Discount rules:", discount_rules)
    # Find matching rule
    # for rule in discount_rules:
    #     print("Rule:", rule)
    #     if (
    #         rule == get_item_name):
    #         valid_rule = rule
    #         break

    # print("Valid rule:", valid_rule)
    # if not valid_rule:
    #     print("No matching promotion found")
    #     return False, f"No matching promotion found for '{buy_item_name}' and '{get_item_name}'"

    if get_item_name in discount_rules:
        # We found a matching rule for this get item
        valid_rule = discount_rules[get_item_name]
        print("Valid rule found:", valid_rule)
    else:
        print(f"No matching promotion found for '{get_item_name}'")
        return False, f"No promotion found for '{get_item_name}' in '{buy_item_name}' promotions"
    
    # Get promotion parameters
    rule_buy_quantity = int(valid_rule.get("buy_quantity", 0))
    rule_get_quantity = int(valid_rule.get("get_quantity", 0))
    rule_price = float(valid_rule.get("discounted_price", 0))
    print('rule_buy_quantity:', rule_buy_quantity, rule_get_quantity, rule_price)
    
    # Calculate allowed sets
    if rule_buy_quantity <= 0:
        return False, "Invalid promotion configuration (buy quantity must be positive)"
    
    max_sets = buy_quantity // rule_buy_quantity
    max_get_items = max_sets * rule_get_quantity

        # Check if requested get quantity exceeds max allowed
    if get_quantity > max_get_items:
        return False, f"Maximum allowed quantity for '{get_item_name}' is {max_get_items}, requested {get_quantity}"
    
    # Check if price matches
    if abs(discounted_price - rule_price) > 0.01:
        return False, f"Discounted price should be {rule_price} per unit, got {discounted_price}"
    print('All checks passed')
    # All checks passed
    return True, ""



def calculate_paid_items(quantity: int, buy_quantity: int, get_quantity: int) -> int:
    """Calculate number of items to pay for in buy X get Y offer"""
    if quantity <= buy_quantity:
        return quantity
        
    total_set_size = buy_quantity + get_quantity
    complete_sets = quantity // total_set_size
    remaining_items = quantity % total_set_size
    
    paid_items = (complete_sets * buy_quantity)
    if remaining_items > 0:
        paid_items += min(remaining_items, buy_quantity)
    print(paid_items)
    return paid_items

# def calculate_discounted_price(menu_item: dict, base_price: float, quantity: int) -> float:
#     print("Calculating discounted price ", menu_item, base_price, quantity)
#     """Calculate final price after applying discounts"""
#     if not menu_item.get("discount_rules"):
#         return base_price * quantity

#     rules = menu_item["discount_rules"]
#     total_price = base_price * quantity
#     print("Total price:", total_price, rules)
#     if rules["type"] == "buy_x_get_y":
#         print("Buy X Get Y discount")
#         paid_items = calculate_paid_items(
#             quantity,
#             int(rules["buy_quantity"]),
#             int(rules["get_quantity"])
#         )
#         return base_price * paid_items
#     elif rules["type"] == "percentage":
#         discount = rules["percentage"] / 100
#         return total_price * (1 - discount)
#     elif rules["type"] == "value":
#         discount = rules["value"] * quantity
#         return max(0, total_price - discount)
#     print("No discount applied")
#     return total_price



def calculate_discounted_price(menu_item: dict, base_price: float, quantity: int) -> float:
    """Calculate final price after applying discounts"""
    print("Calculating discounted price for", menu_item.get("name"), "base_price:", base_price, "quantity:", quantity)
    
    # Check if discount rules exist
    if not menu_item.get("discount_rules"):
        return base_price * quantity

    # Get discount rules
    rules = menu_item["discount_rules"]
    total_price = base_price * quantity
    print("Total price:", total_price)
    
    # If rules is a list, find the highest priority rule
    if isinstance(rules, list):
        # Sort rules by priority (higher number = higher priority)
        sorted_rules = sorted(rules, key=lambda x: x.get("priority", 0), reverse=True)
        
        if not sorted_rules:
            return total_price
            
        # Use the highest priority rule
        rule = sorted_rules[0]
        print("Using rule with priority:", rule.get("priority"), "type:", rule.get("type"))
        
        if rule.get("type") == "buy_x_get_y":
            print("Buy X Get Y discount")
            paid_items = calculate_paid_items(
                quantity,
                int(rule.get("buy_quantity", 1)),
                int(rule.get("get_quantity", 0))
            )
            return base_price * paid_items
            
        elif rule.get("type") == "percentage":
            discount = rule.get("percentage", 0) / 100
            return total_price * (1 - discount)
            
        elif rule.get("type") == "value":
            discount = rule.get("value", 0) * quantity
            return max(0, total_price - discount)
    
    # If rules is a dictionary
    elif isinstance(rules, dict):
        if rules.get("type") == "buy_x_get_y":
            print("Buy X Get Y discount")
            paid_items = calculate_paid_items(
                quantity,
                int(rules.get("buy_quantity", 1)),
                int(rules.get("get_quantity", 0))
            )
            return base_price * paid_items
            
        elif rules.get("type") == "percentage":
            discount = rules.get("percentage", 0) / 100
            return total_price * (1 - discount)
            
        elif rules.get("type") == "value":
            discount = rules.get("value", 0) * quantity
            return max(0, total_price - discount)
    
    # Default: no discount applied
    print("No discount applied")
    return total_price


def get_item_addons_info(
    db: Database,
    item_name: str,
    owner_id: str
):
    """
    Get addon information for a menu item
    
    Args:
        db: Database connection
        item_name: Name of the menu item
        owner_id: Owner ID of the restaurant
        
    Returns:
        List of available addons for this item or empty list if none
    """
    item = db.menu_items.find_one({"name": item_name, "owner_id": owner_id})
    
    if not item:
        return []
    
    # Fetch the addon coupon using the addon field in the item
    addon_coupon_path = item.get("addon")
    if not addon_coupon_path or not isinstance(addon_coupon_path, str):
        return []
    
    # Extract the coupon_id from the addon path
    coupon_id = addon_coupon_path.split("/")[-1]
    
    # Fetch the addon coupon from the coupons collection
    coupon = db.coupons.find_one({"coupon_id": coupon_id, "discount_coupon_type": "addon"})
    if not coupon or "addons" not in coupon:
        return []
    
    return coupon["addons"]



def calculate_addons_price(
    available_addons: List[dict],
    selected_addons: Dict[str, Dict[str, Any]]
) -> float:
    """
    Calculate total price for selected addons
    
    Args:
        available_addons: List of available addons with prices
        selected_addons: Dict of selected addon names to their details
        
    Returns:
        float: Total price of selected addons
    """
    total_price = 0.0
    
    # Create lookup dict of available addons by name
    addon_lookup = {addon["addon_item_name"]: addon for addon in available_addons}
    
    # Calculate price based on selected addons
    for addon_name, addon_info in selected_addons.items():
        if addon_name in addon_lookup:
            addon_price = addon_lookup[addon_name].get("addon_price", 0)
            addon_quantity = addon_info.get("quantity", 1)
            total_price += addon_price * addon_quantity
    
    return total_price

# @router.post("/place_order", response_model=Order)
# async def place_order(
#     token: str = Query(None),
#     table_number: int = Query(...),
#     overall_customization: str = Query(...),
#     item_quantities: Dict[str, int] = Body(...),
#     item_customizations: Dict[str, str] = Body(...),
#     item_food_types: Dict[str, str] = Body(...),
#     item_food_categories: Dict[str, str] = Body(...),
#     item_prices: Dict[str, float] = Body(...),
#     item_discounted_prices: Dict[str, Optional[float]] = Body({}),
#     db: Database = Depends(get_db)
# ):
#     try:
#         current_user = get_current_user(db, token)
#         order_data = db.orders.find_one({
#             "table_number": table_number, 
#             "status": "active", 
#             "owner_id": current_user.owner_id
#         })

#         if not order_data:
#             order = Order(
#                 id=str(ObjectId()),
#                 table_number=table_number,
#                 items=[],
#                 status="active",
#                 employee_id=current_user.employee_id,
#                 owner_id=current_user.owner_id,
#                 overall_customization=overall_customization,
#                 received=False,
#                 timestamp=datetime.now(),
#                 prepared=False
#             )
#         else:
#             order_items = []
#             for item in order_data.get("items", []):
#                 if not item:
#                     continue
                    
#                 order_item = OrderItem(
#                     name=item.get("name"),
#                     quantity=item.get("quantity"),
#                     customization=item.get("customization"),
#                     food_type=item.get("food_type"),
#                     food_category=item.get("food_category"),
#                     prepared_items=item.get("prepared", False),
#                     price=item.get("price", 0),
#                     discounted_price=item.get("discounted_price", 0)
#                 )
#                 order_items.append(order_item)

#             order = Order(
#                 id=str(order_data["_id"]),
#                 table_number=order_data["table_number"],
#                 items=order_items,
#                 status=order_data["status"],
#                 employee_id=order_data["employee_id"],
#                 owner_id=order_data["owner_id"],
#                 overall_customization=overall_customization,
#                 received=False,
#                 timestamp=datetime.now(),
#                 prepared=order_data.get("prepared", False)
#             )

#         # Process new items
#         for item_name, quantity in item_quantities.items():
#             menu_item = db.menu_items.find_one({
#                 "name": item_name,
#                 "owner_id": current_user.owner_id
#             })
            
#             if not menu_item:
#                 continue

#             base_price = item_prices[item_name]
#             total_price = base_price * quantity
            
#             # Calculate discounted price
#             discounted_price = calculate_discounted_price(
#                 menu_item,
#                 base_price,
#                 quantity
#             )

#             order_item = OrderItem(
#                 name=item_name,
#                 quantity=quantity,
#                 customization=item_customizations.get(item_name, ""),
#                 food_type=item_food_types.get(item_name, ""),
#                 food_category=item_food_categories.get(item_name, ""),
#                 prepared_items=False,
#                 price=total_price,
#                 discounted_price=discounted_price
#             )
#             order.items.append(order_item)

#         # Save order
#         db.orders.update_one(
#             {"_id": ObjectId(order.id)},
#             {"$set": order.dict()},
#             upsert=True
#         )

#         # Broadcast order
#         try:
#             await manager.broadcast(
#                 json.dumps(
#                     {'type': 'order_placed', 'order': order.dict()},
#                     cls=CustomJSONEncoder
#                 ),
#                 roles=["kds", "waiter"]
#             )
#         except RuntimeError as e:
#             print(f"Error broadcasting order: {e}")

#         return order

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))




















# @router.post("/place_order", response_model=Order)
# async def place_order(
#     token: str = Query(None),
#     table_number: int = Query(...),
#     overall_customization: str = Query(...),
#     item_quantities: Dict[str, int] = Body(...),
#     item_customizations: Dict[str, str] = Body(...),
#     item_food_types: Dict[str, str] = Body(...),
#     item_food_categories: Dict[str, str] = Body(...),
#     item_prices: Dict[str, float] = Body(...),
#     item_discounted_prices: Dict[str, Optional[float]] = Body({}),
#     promotions: List[Dict[str, Any]] = Body(None, default=[]),  # Optional promotions
#     item_addons: Dict[str, List[dict]] = Body(None, default={}),  # Optional addons
#     db: Database = Depends(get_db)
# ):
#     try:
#         current_user = get_current_user(db, token)
#         order_data = db.orders.find_one({
#             "table_number": table_number, 
#             "status": "active", 
#             "owner_id": current_user.owner_id
#         })

#         if not order_data:
#             order = Order(
#                 id=str(ObjectId()),
#                 table_number=table_number,
#                 items=[],
#                 status="active",
#                 employee_id=current_user.employee_id,
#                 owner_id=current_user.owner_id,
#                 overall_customization=overall_customization,
#                 received=False,
#                 timestamp=datetime.now(),
#                 prepared=False
#             )
#         else:
#             order_items = []
#             for item in order_data.get("items", []):
#                 if not item:
#                     continue
                    
#                 order_item = OrderItem(
#                     name=item.get("name"),
#                     quantity=item.get("quantity"),
#                     customization=item.get("customization"),
#                     food_type=item.get("food_type"),
#                     food_category=item.get("food_category"),
#                     prepared_items=item.get("prepared", False),
#                     price=item.get("price", 0),
#                     discounted_price=item.get("discounted_price", 0),
#                     addons=item.get("addons"),
#                     promotion=item.get("promotion")
#                 )
#                 order_items.append(order_item)

#             order = Order(
#                 id=str(order_data["_id"]),
#                 table_number=order_data["table_number"],
#                 items=order_items,
#                 status=order_data["status"],
#                 employee_id=order_data["employee_id"],
#                 owner_id=order_data["owner_id"],
#                 overall_customization=overall_customization,
#                 received=False,
#                 timestamp=datetime.now(),
#                 prepared=order_data.get("prepared", False)
#             )

#         # Process promotions if provided
#         promotion_items = {}
#         if promotions:
#             for promotion in promotions:
#                 buy_item_name = promotion.get("buy_item_name")
#                 get_item_name = promotion.get("get_item_name")
#                 buy_quantity = promotion.get("buy_quantity", 0)
#                 get_quantity = promotion.get("get_quantity", 0)
#                 discounted_price = promotion.get("discounted_price", 0)
                
#                 # Validate this promotion
#                 is_valid, error_msg = validate_promotion(
#                     db,
#                     buy_item_name,
#                     get_item_name,
#                     buy_quantity,
#                     get_quantity,
#                     discounted_price
#                 )
                
#                 if not is_valid:
#                     # If promotion is invalid, reject the entire order
#                     raise HTTPException(status_code=400, detail=error_msg)
                
#                 # Mark this get item as part of a promotion
#                 promotion_items[get_item_name] = {
#                     "buy_item_name": buy_item_name,
#                     "discounted_price": discounted_price,
#                     "quantity": get_quantity
#                 }

#         # Process new items
#         for item_name, quantity in item_quantities.items():
#             menu_item = db.menu_items.find_one({
#                 "name": item_name,
#                 "owner_id": current_user.owner_id
#             })
            
#             if not menu_item:
#                 continue

#             base_price = item_prices[item_name]
#             total_price = base_price * quantity
            
#             # Process addons if they exist for this item
#             selected_addons = []
#             if item_addons and item_name in item_addons:
#                 # Process addon logic here
#                 addon_data = item_addons[item_name]
#                 # Check if item has addon configuration
#                 addon_coupon_path = menu_item.get("addon")
#                 if addon_coupon_path:
#                     # Get addon coupon
#                     coupon_id = addon_coupon_path.split("/")[-1]
#                     coupon = db.coupons.find_one({
#                         "coupon_id": coupon_id,
#                         "discount_coupon_type": "addon"
#                     })
                    
#                     if coupon and "addons" in coupon:
#                         # Create mapping of addon names to full details
#                         available_addons = {
#                             addon["addon_item_name"]: addon 
#                             for addon in coupon["addons"]
#                         }
                        
#                         # Process each addon request
#                         for addon_request in addon_data:
#                             addon_name = addon_request.get("addon_item_name")
#                             addon_quantity = addon_request.get("quantity", 1)
                            
#                             if addon_name in available_addons:
#                                 # Get the full addon details
#                                 addon_detail = available_addons[addon_name].copy()
#                                 addon_detail["quantity"] = addon_quantity
#                                 selected_addons.append(addon_detail)
                
#                 # If there are addons, update the price
#                 if selected_addons:
#                     addon_price_total = 0
#                     for addon in selected_addons:
#                         addon_price = addon.get("addon_price", 0)
#                         addon_quantity = addon.get("quantity", 1)
#                         addon_price_total += addon_price * addon_quantity
                    
#                     # Add addon costs to the total price
#                     total_price += (addon_price_total * quantity)

#             # Check if this item is part of a promotion
#             promotion_info = None
#             if item_name in promotion_items:
#                 promotion_info = promotion_items[item_name]
#                 # Use the discounted price from the promotion
#                 discounted_price = promotion_info["discounted_price"] * quantity
#             else:
#                 # Regular discount calculation
#                 discounted_price = calculate_discounted_price(menu_item, base_price, quantity)
                
#                 # Add addon costs to discounted price for non-promotion items
#                 if selected_addons:
#                     addon_price_total = 0
#                     for addon in selected_addons:
#                         addon_price = addon.get("addon_price", 0)
#                         addon_quantity = addon.get("quantity", 1)
#                         addon_price_total += addon_price * addon_quantity
                    
#                     discounted_price += (addon_price_total * quantity)

#             order_item = OrderItem(
#                 name=item_name,
#                 quantity=quantity,
#                 customization=item_customizations.get(item_name, ""),
#                 food_type=item_food_types.get(item_name, ""),
#                 food_category=item_food_categories.get(item_name, ""),
#                 prepared_items=False,
#                 price=total_price,
#                 discounted_price=discounted_price,
#                 addons=selected_addons if selected_addons else None,
#                 promotion=promotion_info
#             )
#             order.items.append(order_item)

#         # Save order
#         db.orders.update_one(
#             {"_id": ObjectId(order.id)},
#             {"$set": order.dict()},
#             upsert=True
#         )

#         # Broadcast order
#         try:
#             await manager.broadcast(
#                 json.dumps(
#                     {'type': 'order_placed', 'order': order.dict()},
#                     cls=CustomJSONEncoder
#                 ),
#                 roles=["kds", "waiter"]
#             )
#         except RuntimeError as e:
#             print(f"Error broadcasting order: {e}")

#         return order

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))








@router.post("/place_order", response_model=Order)
async def place_order(
    token: str = Query(None),
    table_number: int = Body(...),
    overall_customization: str = Body(...),
    item_quantities: Dict[str, int] = Body(...),  # Total quantities across customizations
    item_food_types: Dict[str, str] = Body(...),
    item_food_categories: Dict[str, str] = Body(...),
    item_prices: Dict[str, float] = Body(...),
    item_customization_details: Dict[str, List[Dict[str, Any]]] = Body({}),  # New field
    promotions: List[Dict[str, Any]] = Body(default=[]),
    db: Database = Depends(get_db)
):
    try:
        import traceback
        print(f"[DEBUG] Received order data: table={table_number}, items count={len(item_customization_details)}")
        print(f"[DEBUG] Item quantities: {item_quantities}")
        print(f"[DEBUG] Received promotions: {len(promotions)}")
        
        # Get current user
        current_user = get_current_user(db, token)
        print(f"[DEBUG] User authenticated: {current_user.employee_id}")
        
        # Find active order for this table
        order_data = db.orders.find_one({
            "table_number": table_number, 
            "status": "active", 
            "owner_id": current_user.owner_id
        })
        print(f"[DEBUG] Existing order found: {order_data is not None}")

        # Create new order or use existing one
        if not order_data:
            print("[DEBUG] Creating new order")
            order = Order(
                id=str(ObjectId()),
                table_number=table_number,
                items=[],
                status="active",
                employee_id=current_user.employee_id,
                owner_id=current_user.owner_id,
                overall_customization=overall_customization,
                received=False,
                timestamp=datetime.now(),
                payment_status="unpaid",
                prepared=False
            )
        else:
            print(f"[DEBUG] Updating existing order: {order_data['_id']}")
            # Load existing order items
            order_items = []
            for item in order_data.get("items", []):
                if not item:
                    continue
                    
                order_item = OrderItem(
                    name=item.get("name"),
                    quantity=item.get("quantity"),
                    customization=item.get("customization"),  # This will now contain all customization data
                    food_type=item.get("food_type"),
                    food_category=item.get("food_category"),
                    prepared_items=item.get("prepared", False),
                    price=item.get("price", 0),
                    discounted_price=item.get("discounted_price", 0),
                    promotion=item.get("promotion")
                    # Removed addons and sizes fields
                )
                order_items.append(order_item)

            order = Order(
                id=str(order_data["_id"]),
                table_number=order_data["table_number"],
                items=order_items,
                status=order_data["status"],
                employee_id=order_data["employee_id"],
                owner_id=order_data["owner_id"],
                overall_customization=overall_customization,
                received=False,
                timestamp=datetime.now(),
                payment_status="unpaid",
                prepared=order_data.get("prepared", False)
            )
        
        # Process promotions if provided
        promotion_items = {}
        if promotions:
            print("[DEBUG] Processing promotions")
            for i, promotion in enumerate(promotions):
                buy_item_name = promotion.get("buy_item_name")
                get_item_name = promotion.get("get_item_name")
                buy_quantity = promotion.get("buy_quantity", 0)
                get_quantity = promotion.get("get_quantity", 0)
                discounted_price = promotion.get("discounted_price", 0)
                
                print(f"[DEBUG] Promotion #{i+1}: Buy {buy_quantity}x {buy_item_name}, Get {get_quantity}x {get_item_name} at {discounted_price}")
                
                # Validate this promotion
                is_valid, error_msg = validate_promotion(
                    db,
                    buy_item_name,
                    get_item_name,
                    buy_quantity,
                    get_quantity,
                    discounted_price
                )
                
                print(f"[DEBUG] Promotion #{i+1} validation: {is_valid}, {error_msg if not is_valid else 'OK'}")
                
                if not is_valid:
                    # If promotion is invalid, reject the entire order
                    raise HTTPException(status_code=400, detail=error_msg)
                
                # Look up the "get" item to get its food type and category
                get_menu_item = db.menu_items.find_one({
                    "name": get_item_name,
                    "owner_id": current_user.owner_id
                })
                
                if get_menu_item:
                    # Get base price for the promotion item
                    # base_price = item_prices.get(get_item_name, get_menu_item.get("price", 0))
                    base_price = get_menu_item.get("price", 0)
                    
                    # Create promotion info
                    promotion_info = {
                        "buy_item_name": buy_item_name,
                        "discounted_price": discounted_price,
                        "quantity": get_quantity,
                        "buy_quantity": buy_quantity
                    }
                    
                    promo_item_quantity = get_quantity
                    if promo_item_quantity > 0:
                        # Calculate prices
                        total_price = base_price * promo_item_quantity
                        discounted_price_total = discounted_price * promo_item_quantity
                        
                        print(f"[DEBUG] Creating promotion item: {get_item_name}, qty={promo_item_quantity}, price={total_price}, discounted={discounted_price_total}")
                        
                        # For promotions, we'll store an empty customization object
                        customization_data = {
                            "text": "",  # No text customization for promotions
                            "addons": [],  # No addons for promotions
                            "size": None   # No size for promotions
                        }
                        
                        # Create order item for the promotion item
                        promo_order_item = OrderItem(
                            name=get_item_name,
                            quantity=promo_item_quantity,
                            customization=customization_data,  # Using the new structure
                            food_type=get_menu_item.get("food_type", ""),
                            food_category=get_menu_item.get("food_category", ""),
                            prepared_items=False,
                            price=total_price,
                            discounted_price=discounted_price_total,
                        
                            promotion=promotion_info
                            # Removed addons and sizes fields
                        )
                        
                        order.items.append(promo_order_item)
                        print(f"[DEBUG] Added promotion item to order: {get_item_name}")
                        
                        # Store promotion info for later reference
                        promotion_items[get_item_name] = promotion_info

        # Process each item with its customizations
        print("[DEBUG] Processing items with customizations")
        item_counter = 0
        for item_name, customization_list in item_customization_details.items():
            print(f"[DEBUG] Processing {item_name} with {len(customization_list)} customization variations")
            
            # Skip if the item doesn't have customization details
            if not customization_list:
                print(f"[DEBUG] No customization details for {item_name}, skipping")
                continue
                
            # Get menu item details
            menu_item = db.menu_items.find_one({
                "name": item_name,
                "owner_id": current_user.owner_id
            })
            
            if not menu_item:
                print(f"[DEBUG] Menu item not found: {item_name}")
                continue
            
            # Process each customization option as a separate order item
            for cust_idx, customization_detail in enumerate(customization_list):
                item_counter += 1
                # Get customization specific details
                quantity = customization_detail.get("quantity", 1)
                customization_text = customization_detail.get("customization", "")
                
                print(f"[DEBUG] Item #{item_counter}: {item_name}, Custom #{cust_idx+1}: '{customization_text}', qty={quantity}")
                
                # Skip items with zero quantity
                if quantity <= 0:
                    print(f"[DEBUG] Skipping {item_name} with zero quantity")
                    continue
                
                # Check if this is a promotion item
                is_promotion_item = item_name in promotion_items
                promotion_info = promotion_items.get(item_name) if is_promotion_item else None
                
                # Get base price for this item
                # base_price = item_prices.get(item_name, menu_item.get("price", 0))
                base_price = menu_item.get("price", 0)
                print(f"[DEBUG] Base price for {item_name}: {base_price}")
                
                # Create the consolidated customization object
                customization_data = {
                    "text": customization_text,  # Store customization text
                    "addons": [],  # Initialize empty addons list
                    "size": None   # Initialize empty size
                }
                
                # Process size if available (not for promotion items)
                if not is_promotion_item and "size" in customization_detail:
                    size_data = customization_detail.get("size")
                    if size_data:
                        # Store size data directly
                        customization_data["size"] = size_data
                        
                        # Update base price
                        # size_price = size_data.get("price", 0)
                        # With this:
                        size_name = size_data.get("size_name", "")
                        # Look up the size in the database
                        db_size = db.sizes.find_one({
                            "item_name": item_name,
                            "size_name": size_name,
                            "owner_id": current_user.owner_id
                        })
                        if db_size:
                            size_price = db_size.get("price", 0)
                        else:
                            # Fallback to base price if size not found
                            size_price = base_price
                            print(f"[DEBUG] Size {size_name} not found in database, using base price")
                        base_price = size_price
                        print(f"[DEBUG] Size for {item_name}: {size_data.get('size_name')}, price={size_price}")
                        print(f"[DEBUG] Updated base price with size: {base_price}")
                
                # Calculate the initial price (base × quantity)
                total_price = base_price * quantity
                print(f"[DEBUG] Initial total price: {total_price}")
                
                # Process addons if they exist (not for promotion items)
                addon_price_total = 0
                
                if not is_promotion_item and "addons" in customization_detail and customization_detail["addons"]:
                    addon_data_list = customization_detail["addons"]
                    print(f"[DEBUG] Processing {len(addon_data_list)} addons for {item_name}")
                    
                    # Store addons directly in the customization data
                    customization_data["addons"] = addon_data_list
                    
                    # Calculate addon price total
                    for addon_idx, addon in enumerate(addon_data_list):
                        addon_quantity = addon.get("quantity", 1)
                        addon_price = addon.get("price", 0)
                        addon_price_total += addon_price * addon_quantity
                        print(f"[DEBUG] Addon #{addon_idx+1}: {addon.get('addon_name')}, qty={addon_quantity}, price={addon_price}")
                    
                    # Add addon costs to total price
                    if addon_data_list:
                        total_price += (addon_price_total * quantity)
                        print(f"[DEBUG] Total price after addons: {total_price}")
                
                # Calculate discounted price
                if is_promotion_item:
                    # For promotion items, use the promotion's discounted price
                    discounted_price = promotion_info["discounted_price"] * quantity
                    print(f"[DEBUG] Promotion discounted price: {discounted_price}")
                else:
                    # Regular discount calculation for non-promotion items
                    item_base_discounted = calculate_discounted_price(menu_item, base_price, quantity)
                    discounted_price = item_base_discounted
                    print(f"[DEBUG] Base discounted price: {discounted_price}")
                    
                    # Add addon costs to discounted price for non-promotion items
                    if addon_price_total > 0:
                        discounted_price += (addon_price_total * quantity)
                        print(f"[DEBUG] Discounted price after addons: {discounted_price}")
                print(f"[DEBUG] menu item for {item_name}: {menu_item.get('food_type')}")
                # print(f"[DEBUG] discounted price for {item_name}: {}")
                try:
                    # Create order item with the consolidated customization object
                    order_item = OrderItem(
                        name=item_name,
                        quantity=quantity,
                        customization=customization_data,  # Using the new consolidated structure
                        food_type=menu_item.get("food_type", ""),
                        food_category=menu_item.get("category", ""),
                        prepared_items=False,
                        price=total_price,
                        discounted_price=discounted_price,
                        promotion=promotion_info
                        # Removed addons and sizes fields
                    )
                    
                    order.items.append(order_item)
                    print(f"[DEBUG] Added order item #{item_counter} to order")
                
                except Exception as item_error:
                    print(f"[ERROR] Failed to create order item: {str(item_error)}")
                    print(f"[ERROR] Error details: {traceback.format_exc()}")
                    # Continue processing other items rather than failing completely
                    continue
        
        print(f"[DEBUG] Total items in order: {len(order.items)}")
        
        # Save order
        try:
            db.orders.update_one(
                {"_id": ObjectId(order.id)},
                {"$set": order.dict()},
                upsert=True
            )
            print(f"[DEBUG] Order saved successfully: {order.id}")
        except Exception as db_error:
            print(f"[ERROR] Database error when saving order: {str(db_error)}")
            print(f"[ERROR] Error details: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to save order: {str(db_error)}")

        # Broadcast order to kitchen display system and waiters

        try:
            await manager.broadcast(
                json.dumps(
                    {'type': 'order_placed', 'order': order.dict()},
                    cls=CustomJSONEncoder
                ),
                roles=["kds", "waiter"]
            )
            print("[DEBUG] Order broadcast successful")
        except RuntimeError as e:
            print(f"[ERROR] Error broadcasting order: {e}")
        
         # Mark table as occupied when order is placed
        if table_number:
            try:
                print(f"[TABLE] Checking table {table_number} status for order placement")
                
                # Get the table by table_number
                table = db.tables.find_one({"table_number": table_number})
                if table:
                    from routes.table_management.table_management_model import TableStatus
                    
                    # Only update if table is not already occupied
                    if table.get("status") != TableStatus.OCCUPIED:
                        print(f"[TABLE] Marking table {table_number} as occupied for new order")
                        
                        # Update table status to occupied
                        result = db.tables.update_one(
                            {"_id": table["_id"]},
                            {"$set": {"status": TableStatus.OCCUPIED}}
                        )
                        
                        # Broadcast table status update to all clients
                        if result.modified_count > 0:
                            # Import needed only if table was found and updated
                            import asyncio
                            from routes.table_management.table_management import manager as manager1
                            from routes.table_management.table_management import serialize_for_json
                            
                            # Get updated table
                            updated_table = db.tables.find_one({"_id": table["_id"]})
                            if updated_table:
                                # Broadcast update
                                asyncio.create_task(manager1.broadcast({
                                    "type": "table_status_updated",
                                    "data": serialize_for_json(updated_table)
                                }))
                                print(f"[TABLE] Successfully marked table {table_number} as occupied")
            except Exception as table_err:
                print(f"[TABLE] Error updating table status: {str(table_err)}")
                # Don't raise exception - continue even if table update fails


            # Continue even if broadcast fails

        # Broadcast order to kitchen display system and waiters

        return order

    except HTTPException as http_ex:
        # Re-raise HTTP exceptions
        print(f"[ERROR] HTTP Exception: {http_ex.status_code} - {http_ex.detail}")
        raise
    
    except Exception as e:
        print(f"[ERROR] Unhandled exception in place_order: {str(e)}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))





















































@router.websocket("/ws/waiter/{employee_id}")
async def websocket_endpoint_waiter(websocket: WebSocket, employee_id: str, token: str = Query(None), db: Database = Depends(get_db)):
    await websocket_handler(websocket, token, "waiter", db, employee_id=employee_id)

@router.websocket("/ws/kds")
async def websocket_endpoint_kds(websocket: WebSocket, token: str = Query(None), db: Database = Depends(get_db)):
    
    await websocket_handler(websocket, token, "kds", db)



@router.post("/filter_orders")
async def filter_orders(food_types: Optional[List[str]] = None, food_categories: Optional[List[str]] = None, db: Database = Depends(get_db)):
    try:
        update_filter_criteria(food_types, food_categories)
        return {"message": "Filter criteria updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))









