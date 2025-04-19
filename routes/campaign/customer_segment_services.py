# from typing import Dict, Any, List, Optional, Union
# from bson import ObjectId
# import logging
# import json
# from datetime import datetime
# import csv
# import io
# from configurations.config import client
# import pandas as pd

# # Setup logging
# logger = logging.getLogger(__name__)

# # Database access
# db = client["wookraft_db"]
# customer_collection = db["customer_order_history"]
# segment_collection = db["customer_segments"]

# def is_valid_object_id(id_str: str) -> bool:
#     """Check if a string is a valid MongoDB ObjectId"""
#     try:
#         ObjectId(id_str)
#         return True
#     except:
#         return False

# # Segment Management Services
# async def get_all_segments(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
#     """
#     Retrieve all customer segments (predefined and custom).
    
#     Args:
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         List of segment dictionaries
#     """
#     try:
#         # Build query
#         query = {}
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Find all segments
#         cursor = segment_collection.find(query)
        
#         # Convert to list and format _id
#         segments = []
#         for segment in cursor:
#             if "_id" in segment and isinstance(segment["_id"], ObjectId):
#                 segment["_id"] = str(segment["_id"])
#             segments.append(segment)
            
#         # Check for predefined segments
#         if not any(segment.get("type") == "system" for segment in segments):
#             # Create predefined segments if they don't exist
#             await create_predefined_segments(owner_id)
#             # Fetch again including the predefined segments
#             return await get_all_segments(owner_id)
            
#         return segments
        
#     except Exception as e:
#         logger.error(f"Error retrieving segments: {str(e)}")
#         raise ValueError(f"Failed to retrieve segments: {str(e)}")

# async def create_predefined_segments(owner_id: Optional[str] = None) -> None:
#     """
#     Create predefined system segments if they don't exist.
    
#     Args:
#         owner_id: Optional owner ID for data segregation
#     """
#     try:
#         predefined_segments = [
#             {
#                 "id": "vip",
#                 "name": "VIP Customers",
#                 "description": "Customers who have spent over ₹10,000",
#                 "type": "system",
#                 "criteria": {
#                     "operator": "AND",
#                     "conditions": [
#                         {
#                             "field": "total_spent",
#                             "operator": "gte",
#                             "value": 10000
#                         }
#                     ]
#                 },
#                 "customerCount": 0,  # Will be calculated during retrieval
#                 "createdAt": datetime.now(),
#                 "updatedAt": datetime.now(),
#                 "lastUsed": None
#             },
#             {
#                 "id": "frequent",
#                 "name": "Frequent Visitors",
#                 "description": "Customers who have visited more than 5 times",
#                 "type": "system",
#                 "criteria": {
#                     "operator": "AND",
#                     "conditions": [
#                         {
#                             "field": "total_visits",
#                             "operator": "gte",
#                             "value": 5
#                         }
#                     ]
#                 },
#                 "customerCount": 0,
#                 "createdAt": datetime.now(),
#                 "updatedAt": datetime.now(),
#                 "lastUsed": None
#             },
#             {
#                 "id": "recent",
#                 "name": "Recent Customers",
#                 "description": "Customers who visited in the last 30 days",
#                 "type": "system",
#                 "criteria": {
#                     "operator": "AND",
#                     "conditions": [
#                         {
#                             "field": "last_visit",
#                             "operator": "gte",
#                             "value": {"$dateAdd": {"startDate": "$$NOW", "unit": "day", "amount": -30}}
#                         }
#                     ]
#                 },
#                 "customerCount": 0,
#                 "createdAt": datetime.now(),
#                 "updatedAt": datetime.now(),
#                 "lastUsed": None
#             },
#             {
#                 "id": "inactive",
#                 "name": "Inactive Customers",
#                 "description": "Customers who haven't visited in the last 90 days",
#                 "type": "system",
#                 "criteria": {
#                     "operator": "AND",
#                     "conditions": [
#                         {
#                             "field": "last_visit",
#                             "operator": "lt",
#                             "value": {"$dateAdd": {"startDate": "$$NOW", "unit": "day", "amount": -90}}
#                         }
#                     ]
#                 },
#                 "customerCount": 0,
#                 "createdAt": datetime.now(),
#                 "updatedAt": datetime.now(),
#                 "lastUsed": None
#             }
#         ]
        
#         # Add owner_id if provided
#         if owner_id:
#             for segment in predefined_segments:
#                 segment["owner_id"] = owner_id
                
#         # Insert predefined segments
#         for segment in predefined_segments:
#             # Check if segment already exists
#             existing = segment_collection.find_one({"id": segment["id"], "type": "system"})
#             if not existing:
#                 segment_collection.insert_one(segment)
                
#     except Exception as e:
#         logger.error(f"Error creating predefined segments: {str(e)}")
#         raise ValueError(f"Failed to create predefined segments: {str(e)}")

# async def get_segment_by_id(segment_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
#     """
#     Retrieve a specific segment by ID.
    
#     Args:
#         segment_id: ID of the segment to retrieve
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Segment dictionary or None if not found
#     """
#     try:
#         # Build query
#         query = {"id": segment_id}
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Find segment
#         segment = segment_collection.find_one(query)
        
#         if not segment:
#             logger.warning(f"No segment found with ID: {segment_id}")
#             return None
            
#         # Calculate current customer count for the segment
#         segment["customerCount"] = await count_customers_for_segment(segment)
            
#         # Format _id
#         if "_id" in segment and isinstance(segment["_id"], ObjectId):
#             segment["_id"] = str(segment["_id"])
            
#         # Update last used timestamp
#         segment_collection.update_one(
#             {"id": segment_id},
#             {"$set": {"lastUsed": datetime.now()}}
#         )
            
#         return segment
        
#     except Exception as e:
#         logger.error(f"Error retrieving segment by ID: {str(e)}")
#         raise ValueError(f"Failed to retrieve segment: {str(e)}")

# async def create_segment(segment_data: Dict[str, Any], owner_id: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Create a new customer segment.
    
#     Args:
#         segment_data: Dictionary containing segment details
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Created segment dictionary
#     """
#     try:
#         # Generate segment ID if not provided
#         if "id" not in segment_data:
#             segment_data["id"] = f"segment_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
#         # Set segment type to custom
#         segment_data["type"] = "custom"
        
#         # Add timestamps
#         segment_data["createdAt"] = datetime.now()
#         segment_data["updatedAt"] = datetime.now()
#         segment_data["lastUsed"] = None
        
#         # Add owner_id if provided
#         if owner_id:
#             segment_data["owner_id"] = owner_id
            
#         # Calculate customer count for the segment
#         segment_data["customerCount"] = await count_customers_for_segment(segment_data)
            
#         # Insert segment
#         result = segment_collection.insert_one(segment_data)
        
#         # Get created segment
#         created_segment = segment_collection.find_one({"_id": result.inserted_id})
        
#         # Format _id
#         if "_id" in created_segment and isinstance(created_segment["_id"], ObjectId):
#             created_segment["_id"] = str(created_segment["_id"])
            
