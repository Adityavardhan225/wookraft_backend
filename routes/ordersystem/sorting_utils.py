from pymongo.database import Database
from typing import List, Optional

def get_filtered_orders(db: Database, food_types: Optional[List[str]] = None, food_categories: Optional[List[str]] = None):

    
    # Create the match stage to filter orders by status
    match_stage = {"$match": {"status": "active"}}
    
    # Create the unwind stage to deconstruct the items array
    unwind_stage = {"$unwind": "$items"}
    
    # Create the match stage to filter items by food_type and food_category
    item_match_stage = {"$match": {}}
    if food_types:
        item_match_stage["$match"]["items.food_type"] = {"$in": food_types}
    if food_categories:
        item_match_stage["$match"]["items.food_category"] = {"$in": food_categories}
   
    # Create the group stage to reconstruct the orders with only the filtered items
    group_stage = {
        "$group": {
            "_id": "$_id",
            "table_number": {"$first": "$table_number"},
            "status": {"$first": "$status"},
            "employee_id": {"$first": "$employee_id"},
            "owner_id": {"$first": "$owner_id"},
            "overall_customization": {"$first": "$overall_customization"},
            "received": {"$first": "$received"},
            "timestamp": {"$first": "$timestamp"},
            "prepared": {"$first": "$prepared"},
            "items": {"$push": "$items"}
        }
    }
    
    
    # Create the sort stage to sort the orders by prepared status and timestamp
    sort_stage = {"$sort": {"prepared": 1, "timestamp": 1}}
    # Build the aggregation pipeline
    pipeline = [match_stage, unwind_stage, item_match_stage, group_stage, sort_stage]
    
    # Execute the aggregation pipeline
    active_orders = list(db.orders.aggregate(pipeline))
    
    
    return active_orders


def get_orders_by_table(db: Database, table_no: str):
    query = {"table_no": table_no, "status": "active"}
    table_orders = db.orders.find(query).sort([("prepared", 1), ("timestamp", 1)])
    return table_orders