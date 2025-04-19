# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel
# from pymongo.database import Database
# from typing import List, Optional
# from configurations.config import client, get_db
# from routes.image_upload.image_up import image_collection
# from bson import ObjectId
# from routes.security.protected_authorise import get_current_user
# from schema.user import UserOutput
# import pandas as pd
# from fastapi import File, UploadFile
# from fastapi.responses import FileResponse
# import pandas as pd
# import logging
# from routes.security.custom_authorize import dynamic_authorize

# logging.basicConfig(level=logging.INFO)

# COLUMNS = [
#     {'name': 'name', 'type': 'str'},
#     {'name': 'description', 'type': 'str'},
#     {'name': 'price', 'type': 'float'},
#     {'name': 'food_type', 'type': 'str'},
#     {'name': 'category', 'type': 'str'},
#     {'name': 'name_image', 'type': 'str'}
# ]


# router = APIRouter()

# db = client["wookraft_db"]
# food_type_collection = db["food_types"]
# category_collection = db["categories"]
# menu_collection = db["menu_items"]

# class FoodType(BaseModel):
#     name: str
#     owner_id: Optional[str] = None

# class Category(BaseModel):
#     name: str

# class MenuItem(BaseModel):
#     name: str
#     description: Optional[str] = None
#     price: Optional[float] = None
#     food_type: Optional[str] = None
#     category: Optional[str] = None
#     name_image: Optional[str] = None

# class MenuItemUpdate(BaseModel):
#     description: Optional[str] = None
#     price: Optional[float] = None
#     food_type: Optional[str] = None
#     category: Optional[str] = None
#     name_image: Optional[str] = None

# def get_food_types():
#     return list(food_type_collection.find({}, {"_id": 0, "name": 1}))

# def get_categories():
#     return list(category_collection.find({}, {"_id": 0, "name": 1}))

# @router.get("/food_types", response_model=List[FoodType])
# @dynamic_authorize("menu-management", "read")
# async def get_food_types_endpoint(current_user: UserOutput = Depends(get_current_user),db: Database = Depends(get_db)):
#     if current_user.role not in ["admin", "authorized_role"]:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     return get_food_types()


# @router.post("/food_types", response_model=FoodType)
# # @dynamic_authorize(resource="menu_management", action="read")
# def add_food_type(food_type: FoodType, db: Database = Depends(get_db),current_user: UserOutput = Depends(get_current_user)):
#     if food_type_collection.find_one({"name": food_type.name}): 
#         raise HTTPException(status_code=400, detail="Food type already exists")
#     print(f"Current User: {current_user}")
#     print(f"Food Type: {food_type.dict()}")
#     print(f"current_user.owner_id: {current_user.owner_id}")
#     food_type_dict = food_type.dict()
#     food_type_dict["owner_id"] = current_user.owner_id
#     food_type_collection.insert_one(food_type_dict)
#     return food_type

# @router.delete("/food_types/{food_type_name}", response_model=FoodType)
# def delete_food_type(food_type_name: str, current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     result = food_type_collection.delete_one({"name": food_type_name})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Food type not found")
#     return {"name": food_type_name}

# @router.get("/categories", response_model=List[Category])
# def get_categories_endpoint(current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role not in ["admin", "authorized_role"]:
#         raise HTTPException(status_code=403, detail="Not authorized")
#     return get_categories()

# @router.post("/categories", response_model=Category)
# def add_category(category: Category, current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     if category_collection.find_one({"name": category.name}):
#         raise HTTPException(status_code=400, detail="Category already exists")
#     category_collection.insert_one(category.dict())
#     return category

# @router.delete("/categories/{category_name}", response_model=Category)
# def delete_category(category_name: str, current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     result = category_collection.delete_one({"name": category_name})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Category not found")
#     return {"name": category_name}

# @router.post("/menu", response_model=MenuItem)
# def add_menu_item(menu_item: MenuItem, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     if not food_type_collection.find_one({"name": menu_item.food_type}):
#         raise HTTPException(status_code=400, detail="Food type not found")
#     if not category_collection.find_one({"name": menu_item.category}):
#         raise HTTPException(status_code=400, detail="Category not found")
#     if not image_collection.find_one({"name": menu_item.name_image}):
#         raise HTTPException(status_code=400, detail="Image not found")
    
