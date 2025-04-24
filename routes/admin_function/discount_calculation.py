# from fastapi import APIRouter
# from pymongo import MongoClient, UpdateOne
# from pymongo.server_api import ServerApi
# from celery import Celery
# from datetime import datetime, timedelta
# import logging
# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Initialize FastAPI app
# router = APIRouter()

# # MongoDB setup
# client = MongoClient(os.getenv('MONGO_URI'), server_api=ServerApi('1'))
# db = client["wookraft_db"]
# coupon_collection = db["coupons"]
# menu_collection = db["menu_items"]

# # Celery setup
# celery_app = Celery(
#     "discount_tasks",
#     broker="redis://localhost:6379/0",
#     backend="redis://localhost:6379/0"
# )

# # Celery configuration
# celery_app.conf.update(
#     task_serializer='json',
#     accept_content=['json'],
#     result_serializer='json',
#     timezone='UTC',
#     enable_utc=True,
#     task_track_started=True,
#     task_time_limit=30 * 60,  # 30 minutes
#     worker_max_tasks_per_child=200,
#     broker_connection_retry_on_startup=True
# )

# # Logging setup
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def is_day_valid(coupon, now):
#     """Check if the coupon is valid based on the day."""
#     try:
#         days = coupon.get("discount_duration", {}).get("days", [])
#         logger.info(f"Checking day validity for coupon {coupon['coupon_id']}: {days}")
#         return now.strftime("%A").lower() in [day.lower() for day in days]
#     except Exception as e:
#         logger.error(f"Error in day validation: {e}")
#         return False

# def is_time_valid(coupon, now):
#     """Check if the coupon is valid based on the time range."""
#     try:
#         times = coupon.get("discount_duration", {}).get("times", [])
#         logger.info(f"Checking time validity for coupon {coupon['coupon_id']}: {times}")
#         for time_range in times:
#             start = datetime.strptime(time_range["start_time"], "%H:%M").time()
#             end = datetime.strptime(time_range["end_time"], "%H:%M").time()
#             if start <= now.time() <= end:
#                 return True
#         return False
#     except Exception as e:
#         logger.error(f"Error in time validation: {e}")
#         return False

# def is_date_valid(coupon, now):
#     """Check if the coupon is valid based on the date."""
#     try:
#         dates = coupon.get("discount_duration", {}).get("dates", [])
#         logger.info(f"Checking date validity for coupon {coupon['coupon_id']}: {dates}")
#         for date_range in dates:
#             start_date = datetime.strptime(date_range["start_date"], "%Y-%m-%d").date()
#             end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d").date()
#             if start_date <= now.date() <= end_date:
#                 return True
#         return False
#     except Exception as e:
#         logger.error(f"Error in date validation: {e}")
#         return False

# def is_coupon_valid(coupon, now):
#     """Check if a coupon is valid at the given datetime."""
#     try:
#         logger.info(f"Validating coupon {coupon["discount_coupon_type"]}")
#         if coupon["discount_coupon_type"] != "on item":
#             logger.info(f"Coupon {coupon['coupon_id']} is not of type 'on_item'")
#             return False
#         if coupon["discount_type"] not in ["value", "percentage"]:
#             logger.info(f"Coupon {coupon['coupon_id']} has invalid discount type {coupon['discount_type']}")
#             return False
#         if not coupon.get("discount_duration"):
#             logger.info(f"Coupon {coupon['coupon_id']} has no discount duration, considered always valid")
#             return True
#         return any([
#             is_day_valid(coupon, now),
#             is_time_valid(coupon, now),
#             is_date_valid(coupon, now)
#         ])
#     except Exception as e:
#         logger.error(f"Error in coupon validation: {e}")
#         return False

# @celery_app.task(
#     name="update_discounted_prices",
#     bind=False,
#     max_retries=3,
#     default_retry_delay=60
# )
# @celery_app.task(name="update_discounted_prices")
# def update_discounted_prices():
#     try:
#         now = datetime.now()
#         menu_items = list(menu_collection.find())
#         bulk_updates = []
#         logger.info("Running update_discounted_prices task")

#         # Get all coupon IDs
#         coupon_ids = set()
#         for item in menu_items:
#             if "coupon_ids" in item:
#                 coupon_ids.update(item["coupon_ids"])
#                 logger.info(f"Found coupon_ids in item: {item['coupon_ids']}")

#         # Fetch coupons using coupon_id field
#         coupons = list(coupon_collection.find({"coupon_id": {"$in": list(coupon_ids)}}))
#         # Create dictionary with coupon_id as key
#         coupon_dict = {coupon["coupon_id"]: coupon for coupon in coupons}
#         logger.info(f"Found coupons: {coupon_dict}")

#         # Process menu items
#         for item in menu_items:
#             try:
#                 valid_coupon_found = False
#                 max_discount = 0
                
#                 if "coupon_ids" in item:
#                     for coupon_id in item["coupon_ids"]:
#                         logger.info(f"Looking for coupon_id: {coupon_id}")
#                         coupon = coupon_dict.get(coupon_id)  # Direct lookup by coupon_id
                        