#         return created_segment
        
#     except Exception as e:
#         logger.error(f"Error creating segment: {str(e)}")
#         raise ValueError(f"Failed to create segment: {str(e)}")

# async def update_segment(segment_id: str, segment_data: Dict[str, Any], owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
#     """
#     Update an existing customer segment.
    
#     Args:
#         segment_id: ID of the segment to update
#         segment_data: Dictionary containing updated segment details
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Updated segment dictionary or None if not found
#     """
#     try:
#         # Build query
#         query = {"id": segment_id}
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Check if segment exists
#         existing_segment = segment_collection.find_one(query)
#         if not existing_segment:
#             logger.warning(f"No segment found with ID: {segment_id}")
#             return None
            
#         # Prevent updating system segments
#         if existing_segment.get("type") == "system":
#             raise ValueError("System segments cannot be modified")
            
#         # Update timestamp
#         segment_data["updatedAt"] = datetime.now()
        
#         # Calculate customer count for the updated segment
#         combined_data = {**existing_segment, **segment_data}
#         segment_data["customerCount"] = await count_customers_for_segment(combined_data)
            
#         # Update segment
#         result = segment_collection.update_one(
#             query,
#             {"$set": segment_data}
#         )
        
#         if result.matched_count == 0:
#             logger.warning(f"No segment found with ID: {segment_id}")
#             return None
            
#         # Get updated segment
#         updated_segment = segment_collection.find_one(query)
        
#         # Format _id
#         if "_id" in updated_segment and isinstance(updated_segment["_id"], ObjectId):
#             updated_segment["_id"] = str(updated_segment["_id"])
            
#         return updated_segment
        
#     except Exception as e:
#         logger.error(f"Error updating segment: {str(e)}")
#         raise ValueError(f"Failed to update segment: {str(e)}")

# async def delete_segment(segment_id: str, owner_id: Optional[str] = None) -> bool:
#     """
#     Delete a customer segment.
    
#     Args:
#         segment_id: ID of the segment to delete
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         True if deleted, False if not found
#     """
#     try:
#         # Build query
#         query = {"id": segment_id}
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Check if segment exists
#         existing_segment = segment_collection.find_one(query)
#         if not existing_segment:
#             logger.warning(f"No segment found with ID: {segment_id}")
#             return False
            
#         # Prevent deleting system segments
#         if existing_segment.get("type") == "system":
#             raise ValueError("System segments cannot be deleted")
            
#         # Delete segment
#         result = segment_collection.delete_one(query)
        
#         return result.deleted_count > 0
        
#     except Exception as e:
#         logger.error(f"Error deleting segment: {str(e)}")
#         raise ValueError(f"Failed to delete segment: {str(e)}")

# # Customer Segmentation Operations
# async def count_customers_for_segment(segment: Dict[str, Any]) -> int:
#     """
#     Count customers matching a segment's criteria.
    
#     Args:
#         segment: Segment dictionary with criteria
        
#     Returns:
#         Number of matching customers
#     """
#     try:
#         # Build query from segment criteria
#         query = build_query_from_criteria(segment.get("criteria", {}))
        
#         # Add owner_id if present in segment
#         if "owner_id" in segment:
#             query["owner_id"] = segment["owner_id"]
            
#         # Count matching customers
#         count = customer_collection.count_documents(query)
        
#         return count
        
#     except Exception as e:
#         logger.error(f"Error counting customers for segment: {str(e)}")
#         return 0

# async def count_customers_for_criteria(criteria: Dict[str, Any], owner_id: Optional[str] = None) -> int:
#     """
#     Count customers matching the given criteria.
    
#     Args:
#         criteria: Dictionary containing filter criteria
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Number of matching customers
#     """
#     try:
#         # Build query from criteria
#         query = build_query_from_criteria(criteria)
        
#         # Add owner_id if provided
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Count matching customers
#         count = customer_collection.count_documents(query)
        
#         return count
        
#     except Exception as e:
#         logger.error(f"Error counting customers for criteria: {str(e)}")
#         raise ValueError(f"Failed to count customers: {str(e)}")

# async def get_customers_for_criteria(
#     criteria: Dict[str, Any], 
#     limit: int = 10, 
#     skip: int = 0,
#     owner_id: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Retrieve customers matching the given criteria.
    
#     Args:
#         criteria: Dictionary containing filter criteria
#         limit: Maximum number of customers to return
#         skip: Number of customers to skip
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Dictionary with total count and list of matching customers
#     """
#     try:
#         # Build query from criteria
#         query = build_query_from_criteria(criteria)
        
#         # Add owner_id if provided
#         if owner_id:
#             query["owner_id"] = owner_id
            
#         # Count total matching customers
#         total = customer_collection.count_documents(query)
        
#         # Get matching customers with pagination
#         cursor = customer_collection.find(query).skip(skip).limit(limit)
        
#         # Convert to list and format _id
#         customers = []
#         for customer in cursor:
#             if "_id" in customer and isinstance(customer["_id"], ObjectId):
#                 customer["_id"] = str(customer["_id"])
#             customers.append(customer)
            
#         return {
#             "total": total,
#             "customers": customers
#         }
        
#     except Exception as e:
#         logger.error(f"Error retrieving customers for criteria: {str(e)}")
#         raise ValueError(f"Failed to retrieve customers: {str(e)}")

# async def count_customers_for_combined_criteria(
#     segment_ids: List[str],
#     custom_filters: Optional[List[Dict[str, Any]]] = None,
#     operator: str = "AND",
#     owner_id: Optional[str] = None
# ) -> int:
#     """
#     Count customers matching combined segment criteria and custom filters.
    
#     Args:
#         segment_ids: List of segment IDs to include
#         custom_filters: Optional list of custom filter conditions
#         operator: How to combine segments and filters (AND or OR)
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Number of matching customers
#     """
#     try:
#         # Build combined query
#         query = await build_combined_query(segment_ids, custom_filters, operator, owner_id)
        
#         # Count matching customers
#         count = customer_collection.count_documents(query)
        
#         return count
        
#     except Exception as e:
#         logger.error(f"Error counting customers for combined criteria: {str(e)}")
#         raise ValueError(f"Failed to count customers: {str(e)}")

# async def get_customers_for_combined_criteria(
#     segment_ids: List[str],
#     custom_filters: Optional[List[Dict[str, Any]]] = None,
#     operator: str = "AND",
#     limit: int = 10,
#     skip: int = 0,
#     owner_id: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Retrieve customers matching combined segment criteria and custom filters.
    
#     Args:
#         segment_ids: List of segment IDs to include
#         custom_filters: Optional list of custom filter conditions
#         operator: How to combine segments and filters (AND or OR)
#         limit: Maximum number of customers to return
#         skip: Number of customers to skip
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Dictionary with total count and list of matching customers
#     """
#     try:
#         # Build combined query
#         query = await build_combined_query(segment_ids, custom_filters, operator, owner_id)
        
#         # Count total matching customers
#         total = customer_collection.count_documents(query)
        