#     menu_item_dict = menu_item.dict()
#     menu_item_dict["owner_id"] = current_user.owner_id
#     result = menu_collection.insert_one(menu_item_dict)
#     menu_item_dict["_id"] = str(result.inserted_id)
#     return menu_item_dict

# @router.get("/menu", response_model=List[MenuItem])
# def get_menu_items(db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     items = menu_collection.find({"owner_id": current_user.owner_id})
#     return list(items)

# @router.delete("/menu/{menu_item_name}")
# def delete_menu_item(menu_item_name: str, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     item_to_delete = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
#     if not item_to_delete:
#         raise HTTPException(status_code=404, detail="Menu item not found")
    
#     result = menu_collection.delete_one({"name": menu_item_name, "owner_id": current_user.owner_id})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="Menu item not found")
    
#     return item_to_delete

# @router.patch("/menu/{menu_item_name}", response_model=MenuItem)
# def update_menu_item(menu_item_name: str, updates: MenuItemUpdate, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     existing_item = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
#     if not existing_item:
#         raise HTTPException(status_code=404, detail="Menu item not found")
    
#     update_data = {k: v for k, v in updates.dict().items() if v is not None}
#     if "food_type" in update_data and not food_type_collection.find_one({"name": update_data["food_type"]}):
#         raise HTTPException(status_code=400, detail="Food type not found")
#     if "category" in update_data and not category_collection.find_one({"name": update_data["category"]}):
#         raise HTTPException(status_code=400, detail="Category not found")
    
#     menu_collection.update_one({"name": menu_item_name, "owner_id": current_user.owner_id}, {"$set": update_data})
#     updated_item = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
#     updated_item["_id"] = str(updated_item["_id"])
#     return updated_item

# @router.post("/menu/bulk", response_model=List[MenuItem])
# def add_menu_items(menu_items: List[MenuItem], db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     added_items = []
#     for menu_item in menu_items:
#         if not food_type_collection.find_one({"name": menu_item.food_type}):
#             raise HTTPException(status_code=400, detail=f"Food type '{menu_item.food_type}' not found")
#         if not category_collection.find_one({"name": menu_item.category}):
#             raise HTTPException(status_code=400, detail=f"Category '{menu_item.category}' not found")
#         if not image_collection.find_one({"name": menu_item.name_image}):
#             raise HTTPException(status_code=400, detail=f"Image '{menu_item.name_image}' not found")
        
#         menu_item_dict = menu_item.dict()
#         menu_item_dict["owner_id"] = current_user.owner_id
#         menu_collection.insert_one(menu_item_dict)
#         added_items.append(menu_item_dict)
#     return added_items

# @router.put("/menu_items/{item_id}", response_model=MenuItem)
# async def update_menu_item(item_id: str, menu_item_update: MenuItemUpdate, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     menu_item = menu_collection.find_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id})
#     if not menu_item:
#         raise HTTPException(status_code=404, detail="Menu item not found")
#     menu_collection.update_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id}, {"$set": menu_item_update.dict(exclude_unset=True)})
#     updated_menu_item = menu_collection.find_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id})
#     updated_menu_item["_id"] = str(updated_menu_item["_id"])
#     return updated_menu_item

# @router.delete("/menu")
# def delete_all_menu_items(db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     result = menu_collection.delete_many({"owner_id": current_user.owner_id})
#     if result.deleted_count == 0:
#         raise HTTPException(status_code=404, detail="No menu items found to delete")
#     return {"deleted_count": result.deleted_count}






# @router.get("/download_template/")
# async def download_template(current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     food_types = [item['name'] for item in food_type_collection.find()]
#     categories = [item['name'] for item in category_collection.find()]
#     name_image = [item['name'] for item in image_collection.find()]

#     df = pd.DataFrame(columns=[col['name'] for col in COLUMNS])
#     file_path = 'template.xlsx'
#     with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
#         df.to_excel(writer, sheet_name='Sheet1', index=False)
#         workbook = writer.book
#         worksheet = writer.sheets['Sheet1']

#         worksheet.data_validation('D2:D1048576', {'validate': 'list', 'source': food_types})
#         worksheet.data_validation('E2:E1048576', {'validate': 'list', 'source': categories})
#         worksheet.data_validation('F2:F1048576', {'validate': 'list', 'source': name_image})

