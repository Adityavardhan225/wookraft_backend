from fastapi import APIRouter, Depends, HTTPException, Body, WebSocket, WebSocketDisconnect, Query
from pymongo.database import Database
from configurations.config import get_db
from routes.table_management.table_service import TableService
from routes.table_management.reservation_service import ReservationService
from routes.table_management.table_management_model import (
    TableCreate, TableUpdate, TableStatusUpdate, TableResponse,
    TableStatus, TableSection, TableShape,
    ReservationCreate, ReservationUpdate, ReservationResponse, ReservationStatus,
    FloorCreate, FloorUpdate, FloorResponse 
)
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import json
from bson import ObjectId
from fastapi.responses import JSONResponse
import asyncio
from threading import Lock

router = APIRouter()

# WebSocket manager for real-time table status updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.lock = Lock()
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        with self.lock:
            if client_id not in self.active_connections:
                self.active_connections[client_id] = []
            self.active_connections[client_id].append(websocket)
        
    def disconnect(self, websocket: WebSocket, client_id: str):
        with self.lock:
            if client_id in self.active_connections:
                self.active_connections[client_id].remove(websocket)
                if not self.active_connections[client_id]:
                    del self.active_connections[client_id]
            
    async def broadcast(self, message: Dict):
        disconnected = []
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except RuntimeError:
                    disconnected.append((connection, client_id))
        
        # Clean up disconnected connections
        for conn, client in disconnected:
            self.disconnect(conn, client)
                
    async def send_personal_message(self, message: Dict, client_id: str):
        if client_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except RuntimeError:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, client_id)

manager = ConnectionManager()

# Table Management Endpoints

# Add these Floor Management Endpoints after the table endpoints

# Floor Management Endpoints


# Add this import
import json
from datetime import datetime

# Add this helper function
def serialize_for_json(obj):
    """Convert datetime objects to ISO format strings for JSON serialization"""
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(i) for i in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj
    

