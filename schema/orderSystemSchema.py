from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserOutput(BaseModel):
    id: str
    username: str
    role: str
    owner_id: Optional[str] = None
    employee_id: Optional[str] = None






class OrderItem(BaseModel):
    
    name:str
    quantity: int
    customization: Dict[str, Any] = {  # Changed from Optional[str] to Dict[str, Any]
        "text": "",
        "addons": [],
        "size": None
    }
    # customization: Optional[str] = None
    food_type: Optional[str] = None
    food_category: Optional[str] = None
    prepared_items: bool = False
    price: float
    discounted_price: Optional[float] = None
    # addons: Optional[List[Dict[str, Any]]] = None
    promotion: Optional[Dict[str, Any]] = None
    # sizes: Optional[Dict[str, Dict[str, Any]]] = None

class Order(BaseModel):
    id: str
    table_number: int
    items: List[OrderItem]=[]
    status: str
    employee_id: str
    owner_id: str
    overall_customization: Optional[str] = None
    received:bool =False
    timestamp: datetime=datetime.now()
    prepared:bool=False
    payment_status: str = "unpaid" 