#         # Get matching customers with pagination
#         cursor = customer_collection.find(query).skip(skip).limit(limit)
        
#         # Convert to list and format _id
#         customers = []
#         for customer in cursor:
#             if "_id" in customer and isinstance(customer["_id"], ObjectId):
#                 customer["_id"] = str(customer["_id"])
                
#             # Simplify customer object for preview
#             preview_customer = {
#                 "id": customer.get("_id"),
#                 "name": customer.get("name", ""),
#                 "email": customer.get("email", ""),
#                 "phone": customer.get("phone", ""),
#                 "totalSpent": customer.get("total_spent", 0),
#                 "purchaseCount": customer.get("total_visits", 0),
#                 "lastPurchaseDate": customer.get("last_visit")
#             }
            
#             customers.append(preview_customer)
            
#         return {
#             "total": total,
#             "customers": customers
#         }
        
#     except Exception as e:
#         logger.error(f"Error retrieving customers for combined criteria: {str(e)}")
#         raise ValueError(f"Failed to retrieve customers: {str(e)}")

# async def get_filter_fields() -> List[Dict[str, Any]]:
#     """
#     Get available customer fields for filtering.
    
#     Returns:
#         List of field definitions with name, type, and operators
#     """
#     # Define field metadata for the UI
#     fields = [
#         {
#             "name": "name",
#             "label": "Customer Name",
#             "type": "string",
#             "operators": ["equals", "contains", "startsWith", "endsWith"]
#         },
#         {
#             "name": "email",
#             "label": "Email",
#             "type": "string",
#             "operators": ["equals", "contains", "endsWith"]
#         },
#         {
#             "name": "phone",
#             "label": "Phone Number",
#             "type": "string",
#             "operators": ["equals", "contains", "startsWith"]
#         },
#         {
#             "name": "total_spent",
#             "label": "Total Spent",
#             "type": "number",
#             "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
#         },
#         {
#             "name": "total_visits",
#             "label": "Number of Visits",
#             "type": "number",
#             "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
#         },
#         {
#             "name": "first_visit",
#             "label": "First Visit Date",
#             "type": "date",
#             "operators": ["equals", "before", "after", "between", "inLast"]
#         },
#         {
#             "name": "last_visit",
#             "label": "Last Visit Date",
#             "type": "date",
#             "operators": ["equals", "before", "after", "between", "inLast"]
#         },
#         {
#             "name": "status",
#             "label": "Customer Status",
#             "type": "select",
#             "operators": ["equals", "notEquals"],
#             "options": ["active", "inactive", "vip"]
#         },
#         {
#             "name": "location.city",
#             "label": "City",
#             "type": "string",
#             "operators": ["equals", "contains", "in"]
#         },
#         {
#             "name": "tags",
#             "label": "Tags",
#             "type": "array",
#             "operators": ["contains", "containsAny", "containsAll"]
#         }
#     ]
    
#     return fields

# async def import_customers_from_csv(csv_file, owner_id: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Import customers from a CSV file.
    
#     Args:
#         csv_file: CSV file object (e.g., from FastAPI File upload)
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Dictionary with import results
#     """
#     try:
#         # Read CSV file
#         content = await csv_file.read()
        
#         # Convert to StringIO for pandas
#         csv_stringio = io.StringIO(content.decode('utf-8'))
        
#         # Read CSV with pandas
#         df = pd.read_csv(csv_stringio)
        
#         # Basic validation
#         required_fields = ['email', 'name']
#         for field in required_fields:
#             if field not in df.columns:
#                 raise ValueError(f"CSV file must contain '{field}' column")
        
#         # Convert to list of dictionaries
#         customers = df.to_dict('records')
        
#         # Prepare for import
#         import_count = 0
#         update_count = 0
#         error_count = 0
#         errors = []
        
#         for customer in customers:
#             try:
#                 # Add owner_id if provided
#                 if owner_id:
#                     customer["owner_id"] = owner_id
                
#                 # Check if customer already exists by email
#                 existing = customer_collection.find_one({"email": customer["email"]})
                
#                 if existing:
#                     # Update existing customer
#                     customer["updatedAt"] = datetime.now()
#                     result = customer_collection.update_one(
#                         {"email": customer["email"]},
#                         {"$set": customer}
#                     )
#                     if result.modified_count > 0:
#                         update_count += 1
#                 else:
#                     # Add timestamps for new customer
#                     customer["createdAt"] = datetime.now()
#                     customer["updatedAt"] = datetime.now()
                    
#                     # Insert new customer
#                     result = customer_collection.insert_one(customer)
#                     if result.inserted_id:
#                         import_count += 1
            
#             except Exception as e:
#                 error_count += 1
#                 errors.append({
#                     "row": customer,
#                     "error": str(e)
#                 })
        
#         return {
#             "success": True,
#             "total": len(customers),
#             "imported": import_count,
#             "updated": update_count,
#             "errors": error_count,
#             "error_details": errors[:10]  # Limit error details to first 10
#         }
        
#     except Exception as e:
#         logger.error(f"Error importing customers from CSV: {str(e)}")
#         raise ValueError(f"Failed to import customers: {str(e)}")

# # Helper functions
# def build_query_from_criteria(criteria: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Build MongoDB query from segment criteria.
    
#     Args:
#         criteria: Dictionary containing filter criteria
        
#     Returns:
#         MongoDB query dictionary
#     """
#     if not criteria:
#         return {}
    
#     operator = criteria.get("operator", "AND").upper()
#     conditions = criteria.get("conditions", [])
    
#     if not conditions:
#         return {}
    
#     # Process each condition
#     query_conditions = []
#     for condition in conditions:
#         # Check if it's a nested condition group
#         if "operator" in condition and "conditions" in condition:
#             nested_query = build_query_from_criteria(condition)
#             if nested_query:
#                 query_conditions.append(nested_query)
        
#         # Regular condition
#         elif "field" in condition and "operator" in condition and "value" in condition:
#             field = condition["field"]
#             op = condition["operator"]
#             value = condition["value"]
            
#             # Map operators to MongoDB operators
#             if op == "equals":
#                 query_conditions.append({field: value})
#             elif op == "notEquals":
#                 query_conditions.append({field: {"$ne": value}})
#             elif op == "gt":
#                 query_conditions.append({field: {"$gt": value}})
#             elif op == "gte":
#                 query_conditions.append({field: {"$gte": value}})
#             elif op == "lt":
#                 query_conditions.append({field: {"$lt": value}})
#             elif op == "lte":
#                 query_conditions.append({field: {"$lte": value}})
#             elif op == "contains":
#                 query_conditions.append({field: {"$regex": value, "$options": "i"}})
#             elif op == "startsWith":
#                 query_conditions.append({field: {"$regex": f"^{value}", "$options": "i"}})
#             elif op == "endsWith":
#                 query_conditions.append({field: {"$regex": f"{value}$", "$options": "i"}})
#             elif op == "in":
#                 query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
#             elif op == "between":
#                 if isinstance(value, list) and len(value) >= 2:
#                     query_conditions.append({field: {"$gte": value[0], "$lte": value[1]}})
#             elif op == "containsAny":
#                 query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
#             elif op == "containsAll":
#                 query_conditions.append({field: {"$all": value if isinstance(value, list) else [value]}})
    