#                         if coupon and is_coupon_valid(coupon, now):
#                             valid_coupon_found = True
#                             if coupon["discount_type"] == "value":
#                                 discount = coupon["discount_value"]
#                             else:  # percentage
#                                 discount = item["price"] * (coupon["discount_percentage"] / 100)
#                             max_discount = max(max_discount, discount)
#                             logger.info(f"Applied discount: {discount}")

#                 new_price = item["price"] - max_discount if valid_coupon_found else item["price"]
#                 logger.info(f"Item {item['name']}: Original={item['price']}, Discount={max_discount}, New={new_price}")
#                 bulk_updates.append(
#                     UpdateOne(
#                         {"_id": item["_id"]}, 
#                         {"$set": {"discounted_price": new_price}}
#                     )
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing item: {str(e)}")
#                 continue

#         if bulk_updates:
#             result = menu_collection.bulk_write(bulk_updates)
#             logger.info(f"Updated {result.modified_count} items")

#         return {"status": "success", "items_updated": len(bulk_updates)}

#     except Exception as e:
#         logger.error(f"Task failed: {str(e)}")
#         raise


# def schedule_coupon_tasks():
#     """Schedules Celery tasks to trigger discount updates."""
#     try:
#         logger.info("Scheduling discount update tasks...")
#         now = datetime.now()
        
#         # Schedule immediate update
#         update_discounted_prices.delay()
        
#         # Schedule future updates based on coupons
#         for coupon in coupon_collection.find():
#             if "discount_duration" in coupon:
#                 for duration in coupon["discount_duration"]:
#                     if isinstance(duration, dict):
#                         start = duration.get("start")
#                         end = duration.get("end")
                        
#                         if start and end:
#                             start_time = datetime.strptime(start, "%H:%M").time()
#                             end_time = datetime.strptime(end, "%H:%M").time()
                            
#                             today = now.date()
#                             start_dt = datetime.combine(today, start_time)
#                             end_dt = datetime.combine(today, end_time)
                            
#                             if now < start_dt:
#                                 update_discounted_prices.apply_async(eta=start_dt)
#                             if now < end_dt:
#                                 update_discounted_prices.apply_async(eta=end_dt)
        
#         logger.info("Discount update tasks scheduled successfully")
#     except Exception as e:
#         logger.error(f"Error scheduling tasks: {e}")
#         raise

# @router.on_event("startup")
# async def startup_event():
#     """Startup event handler."""
#     logger.info("Starting discount calculation service...")
#     try:
#         schedule_coupon_tasks()
#     except Exception as e:
#         logger.error(f"Startup failed: {e}")
#         raise

# @router.get("/trigger_discount_update")
# async def trigger_update():
#     """Manually trigger discount update."""
#     try:
#         task = update_discounted_prices.delay()
#         return {
#             "status": "success",
#             "message": "Discount update triggered",
#             "task_id": task.id
#         }
#     except Exception as e:
#         logger.error(f"Failed to trigger update: {e}")
#         return {
#             "status": "error",
#             "message": str(e)
#         }

# # Celery beat schedule for periodic tasks
# celery_app.conf.beat_schedule = {
#     'update-discounts-daily': {
#         'task': 'update_discounted_prices',
#         'schedule': timedelta(days=1),
#         'options': {'expires': 3600}
#     },
# }















































































import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any
from bson import ObjectId
from pymongo import MongoClient, UpdateOne
from pymongo.server_api import ServerApi
from celery import Celery
from fastapi import APIRouter
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

# MongoDB setup
client = MongoClient(os.getenv('MONGO_URI'), server_api=ServerApi('1'))
db = client["wookraft_db"]
coupon_collection = db["coupons"]
menu_collection = db["menu_items"]

# Celery setup
# celery_app = Celery(
#     "discount_tasks",
#     broker="redis://localhost:6379/0",
#     backend="redis://localhost:6379/0"
# )

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery setup
celery_app = Celery(
    "discount_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)


# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True
)

def get_discount_priority(discount_type: str) -> int:
    """Define priority order for discount types"""
    priorities = {
        "buy_x_get_y": 3,
        "percentage": 1,
        "value": 1
    }
    return priorities.get(discount_type, 0)

def is_day_valid(coupon: Dict[str, Any], now: datetime) -> bool:
    """Check if coupon is valid for current day"""
    try:
        if not coupon.get("discount_duration", {}).get("days"):
            return True
        return now.strftime("%A").lower() in [
            day.lower() for day in coupon["discount_duration"]["days"]
        ]
    except Exception as e:
        logger.error(f"Error in day validation: {e}")
        return False

