from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import Optional, List
from datetime import datetime
import qrcode
import io
import base64
from pydantic import BaseModel
from bson import ObjectId
from configurations.config import client
from routes.security.protected_authorise import get_current_user
from fpdf import FPDF

router = APIRouter()
db = client["wookraft_db"]
qr_collection = db["qr_codes"]

class QRCodeBase(BaseModel):
    owner_id: str
    url: str
    qr_image: str
    qr_type: str  # "restaurant" or "table"
    table_number: Optional[int] = None
    expiry_date: Optional[datetime] = None

class QRCodeResponse(BaseModel):
    id: str
    qr_image: str
    url: str
    table_number: Optional[int] = None
    expiry_date: Optional[datetime] = None

@router.post("/generate/restaurant", response_model=QRCodeResponse)
async def generate_restaurant_qr(
    expiry_date: Optional[datetime] = None,
    size: int = Query(10, description="Size of the QR code"),
    border: int = Query(5, description="Border size of the QR code"),
    current_user: dict = Depends(get_current_user)
):
    """Generate restaurant-wide QR code"""
    owner_id = current_user.owner_id
    
    # Check if restaurant QR exists
    existing_qr = qr_collection.find_one({
        "owner_id": owner_id,
        "qr_type": "restaurant"
    })
    
    if existing_qr:
        return {
            "id": str(existing_qr["_id"]),
            "qr_image": existing_qr["qr_image"],
            "url": existing_qr["url"],
            "expiry_date": existing_qr.get("expiry_date")
        }

    # Generate QR code
    url = f"https://your-domain.com/restaurant/{owner_id}"
    qr = qrcode.QRCode(version=1, box_size=size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    
    # Convert QR to base64
    img_byte_arr = io.BytesIO()
    qr.make_image().save(img_byte_arr, format='PNG')
    qr_image = base64.b64encode(img_byte_arr.getvalue()).decode()

    # Save to DB
    qr_data = {
        "owner_id": owner_id,
        "url": url,
        "qr_image": qr_image,
        "qr_type": "restaurant",
        "expiry_date": expiry_date
    }
    result = qr_collection.insert_one(qr_data)

    return {
        "id": str(result.inserted_id),
        "qr_image": qr_image,
        "url": url,
        "expiry_date": expiry_date
    }

@router.post("/generate/table/{table_number}", response_model=QRCodeResponse)
async def generate_table_qr(
    table_number: int,
    expiry_date: Optional[datetime] = None,
    size: int = Query(10, description="Size of the QR code"),
    border: int = Query(5, description="Border size of the QR code"),
    current_user: dict = Depends(get_current_user)
):
    """Generate table-specific QR code"""
    owner_id = current_user.owner_id
    
    # Check if table QR exists
    existing_qr = qr_collection.find_one({
        "owner_id": owner_id,
        "qr_type": "table",
        "table_number": table_number
    })
    
    if existing_qr:
        return {
            "id": str(existing_qr["_id"]),
            "qr_image": existing_qr["qr_image"],
            "url": existing_qr["url"],
            "table_number": table_number,
            "expiry_date": existing_qr.get("expiry_date")
        }

    # Generate QR code
    url = f"https://your-domain.com/restaurant/{owner_id}/table/{table_number}"
    qr = qrcode.QRCode(version=1, box_size=size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    
    # Convert QR to base64
    img_byte_arr = io.BytesIO()
    qr.make_image().save(img_byte_arr, format='PNG')
    qr_image = base64.b64encode(img_byte_arr.getvalue()).decode()

    # Save to DB
    qr_data = {
        "owner_id": owner_id,
        "url": url,
        "qr_image": qr_image,
        "qr_type": "table",
        "table_number": table_number,
        "expiry_date": expiry_date
    }
    result = qr_collection.insert_one(qr_data)

    return {
        "id": str(result.inserted_id),
        "qr_image": qr_image,
        "url": url,
        "table_number": table_number,
        "expiry_date": expiry_date
    }

@router.get("/download/{qr_id}")
async def download_qr(
    qr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download QR code as an image file"""
    owner_id = current_user.owner_id
    
    # Find QR code by ID
    qr = qr_collection.find_one({
        "_id": ObjectId(qr_id),
        "owner_id": owner_id
    })
    
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")

    # Decode base64 image
    qr_image = base64.b64decode(qr["qr_image"])
    
    return Response(
        content=qr_image,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=qr_{qr_id}.png"}
    )

@router.get("/download/pdf/{qr_id}")
async def download_qr_pdf(
    qr_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Download QR code as a PDF file"""
    owner_id = current_user.owner_id
    
    # Find QR code by ID
    qr = qr_collection.find_one({
        "_id": ObjectId(qr_id),
        "owner_id": owner_id
    })
    
    if not qr:
        raise HTTPException(status_code=404, detail="QR code not found")

    # Decode base64 image
    qr_image = base64.b64decode(qr["qr_image"])
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.image(io.BytesIO(qr_image), x=10, y=10, w=100, h=100)
    
    # Convert PDF to bytes
    pdf_output = io.BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    
    return Response(
        content=pdf_output.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=qr_{qr_id}.pdf"}
    )