#     # Combine conditions based on operator
#     if not query_conditions:
#         return {}
    
#     if operator == "AND":
#         return {"$and": query_conditions}
#     else:  # OR
#         return {"$or": query_conditions}

# async def build_combined_query(
#     segment_ids: List[str],
#     custom_filters: Optional[List[Dict[str, Any]]] = None,
#     operator: str = "AND",
#     owner_id: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Build combined MongoDB query from segment IDs and custom filters.
    
#     Args:
#         segment_ids: List of segment IDs to include
#         custom_filters: Optional list of custom filter conditions
#         operator: How to combine segments and filters (AND or OR)
#         owner_id: Optional owner ID for data segregation
        
#     Returns:
#         Combined MongoDB query dictionary
#     """
#     query_parts = []
    
#     # Add segment queries
#     for segment_id in segment_ids:
#         segment = await get_segment_by_id(segment_id, owner_id)
#         if segment and "criteria" in segment:
#             segment_query = build_query_from_criteria(segment["criteria"])
#             if segment_query:
#                 query_parts.append(segment_query)
    
#     # Add custom filters
#     if custom_filters:
#         custom_criteria = {
#             "operator": "AND",
#             "conditions": custom_filters
#         }
#         custom_query = build_query_from_criteria(custom_criteria)
#         if custom_query:
#             query_parts.append(custom_query)
    
#     # Add owner_id if provided
#     if owner_id:
#         query_parts.append({"owner_id": owner_id})
    
#     # Combine all parts based on operator
#     if not query_parts:
#         return {}
    
#     if len(query_parts) == 1:
#         return query_parts[0]
    
#     if operator.upper() == "AND":
#         return {"$and": query_parts}
#     else:  # OR
#         return {"$or": query_parts}












































































from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import json
from bson import ObjectId
import csv
import io
import pandas as pd
from configurations.config import client

# Setup logging
logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
customer_collection = db["customer_order_history"]
segment_collection = db["customer_segments"]

def is_valid_object_id(id_str: str) -> bool:
    """Check if a string is a valid MongoDB ObjectId"""
    try:
        ObjectId(id_str)
        return True
    except:
        return False

# Segment Management Services
async def get_all_segments() -> List[Dict[str, Any]]:
    """
    Retrieve all customer segments (predefined and custom).
    
    Returns:
        List of segment dictionaries
    """
    try:
        # Find all segments
        cursor = segment_collection.find()
        
        # Convert to list and format _id
        segments = []
        for segment in cursor:
            if "_id" in segment and isinstance(segment["_id"], ObjectId):
                segment["_id"] = str(segment["_id"])
            segments.append(segment)
            
        # Check for predefined segments
        if not any(segment.get("type") == "system" for segment in segments):
            # Create predefined segments if they don't exist
            await create_predefined_segments()
            # Fetch again including the predefined segments
            return await get_all_segments()
            
        return segments
        
    except Exception as e:
        logger.error(f"Error retrieving segments: {str(e)}")
        raise ValueError(f"Failed to retrieve segments: {str(e)}")

async def create_predefined_segments() -> None:
    """
    Create predefined system segments if they don't exist.
    """
    try:
        predefined_segments = [
            {
                "id": "vip",
                "name": "VIP Customers",
                "description": "Customers who have spent over ₹10,000",
                "type": "system",
                "criteria": {
                    "operator": "AND",
                    "conditions": [
                        {
                            "field": "total_spent",
                            "operator": "gte",
                            "value": 10000
                        }
                    ]
                },
                "statistics": {
                    "customer_count": 0
                },
                "refresh_settings": {
                    "frequency": "daily",
                    "last_refresh": None,
                    "next_scheduled": datetime.now(),
                    "average_duration_ms": None
                },
                "creation_method": "system",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_used": None
            },
            {
                "id": "frequent",
                "name": "Frequent Visitors",
                "description": "Customers who have visited more than 5 times",
                "type": "system",
                "criteria": {
                    "operator": "AND",
                    "conditions": [
                        {
                            "field": "total_visits",
                            "operator": "gte",
                            "value": 5
                        }
                    ]
                },
                "statistics": {
                    "customer_count": 0
                },
                "refresh_settings": {
                    "frequency": "daily",
                    "last_refresh": None,
                    "next_scheduled": datetime.now(),
                    "average_duration_ms": None
                },
                "creation_method": "system",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_used": None
            },
            {
                "id": "recent",
                "name": "Recent Customers",
                "description": "Customers who visited in the last 30 days",
                "type": "system",
                "criteria": {
                    "operator": "AND",
                    "conditions": [
                        {
                            "field": "last_visit",
                            "operator": "gte",
                            "value": {"$dateAdd": {"startDate": "$$NOW", "unit": "day", "amount": -30}}
                        }
                    ]
                },
                "statistics": {
                    "customer_count": 0
                },
                "refresh_settings": {
                    "frequency": "daily",
                    "last_refresh": None,
                    "next_scheduled": datetime.now(),
                    "average_duration_ms": None
                },
                "creation_method": "system",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_used": None
            },
            {
                "id": "inactive",
                "name": "Inactive Customers",
                "description": "Customers who haven't visited in the last 90 days",
                "type": "system",
                "criteria": {
                    "operator": "AND",
                    "conditions": [
                        {
                            "field": "last_visit",
                            "operator": "lt",
                            "value": {"$dateAdd": {"startDate": "$$NOW", "unit": "day", "amount": -90}}
                        }
                    ]
                },
                "statistics": {
                    "customer_count": 0
                },
                "refresh_settings": {
                    "frequency": "daily",
                    "last_refresh": None,
                    "next_scheduled": datetime.now(),
                    "average_duration_ms": None
                },
                "creation_method": "system",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "last_used": None
            }
        ]
                
        # Insert predefined segments
        for segment in predefined_segments:
            # Check if segment already exists
            existing = segment_collection.find_one({"id": segment["id"], "type": "system"})
            if not existing:
                segment_collection.insert_one(segment)
                
    except Exception as e:
        logger.error(f"Error creating predefined segments: {str(e)}")
        raise ValueError(f"Failed to create predefined segments: {str(e)}")

