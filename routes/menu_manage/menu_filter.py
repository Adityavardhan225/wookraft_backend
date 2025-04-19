


from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from configurations.config import client, get_db
from routes.security.protected_authorise import get_current_user
from routes.security.custom_authorize import dynamic_authorize
from pymongo.database import Database

router = APIRouter()

db = client["wookraft_db"]  # Your database name
menu_collection = db["menu_items"]

# API Endpoint for filtering and sorting menu items

@router.get("/menu/filter/sear", response_model=List[dict])
@dynamic_authorize("menu_filter", "read")
async def get_menu_items(
    food_types: Optional[List[str]] = Query(None),
    category: Optional[List[str]] = Query(None),
    sort_by_price: Optional[str] = Query(None, regex="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    print(current_user)
    query = {"owner_id": current_user.owner_id}
    print(query)
    # Apply filters if provided
    if food_types:
        query["food_type"] = {"$in": food_types}
    
    if category:
        query["category"] = {"$in": category}
    
    # Adjust search logic
    if search:
        search_query = {"name": {"$regex": search, "$options": "i"}}
        if query:
            # Combine existing filters with the search
            query = {"$and": [query, search_query]}
        else:
            # Apply search as the only condition
            query = search_query
    
    # Sorting logic
    sort = []
    if sort_by_price:
        sort.append(("price", 1 if sort_by_price == "asc" else -1))
    else:
        sort.append(("name", 1))  # Default sorting by name

    # Fetch menu items from the database
    menu_items = list(menu_collection.find(query, {"_id": 0}).sort(sort))

    for item in menu_items:
        if "_id" in item:
            item["_id"] = str(item["_id"])
    
    # Resolve image URLs before returning
    menu_items_with_urls = resolve_image_urls(db, menu_items)
    print(f"debug 000000 {menu_items_with_urls}")
    
    return menu_items_with_urls





def resolve_image_urls(db, item_data):
    """
    Resolves image names to their actual URLs from food_images collection
    with owner_id matching for security
    
    Args:
        db: MongoDB database instance
        item_data: Single menu item or list of menu items containing image references
    
    Returns:
        Updated item_data with image names replaced by URLs
    """
    try:
        # Handle both single items and lists
        items_list = item_data if isinstance(item_data, list) else [item_data]
        processed_items = []
        
        # Group items by owner_id for security and efficiency
        items_by_owner = {}
        for item in items_list:
            owner_id = item.get("owner_id")
            if owner_id not in items_by_owner:
                items_by_owner[owner_id] = []
            items_by_owner[owner_id].append(item)
        
        # Process each owner group separately
        for owner_id, owner_items in items_by_owner.items():
            # Create a set of all image names to fetch for this owner
            all_image_names = set()
            for item in owner_items:
                if "name_image" in item and item["name_image"]:
                    all_image_names.add(item["name_image"])
            
            # Fetch all needed images at once for this owner
            image_map = {}
            if all_image_names:
                # Only fetch images that belong to this owner
                image_docs = list(db.food_images.find({
                    "name": {"$in": list(all_image_names)},
                    "owner_id": owner_id
                }))
                
                # Log how many images were found vs. requested
                print(f"Found {len(image_docs)} of {len(all_image_names)} requested images for owner {owner_id}")
                
                for img in image_docs:
                    image_map[img["name"]] = img.get("transformed_url", "")
            
            # Process each item to replace image names with URLs
            for item in owner_items:
                item_copy = item.copy()  # Create a copy to avoid modifying the original
                
                # Replace image name with URL if available
                if "name_image" in item_copy and item_copy["name_image"]:
                    image_name = item_copy["name_image"]
                    if image_name in image_map:
                        item_copy["name_image"] = image_map[image_name]
                        # Optionally also add image_url field while keeping name_image
                        # item_copy["image_url"] = image_map[image_name]
                    else:
                        # If image not found, log it but keep the name
                        print(f"Image not found: {image_name} for owner {owner_id}")
                
                processed_items.append(item_copy)
        
        # Return single item or list based on input
        return processed_items[0] if not isinstance(item_data, list) else processed_items
        
    except Exception as e:
        print(f"Error resolving image URLs: {str(e)}")
        # Return original data if there's an error
        return item_data