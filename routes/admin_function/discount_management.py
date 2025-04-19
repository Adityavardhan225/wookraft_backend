import random
import numpy as np
from pydantic import BaseModel, Field
from typing import List, Union, Optional, Dict
from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pymongo.database import Database
from configurations.config import get_db
from bson import ObjectId
from schema.user import UserOutput
from routes.security.protected_authorise import get_current_user

















def check_duplicate_buy_get(new_coupon: dict, db, owner_id: str) -> bool:
    """
    Check for duplication for coupons of type 'buy_x_get_y_at_z_price'.
    
    Rules:
    1. Within the new coupon, ensure that no buy item is the same as any get item.
       (This is validated solely from the new coupon's data.)
    2. For the new coupon, create a set of (buy_item_id, get_item_id) pairs.
       Then, compare against existing coupons (of the same type for this owner)
       to ensure that none of those pairs are already defined.
       
    Returns:
        True if a duplicate (buy_item, get_item) pair exists in any existing coupon.
        Otherwise, False.
        
    Raises:
        HTTPException: If in the new coupon any buy_item is identical to any get_item.
    """
    new_section = new_coupon.get("buy_x_get_y_at_z_price", {})
    new_buy_items = new_section.get("buy_items", [])
    new_get_items = new_section.get("get_items", [])

    # Rule 1: Check within the new coupon that no buy item equals any get item.
    for buy in new_buy_items:
        for get in new_get_items:
            print(f"buy_items123: {buy}")
            print(f"get_items123: {get}")
            if buy.get("item_id") == get.get("item_id"):
                print(f"buy_items_456: {buy}")
                print(f"get_items_456: {get}")
                raise HTTPException(status_code=400, detail="Buy item and get item cannot be the same within a coupon.")
            print(f"get_items_789: {get}")
        print(f'buy_items_101112: {buy}')

    # Create a set of all (buy_item_id, get_item_id) pairs from the new coupon.
    new_pairs = {(buy.get("item_id"), get.get("item_id")) for buy in new_buy_items for get in new_get_items}

    print(f"new_pairs: {new_pairs}")
    # Query existing coupons of type 'buy_x_get_y_at_z_price' for the owner
    existing_coupons = list(db.coupons.find({
        "owner_id": owner_id,
        "discount_type": "buy_x_get_y_at_z_price"
    }))
    print(f"existing_coupons: {existing_coupons}")
    for coupon in existing_coupons:
        if coupon.get("discount_type") == "buy_x_get_y_at_z_price":
            print(f'coupon: {coupon}')
            existing_section = coupon.get("buy_x_get_y_at_z_price", {})
            existing_buy_items = existing_section.get("buy_items", [])
            existing_get_items = existing_section.get("get_items", [])
            print(f"existing_buy_items: {existing_buy_items}")
            print(f"existing_get_items: {existing_get_items}")
            
            # Check if exact same (buy_item, get_item) pair exists
            existing_pairs = {(buy["item_id"], get["item_id"]) 
                            for buy in existing_buy_items 
                            for get in existing_get_items}
            print(f"existing_pairs: {existing_pairs}")
            
            # Only return True if same pair exists
            if new_pairs & existing_pairs:
                print(f"new_pairs: {new_pairs}")
                return True
            print(f"new_pairs_123: {new_pairs}")
    return False





class Addon(BaseModel):
    addon_item_name: str
    addon_price: float
    addon_description: Optional[str] = None

class DiscountDuration(BaseModel):
    days:Optional[List[str]] = None
    dates: Optional[List[Dict[str, date]]] = None
    times: Optional[List[Dict[str, time]]] = None

class BuyXGetYAtZPrice(BaseModel):
    buy_items: List[Dict[str, Union[str, int]]] = Field(
        ...,
        example=[{"item_name": "Pizza", "quantity": 2}]
    )
    get_items: List[Dict[str, Union[str, int, float]]] = Field(
        ...,
        example=[{"item_name": "Coke", "quantity": 1, "discounted_price": 20.00}]
    )






