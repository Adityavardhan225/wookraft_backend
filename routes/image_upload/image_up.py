from fastapi import Depends, FastAPI, File, UploadFile, HTTPException, APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional
import cloudinary.uploader
from bson import ObjectId
import os
from configurations.config import client
import cloudinary
import logging
from routes.security.protected_authorise import get_current_user


router=APIRouter()


# cloudinary.config(
#         cloud_name = 'dl91gwshv', 
#         api_key = '392761399558392', 
#         api_secret = 'N8dW3ksMCt41qCfzFeobTh701hM' 
# )

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

db=client["wookraft_db"]
image_collection=db["food_images"]




class ImageModel(BaseModel):
    id: str
    name:str
    transformed_url: str
    owner_id:str


@router.post("/upload", response_model=ImageModel)
async def upload_image(name: str = Query(...), file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:

        if image_collection.find_one({"name": name}):
            raise HTTPException(status_code=400, detail="image name already exists")
        # Transform and upload image to Cloudinary
        result = cloudinary.uploader.upload(file.file, folder="uploads", transformation=[
            {'width': 1000, 'crop': "scale"},
            {'quality': "auto"},
            {'fetch_format': "auto"}
        ])
        transformed_url = result.get("url")
        public_id = result.get("public_id")

        # Save to MongoDB
        image_data = {
            "name": name,
            "transformed_url": transformed_url,
            "public_id": public_id,
            "owner_id": current_user.owner_id
        }
        insert_result = image_collection.insert_one(image_data)
        saved_image = {
            "id": str(insert_result.inserted_id),
            "name": name,
            "transformed_url": transformed_url,
            "owner_id": current_user.owner_id
        }

        return saved_image
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/images", response_model=List[ImageModel])
async def get_images(current_user: dict = Depends(get_current_user)):
    image = list(image_collection.find({"owner_id": current_user["id"]}))
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return {
            "id": str(image["_id"]),
            "name": image["name"],
            "transformed_url": image["transformed_url"],
            "owner_id":image["owner_id"]
        }
        

@router.get("/images/{image_id}", response_model=ImageModel)
async def get_image(image_id: str, current_user: dict = Depends(get_current_user)):
    image = image_collection.find_one({"_id": ObjectId(image_id), "owner_id": current_user["owner_id"]})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "id": str(image["_id"]),
        "name": image["name"],
        "transformed_url": image["transformed_url"],
        "owner_id":image["owner_id"]
    }

@router.get("/images/name/{image_name}", response_model=ImageModel)
async def get_image_by_name(image_name: str, current_user: dict = Depends(get_current_user)):
    image = image_collection.find_one({"name": image_name, "owner_id": current_user["owner_id"]})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return {
        "id": str(image["_id"]),
        "name": image["name"],
        "transformed_url": image["transformed_url"],
        "owner_id":image["owner_id"]
    }






@router.delete("/images", response_model=dict)
async def delete_image(image_id: Optional[str] = None, image_name: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        if image_id:
            if not ObjectId.is_valid(image_id):
                raise HTTPException(status_code=400, detail="Invalid ObjectId")
            image = image_collection.find_one({"_id": ObjectId(image_id),"owner_id": current_user["owner_id"]})
        elif image_name:
            image = image_collection.find_one({"name": image_name,"owner_id": current_user["owner_id"]})
        else:
            raise HTTPException(status_code=400, detail="Either image_id or image_name must be provided")

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Delete image from Cloudinary
        public_id = image.get("public_id")
        if not public_id:
            raise HTTPException(status_code=500, detail="Public ID not found in the image document")

        cloudinary.uploader.destroy(public_id)

        # Delete image from MongoDB
        image_collection.delete_one({"_id": image["_id"]})

        return {"message": "Image deleted successfully"}
    except Exception as e:
        logging.error(f"Error deleting image: {e}")
        raise HTTPException(status_code=500, detail=str(e))












































from typing import List, Dict
import asyncio
from fastapi import UploadFile, File, Form

class BulkImageResponse(BaseModel):
    successful: List[ImageModel]
    failed: List[Dict[str, str]]

@router.post("/upload/image_bulk", response_model=BulkImageResponse)
async def upload_multiple_images(
    files: List[UploadFile] = File(...),
    names: List[str] = Form(...),
    current_user: dict = Depends(get_current_user)
):
    if len(files) != len(names):
        raise HTTPException(
            status_code=400, 
            detail="Number of files and names must match"
        )

    # Check for duplicate names
    existing_images = image_collection.find(
        {"name": {"$in": names}, "owner_id": current_user.owner_id}
    )
    if list(existing_images):
        raise HTTPException(
            status_code=400,
            detail="One or more image names already exist"
        )

    successful_uploads = []
    failed_uploads = []

    async def upload_single(file: UploadFile, name: str):
        try:
            result = cloudinary.uploader.upload(
                file.file,
                folder="uploads",
                transformation=[
                    {'width': 1000, 'crop': "scale"},
                    {'quality': "auto"},
                    {'fetch_format': "auto"}
                ]
            )

            image_data = {
                "name": name,
                "transformed_url": result.get("url"),
                "public_id": result.get("public_id"),
                "owner_id": current_user.owner_id
            }

            insert_result = image_collection.insert_one(image_data)
            successful_uploads.append({
                "id": str(insert_result.inserted_id),
                "name": name,
                "transformed_url": result.get("url"),
                "owner_id": current_user.owner_id
            })

        except Exception as e:
            failed_uploads.append({
                "name": name,
                "error": str(e)
            })

    # Process all uploads concurrently
    await asyncio.gather(
        *[upload_single(file, name) for file, name in zip(files, names)]
    )

    return {
        "successful": successful_uploads,
        "failed": failed_uploads
    }