from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from routes.table_management.table_management_model import TableStatus, OrderStatus
import logging
import random
import string

class TableService:
    def __init__(self, db: Database):
        self.db = db
        self.ensure_indexes()
        
    def ensure_indexes(self):
        """Create necessary indexes for table management"""
        try:
            self.db.tables.create_index("table_number", unique=True)
            self.db.tables.create_index("status")
            self.db.tables.create_index("section")
            self.db.tables.create_index("employee_id")
            self.db.tables.create_index("floor_id")
        except Exception as e:
            logging.error(f"Error creating table indexes: {str(e)}")


    def create_floor(self, floor_data: Dict) -> Dict:
        """Create a new floor"""
        # Check if floor number already exists
        existing = self.db.floors.find_one({"floor_number": floor_data["floor_number"]})
        if existing:
            raise ValueError(f"Floor number {floor_data['floor_number']} already exists")
            
        floor_data["created_at"] = datetime.now()
        floor_data["updated_at"] = datetime.now()
        
        result = self.db.floors.insert_one(floor_data)
        return self.get_floor_by_id(str(result.inserted_id))

    def get_floor_by_id(self, floor_id: str) -> Dict:
        """Get floor by ID"""
        floor = self.db.floors.find_one({"_id": ObjectId(floor_id)})
        if not floor:
            raise ValueError(f"Floor with ID {floor_id} not found")
        
        # Convert ObjectId to string
        floor["id"] = str(floor["_id"])
        del floor["_id"]
        
        return floor

    def get_all_floors(self) -> List[Dict]:
        """Get all floors"""
        floors = list(self.db.floors.find().sort("floor_number", 1))
        
        result = []
        for floor in floors:
            floor["id"] = str(floor["_id"])
            del floor["_id"]
            result.append(floor)
        
        return result

    def update_floor(self, floor_id: str, update_data: Dict) -> Dict:
        """Update floor details"""
        update_data["updated_at"] = datetime.now()
        
        result = self.db.floors.update_one(
            {"_id": ObjectId(floor_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Floor with ID {floor_id} not found or no changes made")
            
        return self.get_floor_by_id(floor_id)

    def delete_floor(self, floor_id: str) -> bool:
        """Delete a floor"""
        # Check if tables exist for this floor
        tables = self.db.tables.find_one({"floor_id": floor_id})
        if tables:
            raise ValueError("Cannot delete floor with assigned tables")
        
        result = self.db.floors.delete_one({"_id": ObjectId(floor_id)})
        return result.deleted_count > 0

    def get_tables_by_floor(self, floor_id: str) -> List[Dict]:
        """Get tables by floor"""
        tables = list(self.db.tables.find({"floor_id": floor_id}).sort("table_number", 1))
        now = datetime.now()
        tables_to_update = []
        # Process each table
        result = []
        for table in tables:
            print('Debug table is', table)
            
            # Convert ObjectId to string
            if (table.get("upcoming_reservation_time") and 
                
                isinstance(table["upcoming_reservation_time"], datetime) and
                now >= (table["upcoming_reservation_time"] - timedelta(minutes=30)) and
                now < table["upcoming_reservation_time"] and
                table["status"] == TableStatus.VACANT):
                print(f'debug table is table12344{table.get("upcoming_reservation_time")}')
                # Update status dynamically
                table["status"] = TableStatus.RESERVED
                tables_to_update.append(ObjectId(str(table["_id"])))

                
            # Convert ObjectId to string
            
            table["id"] = str(table["_id"])
            del table["_id"]
            
            # Add employee name if employee is assigned
            if table.get("employee_id"):
                try:
                    employee = self.db.employees.find_one({"_id": table["employee_id"]})
                    if employee:
                        table["employee_name"] = employee.get("name", "Unknown")
                except Exception as e:
                    logging.error(f"Error getting employee details: {str(e)}")
            
            # Add order status information if order is linked
            if table.get("order_id"):
                try:
                    order = self.db.orders.find_one({"_id": ObjectId(table["order_id"])})
                    if order:
                        table["order_status"] = order.get("status")
                        table["active_order_items"] = order.get("items", [])
                except Exception as e:
                    logging.error(f"Error getting order details: {str(e)}")
            
            result.append(table)
        if tables_to_update:
            for table_id in tables_to_update:
                self.db.tables.update_one(
                    {"_id": table_id},
                    {
                        "$set": {"status": TableStatus.RESERVED},
                        "$push": {
                            "status_history": {
                                "status": TableStatus.RESERVED,
                                "timestamp": now,
                                "auto_reserved": True
                            }
                        }
                    }
                )
        
        return result
        
    def create_table(self, table_data: Dict) -> Dict:
        """Create a new table in the database"""
        # Check if table number already exists
        existing = self.db.tables.find_one({"table_number": table_data["table_number"]})
        if existing:
            raise ValueError(f"Table number {table_data['table_number']} already exists")
            
        # Add default fields
        table_data["status"] = TableStatus.VACANT
        table_data["created_at"] = datetime.now()
        table_data["updated_at"] = datetime.now()
        table_data["status_history"] = [
            {"status": TableStatus.VACANT, "timestamp": datetime.now()}
        ]
        
        result = self.db.tables.insert_one(table_data)
        return self.get_table_by_id(str(result.inserted_id))
    
    def update_table(self, table_id: str, update_data: Dict) -> Dict:
        """Update table details"""
        update_data["updated_at"] = datetime.now()
        
        result = self.db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise ValueError(f"Table with ID {table_id} not found or no changes made")
            
        return self.get_table_by_id(table_id)
    
    def update_table_status(self, table_id: str, status_data: Dict) -> Dict:
        """Update table status and related information"""
        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
        if not table:
            raise ValueError(f"Table with ID {table_id} not found")
            
        # Create update document
        update_doc = {
            "status": status_data["status"],
            "updated_at": datetime.now()
        }
        
        # Add optional fields if provided
        for field in ["employee_id", "order_id", "customer_count", "notes"]:
            if field in status_data and status_data[field] is not None:
                update_doc[field] = status_data[field]
        
        # Special handling for status transitions
        if status_data["status"] == TableStatus.OCCUPIED and table["status"] != TableStatus.OCCUPIED:
            update_doc["occupied_since"] = datetime.now()
        
        if status_data["status"] == TableStatus.VACANT:
            # Clear related fields when table becomes vacant
            update_doc["employee_id"] = None
            update_doc["order_id"] = None
            update_doc["customer_count"] = None
            update_doc["occupied_since"] = None
            update_doc["reserved_until"] = None
            
        # Update the document
        self.db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {
                "$set": update_doc,
                "$push": {
                    "status_history": {
                        "status": status_data["status"],
                        "timestamp": datetime.now(),
                        "employee_id": status_data.get("employee_id")
                    }
                }
            }
        )
        
        # Get updated table with related information
        return self.get_table_by_id(table_id)
    
    def get_table_by_id(self, table_id: str) -> Dict:
        """Get table by ID with enhanced information"""
        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
        if not table:
            raise ValueError(f"Table with ID {table_id} not found")
        
        # Convert ObjectId to string
        table["id"] = str(table["_id"])
        del table["_id"]

        now = datetime.now()
        if (table.get("upcoming_reservation_time") and 
            isinstance(table["upcoming_reservation_time"], datetime) and
            now >= (table["upcoming_reservation_time"] - timedelta(minutes=30)) and
            now < table["upcoming_reservation_time"] and
            table["status"] == TableStatus.VACANT):
            
            # Dynamically update status to RESERVED
            table["status"] = TableStatus.RESERVED
            
            # Persist the status change to the database
            self.db.tables.update_one(
                {"_id": ObjectId(table_id)},
                {
                    "$set": {"status": TableStatus.RESERVED},
                    "$push": {
                        "status_history": {
                            "status": TableStatus.RESERVED,
                            "timestamp": now,
                            "auto_reserved": True
                        }
                    }
                }
            )
        
        # Add employee name if employee is assigned
        if table.get("employee_id"):
            employee = self.db.employees.find_one({"_id": table["employee_id"]})
            if employee:
                table["employee_name"] = employee.get("name", "Unknown")
        
        # Add order status information if order is linked
        if table.get("order_id"):
            try:
                order = self.db.orders.find_one({"_id": ObjectId(table["order_id"])})
                if order:
                    table["order_status"] = order.get("status")
                    table["active_order_items"] = order.get("items", [])
            except Exception as e:
                logging.error(f"Error retrieving order details: {str(e)}")
        
        return table
    
    def get_all_tables(self) -> List[Dict]:
        """Get all tables with enhanced information"""
        tables = list(self.db.tables.find().sort("table_number", 1))
        now = datetime.now()
        tables_to_update = []
        
        # Process each table
        result = []
        for table in tables:

            if (table.get("upcoming_reservation_time") and 
                isinstance(table["upcoming_reservation_time"], datetime) and
                now >= (table["upcoming_reservation_time"] - timedelta(minutes=30)) and
                now < table["upcoming_reservation_time"] and
                table["status"] == TableStatus.VACANT):
                
                # Update status dynamically
                table["status"] = TableStatus.RESERVED
                tables_to_update.append(table["_id"])
            # Convert ObjectId to string
            table["id"] = str(table["_id"])
            del table["_id"]
            
            # Add employee name if employee is assigned
            if table.get("employee_id"):
                try:
                    employee = self.db.employees.find_one({"_id": table["employee_id"]})
                    if employee:
                        table["employee_name"] = employee.get("name", "Unknown")
                except Exception as e:
                    logging.error(f"Error getting employee details: {str(e)}")
            
            # Add order status information if order is linked
            if table.get("order_id"):
                try:
                    order = self.db.orders.find_one({"_id": ObjectId(table["order_id"])})
                    if order:
                        table["order_status"] = order.get("status")
                        table["active_order_items"] = order.get("items", [])
                except Exception as e:
                    logging.error(f"Error getting order details: {str(e)}")
            
            result.append(table)  
        if tables_to_update:
                for table_id in tables_to_update:
                    self.db.tables.update_one(
                        {"_id": table_id},
                        {
                            "$set": {"status": TableStatus.RESERVED},
                            "$push": {
                                "status_history": {
                                    "status": TableStatus.RESERVED,
                                    "timestamp": now,
                                    "auto_reserved": True
                                }
                            }
                        }
                    )


        
            
            
        
        return result
    
    def delete_table(self, table_id: str) -> bool:
        """Delete a table"""
        result = self.db.tables.delete_one({"_id": ObjectId(table_id)})
        return result.deleted_count > 0
    
    def assign_order_to_table(self, table_id: str, order_id: str, employee_id: str = None) -> Dict:
        """Assign an order to a table"""
        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
        if not table:
            raise ValueError(f"Table with ID {table_id} not found")
        
        # Update table with order information
        update_doc = {
            "order_id": order_id,
            "status": TableStatus.OCCUPIED,
            "updated_at": datetime.now()
        }
        
        if employee_id:
            update_doc["employee_id"] = employee_id
            
        if table["status"] != TableStatus.OCCUPIED:
            update_doc["occupied_since"] = datetime.now()
            
        # Update the document
        self.db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {
                "$set": update_doc,
                "$push": {
                    "status_history": {
                        "status": TableStatus.OCCUPIED,
                        "timestamp": datetime.now(),
                        "employee_id": employee_id,
                        "order_id": order_id
                    }
                }
            }
        )
        
        # Get updated table with related information
        return self.get_table_by_id(table_id)
    




    def find_available_tables_for_time(self, reservation_time: datetime, duration_minutes: int = 90) -> List[Dict]:
        """
        Find tables available for a specific reservation time.
        Checks if tables are free during the entire duration window.
        
        Args:
            reservation_time: When the reservation starts
            duration_minutes: How long the reservation lasts
        
        Returns:
            List of available tables
        """
        # Calculate window end time
        reservation_end = reservation_time + timedelta(minutes=duration_minutes)
        
        # Get all tables
        all_tables = self.get_all_tables()
        
        # Filter out tables that have upcoming reservations during our window
        available_tables = []
        for table in all_tables:
            # Skip tables that are under maintenance
            if table["status"] == TableStatus.MAINTENANCE:
                continue
                
            # Check if table has an upcoming reservation that would conflict
            upcoming_time = table.get("upcoming_reservation_time")
            reserved_until = table.get("reserved_until")
            
            is_available = True
            
            # Case 1: Table has an upcoming reservation
            if upcoming_time and isinstance(upcoming_time, datetime):
                # If our reservation ends after their reservation starts, conflict
                if reservation_end > upcoming_time:
                    is_available = False
                    
            # Case 2: Table is already reserved but will be free before our time
            if reserved_until and isinstance(reserved_until, datetime):
                # If their reservation ends after our reservation starts, conflict
                if reserved_until > reservation_time:
                    is_available = False
                    
            # Consider current status - only VACANT tables can be booked
            # Unless the booking is far in the future
            reservation_is_soon = reservation_time < (datetime.now() + timedelta(hours=1))
            if reservation_is_soon and table["status"] not in [TableStatus.VACANT]:
                is_available = False
                
            if is_available:
                available_tables.append(table)
                
        return available_tables




        
    def get_tables_by_status(self, status: str) -> List[Dict]:
        """Get tables by status"""
        tables = list(self.db.tables.find({"status": status}).sort("table_number", 1))
        
        # Process each table
        result = []
        for table in tables:
            # Convert ObjectId to string
            table["id"] = str(table["_id"])
            del table["_id"]
            
            # Add employee name if employee is assigned
            if table.get("employee_id"):
                try:
                    employee = self.db.employees.find_one({"_id": table["employee_id"]})
                    if employee:
                        table["employee_name"] = employee.get("name", "Unknown")
                except Exception as e:
                    logging.error(f"Error getting employee details: {str(e)}")
            
            # Add order status information if order is linked
            if table.get("order_id"):
                try:
                    order = self.db.orders.find_one({"_id": ObjectId(table["order_id"])})
                    if order:
                        table["order_status"] = order.get("status")
                        table["active_order_items"] = order.get("items", [])
                except Exception as e:
                    logging.error(f"Error getting order details: {str(e)}")
            
            result.append(table)
        
        return result
    
    def get_tables_by_section(self, section: str) -> List[Dict]:
        """Get tables by section"""
        tables = list(self.db.tables.find({"section": section}).sort("table_number", 1))
        
        # Process each table
        result = []
        for table in tables:
            # Convert ObjectId to string
            table["id"] = str(table["_id"])
            del table["_id"]
            
            # Add employee name if employee is assigned
            if table.get("employee_id"):
                try:
                    employee = self.db.employees.find_one({"_id": table["employee_id"]})
                    if employee:
                        table["employee_name"] = employee.get("name", "Unknown")
                except Exception as e:
                    logging.error(f"Error getting employee details: {str(e)}")
            
            # Add order status information if order is linked
            if table.get("order_id"):
                try:
                    order = self.db.orders.find_one({"_id": ObjectId(table["order_id"])})
                    if order:
                        table["order_status"] = order.get("status")
                        table["active_order_items"] = order.get("items", [])
                except Exception as e:
                    logging.error(f"Error getting order details: {str(e)}")
            
            result.append(table)
        
        return result
    
    def get_available_tables(self, party_size: int = None, section: str = None) -> List[Dict]:
        """
        Get available tables with optional filters
        
        Args:
            party_size: Minimum capacity required
            section: Table section
        
        Returns:
            List of available tables
        """
        query = {"status": TableStatus.VACANT}
        
        if party_size:
            query["capacity"] = {"$gte": party_size}
            
        if section:
            query["section"] = section
            
        tables = list(self.db.tables.find(query).sort("capacity", 1))
        
        # Process each table
        result = []
        for table in tables:
            # Convert ObjectId to string
            table["id"] = str(table["_id"])
            del table["_id"]
            result.append(table)
            
        return result