class Coupon(BaseModel):
    discount_value: Optional[float] = None
    discount_percentage: Optional[float] = None
    discount_coupon_name: Optional[str] = None
    discount_coupon_type: str
    discount_type: Optional[str] = None # For use in case of discount on food_items
    discount_max_value: Optional[float] = None  # For discount of x% up to rs y
    min_bill_amount: Optional[float] = None  # For discount of x amount from bill of y amount
    discount_duration: Optional[DiscountDuration] = None
    owner_id: str
    coupon_id: str
    buy_x_get_y: Optional[Dict[str, Union[str, int]]] = None  # New feature: Buy X Get Y (Same Item)
    buy_x_get_y_diff: Optional[Dict[str, Union[List[Dict[str, Union[str, int]]], List[Dict[str, Union[str, int, float]]]]]] = None  # New feature: Buy X Get Y (Different Items)
    buy_x_get_percentage_off: Optional[Dict[str, Union[str, int, float]]] = None  # New feature: Buy X Get Percentage Off
    buy_x_get_y_at_z_price: Optional[BuyXGetYAtZPrice] = None  # New feature: Buy X and Get Different Y at Different Z Price
    message: Optional[str] = None  # Field to store terms and conditions
    loyalty_points_required: Optional[int] = None  # New feature: Loyalty Discounts
    combo_items: Optional[List[str]] = None  # New feature: Combo Discounts
    addons:Optional[List[Addon]] = None  # New feature: Addons
    can_apply_with_other_coupons: Optional[bool] = False
    details_required: Optional[Dict[str, str]] = None 


router = APIRouter()