@router.get("/tables/available", response_model=List[TableResponse])
async def get_available_tables(
    reservation_time: str = Query(..., description="Reservation date and time in ISO format"),
    party_size: int = Query(..., description="Number of people in the party"),
    duration_minutes: int = Query(90, description="Expected duration of the reservation in minutes"),
    db: Database = Depends(get_db)
):
    """
    Get tables available for a specific reservation time and party size
    """
    try:
        # Convert the reservation time string to datetime object
        date_obj = datetime.fromisoformat(reservation_time.replace('Z', '+00:00'))
        
        # Validate parameters
        if party_size <= 0:
            raise HTTPException(status_code=400, detail="Party size must be positive")
        
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="Duration must be positive")
        
        # Get reservation service
        reservation_service = ReservationService(db)
        
        # Find available tables using both methods for comprehensive results
        tables_by_size = reservation_service.find_available_tables(date_obj, party_size, duration_minutes)
        tables_by_time = reservation_service.find_available_tables_for_time(date_obj, duration_minutes)
        print("tables_by_size", tables_by_size)
        # Merge results and filter by party_size for the tables_by_time results
        available_tables = tables_by_size
        
        # Add tables from the time-based search that meet size requirements
        # and aren't already in the results
        existing_ids = {str(table["_id"]) for table in available_tables}
        
        for table in tables_by_time:
            table_id = str(table["_id"])
            if table_id not in existing_ids and table["capacity"] >= party_size:
                available_tables.append(table)
        print("available_tables", available_tables)
        # Sort by capacity to minimize wastage
        available_tables.sort(key=lambda t: t["capacity"])
        
        # Convert ObjectIDs to strings for all tables
        for table in available_tables:
            if "_id" in table:
                table["id"] = str(table["_id"])
                del table["_id"]
        print("available_tables 12223", available_tables)
        # Add availability status and reservation time info to each table
        for table in available_tables:
            table["availability"] = "AVAILABLE"
            table["reservation_time"] = date_obj.isoformat()
        print("available_tables 123", available_tables)  
        return available_tables
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format or value: {str(e)}")
    except Exception as e:
        logging.error(f"Error finding available tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

    
@router.post("/floors", response_model=FloorResponse)
async def create_floor(
    floor: FloorCreate,
    db: Database = Depends(get_db)
):
    """Create a new floor"""
    try:
        table_service = TableService(db)
        result = table_service.create_floor(floor.dict())
        result = serialize_for_json(result)
        
        # Broadcast floor creation to all clients
        await manager.broadcast({
            "type": "floor_created",
            "data": result
        })
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creating floor: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/floors", response_model=List[FloorResponse])
async def get_all_floors(db: Database = Depends(get_db)):
    """Get all floors"""
    try:
        table_service = TableService(db)
        return table_service.get_all_floors()
    except Exception as e:
        logging.error(f"Error getting floors: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/floors/{floor_id}", response_model=FloorResponse)
async def get_floor(
    floor_id: str,
    db: Database = Depends(get_db)
):
    """Get floor by ID"""
    try:
        table_service = TableService(db)
        return table_service.get_floor_by_id(floor_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting floor: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/floors/{floor_id}", response_model=FloorResponse)
async def update_floor(
    floor_id: str,
    floor_update: FloorUpdate,
    db: Database = Depends(get_db)
):
    """Update floor details"""
    try:
        table_service = TableService(db)
        updated_floor = table_service.update_floor(floor_id, floor_update.dict(exclude_unset=True))
        updated_floor = serialize_for_json(updated_floor)
        # Broadcast floor update to all clients
        await manager.broadcast({
            "type": "floor_updated",
            "data": updated_floor
        })
        
        return updated_floor
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating floor: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/floors/{floor_id}")
async def delete_floor(
    floor_id: str,
    db: Database = Depends(get_db)
):
    """Delete floor"""
    try:
        table_service = TableService(db)
        if table_service.delete_floor(floor_id):
            # Broadcast floor deletion to all clients
            await manager.broadcast({
                "type": "floor_deleted",
                "floor_id": floor_id
            })
            return {"message": "Floor deleted successfully"}
        raise HTTPException(status_code=404, detail="Floor not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error deleting floor: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/tables/floor/{floor_id}", response_model=List[TableResponse])
async def get_tables_by_floor(
    floor_id: str,
    db: Database = Depends(get_db)
):
    """Get tables by floor"""
    try:
        table_service = TableService(db)
        return table_service.get_tables_by_floor(floor_id)
    except Exception as e:
        logging.error(f"Error getting tables by floor: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.post("/tables", response_model=TableResponse)
async def create_table(
    table: TableCreate,
    db: Database = Depends(get_db)
):
    """Create a new table"""
    try:
        table_service = TableService(db)
        result = table_service.create_table(table.dict())
        result = serialize_for_json(result)
        
        # Broadcast table creation to all clients
        await manager.broadcast({
            "type": "table_created",
            "data": result
        })
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creating table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# @router.get("/tables", response_model=List[TableResponse])
# async def get_all_tables(
#     section: Optional[TableSection] = None,
#     status: Optional[TableStatus] = None,
#     floor_id: Optional[str] = None,
#     
#     db: Database = Depends(get_db)
# ):
#     """Get all tables with optional filtering"""
#     try:
#         table_service = TableService(db)

        
#         if status:
#             return table_service.get_tables_by_status(status)
#         elif floor_id:
#             tables = table_service.get_tables_by_floor(floor_id)
#         else:
#             tables = table_service.get_all_tables()
        
#         # tables = table_service.get_all_tables()
        
#         # Filter by section if provided
#         if section:
#             tables = [table for table in tables if table["section"] == section]
            
#         return tables
#     except Exception as e:
#         logging.error(f"Error getting tables: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/tables", response_model=List[TableResponse])
async def get_all_tables(
    section: Optional[TableSection] = None,
    status: Optional[TableStatus] = None,
    floor_id: Optional[str] = None,
    reservation_datetime: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """Get all tables with optional filtering, including reservation availability"""
    try:
        table_service = TableService(db)
        
        # Check if requesting tables for a specific reservation time
        if reservation_datetime:
            # Use the reservation service to find tables not reserved at that time
            reservation_service = ReservationService(db)
            date_obj = datetime.fromisoformat(reservation_datetime.replace('Z', '+00:00'))
            
            # Get all tables - filtered by floor_id if provided
            if floor_id:
                all_tables = table_service.get_tables_by_floor(floor_id)
            else:
                all_tables = table_service.get_all_tables()
            
            # Get reservations that overlap with the requested time
            # We're using a 2-hour default duration for checking conflicts
            end_date = date_obj + timedelta(minutes=120)
            
            conflicting_reservations = list(db.reservations.find({
                "reservation_date": {"$lt": end_date},
                "expected_end_time": {"$gt": date_obj},
                "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]}
            }))
            
            # Extract all table IDs that are reserved during the time period
            reserved_table_ids = set()
            for reservation in conflicting_reservations:
                if "table_ids" in reservation:
                    reserved_table_ids.update(reservation["table_ids"])
                    
            # Filter out tables that are already reserved
            tables = []
            for table in all_tables:
                table_id_str = table["id"]
                if table_id_str not in reserved_table_ids:
                    # Also check for upcoming reservation times
                    upcoming_time = table.get("upcoming_reservation_time")
                if upcoming_time and isinstance(upcoming_time, datetime):
                    # First check if upcoming reservation starts during our needed window
                    if upcoming_time >= date_obj and upcoming_time <= end_date:
                        continue
                        
                    # Then check if our requested time is during an existing reservation
                    reserved_until = table.get("reserved_until")
                    if reserved_until is not None and date_obj >= upcoming_time and date_obj <= reserved_until:
                        continue
                    tables.append(table)
        
        elif status:
            tables = table_service.get_tables_by_status(status)
        elif floor_id:
            tables = table_service.get_tables_by_floor(floor_id)
        else:
            tables = table_service.get_all_tables()
        
        # Filter by section if provided
        if section:
            tables = [table for table in tables if table.get("section") == section]
            
        return tables
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tables/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: str,
    db: Database = Depends(get_db)
):
    """Get table by ID"""
    try:
        table_service = TableService(db)
        return table_service.get_table_by_id(table_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/tables/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: str,
    table_update: TableUpdate,
    db: Database = Depends(get_db)
):
    """Update table details"""
    try:
        table_service = TableService(db)
        updated_table = table_service.update_table(table_id, table_update.dict(exclude_unset=True))
        updated_table = serialize_for_json(updated_table)
        
        # Broadcast table update to all clients
        await manager.broadcast({
            "type": "table_updated",
            "data": updated_table
        })
        
        return updated_table
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/tables/{table_id}/status", response_model=TableResponse)
async def update_table_status(
    table_id: str,
    status_update: TableStatusUpdate,
    db: Database = Depends(get_db)
):
    """Update table status"""
    try:
        table_service = TableService(db)
        updated_table = table_service.update_table_status(table_id, status_update.dict())

        updated_table = serialize_for_json(updated_table)
        
        # Broadcast table status update to all clients
        await manager.broadcast({
            "type": "table_status_updated",
            "data": updated_table
        })
        
        return updated_table
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating table status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/tables/{table_id}")
async def delete_table(
    table_id: str,
    db: Database = Depends(get_db)
):
    """Delete table"""
    try:
        table_service = TableService(db)
        if table_service.delete_table(table_id):
            # Broadcast table deletion to all clients
            await manager.broadcast({
                "type": "table_deleted",
                "table_id": table_id
            })
            return {"message": "Table deleted successfully"}
        raise HTTPException(status_code=404, detail="Table not found")
    except Exception as e:
        logging.error(f"Error deleting table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/tables/{table_id}/assign-order")
async def assign_order_to_table(
    table_id: str,
    order_id: str = Body(..., embed=True),
    employee_id: str = Body(None, embed=True),
    db: Database = Depends(get_db)
):
    """Assign an order to a table"""
    try:
        table_service = TableService(db)
        result = table_service.assign_order_to_table(table_id, order_id, employee_id)
        result = serialize_for_json(result)
        
        # Broadcast table update to all clients
        await manager.broadcast({
            "type": "table_order_assigned",
            "data": result
        })
        
        return {"message": "Order assigned to table successfully", "table": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error assigning order to table: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Reservation Management Endpoints
@router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(
    reservation: ReservationCreate,
    db: Database = Depends(get_db)
):
    """Create a new reservation"""
    try:
        reservation_service = ReservationService(db)
        print('999debug', reservation)
        result = reservation_service.create_reservation(reservation.dict())
        print('999222debug', result)
        result = serialize_for_json(result)
        print('999333debug', result)
        
        # Broadcast reservation creation to all clients
        await manager.broadcast({
            "type": "reservation_created",
            "data": result
        })
        
        # Send confirmation email
        asyncio.create_task(send_confirmation_email_async(reservation_service, str(result["id"])))
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error creating reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")



@router.get("/reservations_code/{reservation_code}", response_model=ReservationResponse)
async def get_reservation_by_code(
    reservation_code: str,
    db: Database = Depends(get_db)
):
    """Get reservation by code"""
    try:
        reservation_service = ReservationService(db)
        return reservation_service.get_reservation_by_code(reservation_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting reservation by code: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reservations", response_model=List[ReservationResponse])
async def get_reservations_by_date(
    date: str = Query(..., description="Date in ISO format (YYYY-MM-DD)"),
    include_completed: bool = False,
    db: Database = Depends(get_db)
):
    print('999debug', date, include_completed)
    """Get reservations by date"""
    try:
        reservation_service = ReservationService(db)
        date_obj = datetime.fromisoformat(date)
        return reservation_service.get_reservations_by_date(date_obj, include_completed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting reservations by date: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reservations_upcoming/{hours}", response_model=List[ReservationResponse])
async def get_upcoming_reservations(
    hours: int = 24,
    db: Database = Depends(get_db)
):
    """Get upcoming reservations for the next X hours"""
    try:
        reservation_service = ReservationService(db)
        return reservation_service.get_upcoming_reservations(hours)
    except Exception as e:
        logging.error(f"Error getting upcoming reservations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reservations_search/{query}", response_model=List[ReservationResponse])
async def search_reservations(
    query: str,
    db: Database = Depends(get_db)
):
    """Search for reservations"""
    try:
        reservation_service = ReservationService(db)
        return reservation_service.search_reservations(query)
    except Exception as e:
        logging.error(f"Error searching reservations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: str,
    reservation_update: ReservationUpdate,
    db: Database = Depends(get_db)
):
    """Update reservation details"""
    try:
        reservation_service = ReservationService(db)
        updated_reservation = reservation_service.update_reservation(
            reservation_id, 
            reservation_update.dict(exclude_unset=True)
        )
        updated_reservation = serialize_for_json(updated_reservation)
        
        # Broadcast reservation update to all clients
        await manager.broadcast({
            "type": "reservation_updated",
            "data": updated_reservation
        })
        
        return updated_reservation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error updating reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}/cancel", response_model=ReservationResponse)
async def cancel_reservation(
    reservation_id: str,
    reason: str = Body(None, embed=True),
    db: Database = Depends(get_db)
):
    """Cancel a reservation"""
    try:
        reservation_service = ReservationService(db)
        cancelled_reservation = reservation_service.cancel_reservation(reservation_id, reason)
        cancelled_reservation = serialize_for_json(cancelled_reservation)
        
        # Broadcast reservation cancellation to all clients
        await manager.broadcast({
            "type": "reservation_cancelled",
            "data": cancelled_reservation
        })
        
        return cancelled_reservation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error cancelling reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}/check-in", response_model=ReservationResponse)
async def check_in_reservation(
    reservation_id: str,
    table_ids: List[str] = Body(None, embed=True),
    employee_id: str = Body(None, embed=True),
    db: Database = Depends(get_db)
):
    """Check in a reservation"""
    try:
        reservation_service = ReservationService(db)
        checked_in_reservation = reservation_service.check_in_reservation(
            reservation_id, 
            table_ids, 
            employee_id
        )
        checked_in_reservation = serialize_for_json(checked_in_reservation)
        # Broadcast reservation check-in to all clients
        await manager.broadcast({
            "type": "reservation_checked_in",
            "data": checked_in_reservation
        })
        
        return checked_in_reservation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error checking in reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}/complete", response_model=ReservationResponse)
async def complete_reservation(
    reservation_id: str,
    db: Database = Depends(get_db)
):
    """Complete a reservation"""
    try:
        reservation_service = ReservationService(db)
        completed_reservation = reservation_service.complete_reservation(reservation_id)
        completed_reservation = serialize_for_json(completed_reservation)
        # Broadcast reservation completion to all clients
        await manager.broadcast({
            "type": "reservation_completed",
            "data": completed_reservation
        })
        
        return completed_reservation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error completing reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/reservations/{reservation_id}/no-show", response_model=ReservationResponse)
async def mark_reservation_no_show(
    reservation_id: str,
    db: Database = Depends(get_db)
):
    """Mark reservation as no-show"""
    try:
        reservation_service = ReservationService(db)
        no_show_reservation = reservation_service.mark_no_show(reservation_id)
        no_show_reservation = serialize_for_json(no_show_reservation)
        # Broadcast no-show update to all clients
        await manager.broadcast({
            "type": "reservation_no_show",
            "data": no_show_reservation
        })
        
        return no_show_reservation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error marking reservation as no-show: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reservations/{reservation_id}/send-confirmation")
async def send_confirmation_email(
    reservation_id: str,
    db: Database = Depends(get_db)
):
    """Send confirmation email for a reservation"""
    try:
        reservation_service = ReservationService(db)
        result = reservation_service.send_confirmation_email(reservation_id)
        return {"success": result}
    except Exception as e:
        logging.error(f"Error sending confirmation email: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.get("/reservations_stats/{start_date}/{end_date}")
async def get_reservation_stats(
    start_date: str,
    end_date: str,
    db: Database = Depends(get_db)
):
    print('9991debug', start_date, end_date)
    """Get reservation statistics for a date range"""
    try:
        reservation_service = ReservationService(db)
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        stats = reservation_service.get_stats_by_date_range(start, end)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting reservation stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reservations/{reservation_id}/send-reminder")
async def send_reminder_email(
    reservation_id: str,
    db: Database = Depends(get_db)
):
    """Send reminder email for a reservation"""
    try:
        reservation_service = ReservationService(db)
        result = reservation_service.send_reminder_email(reservation_id)
        return {"success": result}
    except Exception as e:
        logging.error(f"Error sending reminder email: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: str,
    db: Database = Depends(get_db)
):
    """Get reservation by ID"""
    try:
        reservation_service = ReservationService(db)
        return reservation_service.get_reservation_by_id(reservation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"Error getting reservation: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    

@router.post("/system/process-overdue-reservations")
async def process_overdue_reservations(
    db: Database = Depends(get_db)
):
    """Process overdue reservations (admin only)"""
    try:
        reservation_service = ReservationService(db)
        count = reservation_service.process_overdue_reservations()
        return {"message": f"Processed {count} overdue reservations"}
    except Exception as e:
        logging.error(f"Error processing overdue reservations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Utility functions
async def send_confirmation_email_async(reservation_service, reservation_id):
    """Asynchronously send confirmation email"""
    try:
        reservation_service.send_confirmation_email(reservation_id)
    except Exception as e:
        logging.error(f"Error in async email sending: {str(e)}")





# WebSocket endpoint for real-time table updates
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    db: Database = Depends(get_db)
):
    await manager.connect(websocket, client_id)
    
    try:
        # Send initial data when client connects
        table_service = TableService(db)
        tables = table_service.get_all_tables()
        floors = table_service.get_all_floors()
        tables = serialize_for_json(tables)
        floors = serialize_for_json(floors)
        
        await websocket.send_json({
            "type": "initial_data",
            "tables": tables,
            "floors": floors  
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif message["type"] == "update_table_status":
                table_id = message["table_id"]
                status_data = message["status_data"]
                
                # Update table status
                updated_table = table_service.update_table_status(table_id, status_data)
                updated_table = serialize_for_json(updated_table)
                print("updated_table", updated_table)
                # Broadcast update to all clients
                await manager.broadcast({
                    "type": "table_status_updated",
                    "data": updated_table
                })

                
            elif message["type"] == "request_refresh":
                # Send fresh data to requesting client
                tables = table_service.get_all_tables()
                print("updated_table", tables)
                tables = serialize_for_json(tables) 
                
                await websocket.send_json({
                    "type": "refresh_data",
                    "tables": tables
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket, client_id)





























