from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class TableStatus(str, Enum):
    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"
    CLEANING = "CLEANING"

class TableSection(str, Enum):
    MAIN = "MAIN"
    OUTDOOR = "OUTDOOR"
    PRIVATE = "PRIVATE"
    BAR = "BAR"
    ROOFTOP = "ROOFTOP"

class TableShape(str, Enum):
    SQUARE = "SQUARE"
    ROUND = "ROUND"
    RECTANGULAR = "RECTANGULAR"
    OVAL = "OVAL"

class OrderStatus(str, Enum):
    ORDERED = "ordered"
    PREPARING = "preparing"
    PARTIALLY_SERVED = "partially_served"
    SERVED = "served"
    BILL_REQUESTED = "bill_requested"
    PAYMENT_COMPLETED = "payment_completed"

class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

# Table Models



# Floor Models - Add these at the end of the file
class FloorCreate(BaseModel):
    floor_number: int
    name: str
    description: Optional[str] = None

class FloorUpdate(BaseModel):
    floor_number: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None

class FloorResponse(BaseModel):
    id: str
    floor_number: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime



class TableCreate(BaseModel):
    table_number: int
    capacity: int
    section: TableSection = TableSection.MAIN
    shape: TableShape = TableShape.SQUARE
    position_x: float = 0  # For visual positioning in floor plan
    position_y: float = 0
    description: Optional[str] = None
    floor_id: Optional[str] = None

class TableUpdate(BaseModel):
    capacity: Optional[int] = None
    section: Optional[TableSection] = None
    shape: Optional[TableShape] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    description: Optional[str] = None

class TableStatusUpdate(BaseModel):
    status: TableStatus
    employee_id: Optional[str] = None
    order_id: Optional[str] = None
    customer_count: Optional[int] = None
    notes: Optional[str] = None

class TableResponse(BaseModel):
    id: str
    table_number: int
    capacity: int
    section: TableSection
    shape: TableShape
    position_x: float
    position_y: float
    description: Optional[str] = None
    status: TableStatus
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    order_id: Optional[str] = None
    order_status: Optional[str] = None
    customer_count: Optional[int] = None
    occupied_since: Optional[datetime] = None
    reserved_until: Optional[datetime] = None
    notes: Optional[str] = None
    floor_id: Optional[str] = None  # Add this line
    floor_name: Optional[str] = None  # Add this line
    floor_number: Optional[int] = None  # Add this line
    created_at: datetime
    updated_at: datetime
    upcoming_reservation_time: Optional[datetime] = None
    reserved_until: Optional[datetime] = None

# Reservation Models
class ReservationCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    party_size: int
    reservation_date: datetime
    expected_duration_minutes: int = 90
    special_requests: Optional[str] = None
    table_preference: Optional[str] = None

class ReservationUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    party_size: Optional[int] = None
    reservation_date: Optional[datetime] = None
    expected_duration_minutes: Optional[int] = None
    special_requests: Optional[str] = None
    status: Optional[ReservationStatus] = None
    table_ids: Optional[List[str]] = None
    assigned_employee_id: Optional[str] = None

class ReservationResponse(BaseModel):
    id: str
    customer_name: str
    customer_phone: str
    customer_email: Optional[str] = None
    party_size: int
    reservation_date: datetime
    expected_duration_minutes: int
    special_requests: Optional[str] = None
    status: ReservationStatus
    table_ids: List[str] = []
    assigned_employee_id: Optional[str] = None
    reservation_code: str
    created_at: datetime
    updated_at: datetime
    tables: Optional[List[Dict[str, Any]]] = None