def is_time_valid(coupon: Dict[str, Any], now: datetime) -> bool:
    """Check if coupon is valid for current time"""
    try:
        times = coupon.get("discount_duration", {}).get("times", [])
        if not times:
            return True
            
        current_time = now.time()
        for time_range in times:
            start_time = datetime.strptime(time_range["start_time"], "%H:%M:%S").time()
            end_time = datetime.strptime(time_range["end_time"], "%H:%M:%S").time()
            if start_time <= current_time <= end_time:
                return True
        return False
    except Exception as e:
        logger.error(f"Error in time validation: {e}")
        return False

def is_date_valid(coupon: Dict[str, Any], now: datetime) -> bool:
    """Check if coupon is valid for current date"""
    try:
        dates = coupon.get("discount_duration", {}).get("dates", [])
        if not dates:
            return True
            
        current_date = now.date()
        for date_range in dates:
            start_date = datetime.strptime(date_range["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d").date()
            if start_date <= current_date <= end_date:
                return True
        return False
    except Exception as e:
        logger.error(f"Error in date validation: {e}")
        return False

def is_coupon_valid(coupon: Dict[str, Any], now: datetime) -> bool:
    """Check if coupon is valid"""
    try:
        if coupon["discount_coupon_type"] == "addon":
            return True  # Addons are always valid as they don't have a duration field
        
        if coupon["discount_coupon_type"] != "on item":
            return False
            
        if not coupon.get("discount_duration"):
            return True
            
        return any([
            is_day_valid(coupon, now),
            is_time_valid(coupon, now),
            is_date_valid(coupon, now)
        ])
    except Exception as e:
        logger.error(f"Error in coupon validation: {e}")
        return False




# @celery_app.task(name="update_discounted_prices")
# def update_discounted_prices():
#     """Update menu items with current valid discounts"""
#     try:
#         now = datetime.now()
#         menu_items = list(menu_collection.find())
#         bulk_updates = []

#         for item in menu_items:
#             try:
#                 if "coupon_ids" not in item:
#                     continue

#                 valid_discounts = []
#                 for coupon_id in item["coupon_ids"]:
#                     coupon = coupon_collection.find_one({"coupon_id": coupon_id})
#                     if coupon and is_coupon_valid(coupon, now):
#                         discount_info = {
#                             "type": coupon["discount_type"],
#                             "priority": get_discount_priority(coupon["discount_type"]),
#                         }
                        
#                         # Add specific discount details
#                         if coupon["discount_type"] == "buy_x_get_y" and coupon.get("buy_x_get_y"):
#                             discount_info["buy_quantity"] = int(coupon["buy_x_get_y"]["buy_quantity"])
#                             discount_info["get_quantity"] = int(coupon["buy_x_get_y"]["get_quantity"])
#                         elif coupon["discount_type"] == "value":
#                             discount_info["value"] = coupon["discount_value"]
#                         elif coupon["discount_type"] == "percentage":
#                             discount_info["percentage"] = coupon["discount_percentage"]
#                         elif coupon["discount_type"] == "buy_x_get_y_at_z_price" and coupon.get("buy_x_get_y_at_z_price"):
#                             discount_info["buy_x_get_y_at_z_price"] = coupon["buy_x_get_y_at_z_price"]
#                             discount_info["get_items"] = [
#                                 {
#                                     "item_id": get_item["item_id"],
#                                     "quantity": get_item["quantity"],
#                                     "discounted_price": get_item["discounted_price"]
#                                 }
#                                 for get_item in coupon["buy_x_get_y_at_z_price"]["get_items"]
#                             ]
                            
#                         valid_discounts.append(discount_info)

#                 update_data = {}
#                 if valid_discounts:
#                     best_discount = max(valid_discounts, key=lambda x: x["priority"])
#                     update_data["discount_type"] = best_discount["type"]
#                     update_data["discount_rules"] = best_discount

#                     # Calculate discounted_price only for value/percentage
#                     if best_discount["type"] in ["value", "percentage"]:
#                         if best_discount["type"] == "value":
#                             discounted_price = item["price"] - best_discount["value"]
#                         else:
#                             discounted_price = item["price"] * (1 - best_discount["percentage"]/100)
#                         update_data["discounted_price"] = max(0, discounted_price)
#                     else:
#                         update_data["discounted_price"] = item["price"]

#             # Check for buy_x_get_y_at_z_price and add it to the list
#                     buy_x_get_y_at_z_discount = next((d for d in valid_discounts if d["type"] == "buy_x_get_y_at_z_price"), None)
#                     if buy_x_get_y_at_z_discount:
#                             update_data["discount_type"].append(buy_x_get_y_at_z_discount["type"])
#                             update_data["discount_rules"].append(buy_x_get_y_at_z_discount)

#                                                     # Store get_item details in menu_item
#                             buy_x_get_y_at_z_details = []
#                             for get_item in buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]["get_items"]:
#                                 menu_item = menu_collection.find_one({"_id": ObjectId(get_item["item_id"]), "owner_id": item["owner_id"]})
#                                 if menu_item:
#                                     buy_x_get_y_at_z_details.append({
#                                         "name": menu_item["name"],
#                                         "original_price": menu_item["price"],
#                                         "discounted_price": get_item["discounted_price"]
#                                     })
#                             update_data["buy_x_get_y_at_z_details"] = buy_x_get_y_at_z_details

#                 else:
#                     update_data = {
#                         "discount_type": [],
#                         "discount_rules": [],
#                         "discounted_price": item["price"]
#                     }

#                 bulk_updates.append(
#                     UpdateOne(
#                         {"_id": item["_id"]},
#                         {"$set": update_data}
#                     )
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing item {item.get('name', '')}: {e}")
#                 continue

#         if bulk_updates:
#             result = menu_collection.bulk_write(bulk_updates)
#             logger.info(f"Updated {result.modified_count} items")

#         return {"status": "success", "items_updated": len(bulk_updates)}

#     except Exception as e:
#         logger.error(f"Task failed: {e}")
#         raise

# @celery_app.task(name="update_discounted_prices")
# def update_discounted_prices():
#     """Update menu items with current valid discounts"""
#     try:
#         now = datetime.now()
#         menu_items = list(menu_collection.find())
#         bulk_updates = []

#         for item in menu_items:
#             try:
#                 if "coupon_ids" not in item:
#                     continue

#                 valid_discounts = []
#                 for coupon_id in item["coupon_ids"]:
#                     coupon = coupon_collection.find_one({"coupon_id": coupon_id})
#                     if coupon and is_coupon_valid(coupon, now):
#                         discount_info = {
#                             "type": coupon["discount_type"],
#                             "priority": get_discount_priority(coupon["discount_type"]),
#                         }
                        
#                         # Add specific discount details
#                         if coupon["discount_type"] == "buy_x_get_y" and coupon.get("buy_x_get_y"):
#                             discount_info["buy_quantity"] = int(coupon["buy_x_get_y"]["buy_quantity"])
#                             discount_info["get_quantity"] = int(coupon["buy_x_get_y"]["get_quantity"])
#                         elif coupon["discount_type"] == "value":
#                             discount_info["value"] = coupon["discount_value"]
#                         elif coupon["discount_type"] == "percentage":
#                             discount_info["percentage"] = coupon["discount_percentage"]
#                         elif coupon["discount_type"] == "buy_x_get_y_at_z_price" and coupon.get("buy_x_get_y_at_z_price"):
#                             discount_info["buy_x_get_y_at_z_price"] = coupon["buy_x_get_y_at_z_price"]
#                             discount_info["get_items"] = [
#                                 {
#                                     "item_id": get_item["item_id"],
#                                     "quantity": get_item["quantity"],
#                                     "discounted_price": get_item["discounted_price"]
#                                 }
#                                 for get_item in coupon["buy_x_get_y_at_z_price"]["get_items"]
#                             ]
                        
#                         valid_discounts.append(discount_info)

#                 update_data = {}
#                 if valid_discounts:
#                     best_discount = max(valid_discounts, key=lambda x: x["priority"])
#                     update_data["discount_type"] = [best_discount["type"]]
#                     update_data["discount_rules"] = [best_discount]

#                     # Calculate discounted_price only for value/percentage
#                     if best_discount["type"] in ["value", "percentage"]:
#                         if best_discount["type"] == "value":
#                             discounted_price = item["price"] - best_discount["value"]
#                         else:
#                             discounted_price = item["price"] * (1 - best_discount["percentage"]/100)
#                         update_data["discounted_price"] = max(0, discounted_price)
#                     else:
#                         update_data["discounted_price"] = item["price"]

#                     # Check for buy_x_get_y_at_z_price and add it to the list
#                     buy_x_get_y_at_z_discount = next((d for d in valid_discounts if d["type"] == "buy_x_get_y_at_z_price"), None)
#                     if buy_x_get_y_at_z_discount:
#                         update_data["discount_type"].append(buy_x_get_y_at_z_discount["type"])
#                         update_data["discount_rules"].append(buy_x_get_y_at_z_discount)

#                         # Store get_item details in menu_item
#                         buy_x_get_y_at_z_details = []
#                         for get_item in buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]["get_items"]:
#                             menu_item = menu_collection.find_one({"_id": ObjectId(get_item["item_id"]), "owner_id": item["owner_id"]})
#                             if menu_item:
#                                 buy_x_get_y_at_z_details.append({
#                                     "name": menu_item["name"],
#                                     "original_price": menu_item["price"],
#                                     "discounted_price": get_item["discounted_price"]
#                                 })
#                             update_data["buy_x_get_y_at_z_price"] = buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]
#                             update_data["buy_x_get_y_at_z_price"]["details"] = buy_x_get_y_at_z_details
#                     else:
#                         # Remove the buy_x_get_y_at_z_price field if no valid discounts
#                         update_data["$unset"] = {
#                             "buy_x_get_y_at_z_price": ""
#                         }

#                 else:
#                     update_data = {
#                         "discounted_price": item["price"]
#                     }
#                     # Remove the buy_x_get_y_at_z_price, discount_rules, and discount_type fields if no valid discounts
#                     update_data["$unset"] = {
#                         "buy_x_get_y_at_z_price": "",
#                         "discount_rules": "",
#                         "discount_type": ""
#                     }

#                 bulk_updates.append(
#                     UpdateOne(
#                         {"_id": item["_id"]},
#                         {"$set": update_data}
#                     )
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing item {item.get('name', '')}: {e}")
#                 continue

#         if bulk_updates:
#             result = menu_collection.bulk_write(bulk_updates)
#             logger.info(f"Updated {result.modified_count} items")

#         return {"status": "success", "items_updated": len(bulk_updates)}

#     except Exception as e:
#         logger.error(f"Task failed: {e}")
#         raise













# @celery_app.task(name="update_discounted_prices")
# def update_discounted_prices():
#     """Update menu items with current valid discounts"""
#     try:
#         now = datetime.now()
#         menu_items = list(menu_collection.find())
#         bulk_updates = []

#         for item in menu_items:
#             try:
#                 if "coupon_ids" not in item:
#                     continue

#                 valid_discounts = []
#                 for coupon_id in item["coupon_ids"]:
#                     coupon = coupon_collection.find_one({"coupon_id": coupon_id})
#                     if coupon and is_coupon_valid(coupon, now):
#                         discount_info = {
#                             "type": coupon["discount_type"],
#                             "priority": get_discount_priority(coupon["discount_type"]),
#                         }
                        
#                         # Add specific discount details
#                         if coupon["discount_type"] == "buy_x_get_y" and coupon.get("buy_x_get_y"):
#                             discount_info["buy_quantity"] = int(coupon["buy_x_get_y"]["buy_quantity"])
#                             discount_info["get_quantity"] = int(coupon["buy_x_get_y"]["get_quantity"])
#                         elif coupon["discount_type"] == "value":
#                             discount_info["value"] = coupon["discount_value"]
#                         elif coupon["discount_type"] == "percentage":
#                             discount_info["percentage"] = coupon["discount_percentage"]
#                         elif coupon["discount_type"] == "buy_x_get_y_at_z_price" and coupon.get("buy_x_get_y_at_z_price"):
#                             discount_info["buy_x_get_y_at_z_price"] = coupon["buy_x_get_y_at_z_price"]
#                             discount_info["get_items"] = [
#                                 {
#                                     "item_id": get_item["item_id"],
#                                     "quantity": get_item["quantity"],
#                                     "discounted_price": get_item["discounted_price"]
#                                 }
#                                 for get_item in coupon["buy_x_get_y_at_z_price"]["get_items"]
#                             ]
                        
#                         valid_discounts.append(discount_info)

#                 update_data = {}
#                 unset_data = {}
#                 if valid_discounts:
#                     best_discount = max(valid_discounts, key=lambda x: x["priority"])
#                     update_data["discount_type"] = [best_discount["type"]]
#                     update_data["discount_rules"] = [best_discount]

#                     # Calculate discounted_price only for value/percentage
#                     if best_discount["type"] in ["value", "percentage"]:
#                         if best_discount["type"] == "value":
#                             discounted_price = item["price"] - best_discount["value"]
#                         else:
#                             discounted_price = item["price"] * (1 - best_discount["percentage"]/100)
#                         update_data["discounted_price"] = max(0, discounted_price)
#                     else:
#                         update_data["discounted_price"] = item["price"]

#                     # Check for buy_x_get_y_at_z_price and store only details
#                     buy_x_get_y_at_z_discount = next((d for d in valid_discounts if d["type"] == "buy_x_get_y_at_z_price"), None)
#                     if buy_x_get_y_at_z_discount:
#                         # Store get_item details in buy_x_get_y_at_z_price
#                         buy_x_get_y_at_z_details = []
#                         for get_item in buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]["get_items"]:
#                             menu_item = menu_collection.find_one({"_id": ObjectId(get_item["item_id"]), "owner_id": item["owner_id"]})
#                             if menu_item:
#                                 buy_x_get_y_at_z_details.append({
#                                     "name": menu_item["name"],
#                                     "original_price": menu_item["price"],
#                                     "discounted_price": get_item["discounted_price"]
#                                 })
#                         update_data["buy_x_get_y_at_z_price"] = {"details": buy_x_get_y_at_z_details}

#                     else:
#                         # Remove the buy_x_get_y_at_z_price field if no valid discounts
#                         unset_data["buy_x_get_y_at_z_price"] = ""

#                 else:
#                     update_data = {
#                         "discounted_price": item["price"]
#                     }
#                     # Remove the buy_x_get_y_at_z_price, discount_rules, and discount_type fields if no valid discounts
#                     unset_data["buy_x_get_y_at_z_price"] = ""
#                     unset_data["discount_rules"] = ""
#                     unset_data["discount_type"] = ""

#                                     # Check if the discount_coupon_type is addon and store its path in menu_item
#                 if best_discount["type"] == "addon":
#                         update_data["addon"] = f"/coupons/{coupon_id}"

#                 else:
#                     # Remove the addon field if the discount coupon type is not addon
#                     if "$unset" not in update_data:
#                          unset_data["addon"] = ""

#                 bulk_updates.append(
#                     UpdateOne(
#                         {"_id": item["_id"]},
#                         {"$set": update_data, "$unset":unset_data }
#                     )
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing item {item.get('name', '')}: {e}")
#                 continue

#         if bulk_updates:
#             result = menu_collection.bulk_write(bulk_updates)
#             logger.info(f"Updated {result.modified_count} items")

#         return {"status": "success", "items_updated": len(bulk_updates)}

#     except Exception as e:
#         logger.error(f"Task failed: {e}")
#         raise












# @celery_app.task(name="update_discounted_prices")
# def update_discounted_prices():
#     """Update menu items with current valid discounts"""
#     try:
#         now = datetime.now()
#         menu_items = list(menu_collection.find())
#         bulk_updates = []
#         # buy_x_get_y_at_z_buy_quantity=[]

#         for item in menu_items:
#             try:
#                 if "coupon_ids" not in item:
#                     continue

#                 valid_discounts = []
#                 addon_coupon_id = None
#                 for coupon_id in item["coupon_ids"]:
#                     coupon = coupon_collection.find_one({"coupon_id": coupon_id})
#                     if coupon and is_coupon_valid(coupon, now):
#                         if coupon["discount_coupon_type"] == "addon":
#                             addon_coupon_id = coupon_id
#                             logger.info(f"Addon coupon {coupon_id} found for item")
#                         else:
#                             discount_info = {
#                                 "type": coupon["discount_type"],
#                                 "priority": get_discount_priority(coupon["discount_type"]),
#                             }
                            
#                             # Add specific discount details
#                             if coupon["discount_type"] == "buy_x_get_y" and coupon.get("buy_x_get_y"):
#                                 discount_info["buy_quantity"] = int(coupon["buy_x_get_y"]["buy_quantity"])
#                                 discount_info["get_quantity"] = int(coupon["buy_x_get_y"]["get_quantity"])
#                             elif coupon["discount_type"] == "value":
#                                 discount_info["value"] = coupon["discount_value"]
#                             elif coupon["discount_type"] == "percentage":
#                                 discount_info["percentage"] = coupon["discount_percentage"]
#                             elif coupon["discount_type"] == "buy_x_get_y_at_z_price" and coupon.get("buy_x_get_y_at_z_price"):
#                                 discount_info["buy_x_get_y_at_z_price"] = coupon["buy_x_get_y_at_z_price"]
#                                 discount_info["get_items"] = [
#                                     {
#                                         "item_id": get_item["item_id"],
#                                         "quantity": get_item["quantity"],
#                                         "discounted_price": get_item["discounted_price"]
            
#                                     }
#                                     for get_item in coupon["buy_x_get_y_at_z_price"]["get_items"]
#                                 ]
#                                 for buy_item in coupon["buy_x_get_y_at_z_price"]["buy_items"]:
#                                     print("456 checking")
#                                     print('buy_item',buy_item)
#                                     print('buy_item["item_id"]',buy_item["item_id"])
                                   
#                                     if buy_item["item_id"] == str(item["_id"]):
#                                         print("123for chrcking")
#                                         print(f'buy_x_get_y_at_z_buy_quantity: {buy_item["quantity"]}')
#                                         # buy_x_get_y_at_z_buy_quantity = buy_item["quantity"]
#                                         buy_x_get_y_at_z_buy_quantity=buy_item['quantity']            
                                        

                            
#                             valid_discounts.append(discount_info)

#                 update_data = {}
#                 unset_data = {}
#                 if valid_discounts:
#                     best_discount = max(valid_discounts, key=lambda x: x["priority"])
#                     update_data["discount_type"] = [best_discount["type"]]
#                     update_data["discount_rules"] = [best_discount]

#                     # Calculate discounted_price only for value/percentage
#                     if best_discount["type"] in ["value", "percentage"]:
#                         if best_discount["type"] == "value":
#                             discounted_price = item["price"] - best_discount["value"]
#                         else:
#                             discounted_price = item["price"] * (1 - best_discount["percentage"]/100)
#                         update_data["discounted_price"] = max(0, discounted_price)
#                     else:
#                         update_data["discounted_price"] = item["price"]

#                     # Check for buy_x_get_y_at_z_price and store only details
#                     # buy_x_get_y_at_z_discount = next((d for d in valid_discounts if d["type"] == "buy_x_get_y_at_z_price"), None)
#                     # if buy_x_get_y_at_z_discount:
#                     #     # Store get_item details in buy_x_get_y_at_z_price
#                     #     buy_x_get_y_at_z_details = {}
#                     #     for get_item in buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]["get_items"]:
#                     #         menu_item = menu_collection.find_one({"_id": ObjectId(get_item["item_id"]), "owner_id": item["owner_id"]})
#                     #         # if menu_item:
#                     #         #     buy_x_get_y_at_z_details.append({
#                     #         #         "item_path": f"/menu/items/{get_item['item_id']}",
#                     #         #         "original_price": menu_item["price"],
#                     #         #         "discounted_price": get_item["discounted_price"],
#                     #         #         "get_quantity": get_item["quantity"],
#                     #         #         "buy_quantity": buy_x_get_y_at_z_buy_quantity
#                     #         #     })
#                     #     if menu_item:
#                     #         detail = {
#                     #             "item_path": f"/menu/items/{get_item['item_id']}",
#                     #             "original_price": menu_item["price"],
#                     #             "discounted_price": get_item["discounted_price"],
#                     #             "get_quantity": get_item["quantity"],
#                     #             "buy_quantity": buy_x_get_y_at_z_buy_quantity
#                     #         }
#                     #         buy_x_get_y_at_z_details[menu_item["name"]] = detail
#                     #     update_data["buy_x_get_y_at_z_price"] = buy_x_get_y_at_z_details

#                     # else:
#                     #     # Remove the buy_x_get_y_at_z_price field if no valid discounts
#                     #     unset_data["buy_x_get_y_at_z_price"] = ""










#                                         # Check for buy_x_get_y_at_z_price and store only details
#                     buy_x_get_y_at_z_discount = next((d for d in valid_discounts if d["type"] == "buy_x_get_y_at_z_price"), None)
#                     if buy_x_get_y_at_z_discount:
#                         # Store get_item details in buy_x_get_y_at_z_price
#                         buy_x_get_y_at_z_details = {}
#                         for get_item in buy_x_get_y_at_z_discount["buy_x_get_y_at_z_price"]["get_items"]:
#                             menu_item = menu_collection.find_one({
#                                 "_id": ObjectId(get_item["item_id"]),
#                                 "owner_id": item["owner_id"]
#                             })
#                             if menu_item:
#                                 detail = {
#                                     "item_path": f"/menu/items/{get_item['item_id']}",
#                                     "original_price": menu_item["price"],
#                                     "discounted_price": get_item["discounted_price"],
#                                     "get_quantity": get_item["quantity"],
#                                     "buy_quantity": buy_x_get_y_at_z_buy_quantity
#                                 }
#                                 buy_x_get_y_at_z_details[menu_item["name"]] = detail
#                         update_data["buy_x_get_y_at_z_price"] = buy_x_get_y_at_z_details
#                     else:
#                         # Remove the buy_x_get_y_at_z_price field if no valid discounts
#                         unset_data["buy_x_get_y_at_z_price"] = ""

#                 else:
#                     update_data = {
#                         "discounted_price": item["price"]
#                     }
#                     # Remove the buy_x_get_y_at_z_price, discount_rules, and discount_type fields if no valid discounts
#                     unset_data["buy_x_get_y_at_z_price"] = ""
#                     unset_data["discount_rules"] = ""
#                     unset_data["discount_type"] = ""

#                 # Check if the discount_coupon_type is addon and store its path in menu_item
#                 if addon_coupon_id:
#                     logger.info(f"Addon coupon {addon_coupon_id} found for item")
#                     update_data["addon"] = f"/coupons/{addon_coupon_id}"
#                 else:
#                     # Remove the addon field if the discount coupon type is not addon
#                     unset_data["addon"] = ""

#                 bulk_updates.append(
#                     UpdateOne(
#                         {"_id": item["_id"]},
#                         {"$set": update_data, "$unset": unset_data}
#                     )
#                 )

#             except Exception as e:
#                 logger.error(f"Error processing item {item.get('name', '')}: {e}")
#                 continue

#         if bulk_updates:
#             result = menu_collection.bulk_write(bulk_updates)
#             logger.info(f"Updated {result.modified_count} items")

#         return {"status": "success", "items_updated": len(bulk_updates)}

#     except Exception as e:
#         logger.error(f"Task failed: {e}")
#         raise










































@celery_app.task(name="update_discounted_prices")
def update_discounted_prices():
    """Update menu items with current valid discounts"""
    try:
        now = datetime.now()
        menu_items = list(menu_collection.find())
        bulk_updates = []

        for item in menu_items:
            try:
                if "coupon_ids" not in item:
                    continue

                valid_discounts = []
                addon_coupon_id = None
                buy_x_get_y_at_z_details = {}  # Will store details from all valid discounts

                for coupon_id in item["coupon_ids"]:
                    coupon = coupon_collection.find_one({"coupon_id": coupon_id})
                    if coupon and is_coupon_valid(coupon, now):
                        if coupon["discount_type"] == "buy_x_get_y_at_z_price":
                            # Check if current item is in buy_items
                            buy_x_get_y_at_z_buy_quantity = None
                            for buy_item in coupon["buy_x_get_y_at_z_price"]["buy_items"]:
                                if buy_item["item_id"] == str(item["_id"]):
                                    buy_x_get_y_at_z_buy_quantity = buy_item["quantity"]
                                    # Process all get_items for this buy_item
                                    for get_item in coupon["buy_x_get_y_at_z_price"]["get_items"]:
                                        menu_item = menu_collection.find_one({
                                            "_id": ObjectId(get_item["item_id"]),
                                            "owner_id": item["owner_id"]
                                        })
                                        if menu_item:
                                            detail = {
                                                "item_path": f"/menu/items/{get_item['item_id']}",
                                                "original_price": menu_item["price"],
                                                "discounted_price": get_item["discounted_price"],
                                                "get_quantity": get_item["quantity"],
                                                "buy_quantity": buy_x_get_y_at_z_buy_quantity
                                            }
                                            buy_x_get_y_at_z_details[menu_item["name"]] = detail
                        
                        elif coupon["discount_coupon_type"] == "addon":
                            addon_coupon_id = coupon_id
                            logger.info(f"Addon coupon {coupon_id} found for item")
                        else:
                            discount_info = {
                                "type": coupon["discount_type"],
                                "priority": get_discount_priority(coupon["discount_type"]),
                            }
                            
                            if coupon["discount_type"] == "buy_x_get_y" and coupon.get("buy_x_get_y"):
                                discount_info["buy_quantity"] = int(coupon["buy_x_get_y"]["buy_quantity"])
                                discount_info["get_quantity"] = int(coupon["buy_x_get_y"]["get_quantity"])
                            elif coupon["discount_type"] == "value":
                                discount_info["value"] = coupon["discount_value"]
                            elif coupon["discount_type"] == "percentage":
                                discount_info["percentage"] = coupon["discount_percentage"]
                            
                            valid_discounts.append(discount_info)

                update_data = {}
                unset_data = {}

                if valid_discounts:
                    best_discount = max(valid_discounts, key=lambda x: x["priority"])
                    update_data["discount_type"] = [best_discount["type"]]
                    update_data["discount_rules"] = [best_discount]

                    if best_discount["type"] in ["value", "percentage"]:
                        if best_discount["type"] == "value":
                            discounted_price = item["price"] - best_discount["value"]
                        else:
                            discounted_price = item["price"] * (1 - best_discount["percentage"]/100)
                        update_data["discounted_price"] = max(0, discounted_price)
                    else:
                        update_data["discounted_price"] = item["price"]

                if buy_x_get_y_at_z_details:
                    update_data["buy_x_get_y_at_z_price"] = buy_x_get_y_at_z_details
                else:
                    unset_data["buy_x_get_y_at_z_price"] = ""

                if addon_coupon_id:
                    logger.info(f"Addon coupon {addon_coupon_id} found for item")
                    update_data["addon"] = f"/coupons/{addon_coupon_id}"
                else:
                    unset_data["addon"] = ""

                bulk_updates.append(
                    UpdateOne(
                        {"_id": item["_id"]},
                        {"$set": update_data, "$unset": unset_data}
                    )
                )

            except Exception as e:
                logger.error(f"Error processing item {item.get('name', '')}: {e}")
                continue

        if bulk_updates:
            result = menu_collection.bulk_write(bulk_updates)
            logger.info(f"Updated {result.modified_count} items")

        return {"status": "success", "items_updated": len(bulk_updates)}

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise







    















def schedule_coupon_tasks():
    """Schedules Celery tasks to trigger discount updates."""
    try:
        logger.info("Scheduling discount update tasks...")
        now = datetime.now()
        
        # Schedule immediate update
        update_discounted_prices.delay()
        
        # Schedule future updates based on coupons
        for coupon in coupon_collection.find():
            if "discount_duration" in coupon and coupon["discount_duration"]:
                for duration in coupon["discount_duration"]  :
                    if isinstance(duration, dict):
                        start = duration.get("start")
                        end = duration.get("end")
                        
                        if start and end:
                            start_time = datetime.strptime(start, "%H:%M").time()
                            end_time = datetime.strptime(end, "%H:%M").time()
                            
                            today = now.date()
                            start_dt = datetime.combine(today, start_time)
                            end_dt = datetime.combine(today, end_time)
                            
                            if now < start_dt:
                                update_discounted_prices.apply_async(eta=start_dt)
                            if now < end_dt:
                                update_discounted_prices.apply_async(eta=end_dt)
        
        logger.info("Discount update tasks scheduled successfully")
    except Exception as e:
        logger.error(f"Error scheduling tasks: {e}")
        raise

@router.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting discount calculation service...")
    try:
        schedule_coupon_tasks()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@router.get("/trigger_discount_update")
async def trigger_update():
    """Manually trigger discount update."""
    try:
        task = update_discounted_prices.delay()
        return {
            "status": "success",
            "message": "Discount update triggered",
            "task_id": task.id
        }
    except Exception as e:
        logger.error(f"Failed to trigger update: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'update-discounts-daily': {
        'task': 'update_discounted_prices',
        'schedule': timedelta(days=1),
        'options': {'expires': 3600}
    },
}