async def get_segment_by_id(segment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific segment by ID.
    
    Args:
        segment_id: ID of the segment to retrieve
        
    Returns:
        Segment dictionary or None if not found
    """
    try:
        # Find segment
        segment = segment_collection.find_one({"id": segment_id})
        
        if not segment:
            logger.warning(f"No segment found with ID: {segment_id}")
            return None
            
        # Format _id
        if "_id" in segment and isinstance(segment["_id"], ObjectId):
            segment["_id"] = str(segment["_id"])
            
        # Update last used timestamp
        segment_collection.update_one(
            {"id": segment_id},
            {"$set": {"last_used": datetime.now()}}
        )
            
        return segment
        
    except Exception as e:
        logger.error(f"Error retrieving segment by ID: {str(e)}")
        raise ValueError(f"Failed to retrieve segment: {str(e)}")

async def create_segment(segment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new customer segment.
    
    Args:
        segment_data: Dictionary containing segment details
        
    Returns:
        Created segment dictionary
    """
    try:
        # Generate segment ID if not provided
        if "id" not in segment_data:
            segment_data["id"] = f"segment_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
        # Set segment type to custom
        segment_data["type"] = "custom"
        
        # Add timestamps
        segment_data["created_at"] = datetime.now()
        segment_data["updated_at"] = datetime.now()
        segment_data["last_used"] = None
        
        # Add default statistics and refresh settings if not provided
        if "statistics" not in segment_data:
            segment_data["statistics"] = {"customer_count": 0}
            
        if "refresh_settings" not in segment_data:
            segment_data["refresh_settings"] = {
                "frequency": "daily",
                "last_refresh": None,
                "next_scheduled": datetime.now(),
                "average_duration_ms": None
            }
            
        if "creation_method" not in segment_data:
            segment_data["creation_method"] = "user"
            
        # Insert segment
        result = segment_collection.insert_one(segment_data)
        
        # Get created segment
        created_segment = segment_collection.find_one({"_id": result.inserted_id})
        
        # Format _id
        if "_id" in created_segment and isinstance(created_segment["_id"], ObjectId):
            created_segment["_id"] = str(created_segment["_id"])
            
        # Schedule initial refresh (will be done asynchronously)
        from .segment_scheduler import refresh_segment_membership
        import asyncio
        asyncio.create_task(refresh_segment_membership(segment_data["id"]))
            
        return created_segment
        
    except Exception as e:
        logger.error(f"Error creating segment: {str(e)}")
        raise ValueError(f"Failed to create segment: {str(e)}")

async def update_segment(segment_id: str, segment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update an existing customer segment.
    
    Args:
        segment_id: ID of the segment to update
        segment_data: Dictionary containing updated segment details
        
    Returns:
        Updated segment dictionary or None if not found
    """
    try:
        # Check if segment exists
        existing_segment = segment_collection.find_one({"id": segment_id})
        if not existing_segment:
            logger.warning(f"No segment found with ID: {segment_id}")
            return None
            
        # Prevent updating system segments (except refresh settings)
        if existing_segment.get("type") == "system" and any(key not in ["refresh_settings"] for key in segment_data.keys()):
            raise ValueError("System segments cannot be modified except for refresh settings")
            
        # Update timestamp
        segment_data["updated_at"] = datetime.now()
        
        # Update segment
        result = segment_collection.update_one(
            {"id": segment_id},
            {"$set": segment_data}
        )
        
        if result.matched_count == 0:
            logger.warning(f"No segment found with ID: {segment_id}")
            return None
            
        # Get updated segment
        updated_segment = segment_collection.find_one({"id": segment_id})
        
        # Format _id
        if "_id" in updated_segment and isinstance(updated_segment["_id"], ObjectId):
            updated_segment["_id"] = str(updated_segment["_id"])
            
        # Schedule refresh if criteria changed
        if "criteria" in segment_data:
            from .segment_scheduler import refresh_segment_membership
            import asyncio
            asyncio.create_task(refresh_segment_membership(segment_id))
            
        return updated_segment
        
    except Exception as e:
        logger.error(f"Error updating segment: {str(e)}")
        raise ValueError(f"Failed to update segment: {str(e)}")

async def delete_segment(segment_id: str) -> bool:
    """
    Delete a customer segment.
    
    Args:
        segment_id: ID of the segment to delete
        
    Returns:
        True if deleted, False if not found
    """
    try:
        # Check if segment exists
        existing_segment = segment_collection.find_one({"id": segment_id})
        if not existing_segment:
            logger.warning(f"No segment found with ID: {segment_id}")
            return False
            
        # Prevent deleting system segments
        if existing_segment.get("type") == "system":
            raise ValueError("System segments cannot be deleted")
            
        # Delete segment
        result = segment_collection.delete_one({"id": segment_id})
        
        # Also delete membership data
        from .segment_membership_services import segment_membership_collection, customer_segment_membership_collection
        segment_membership_collection.delete_one({"segment_id": segment_id})
        
        # Update customer segment membership records
        customer_segment_membership_collection.update_many(
            {"segment_ids": segment_id},
            {"$pull": {"segment_ids": segment_id}}
        )
        
        return result.deleted_count > 0
        
    except Exception as e:
        logger.error(f"Error deleting segment: {str(e)}")
        raise ValueError(f"Failed to delete segment: {str(e)}")

# Customer Segmentation Operations
async def count_customers_for_criteria(criteria: Dict[str, Any]) -> int:
    """
    Count customers matching the given criteria.
    
    Args:
        criteria: Dictionary containing filter criteria
        
    Returns:
        Number of matching customers
    """
    try:
        # Build query from criteria
        query = build_query_from_criteria(criteria)
            
        # Count matching customers
        count = customer_collection.count_documents(query)
        
        return count
        
    except Exception as e:
        logger.error(f"Error counting customers for criteria: {str(e)}")
        raise ValueError(f"Failed to count customers: {str(e)}")

async def get_customers_for_criteria(
    criteria: Dict[str, Any], 
    limit: int = 10, 
    skip: int = 0
) -> Dict[str, Any]:
    """
    Retrieve customers matching the given criteria.
    
    Args:
        criteria: Dictionary containing filter criteria
        limit: Maximum number of customers to return
        skip: Number of customers to skip
        
    Returns:
        Dictionary with total count and list of matching customers
    """
    try:
        # Build query from criteria
        query = build_query_from_criteria(criteria)
            
        # Count total matching customers
        total = customer_collection.count_documents(query)
        
        # Get matching customers with pagination
        cursor = customer_collection.find(query).skip(skip).limit(limit)
        
        # Convert to list and format _id
        customers = []
        for customer in cursor:
            if "_id" in customer and isinstance(customer["_id"], ObjectId):
                customer["_id"] = str(customer["_id"])
            customers.append(customer)
            
        return {
            "total": total,
            "customers": customers
        }
        
    except Exception as e:
        logger.error(f"Error retrieving customers for criteria: {str(e)}")
        raise ValueError(f"Failed to retrieve customers: {str(e)}")

async def count_customers_for_combined_criteria(
    segment_ids: List[str],
    custom_filters: Optional[List[Dict[str, Any]]] = None,
    operator: str = "AND"
) -> int:
    """
    Count customers matching combined segment criteria and custom filters.
    
    Args:
        segment_ids: List of segment IDs to include
        custom_filters: Optional list of custom filter conditions
        operator: How to combine segments and filters (AND or OR)
        
    Returns:
        Number of matching customers
    """
    try:
        # Check if we can use materialized data for all segments
        use_materialized = False
        if segment_ids and not custom_filters:
            from .segment_membership_services import segment_membership_collection
            materialized_segments = list(segment_membership_collection.find({"segment_id": {"$in": segment_ids}}))
            
            if len(materialized_segments) == len(segment_ids) and all(s.get("refreshed_at") for s in materialized_segments):
                use_materialized = True
                
        if use_materialized:
            # Use materialized segment counts
            if operator.upper() == "AND" and len(segment_ids) > 1:
                # For AND, we need the intersection count which requires querying the database
                # Build combined query
                query = await build_combined_query(segment_ids, custom_filters, operator)
                count = customer_collection.count_documents(query)
            else:
                # For OR, we can use the cached counts
                from .segment_membership_services import segment_membership_collection
                if len(segment_ids) == 1:
                    membership = segment_membership_collection.find_one({"segment_id": segment_ids[0]})
                    count = membership.get("customer_count", 0) if membership else 0
                else:
                    # Need to query since we can't add counts (would double count customers in multiple segments)
                    query = await build_combined_query(segment_ids, custom_filters, operator)
                    count = customer_collection.count_documents(query)
        else:
            # Build combined query
            query = await build_combined_query(segment_ids, custom_filters, operator)
            
            # Count matching customers
            count = customer_collection.count_documents(query)
        
        return count
        
    except Exception as e:
        logger.error(f"Error counting customers for combined criteria: {str(e)}")
        raise ValueError(f"Failed to count customers: {str(e)}")

async def get_customers_for_combined_criteria(
    segment_ids: List[str],
    custom_filters: Optional[List[Dict[str, Any]]] = None,
    operator: str = "AND",
    limit: int = 10,
    skip: int = 0
) -> Dict[str, Any]:
    """
    Retrieve customers matching combined segment criteria and custom filters.
    
    Args:
        segment_ids: List of segment IDs to include
        custom_filters: Optional list of custom filter conditions
        operator: How to combine segments and filters (AND or OR)
        limit: Maximum number of customers to return
        skip: Number of customers to skip
        
    Returns:
        Dictionary with total count and list of matching customers
    """
    try:
        # Build combined query
        query = await build_combined_query(segment_ids, custom_filters, operator)
        print(f'query: {query}')
        # Count total matching customers
        total = customer_collection.count_documents(query)
        
        # Get matching customers with pagination
        cursor = customer_collection.find(query).skip(skip).limit(limit)
        
        # Convert to list and format _id
        customers = []
        for customer in cursor:
            if "_id" in customer and isinstance(customer["_id"], ObjectId):
                customer["_id"] = str(customer["_id"])
                
            # Simplify customer object for preview
            preview_customer = {
                "id": customer.get("_id"),
                "name": customer.get("name", ""),
                "email": customer.get("email", ""),
                "phone": customer.get("phone", ""),
                "totalSpent": customer.get("total_spent", 0),
                "purchaseCount": customer.get("total_visits", 0),
                "lastPurchaseDate": customer.get("last_visit")
            }
            
            customers.append(preview_customer)
            
        return {
            "total": total,
            "customers": customers
        }
        
    except Exception as e:
        logger.error(f"Error retrieving customers for combined criteria: {str(e)}")
        raise ValueError(f"Failed to retrieve customers: {str(e)}")

# async def get_filter_fields() -> List[Dict[str, Any]]:
#     """
#     Get available customer fields for filtering.
    
#     Returns:
#         List of field definitions with name, type, and operators
#     """
#     # Define field metadata for the UI
#     fields = [
#         {
#             "name": "name",
#             "label": "Customer Name",
#             "type": "string",
#             "operators": ["equals", "contains", "startsWith", "endsWith"]
#         },
#         {
#             "name": "email",
#             "label": "Email",
#             "type": "string",
#             "operators": ["equals", "contains", "endsWith"]
#         },
#         {
#             "name": "phone",
#             "label": "Phone Number",
#             "type": "string",
#             "operators": ["equals", "contains", "startsWith"]
#         },
#         {
#             "name": "total_spent",
#             "label": "Total Spent",
#             "type": "number",
#             "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
#         },
#         {
#             "name": "total_visits",
#             "label": "Number of Visits",
#             "type": "number",
#             "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
#         },
#         {
#             "name": "first_visit",
#             "label": "First Visit Date",
#             "type": "date",
#             "operators": ["equals", "before", "after", "between", "inLast"]
#         },
#         {
#             "name": "last_visit",
#             "label": "Last Visit Date",
#             "type": "date",
#             "operators": ["equals", "before", "after", "between", "inLast"]
#         },
#         {
#             "name": "status",
#             "label": "Customer Status",
#             "type": "select",
#             "operators": ["equals", "notEquals"],
#             "options": ["active", "inactive", "vip"]
#         },
#         {
#             "name": "tags",
#             "label": "Tags",
#             "type": "array",
#             "operators": ["contains", "containsAny", "containsAll"]
#         }
#     ]
    
#     return fields




# Replace the existing get_filter_fields() function with this enhanced version

async def get_filter_fields() -> List[Dict[str, Any]]:
    """
    Get available customer fields for filtering.
    
    Returns:
        List of field definitions with name, type, and operators
    """
    # Define field metadata for the UI
    fields = [
        # Basic fields
        {
            "name": "name",
            "label": "Customer Name",
            "type": "string",
            "operators": ["equals", "contains", "startsWith", "endsWith"]
        },
        {
            "name": "email",
            "label": "Email",
            "type": "string",
            "operators": ["equals", "contains", "endsWith"]
        },
        {
            "name": "phone",
            "label": "Phone Number",
            "type": "string",
            "operators": ["equals", "contains", "startsWith"]
        },
        {
            "name": "total_spent",
            "label": "Total Spent",
            "type": "number",
            "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
        },
        {
            "name": "total_visits",
            "label": "Number of Visits",
            "type": "number",
            "operators": ["equals", "gt", "gte", "lt", "lte", "between"]
        },
        {
            "name": "first_visit",
            "label": "First Visit Date",
            "type": "date",
            "operators": ["equals", "before", "after", "between", "inLast"]
        },
        {
            "name": "last_visit",
            "label": "Last Visit Date",
            "type": "date",
            "operators": ["equals", "before", "after", "between", "inLast"]
        },
        
        # Calculated fields
        {
            "name": "avg_order_value",
            "label": "Average Order Value",
            "type": "number",
            "operators": ["gt", "gte", "lt", "lte", "between"],
            "calculated": True
        },
        {
            "name": "days_since_last_visit",
            "label": "Days Since Last Visit",
            "type": "number",
            "operators": ["gt", "gte", "lt", "lte", "between"],
            "calculated": True
        },
        {
            "name": "visit_frequency",
            "label": "Visit Frequency",
            "type": "select",
            "operators": ["equals", "notEquals"],
            "options": ["daily", "weekly", "monthly", "quarterly", "irregular"],
            "calculated": True
        },
        {
            "name": "spending_trend",
            "label": "Spending Trend",
            "type": "select",
            "operators": ["equals", "notEquals"],
            "options": ["increasing", "stable", "decreasing", "insufficient_data"],
            "calculated": True
        },
        {
            "name": "day_of_week",
            "label": "Day of Week",
            "type": "select",
            "operators": ["equals", "notEquals", "in"],
            "options": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "calculated": True
        },
        {
            "name": "time_of_day",
            "label": "Time of Day",
            "type": "select",
            "operators": ["equals", "notEquals", "in"],
            "options": ["morning", "lunch", "dinner", "late_night"],
            "calculated": True
        },
        {
            "name": "is_weekday_customer",
            "label": "Is Weekday Customer",
            "type": "boolean",
            "operators": ["equals"],
            "calculated": True
        },
        {
            "name": "is_weekend_customer",
            "label": "Is Weekend Customer",
            "type": "boolean",
            "operators": ["equals"],
            "calculated": True
        }
    ]
    
    return fields

async def import_customers_from_csv(csv_file) -> Dict[str, Any]:
    """
    Import customers from a CSV file.
    
    Args:
        csv_file: CSV file object (e.g., from FastAPI File upload)
        
    Returns:
        Dictionary with import results
    """
    try:
        # Read CSV file
        content = await csv_file.read()
        
        # Convert to StringIO for pandas
        csv_stringio = io.StringIO(content.decode('utf-8'))
        
        # Read CSV with pandas
        df = pd.read_csv(csv_stringio)
        
        # Basic validation
        required_fields = ['email', 'name']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"CSV file must contain '{field}' column")
        
        # Convert to list of dictionaries
        customers = df.to_dict('records')
        
        # Prepare for import
        import_count = 0
        update_count = 0
        error_count = 0
        errors = []
        
        for customer in customers:
            try:
                # Check if customer already exists by email
                existing = customer_collection.find_one({"email": customer["email"]})
                
                if existing:
                    # Update existing customer
                    customer["updatedAt"] = datetime.now()
                    result = customer_collection.update_one(
                        {"email": customer["email"]},
                        {"$set": customer}
                    )
                    if result.modified_count > 0:
                        update_count += 1
                else:
                    # Add timestamps for new customer
                    customer["createdAt"] = datetime.now()
                    customer["updatedAt"] = datetime.now()
                    
                    # Insert new customer
                    result = customer_collection.insert_one(customer)
                    if result.inserted_id:
                        import_count += 1
            
            except Exception as e:
                error_count += 1
                errors.append({
                    "row": customer,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total": len(customers),
            "imported": import_count,
            "updated": update_count,
            "errors": error_count,
            "error_details": errors[:10]  # Limit error details to first 10
        }
        
    except Exception as e:
        logger.error(f"Error importing customers from CSV: {str(e)}")
        raise ValueError(f"Failed to import customers: {str(e)}")

# Helper functions
# def build_query_from_criteria(criteria: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     Build MongoDB query from segment criteria.
    
#     Args:
#         criteria: Dictionary containing filter criteria
        
#     Returns:
#         MongoDB query dictionary
#     """
#     if not criteria:
#         return {}
    
#     operator = criteria.get("operator", "AND").upper()
#     conditions = criteria.get("conditions", [])
    
#     if not conditions:
#         return {}
    
#     # Process each condition
#     query_conditions = []
#     for condition in conditions:
#         # Check if it's a nested condition group
#         if "operator" in condition and "conditions" in condition:
#             nested_query = build_query_from_criteria(condition)
#             if nested_query:
#                 query_conditions.append(nested_query)
        
#         # Regular condition
#         elif "field" in condition and "operator" in condition and "value" in condition:
#             field = condition["field"]
#             op = condition["operator"]
#             value = condition["value"]
            
#             # Map operators to MongoDB operators
#             if op == "equals":
#                 query_conditions.append({field: value})
#             elif op == "notEquals":
#                 query_conditions.append({field: {"$ne": value}})
#             elif op == "gt":
#                 query_conditions.append({field: {"$gt": value}})
#             elif op == "gte":
#                 query_conditions.append({field: {"$gte": value}})
#             elif op == "lt":
#                 query_conditions.append({field: {"$lt": value}})
#             elif op == "lte":
#                 query_conditions.append({field: {"$lte": value}})
#             elif op == "contains":
#                 query_conditions.append({field: {"$regex": value, "$options": "i"}})
#             elif op == "startsWith":
#                 query_conditions.append({field: {"$regex": f"^{value}", "$options": "i"}})
#             elif op == "endsWith":
#                 query_conditions.append({field: {"$regex": f"{value}$", "$options": "i"}})
#             elif op == "in":
#                 query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
#             elif op == "between":
#                 if isinstance(value, list) and len(value) >= 2:
#                     query_conditions.append({field: {"$gte": value[0], "$lte": value[1]}})
#             elif op == "containsAny":
#                 query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
#             elif op == "containsAll":
#                 query_conditions.append({field: {"$all": value if isinstance(value, list) else [value]}})
    
#     # Combine conditions based on operator
#     if not query_conditions:
#         return {}
    
#     if operator == "AND":
#         return {"$and": query_conditions}
#     else:  # OR
#         return {"$or": query_conditions}








# Add this import at the top:
from .segment_calculated_fields import *

# Update the build_query_from_criteria function to handle calculated fields
def build_query_from_criteria(criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build MongoDB query from segment criteria.
    
    Args:
        criteria: Dictionary containing filter criteria
        
    Returns:
        MongoDB query dictionary
    """
    if not criteria:
        return {}
    
    operator = criteria.get("operator", "AND").upper()
    conditions = criteria.get("conditions", [])
    
    if not conditions:
        return {}
    
    # Process each condition
    query_conditions = []
    for condition in conditions:
        # Check if it's a nested condition group
        if "operator" in condition and "conditions" in condition:
            nested_query = build_query_from_criteria(condition)
            if nested_query:
                query_conditions.append(nested_query)
        
        # Regular condition
        elif "field" in condition and "operator" in condition and "value" in condition:
            field = condition["field"]
            op = condition["operator"]
            value = condition["value"]
            
            # Handle calculated fields with aggregation or special logic
            if field == "avg_order_value":
                # For average order value, use aggregation
                if op == "gt":
                    query_conditions.append({"$expr": {"$gt": [{"$avg": "$orders.total"}, value]}})
                elif op == "gte":
                    query_conditions.append({"$expr": {"$gte": [{"$avg": "$orders.total"}, value]}})
                elif op == "lt":
                    query_conditions.append({"$expr": {"$lt": [{"$avg": "$orders.total"}, value]}})
                elif op == "lte":
                    query_conditions.append({"$expr": {"$lte": [{"$avg": "$orders.total"}, value]}})
                elif op == "between" and isinstance(value, list) and len(value) >= 2:
                    query_conditions.append({
                        "$expr": {
                            "$and": [
                                {"$gte": [{"$avg": "$orders.total"}, value[0]]},
                                {"$lte": [{"$avg": "$orders.total"}, value[1]]}
                            ]
                        }
                    })
            
            elif field == "days_since_last_visit":
                # Calculate days since last visit
                if op == "gt":
                    date_threshold = datetime.now() - timedelta(days=value)
                    query_conditions.append({"last_visit": {"$lt": date_threshold}})
                elif op == "lt":
                    date_threshold = datetime.now() - timedelta(days=value)
                    query_conditions.append({"last_visit": {"$gt": date_threshold}})
                elif op == "between" and isinstance(value, list) and len(value) >= 2:
                    date_min = datetime.now() - timedelta(days=value[1])  # Longer ago
                    date_max = datetime.now() - timedelta(days=value[0])  # More recent
                    query_conditions.append({"last_visit": {"$lt": date_max, "$gt": date_min}})
            
            elif field == "visit_frequency":
                # For now, handle simple cases - complex patterns require pipeline aggregation
                if value == "daily":
                    query_conditions.append({"total_visits": {"$gte": 15}})
                elif value == "weekly":
                    query_conditions.append({"total_visits": {"$gte": 4, "$lt": 15}})
                elif value == "monthly":
                    query_conditions.append({"total_visits": {"$gte": 1, "$lt": 4}})
                
            elif field == "day_of_week":
                # Day of week requires regex on visit dates
                day_num = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, 
                         "Friday": 4, "Saturday": 5, "Sunday": 6}.get(value)
                if day_num is not None:
                    query_conditions.append({"visits.day_of_week": day_num})
            
            # Regular fields with standard operators
            else:
                # Map operators to MongoDB operators
                if op == "equals":
                    query_conditions.append({field: value})
                elif op == "notEquals":
                    query_conditions.append({field: {"$ne": value}})
                elif op == "gt":
                    query_conditions.append({field: {"$gt": value}})
                elif op == "gte":
                    query_conditions.append({field: {"$gte": value}})
                elif op == "lt":
                    query_conditions.append({field: {"$lt": value}})
                elif op == "lte":
                    query_conditions.append({field: {"$lte": value}})
                elif op == "contains":
                    query_conditions.append({field: {"$regex": value, "$options": "i"}})
                elif op == "startsWith":
                    query_conditions.append({field: {"$regex": f"^{value}", "$options": "i"}})
                elif op == "endsWith":
                    query_conditions.append({field: {"$regex": f"{value}$", "$options": "i"}})
                elif op == "in":
                    query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
                elif op == "between":
                    if isinstance(value, list) and len(value) >= 2:
                        query_conditions.append({field: {"$gte": value[0], "$lte": value[1]}})
                elif op == "containsAny":
                    query_conditions.append({field: {"$in": value if isinstance(value, list) else [value]}})
                elif op == "containsAll":
                    query_conditions.append({field: {"$all": value if isinstance(value, list) else [value]}})
                elif op == "before" and field.endswith("_date"):
                    query_conditions.append({field: {"$lt": value}})
                elif op == "after" and field.endswith("_date"):
                    query_conditions.append({field: {"$gt": value}})
                elif op == "inLast" and field.endswith("_date"):
                    date_threshold = datetime.now() - timedelta(days=value)
                    query_conditions.append({field: {"$gte": date_threshold}})
    
    # Combine conditions based on operator
    if not query_conditions:
        return {}
    
    if operator == "AND":
        return {"$and": query_conditions}
    else:  # OR
        return {"$or": query_conditions}
    


async def build_combined_query(
    segment_ids: List[str],
    custom_filters: Optional[List[Dict[str, Any]]] = None,
    operator: str = "AND"
) -> Dict[str, Any]:
    """
    Build combined MongoDB query from segment IDs and custom filters.
    
    Args:
        segment_ids: List of segment IDs to include
        custom_filters: Optional list of custom filter conditions
        operator: How to combine segments and filters (AND or OR)
        
    Returns:
        Combined MongoDB query dictionary
    """
    query_parts = []
    
    # Add segment queries
    for segment_id in segment_ids:
        segment = await get_segment_by_id(segment_id)
        if segment and "criteria" in segment:
            segment_query = build_query_from_criteria(segment["criteria"])
            if segment_query:
                query_parts.append(segment_query)
    
    # Add custom filters - THIS IS THE FIXED PART
    if custom_filters:
        print(f"Processing custom filters: {custom_filters}")
        
        # Process each filter individually to ensure proper handling
        for filter_item in custom_filters:
            # Handle direct filter condition (dictionary format)
            if isinstance(filter_item, dict) and "field" in filter_item and "operator" in filter_item:
                field = filter_item.get("field")
                op = filter_item.get("operator")
                value = filter_item.get("value")
                
                # Create MongoDB condition
                condition = None
                
                # Map operators to MongoDB syntax
                if op == "equals":
                    condition = {field: value}
                elif op == "notEquals":
                    condition = {field: {"$ne": value}}
                elif op == "gt":
                    condition = {field: {"$gt": value}}
                elif op == "gte":
                    condition = {field: {"$gte": value}}
                elif op == "lt":
                    condition = {field: {"$lt": value}}
                elif op == "lte":
                    condition = {field: {"$lte": value}}
                elif op == "contains":
                    condition = {field: {"$regex": value, "$options": "i"}}
                
                if condition:
                    query_parts.append(condition)
                    print(f"Added direct filter condition: {condition}")
            
            # Handle Pydantic model (FilterCondition) with hasattr checking
            elif hasattr(filter_item, 'field') and hasattr(filter_item, 'operator'):
                field = filter_item.field
                op = filter_item.operator
                value = filter_item.value
                
                # Create MongoDB condition
                condition = None
                
                # Map operators to MongoDB syntax
                if op == "equals":
                    condition = {field: value}
                elif op == "notEquals":
                    condition = {field: {"$ne": value}}
                elif op == "gt":
                    condition = {field: {"$gt": value}}
                elif op == "gte":
                    condition = {field: {"$gte": value}}
                elif op == "lt":
                    condition = {field: {"$lt": value}}
                elif op == "lte":
                    condition = {field: {"$lte": value}}
                elif op == "contains":
                    condition = {field: {"$regex": value, "$options": "i"}}
                
                if condition:
                    query_parts.append(condition)
                    print(f"Added model filter condition: {condition}")
            
            # Handle nested filter criteria
            elif isinstance(filter_item, dict) and "operator" in filter_item and "conditions" in filter_item:
                nested_criteria = {
                    "operator": filter_item.get("operator", "AND"),
                    "conditions": filter_item.get("conditions", [])
                }
                nested_query = build_query_from_criteria(nested_criteria)
                if nested_query:
                    query_parts.append(nested_query)
                    print(f"Added nested filter: {nested_query}")
    
    # Combine all parts based on operator
    if not query_parts:
        print("No query parts found")
        return {}
    
    if len(query_parts) == 1:
        print(f"Only one query part found: {query_parts[0]}")
        return query_parts[0]
    
    if operator.upper() == "AND":
        final_query = {"$and": query_parts}
        print(f"Using AND operator with {len(query_parts)} parts: {final_query}")
        return final_query
    else:  # OR
        final_query = {"$or": query_parts}
        print(f"Using OR operator with {len(query_parts)} parts: {final_query}")
        return final_query