@router.post("/add_addon")
async def add_addon(
    item_names: Optional[List[str]] = Body(..., description="List of item names to apply the add-on to"),
    food_categories: Optional[List[str]] = Body(None, description="List of food categories to apply the discount to"), # New feature: Discount on food categories
    food_types: Optional[List[str]] = Body(None, description="List of food types to apply the discount to"), # New feature: Discount on food types
    # addon_item_name: List[str] = Body(..., description="Name of the addon item"),
    # addon_price: List[float] = Body(..., description="Price of the addon item"),
    # addon_description: Optional[List[str]] = Body(None, description="Description of the addon item"),
    addons: List[Addon] = Body(..., description="List of addon items"),
    # discount_duration: Optional[DiscountDuration] = Body(None, description="Duration of the discount (days, dates, times)"),
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    owner_id = current_user.owner_id
    coupon_id = str(ObjectId())
    # addon_data = [Addon(
    #     addon_item_name=addon_item_name,
    #     addon_price=addon_price,
    #     addon_description=addon_description,  
    # )]

    coupon_data= Coupon(
        discount_coupon_type="addon",
        owner_id=owner_id,
        discount_duration=None,
        coupon_id=coupon_id,
        addons=addons
    )

    # Fetch item_ids based on item_names
    item_ids = []
    if item_names:
        items = db.menu_items.find({"name": {"$in": item_names}, "owner_id": owner_id})
        item_ids = [str(item["_id"]) for item in items]
    if food_categories:
        items = db.menu_items.find({"category": {"$in": food_categories}, "owner_id": owner_id})
        item_ids.extend([str(item["_id"]) for item in items])
    if food_types:
        items = db.menu_items.find({"food_type": {"$in": food_types}, "owner_id": owner_id})
        item_ids.extend([str(item["_id"]) for item in items])

    # Save addon details in a separate collection
    db.coupons.insert_one(coupon_data.dict())

    db.menu_items.update_many(
        {"_id": {"$in": [ObjectId(item_id) for item_id in item_ids]}},
        {"$addToSet": {"coupon_ids": coupon_id}}
    )

    return {"message": "Addon added successfully", "addon_id": coupon_id}



@router.post("/add_discount/on_items")
async def add_discount(
    discount_value: Optional[float] = Query(None, description="Value of the discount"),
    discount_percentage: Optional[float] = Query(None, description="Percentage of the discount"),
    discount_coupon_name: Optional[str] = Query(None, description="Name of the discount coupon"),
    item_names: Optional[List[str]] = Body(None, description="List of item names to apply the discount to"),
    food_categories: Optional[List[str]] = Body(None, description="List of food categories to apply the discount to"), # New feature: Discount on food categories
    food_types: Optional[List[str]] = Body(None, description="List of food types to apply the discount to"), # New feature: Discount on food types
    discount_duration: Optional[DiscountDuration] = Body(None, description="Duration of the discount (days, dates, times)"),
    buy_x_get_y: Optional[Dict[str, Union[str, int]]] = Body(None, description="Buy X Get Y (Same Item)"),
    buy_x_get_y_diff: Optional[Dict[str, Union[List[Dict[str, Union[str, int]]], List[Dict[str, Union[str, int, float]]]]]] = Body(None, description="Buy X Get Y (Different Items)"),
    buy_x_get_percentage_off: Optional[Dict[str, Union[str, int, float]]] = Body(None, description="Buy X Get Percentage Off"),
    buy_x_get_y_at_z_price: Optional[BuyXGetYAtZPrice] = Body(None, description="Buy X and Get Different Y at Different Z Price"),
    message: Optional[str] = Body(None, description="Message to be displayed to the user"),
    loyalty_points_required: Optional[int] = Query(None, description="Loyalty points required for the discount"),
    combo_items: Optional[List[str]] = Body(None, description="List of combo items for the discount"),
    discount_type: str = Body(None, description="Type of discount coupon"),
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    if discount_value is None and discount_percentage is None and buy_x_get_y is None and buy_x_get_y_diff is None and buy_x_get_percentage_off is None and buy_x_get_y_at_z_price is None and loyalty_points_required is None and combo_items is None:
        raise HTTPException(status_code=400, detail="At least one discount type must be provided")
    if discount_value is not None and discount_percentage is not None:
        raise HTTPException(status_code=400, detail="Only one of discount_value or discount_percentage can be provided")
    if discount_percentage is not None and discount_percentage >= 100:
        raise HTTPException(status_code=400, detail="Discount percentage cannot be greater than or equal to 100")

    owner_id = current_user.owner_id
    coupon_id = str(ObjectId())

    print(f"discount_value: {discount_value}")
    print(f"discount_percentage: {discount_percentage}")
    print(f"discount_coupon_name: {discount_coupon_name}")
    print(f"item_names: {item_names}")
    print(f"discount_duration: {discount_duration}")
    print(f"buy_x_get_y: {buy_x_get_y}")
    print(f"buy_x_get_y_diff: {buy_x_get_y_diff}")
    print(f"buy_x_get_percentage_off: {buy_x_get_percentage_off}")
    print(f"buy_x_get_y_at_z_price: {buy_x_get_y_at_z_price}")
    print(f"loyalty_points_required: {loyalty_points_required}")
    print(f"combo_items: {combo_items}")

    # Fetch item_ids based on item_names
    item_ids = []
    if item_names:
        items = db.menu_items.find({"name": {"$in": item_names}, "owner_id": owner_id})
        item_ids = [str(item["_id"]) for item in items]
    if food_categories:
        items = db.menu_items.find({"category": {"$in": food_categories}, "owner_id": owner_id})
        item_ids.extend([str(item["_id"]) for item in items])
    if food_types:
        items = db.menu_items.find({"food_type": {"$in": food_types}, "owner_id": owner_id})
        item_ids.extend([str(item["_id"]) for item in items])

        # Convert dates to ISO format
    if discount_duration and discount_duration.dates:
        for date_range in discount_duration.dates:
            date_range["start_date"] = date_range["start_date"].isoformat()
            date_range["end_date"] = date_range["end_date"].isoformat()


        # Convert times to ISO format
    if discount_duration and discount_duration.times:
        for time_range in discount_duration.times:
            time_range["start_time"] = time_range["start_time"].isoformat()
            time_range["end_time"] = time_range["end_time"].isoformat()


    if buy_x_get_y_at_z_price:
        mapped_buy_items = []
        for item in buy_x_get_y_at_z_price.buy_items:
            menu_item = db.menu_items.find_one({"name": item["item_name"], "owner_id": owner_id})
            if not menu_item:
                raise HTTPException(status_code=404, detail=f"Buy item not found: {item['item_name']}")
            mapped_buy_items.append({"item_id": str(menu_item["_id"]), "quantity": item["quantity"]})

        mapped_get_items = []
        for item in buy_x_get_y_at_z_price.get_items:
            menu_item = db.menu_items.find_one({"name": item["item_name"], "owner_id": owner_id})
            if not menu_item:
                raise HTTPException(status_code=404, detail=f"Get item not found: {item['item_name']}")
            mapped_get_items.append({"item_id": str(menu_item["_id"]), "quantity": item["quantity"], "discounted_price": item["discounted_price"]})

        buy_x_get_y_at_z_price = {
            "buy_items": mapped_buy_items,
            "get_items": mapped_get_items
        }


        temp_coupon = {
            "discount_type": discount_type,
            "buy_x_get_y_at_z_price": buy_x_get_y_at_z_price
        }

        if check_duplicate_buy_get(temp_coupon, db, owner_id):
            raise HTTPException(status_code=400, detail="Duplicate coupon: The same buy item already has this get item option.")
        

        all_items = [item["item_id"] for item in mapped_buy_items]
        item_ids.extend(all_items)


    # Create coupon data
    coupon_data = Coupon(
        discount_value=discount_value,
        discount_percentage=discount_percentage,
        discount_coupon_name=discount_coupon_name,
        discount_coupon_type="on item",
        item_ids=item_ids,
        discount_duration=discount_duration,
        owner_id=owner_id,
        coupon_id=coupon_id,
        discount_type=discount_type,
        buy_x_get_y=buy_x_get_y,
        buy_x_get_y_diff=buy_x_get_y_diff,
        buy_x_get_percentage_off=buy_x_get_percentage_off,
        buy_x_get_y_at_z_price=buy_x_get_y_at_z_price,
        message=message,
        loyalty_points_required=loyalty_points_required,
        combo_items=combo_items
    )

    # Save coupon details in a separate collection
    db.coupons.insert_one(coupon_data.dict())

    # Associate coupon_id with menu_items
    db.menu_items.update_many(
        {"_id": {"$in": [ObjectId(item_id) for item_id in item_ids]}},
        {"$addToSet": {"coupon_ids": coupon_id}}   
    )

    return {"message": "Discount applied successfully"}

@router.post("/add_discount/on_bill")
async def add_discount_on_bill(
    discount_percentage: Optional[float] = Body(None, description="Percentage of the discount"),
    discount_max_value: Optional[float] = Body(None, description="Maximum value of the discount"),
    discount_value: Optional[float] = Body(None, description="Value of the discount"),
    min_bill_amount: Optional[float] = Body(None, description="Minimum bill amount for the discount"),
    discount_coupon_name: Optional[str] = Body(None, description="Name of the discount coupon"),
    discount_duration: Optional[DiscountDuration] = Body(None, description="Duration of the discount (days, dates, times)"),
    message: Optional[str] = Body(None, description="Message to be displayed to the user"),
    # New parameters
    can_apply_with_other_coupons: bool = Body(False, description="Whether this coupon can be applied with other coupons"),
    details_required: Optional[Dict[str, str]] = Body(None, description="Details required from customers when redeeming this coupon"),
    current_user: UserOutput = Depends(get_current_user),
    discount_coupon_type: str = Body(None, description="Type of discount coupon"),
    db: Database = Depends(get_db)
):
    
    print(f"discount_percentage: {discount_percentage}")
    print(f"discount_max_value: {discount_max_value}")
    print(f"discount_value: {discount_value}")
    print(f"min_bill_amount: {min_bill_amount}")
    print(f"discount_coupon_name: {discount_coupon_name}")
    print(f"discount_duration: {discount_duration}")
    print(f"message: {message}")

    print(f"can_apply_with_other_coupons: {can_apply_with_other_coupons}")
    print(f"details_required: {details_required}")

    if discount_percentage is None and discount_value is None:
        raise HTTPException(status_code=400, detail="Either discount_percentage or discount_value must be provided")
    if discount_percentage is not None and discount_percentage >= 100:
        raise HTTPException(status_code=400, detail="Discount percentage cannot be greater than or equal to 100")

    owner_id = current_user.owner_id
    coupon_id = str(ObjectId())

    # Convert dates to ISO format
    if discount_duration and discount_duration.dates:
        for date_range in discount_duration.dates:
            date_range["start_date"] = date_range["start_date"].isoformat()
            date_range["end_date"] = date_range["end_date"].isoformat()

    # Convert times to ISO format
    if discount_duration and discount_duration.times:
        for time_range in discount_duration.times:
            time_range["start_time"] = time_range["start_time"].isoformat()
            time_range["end_time"] = time_range["end_time"].isoformat()

    # Create coupon data with new fields
    coupon_data = Coupon(
        discount_percentage=discount_percentage,
        discount_max_value=discount_max_value,
        discount_value=discount_value,
        min_bill_amount=min_bill_amount,
        discount_coupon_name=discount_coupon_name,
        discount_coupon_type=discount_coupon_type,
        discount_duration=discount_duration,
        owner_id=owner_id,
        coupon_id=coupon_id,
        message=message,
        # New fields
        can_apply_with_other_coupons=can_apply_with_other_coupons,
        details_required=details_required
    )

    # Save coupon details in a separate collection
    db.coupons.insert_one(coupon_data.dict())

    return {
        "message": "Discount applied successfully",
        "coupon_id": coupon_id,
        "details_required": True if details_required else False
    }







@router.get("/coupons")
async def get_coupons(
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    owner_id = current_user.owner_id
    coupons = list(db.coupons.find({"owner_id": owner_id}))
    return {"coupons": coupons}

@router.delete("/remove_coupon/{coupon_id}")
async def remove_coupon(
    coupon_id: str,
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    owner_id = current_user.owner_id
    result = db.coupons.delete_one({"coupon_id": coupon_id, "owner_id": owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Coupon not found")

    # Remove the coupon_id from menu_items
    db.menu_items.update_many(
        {"coupon_ids": coupon_id, "owner_id": owner_id},
        {"$pull": {"coupon_ids": coupon_id}}
    )

    return {"message": "Coupon removed successfully"}

@router.delete("/remove_item_from_coupon/{coupon_id}/{item_id}")
async def remove_item_from_coupon(
    coupon_id: str,
    item_id: str,
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    owner_id = current_user.owner_id
    result = db.coupons.update_one(
        {"coupon_id": coupon_id, "owner_id": owner_id},
        {"$pull": {"item_ids": item_id}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Coupon or item not found")

    # Remove the coupon_id from the specific item in menu_items
    db.menu_items.update_one(
        {"_id": ObjectId(item_id), "coupon_ids": coupon_id, "owner_id": owner_id},
        {"$pull": {"coupon_ids": coupon_id}}
    )

    return {"message": "Item removed from coupon successfully"}

@router.get("/menu_items")
async def get_menu_items(
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    owner_id = current_user.owner_id
    menu_items = list(db.menu_items.find({"owner_id": owner_id}))
    coupons = list(db.coupons.find({"owner_id": owner_id}))

    # Calculate discounted prices dynamically
    for item in menu_items:
        original_price = item["price"]
        discounted_price = original_price
        applicable_coupon = None

        for coupon_id in item.get("coupon_ids", []):
            coupon = next((c for c in coupons if c["coupon_id"] == coupon_id), None)
            if coupon:
                if coupon["discount_value"] is not None:
                    price_after_discount = original_price - coupon["discount_value"]
                elif coupon["discount_percentage"] is not None:
                    price_after_discount = original_price * (1 - coupon["discount_percentage"] / 100)
                else:
                    price_after_discount = original_price

                if price_after_discount < discounted_price:
                    discounted_price = price_after_discount
                    applicable_coupon = coupon

        item["discounted_price"] = discounted_price
        item["applicable_coupon"] = applicable_coupon

    return {"menu_items": menu_items}




@router.get("/item/{item_name}/addons", response_model=List[Addon])
async def get_item_addons(
    item_name: str,
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    print(f"item_name for addons: {item_name}")
    item = db.menu_items.find_one({"name": item_name, "owner_id": current_user.owner_id})

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Fetch the addon coupon using the addon field in the item
    addon_coupon_path = item.get("addon")
    if not addon_coupon_path:
        print("No addon coupon found")
        return []

    # Extract the coupon_id from the addon path
    coupon_id = addon_coupon_path.split("/")[-1]
    print(f"coupon_id: {coupon_id}")
    # Fetch the addon coupon from the coupons collection
    coupon = db.coupons.find_one({"coupon_id": coupon_id, "discount_coupon_type": "addon"})
    if not coupon or "addons" not in coupon:
        return []
    
    print(f'coupon: {coupon}')
    print(f'addons: {coupon["addons"]}')

    return coupon["addons"]


class DiscountDetail(BaseModel):
    name: str
    price: float
    discounted_price: float
    food_type: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    buy_item_quantity: Optional[int] = None
    get_item_quantity: Optional[int] = None

class DiscountedItem(BaseModel):
    item_name: str
    details: List[DiscountDetail]

@router.get("/item/{item_name}/discounted_items", response_model=DiscountedItem)
async def get_discounted_prices(
    item_name: str,
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    item = db.menu_items.find_one({"name": item_name, "owner_id": current_user.owner_id})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "buy_x_get_y_at_z_price" not in item or not item["buy_x_get_y_at_z_price"]:
        return DiscountedItem(
            item_name=item_name,
            details=[]
        )

    discount_details = item["buy_x_get_y_at_z_price"]
    print(f"Discount details: {discount_details}")  # Add this line to print the discount_details
    details = []

    for detail in discount_details.values():
        item_path = detail["item_path"]
        item_id = item_path.split("/")[-1]
        related_item = db.menu_items.find_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id})
        if not related_item:
            continue

        details.append(
            DiscountDetail(
                name=related_item["name"],
                price=related_item["price"],
                discounted_price=detail["discounted_price"],
                food_type=related_item["food_type"],
                image_url=related_item.get("image_url"),
                description=related_item.get("description"),
                buy_item_quantity=detail.get("buy_quantity"),
                get_item_quantity=detail.get("get_quantity")
            )
        )
    return DiscountedItem(
        item_name=item_name,
        details=details
    )
























from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class SizeOption(BaseModel):
    name: str
    price_increment: float
    is_default: bool = False

class AddSizeRequest(BaseModel):
    sizes: List[SizeOption]
    item_names: Optional[List[str]] = None
    food_categories: Optional[List[str]] = None 
    food_types: Optional[List[str]] = None


@router.post("/menu/sizes/add")
async def add_sizes(
    request: AddSizeRequest,
    current_user: UserOutput = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Add size options to multiple items based on criteria"""
    owner_id = current_user.owner_id
    
    # Validate at least one target specified
    if not any([request.item_names, request.food_categories, request.food_types]):
        raise HTTPException(
            status_code=400,
            detail="Specify at least one target: item_names, food_categories, or food_types"
        )

    # Ensure exactly one default size
    default_sizes = [size for size in request.sizes if size.is_default]
    if len(default_sizes) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one size must be marked as default"
        )

    # Build query to find affected items
    query = {"owner_id": owner_id}
    
    # Combine all criteria with OR
    criteria = []
    if request.item_names:
        criteria.append({"name": {"$in": request.item_names}})
    if request.food_categories:
        criteria.append({"category": {"$in": request.food_categories}})
    if request.food_types:
        criteria.append({"food_type": {"$in": request.food_types}})
    
    if criteria:
        query["$or"] = criteria

    # Update all matching items with size options
    result = db.menu_items.update_many(
        query,
        {"$set": {"sizes": [size.dict() for size in request.sizes]}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No matching items found"
        )

    return {
        "message": "Size options added successfully",
        "items_updated": result.modified_count
    }









































# Helper function to generate random discount value
def generate_random_discount(
    min_value: Optional[float] = None, 
    max_value: Optional[float] = None, 
    weighted_probability: bool = False,
    discrete_values: Optional[List[float]] = None
) -> float:
    """
    Generate a random discount value based on parameters.
    
    Args:
        min_value: Minimum discount value/percentage (used with max_value)
        max_value: Maximum discount value/percentage (used with min_value)
        weighted_probability: If True, values closer to min have higher probability
        discrete_values: List of specific values to choose from (alternative to min/max)
        
    Returns:
        A randomly selected discount value
    """
    if discrete_values:
        if weighted_probability:
            # Create weights inversely proportional to value
            # Higher values get lower weights (lower probability)
            weights = [(max(discrete_values) - value + min(discrete_values)) for value in discrete_values]
            # Normalize weights
            weights = [w/sum(weights) for w in weights]
            return float(np.random.choice(discrete_values, p=weights))
        else:
            return float(random.choice(discrete_values))
    else:
        if weighted_probability:
            # Use exponential distribution skewed toward minimum
            # Scale parameter controls the distribution shape
            scale = (max_value - min_value) / 3
            # Generate a random value and clip it to our range
            rand_val = min_value + random.expovariate(1/scale)
            return float(min(rand_val, max_value))
        else:
            return float(random.uniform(min_value, max_value))

@router.post("/create_random_bill_discount")
async def create_random_bill_discount(
    discount_type: str = Body(..., description="PERCENTAGE or AMOUNT"),
    min_value: Optional[float] = Body(None, description="Minimum discount value/percentage"),
    max_value: Optional[float] = Body(None, description="Maximum discount value/percentage"),
    min_bill_amount: float = Body(0, description="Minimum bill amount required"),
    discrete_values: Optional[List[float]] = Body(None, description="List of specific values to choose from"),
    weighted_probability: bool = Body(False, description="Whether to weight probability toward minimum values"),
    discount_duration: dict = Body(..., description="Discount duration parameters"),
    message: str = Body("", description="Discount message"),
    token: str = Body(...),
    db: Database = Depends(get_db)
):
    """Create a randomly generated bill discount."""
    try:
        # Verify user is authorized
        current_user = get_current_user(db, token)
        
        owner_id = current_user.owner_id
        
        # Validate inputs - ensure user provided either min/max OR discrete values but not both
        if (min_value is not None and max_value is not None) and discrete_values:
            raise HTTPException(
                status_code=400, 
                detail="Please provide either min/max value range OR discrete values, not both"
            )
            
        if (min_value is None or max_value is None) and not discrete_values:
            raise HTTPException(
                status_code=400, 
                detail="Please provide either min/max value range OR discrete values"
            )
            
        # Validate min/max if provided
        if min_value is not None and max_value is not None and min_value > max_value:
            raise HTTPException(
                status_code=400, 
                detail="Minimum value cannot be greater than maximum value"
            )
            
        # Generate random discount value
        discount_value = generate_random_discount(
            min_value=min_value,
            max_value=max_value,
            weighted_probability=weighted_probability,
            discrete_values=discrete_values
        )
        
        # Create coupon data
        coupon_data = {
            "owner_id": owner_id,
            "discount_coupon_type": "BILL",
            "discount_type": discount_type,
            "min_bill_amount": min_bill_amount,
            "discount_duration": discount_duration,
            "message": message,
            "discount_coupon_name": f"Random {discount_type.lower()} discount",
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "details_required": {}
        }
        
        # Set either discount_value or discount_percentage based on type
        if discount_type == "PERCENTAGE":
            coupon_data["discount_percentage"] = round(discount_value, 2)
            # Add max value cap for percentage discounts
            coupon_data["discount_max_value"] = 0  # No limit by default
        else:  # AMOUNT
            coupon_data["discount_value"] = round(discount_value, 2)
        
        # Insert into database
        result = db.coupons.insert_one(coupon_data)
        
        return {
            "id": str(result.inserted_id),
            "message": f"Random bill discount created with {discount_type.lower()}: {round(discount_value, 2)}",
            "generated_value": round(discount_value, 2),
            "coupon_data": {**coupon_data, "_id": str(result.inserted_id)}
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

