#     return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_path)

# @router.post("/upload_data/")
# async def upload_data(file: UploadFile = File(...), db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized")
#     try:
#         df = pd.read_excel(file.file)

#         expected_columns = [col['name'] for col in COLUMNS]
#         if list(df.columns) != expected_columns:
#             raise HTTPException(status_code=400, detail="Invalid columns. Expected columns: " + ", ".join(expected_columns))

#         for col in COLUMNS:
#             if col['type'] == 'str' and not df[col['name']].apply(lambda x: isinstance(x, str)).all():
#                 raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
#             elif col['type'] == 'int' and not df[col['name']].apply(lambda x: isinstance(x, int)).all():
#                 raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
#             elif col['type'] == 'float' and not df[col['name']].apply(lambda x: isinstance(x, (int, float))).all():
#                 raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
#             elif col['type'] == 'date' and not pd.to_datetime(df[col['name']], errors='coerce').notna().all():
#                 raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")

#         food_types = [item['name'] for item in food_type_collection.find()]
#         categories = [item['name'] for item in category_collection.find()]
#         name_image = [item['name'] for item in image_collection.find()]

#         if not df['food_type'].isin(food_types).all():
#             raise HTTPException(status_code=400, detail="Invalid food_type value")
#         if not df['category'].isin(categories).all():
#             raise HTTPException(status_code=400, detail="Invalid category value")
#         if not df['name_image'].isin(name_image).all():
#             raise HTTPException(status_code=400, detail="Invalid image_name value")

#         menu_items = df.to_dict(orient='records')
#         for item in menu_items:
#             item["owner_id"] = current_user.owner_id

#         result = menu_collection.insert_many(menu_items)

#         inserted_ids = result.inserted_ids
#         if not inserted_ids:
#             raise HTTPException(status_code=500, detail="Failed to insert data into the database")

#         logging.info(f"Data uploaded and validated successfully. Inserted IDs: {inserted_ids}")
#         return {
#             "message": "Data uploaded and validated successfully",
#             "inserted_ids": [str(id) for id in inserted_ids]
#         }

#     except Exception as e:
#         logging.error(f"Error processing file: {e}")
#         raise HTTPException(status_code=500, detail="An error occurred while processing the file")










































from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo.database import Database
from typing import List, Optional, Union
from configurations.config import client, get_db
from routes.image_upload.image_up import image_collection
from bson import ObjectId
from routes.security.protected_authorise import get_current_user
from schema.user import UserOutput
import pandas as pd
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
import logging
from routes.security.custom_authorize import dynamic_authorize


from datetime import date, time 


logging.basicConfig(level=logging.INFO)

COLUMNS = [
    {'name': 'name', 'type': 'str'},
    {'name': 'description', 'type': 'str'},
    {'name': 'price', 'type': 'float'},
    {'name': 'food_type', 'type': 'str'},
    {'name': 'category', 'type': 'str'},
    {'name': 'name_image', 'type': 'str'}
]

router = APIRouter()

db = client["wookraft_db"]
food_type_collection = db["food_types"]
category_collection = db["categories"]
menu_collection = db["menu_items"]

class FoodType(BaseModel):
    name: str
    owner_id: Optional[str] = None

class Category(BaseModel):
    name: str

class MenuItem(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    food_type: Optional[str] = None
    category: Optional[str] = None
    name_image: Optional[str] = None

class MenuItemUpdate(BaseModel):
    description: Optional[str] = None
    price: Optional[float] = None
    food_type: Optional[str] = None
    category: Optional[str] = None
    name_image: Optional[str] = None

def get_food_types(owner_id: str):
    return list(food_type_collection.find({"owner_id": owner_id}, {"_id": 0, "name": 1}))

def get_categories(owner_id: str):
    return list(category_collection.find({"owner_id": owner_id}, {"_id": 0, "name": 1}))


@dynamic_authorize("food-types", "read")
@router.get("/food_types", response_model=List[FoodType])

async def get_food_types_endpoint(current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    return get_food_types(current_user.owner_id)


@dynamic_authorize("food-types", "write")
@router.post("/food_types", response_model=FoodType)
def add_food_type(food_type: FoodType, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    print(f"Received food type: {food_type}")
    if food_type_collection.find_one({"name": food_type.name, "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Food type already exists")
    food_type_dict = food_type.dict()
    food_type_dict["owner_id"] = current_user.owner_id
    food_type_collection.insert_one(food_type_dict)
    return food_type


@dynamic_authorize("food-types", "delete")
@router.delete("/food_types/{food_type_name}", response_model=FoodType)
def delete_food_type(food_type_name: str, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    
    result = food_type_collection.delete_one({"name": food_type_name, "owner_id": current_user.owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Food type not found")
    return {"name": food_type_name}


# @dynamic_authorize("food-categories", "read")
@router.get("/categories", response_model=List[Category])
def get_categories_endpoint(current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    # if current_user.role not in ["admin", "authorized_role"]:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    return get_categories(current_user.owner_id)


@dynamic_authorize("food-categories", "write")
@router.post("/categories", response_model=Category)
def add_category(category: Category, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):
    if category_collection.find_one({"name": category.name, "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Category already exists")
    category_dict = category.dict()
    category_dict["owner_id"] = current_user.owner_id
    category_collection.insert_one(category_dict)
    return category

@dynamic_authorize("food-categories", "delete")
@router.delete("/categories/{category_name}", response_model=Category)
def delete_category(category_name: str, current_user: UserOutput = Depends(get_current_user), db: Database = Depends(get_db)):

    result = category_collection.delete_one({"name": category_name, "owner_id": current_user.owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"name": category_name}

@dynamic_authorize("menu-items", "write")
@router.post("/menu", response_model=MenuItem)
def add_menu_item(menu_item: MenuItem, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    if not food_type_collection.find_one({"name": menu_item.food_type, "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Food type not found")
    if not category_collection.find_one({"name": menu_item.category, "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Category not found")
    if not image_collection.find_one({"name": menu_item.name_image, "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Image not found")
    
    menu_item_dict = menu_item.dict()
    menu_item_dict["owner_id"] = current_user.owner_id
    result = menu_collection.insert_one(menu_item_dict)
    menu_item_dict["_id"] = str(result.inserted_id)
    return menu_item_dict

@dynamic_authorize("menu-items", "read")
@router.get("/menu", response_model=List[MenuItem])
def get_menu_items(db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    items = menu_collection.find({"owner_id": current_user.owner_id})
    return list(items)


@dynamic_authorize("menu-items", "delete")
@router.delete("/menu/{menu_item_name}")

def delete_menu_item(menu_item_name: str, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    item_to_delete = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
    if not item_to_delete:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    result = menu_collection.delete_one({"name": menu_item_name, "owner_id": current_user.owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    return item_to_delete


@dynamic_authorize("menu-items", "update")
@router.patch("/menu/{menu_item_name}", response_model=MenuItem)

def update_menu_item(menu_item_name: str, updates: MenuItemUpdate, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
   
    existing_item = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
    if not existing_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if "food_type" in update_data and not food_type_collection.find_one({"name": update_data["food_type"], "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Food type not found")
    if "category" in update_data and not category_collection.find_one({"name": update_data["category"], "owner_id": current_user.owner_id}):
        raise HTTPException(status_code=400, detail="Category not found")
    
    menu_collection.update_one({"name": menu_item_name, "owner_id": current_user.owner_id}, {"$set": update_data})
    updated_item = menu_collection.find_one({"name": menu_item_name, "owner_id": current_user.owner_id})
    updated_item["_id"] = str(updated_item["_id"])
    return updated_item


@dynamic_authorize("menu-items", "write")
@router.post("/menu/bulk", response_model=List[MenuItem])

def add_menu_items(menu_items: List[MenuItem], db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    added_items = []
    for menu_item in menu_items:
        if not food_type_collection.find_one({"name": menu_item.food_type, "owner_id": current_user.owner_id}):
            raise HTTPException(status_code=400, detail=f"Food type '{menu_item.food_type}' not found")
        if not category_collection.find_one({"name": menu_item.category, "owner_id": current_user.owner_id}):
            raise HTTPException(status_code=400, detail=f"Category '{menu_item.category}' not found")
        if not image_collection.find_one({"name": menu_item.name_image, "owner_id": current_user.owner_id}):
            raise HTTPException(status_code=400, detail=f"Image '{menu_item.name_image}' not found")
        
        menu_item_dict = menu_item.dict()
        menu_item_dict["owner_id"] = current_user.owner_id
        menu_collection.insert_one(menu_item_dict)
        added_items.append(menu_item_dict)
    return added_items


@dynamic_authorize("menu-items", "update")
@router.put("/menu_items/{item_id}", response_model=MenuItem)

async def update_menu_item(item_id: str, menu_item_update: MenuItemUpdate, db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):

    menu_item = menu_collection.find_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id})
    if not menu_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    menu_collection.update_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id}, {"$set": menu_item_update.dict(exclude_unset=True)})
    updated_menu_item = menu_collection.find_one({"_id": ObjectId(item_id), "owner_id": current_user.owner_id})
    updated_menu_item["_id"] = str(updated_menu_item["_id"])
    return updated_menu_item


@dynamic_authorize("menu-items", "delete")
@router.delete("/menu")
def delete_all_menu_items(db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    result = menu_collection.delete_many({"owner_id": current_user.owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No menu items found to delete")
    return {"deleted_count": result.deleted_count}


@dynamic_authorize("menu-items", "read")
@router.get("/download_template/")
async def download_template(current_user: UserOutput = Depends(get_current_user)):
    
    food_types = [item['name'] for item in food_type_collection.find({"owner_id": current_user.owner_id})]
    categories = [item['name'] for item in category_collection.find({"owner_id": current_user.owner_id})]
    name_image = [item['name'] for item in image_collection.find({"owner_id": current_user.owner_id})]

    df = pd.DataFrame(columns=[col['name'] for col in COLUMNS])
    file_path = 'template.xlsx'
    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        worksheet.data_validation('D2:D1048576', {'validate': 'list', 'source': food_types})
        worksheet.data_validation('E2:E1048576', {'validate': 'list', 'source': categories})
        worksheet.data_validation('F2:F1048576', {'validate': 'list', 'source': name_image})

    return FileResponse(file_path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename=file_path)


@dynamic_authorize("menu-items", "write")
@router.post("/upload_data/")
async def upload_data(file: UploadFile = File(...), db: Database = Depends(get_db), current_user: UserOutput = Depends(get_current_user)):
    
    try:
        df = pd.read_excel(file.file)

        expected_columns = [col['name'] for col in COLUMNS]
        if list(df.columns) != expected_columns:
            raise HTTPException(status_code=400, detail="Invalid columns. Expected columns: " + ", ".join(expected_columns))

        for col in COLUMNS:
            if col['type'] == 'str' and not df[col['name']].apply(lambda x: isinstance(x, str)).all():
                raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
            elif col['type'] == 'int' and not df[col['name']].apply(lambda x: isinstance(x, int)).all():
                raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
            elif col['type'] == 'float' and not df[col['name']].apply(lambda x: isinstance(x, (int, float))).all():
                raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")
            elif col['type'] == 'date' and not pd.to_datetime(df[col['name']], errors='coerce').notna().all():
                raise HTTPException(status_code=400, detail=f"Column {col['name']} must be of type {col['type']}")

        food_types = [item['name'] for item in food_type_collection.find({"owner_id": current_user.owner_id})]
        categories = [item['name'] for item in category_collection.find({"owner_id": current_user.owner_id})]
        name_image = [item['name'] for item in image_collection.find({"owner_id": current_user.owner_id})]

        if not df['food_type'].isin(food_types).all():
            raise HTTPException(status_code=400, detail="Invalid food_type value")
        if not df['category'].isin(categories).all():
            raise HTTPException(status_code=400, detail="Invalid category value")
        if not df['name_image'].isin(name_image).all():
            raise HTTPException(status_code=400, detail="Invalid image_name value")

        menu_items = df.to_dict(orient='records')
        for item in menu_items:
            item["owner_id"] = current_user.owner_id

        result = menu_collection.insert_many(menu_items)

        inserted_ids = result.inserted_ids
        if not inserted_ids:
            raise HTTPException(status_code=500, detail="Failed to insert data into the database")

        logging.info(f"Data uploaded and validated successfully. Inserted IDs: {inserted_ids}")
        return {
            "message": "Data uploaded and validated successfully",
            "inserted_ids": [str(id) for id in inserted_ids]
        }

    except Exception as e:
        logging.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the file")
    















