from pymongo.database import Database
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from routes.table_management.table_management_model import (
    TableStatus, ReservationStatus, ReservationCreate,
    ReservationUpdate, ReservationResponse
)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from configurations.config import settings
import random
import string
from fastapi import HTTPException


class ReservationService:
    def __init__(self, db: Database):
        """Initialize the reservation service with database connection"""
        self.db = db
        self.ensure_indexes()
        
    def ensure_indexes(self):
        """Create necessary indexes for reservation collection"""
        self.db.reservations.create_index("reservation_date")
        self.db.reservations.create_index("status")
        self.db.reservations.create_index("customer_phone")
        self.db.reservations.create_index("customer_email")
        self.db.reservations.create_index("reservation_code", unique=True)
        self.db.reservations.create_index([("reservation_date", 1), ("status", 1)])
        
    def generate_reservation_code(self) -> str:
        """Generate a unique reservation code"""
        while True:
            # Generate a random code with RS prefix
            code = "RS" + ''.join(random.choices(string.digits, k=5))
            
            # Check if code already exists
            existing = self.db.reservations.find_one({"reservation_code": code})
            if not existing:
                return code
                
    def find_available_tables(self, date: datetime, party_size: int, duration_minutes: int = 90) -> List[Dict]:
        """
        Find tables that are available for the given date and party size
        
        Args:
            date: Desired reservation datetime
            party_size: Number of people in the party
            duration_minutes: Expected duration of the reservation
            
        Returns:
            List of available table documents
        """
        # Calculate the end time of the potential reservation
        end_date = date + timedelta(minutes=duration_minutes)
        
        # Find all tables with sufficient capacity
        all_suitable_tables = list(self.db.tables.find({"capacity": {"$gte": party_size}}))
        
        # If no tables have enough capacity, return empty list
        if not all_suitable_tables:
            return []
        
        # Find existing reservations that overlap with the requested time
        conflicting_reservations = list(self.db.reservations.find({
            "reservation_date": {"$lt": end_date},
            "expected_end_time": {"$gt": date},
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]}
        }))
        
        # Extract all table IDs that are reserved during the time period
        reserved_table_ids = set()
        for reservation in conflicting_reservations:
            if "table_ids" in reservation:
                reserved_table_ids.update(reservation["table_ids"])
            
        # Filter out tables that are already reserved
        available_tables = []
        for table in all_suitable_tables:
            table_id_str = str(table["_id"])
            if table_id_str not in reserved_table_ids:
                # Also check if any tables are currently occupied
                upcoming_time = table.get("upcoming_reservation_time")
# With this safer implementation:
                if upcoming_time and isinstance(upcoming_time, datetime):
                    # If the table has a reservation starting during our needed window, it's not available
                    reservation_end_time = date + timedelta(minutes=duration_minutes)
                    
                    # Get reserved_until with a safe default that's definitely a datetime
                    reserved_until = table.get("reserved_until")
                    
                    # First check first part of condition without involving reserved_until
                    if upcoming_time >= date and upcoming_time <= reservation_end_time:
                        continue
                        
                    # Then check second part, but only if both values are not None
                    if date >= upcoming_time and reserved_until is not None and date <= reserved_until:
                        continue
                # Also check if any tables are currently occupied
                if table.get("status") != TableStatus.OCCUPIED:
                    available_tables.append(table)
                elif table.get("reserved_until") is not None and table.get("reserved_until") < date:
                    available_tables.append(table)
                    
        # Sort tables by capacity (to minimize wastage)
        return sorted(available_tables, key=lambda t: t["capacity"])
    

    # Add this new helper method after the ensure_indexes method
    def _get_enhanced_table_info(self, table: Dict) -> Dict:
        """
        Helper method to get enhanced table info including floor information
        
        Args:
            table: Table document from DB
            
        Returns:
            Enhanced table info dictionary
        """
        table_info = {
            "id": str(table["_id"]),
            "table_number": table["table_number"],
            "capacity": table["capacity"],
            "section": table.get("section"),
            "shape": table.get("shape")
        }
        
        # Add floor information if available
        if table.get("floor_id"):
            try:
                floor = self.db.floors.find_one({"_id": ObjectId(table["floor_id"])})
                if floor:
                    table_info["floor_id"] = str(floor["_id"])
                    table_info["floor_name"] = floor.get("name")
                    table_info["floor_number"] = floor.get("floor_number")
            except Exception as e:
                logging.error(f"Error getting floor details for table: {str(e)}")
        
        return table_info


    
    def create_reservation(self, reservation_data: Dict) -> Dict:
        """
        Create a new reservation
        
        Args:
            reservation_data: Dictionary containing reservation details
            
        Returns:
            The created reservation document
        """
        # Validate required fields
        required_fields = ["customer_name", "customer_phone", "party_size", "reservation_date"]
        for field in required_fields:
            if field not in reservation_data:
                raise ValueError(f"Missing required field: {field}")
                
        # Set default values
        reservation_data["status"] = ReservationStatus.PENDING
        reservation_data["created_at"] = datetime.now()
        reservation_data["updated_at"] = datetime.now()
        reservation_data["notification_sent"] = False
        reservation_data["reminder_sent"] = False
        reservation_data["reservation_code"] = self.generate_reservation_code()
        
        # Calculate expected end time based on duration
        duration = reservation_data.get("expected_duration_minutes", 90)
        reservation_date = reservation_data["reservation_date"]
        if isinstance(reservation_date, str):
            reservation_date = datetime.fromisoformat(reservation_date.replace('Z', '+00:00'))
            reservation_data["reservation_date"] = reservation_date
            
        reservation_data["expected_end_time"] = reservation_date + timedelta(minutes=duration)
        print(f"Expected end time: {reservation_data['expected_end_time']}")  # Debugging line
        # Try to assign tables if possible
        if "table_ids" not in reservation_data:
            party_size = reservation_data["party_size"]
            available_tables = self.find_available_tables(
                reservation_date, 
                party_size,
                duration
            )
            
            if available_tables:
                # Find smallest table(s) that can accommodate the party
                assigned_tables = []
                remaining_seats = party_size
                
                # First try to find a perfect or near-perfect fit
                for table in available_tables:
                    if table["capacity"] >= remaining_seats:
                        assigned_tables.append(str(table["_id"]))
                        break
                
                # If no single table fits, combine smaller tables
                if not assigned_tables:
                    for table in available_tables:
                        assigned_tables.append(str(table["_id"]))
                        remaining_seats -= table["capacity"]
                        if remaining_seats <= 0:
                            break
                
                reservation_data["table_ids"] = assigned_tables
        print(f"Assigned tables: {reservation_data['table_ids']}")
        # Insert the reservation
        result = self.db.reservations.insert_one(reservation_data)
        print(f"Reservation ID: {result.inserted_id}")
        # Update tables with reservation information if tables assigned
        if "table_ids" in reservation_data and reservation_data["table_ids"]:
            for table_id in reservation_data["table_ids"]:
                try:
                    # CHANGE: Store upcoming reservation time rather than immediately setting to RESERVED
                    now = datetime.now()
                    reservation_time = reservation_data["reservation_date"]
                    
                    # Only set status to RESERVED if reservation is within 30 minutes
                    status = TableStatus.RESERVED if (reservation_time - now).total_seconds() <= 1800 else TableStatus.VACANT
                    
                    self.db.tables.update_one(
                        {"_id": ObjectId(table_id)},
                        {
                            "$set": {
                                "upcoming_reservation_time": reservation_time,  # Add this line
                                "reserved_until": reservation_data["expected_end_time"],
                                "reservation_id": str(result.inserted_id),  # Add this line
                                "status": status,  # Conditionally set status
                                "updated_at": datetime.now()
                            }
                        }
                    )
                except Exception as e:
                    logging.error(f"Error updating table {table_id} with reservation: {str(e)}")
        
        print(f"Reservation created with ID: {result.inserted_id}")       
        # Return the created reservation
        return self.get_reservation_by_id(str(result.inserted_id))
    




    def get_reservation_by_id(self, reservation_id: str) -> Dict:
        """
        Get a reservation by ID
        
        Args:
            reservation_id: ID of the reservation
            
        Returns:
            The reservation document
        """
        reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
            
        # Convert ObjectId to string
        reservation["id"] = str(reservation["_id"])
        del reservation["_id"]
        
        # Add additional information about assigned tables
        if "table_ids" in reservation:
            tables_info = []
            for table_id in reservation["table_ids"]:
                try:
                    table = self.db.tables.find_one({"_id": ObjectId(table_id)})
                    if table:
                        # tables_info.append({
                        #     "id": str(table["_id"]),
                        #     "table_number": table["table_number"],
                        #     "capacity": table["capacity"],
                        #     "section": table.get("section")
                        # })
                        tables_info.append(self._get_enhanced_table_info(table))
                except Exception as e:
                    logging.error(f"Error fetching table {table_id}: {str(e)}")
                    
            reservation["tables"] = tables_info
        
        return reservation
    
    def get_reservations_by_date(self, date: datetime, include_completed: bool = False) -> List[Dict]:
        """
        Get reservations for a specific date
        
        Args:
            date: The date to filter by
            include_completed: If True, include completed and cancelled reservations
            
        Returns:
            List of reservation documents
        """
        # Create datetime range for the entire day
        start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
        end_date = datetime(date.year, date.month, date.day, 23, 59, 59)
        
        # Build query
        query = {
            "reservation_date": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        # Exclude completed/cancelled reservations if specified
        if not include_completed:
            query["status"] = {"$nin": [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW]}
        
        # Get reservations
        reservations = list(self.db.reservations.find(query).sort("reservation_date", 1))
        
        # Process each reservation
        result = []
        for reservation in reservations:
            # Convert ObjectId to string
            reservation["id"] = str(reservation["_id"])
            del reservation["_id"]
            
            # Add table information if available
            if "table_ids" in reservation:
                tables_info = []
                for table_id in reservation["table_ids"]:
                    try:
                        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
                        if table:
                            # tables_info.append({
                            #     "id": str(table["_id"]),
                            #     "table_number": table["table_number"],
                            #     "capacity": table["capacity"],
                            #     "section": table.get("section")
                            # })
                            tables_info.append(self._get_enhanced_table_info(table))
                    except Exception as e:
                        logging.error(f"Error fetching table {table_id}: {str(e)}")
                        
                reservation["tables"] = tables_info
            
            result.append(reservation)
        
        return result
    
    def update_reservation(self, reservation_id: str, update_data: Dict) -> Dict:
        """
        Update an existing reservation
        
        Args:
            reservation_id: ID of the reservation to update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated reservation document
        """
        # Get current reservation
        current_reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not current_reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
            
        # Set updated timestamp
        update_data["updated_at"] = datetime.now()
        
        # Handle date changes
        if "reservation_date" in update_data:
            reservation_date = update_data["reservation_date"]
            if isinstance(reservation_date, str):
                reservation_date = datetime.fromisoformat(reservation_date.replace('Z', '+00:00'))
                update_data["reservation_date"] = reservation_date
            
            # Recalculate expected_end_time if duration or date changed
            duration = update_data.get("expected_duration_minutes", current_reservation.get("expected_duration_minutes", 90))
            update_data["expected_end_time"] = reservation_date + timedelta(minutes=duration)
        elif "expected_duration_minutes" in update_data:
            # Only duration changed, recalculate end time
            reservation_date = current_reservation["reservation_date"]
            duration = update_data["expected_duration_minutes"]
            update_data["expected_end_time"] = reservation_date + timedelta(minutes=duration)
            
        # Handle table reassignment
        if "table_ids" in update_data:
            new_table_ids = update_data["table_ids"]
            old_table_ids = current_reservation.get("table_ids", [])
            
            # Release old tables
            for table_id in old_table_ids:
                if table_id not in new_table_ids:
                    try:
                        self.db.tables.update_one(
                            {"_id": ObjectId(table_id)},
                            {
                                "$set": {
                                    "status": TableStatus.VACANT,
                                    "reserved_until": None,
                                    "upcoming_reservation_time": None,  # Add this line
                                    "reservation_id": None,  # Add this line
                                    "updated_at": datetime.now()
                                }
                            }
                        )
                    except Exception as e:
                        logging.error(f"Error releasing table {table_id}: {str(e)}")
        
            
            # Assign new tables
            for table_id in new_table_ids:
                    if table_id not in old_table_ids:
                        try:
                            # Calculate the right status based on timing
                            now = datetime.now()
                            reservation_time = update_data.get("reservation_date", current_reservation["reservation_date"])
                            status = TableStatus.RESERVED if (reservation_time - now).total_seconds() <= 1800 else TableStatus.VACANT
                            
                            self.db.tables.update_one(
                                {"_id": ObjectId(table_id)},
                                {
                                    "$set": {
                                        "status": status,
                                        "upcoming_reservation_time": reservation_time,  # Add this line
                                        "reservation_id": reservation_id,  # Add this line
                                        "reserved_until": update_data.get("expected_end_time", current_reservation.get("expected_end_time")),
                                        "updated_at": datetime.now()
                                    }
                                }
                            )
                        except Exception as e:
                            logging.error(f"Error assigning table {table_id}: {str(e)}")
        
        # Update the document
        self.db.reservations.update_one(
            {"_id": ObjectId(reservation_id)},
            {"$set": update_data}
        )
        
        # Return updated reservation
        return self.get_reservation_by_id(reservation_id)
    
    def cancel_reservation(self, reservation_id: str, reason: str = None) -> Dict:
        """
        Cancel a reservation
        
        Args:
            reservation_id: ID of the reservation to cancel
            reason: Optional reason for cancellation
            
        Returns:
            Updated reservation document
        """
        # Get current reservation
        reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
        
        # Check if reservation can be cancelled
        if reservation["status"] in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel reservation with status: {reservation['status']}")
            
        # Update reservation status
        update_data = {
            "status": ReservationStatus.CANCELLED,
            "updated_at": datetime.now()
        }
        
        if reason:
            update_data["cancellation_reason"] = reason
            
        self.db.reservations.update_one(
            {"_id": ObjectId(reservation_id)},
            {
                "$set": update_data,
                "$push": {
                    "status_history": {
                        "status": ReservationStatus.CANCELLED,
                        "reserved_until": None,
                        "upcoming_reservation_time": None,  # Add this line
                        "reservation_id": None,  # Add this line
                        "updated_at": datetime.now(),
                        "timestamp": datetime.now(),
                        "reason": reason
                    }
                }
            }
        )
        
        # Release tables
        if "table_ids" in reservation:
            for table_id in reservation["table_ids"]:
                try:
                    self.db.tables.update_one(
                        {"_id": ObjectId(table_id)},
                        {
                            "$set": {
                                "status": TableStatus.VACANT,
                                "reserved_until": None,
                                "upcoming_reservation_time": None,
                                "reservation_id": None,
                                "updated_at": datetime.now()
                            }
                        }
                    )
                except Exception as e:
                    logging.error(f"Error releasing table {table_id}: {str(e)}")
        
        # Return updated reservation
        return self.get_reservation_by_id(reservation_id)
    
    def check_in_reservation(self, reservation_id: str, table_ids: List[str] = None, employee_id: str = None) -> Dict:
        """
        Check in a reservation - mark as CHECKED_IN and assign tables
        
        Args:
            reservation_id: ID of the reservation
            table_ids: Optional list of table IDs to assign
            employee_id: Optional employee handling the check-in
            
        Returns:
            Updated reservation document
        """
        # Get current reservation
        reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
        
        # Update reservation status
        update_data = {
            "status": ReservationStatus.CHECKED_IN,
            "check_in_time": datetime.now(),
            "updated_at": datetime.now()
        }
        
        if employee_id:
            update_data["assigned_employee_id"] = employee_id
            
        # Use provided table_ids or existing ones
        final_table_ids = table_ids if table_ids else reservation.get("table_ids", [])
        update_data["table_ids"] = final_table_ids
        
        self.db.reservations.update_one(
            {"_id": ObjectId(reservation_id)},
            {
                "$set": update_data,
                "$push": {
                    "status_history": {
                        "status": ReservationStatus.CHECKED_IN,
                        "timestamp": datetime.now(),
                        "employee_id": employee_id
                    }
                }
            }
        )
        
        # Update tables to OCCUPIED status
        for table_id in final_table_ids:
            try:
                self.db.tables.update_one(
                    {"_id": ObjectId(table_id)},
                    {
                        "$set": {
                            "status": TableStatus.OCCUPIED,
                            "occupied_since": datetime.now(),
                            "employee_id": employee_id,
                            "updated_at": datetime.now()
                        }
                    }
                )
            except Exception as e:
                logging.error(f"Error updating table {table_id} status: {str(e)}")
                
        # Return updated reservation
        return self.get_reservation_by_id(reservation_id)
        
    def complete_reservation(self, reservation_id: str) -> Dict:
        """
        Complete a reservation - mark as COMPLETED and release tables
        
        Args:
            reservation_id: ID of the reservation
            
        Returns:
            Updated reservation document
        """
        # Get current reservation
        reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
            
        # Update reservation status
        update_data = {
            "status": ReservationStatus.COMPLETED,
            "completion_time": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.db.reservations.update_one(
            {"_id": ObjectId(reservation_id)},
            {
                "$set": update_data,
                "$push": {
                    "status_history": {
                        "status": ReservationStatus.COMPLETED,
                        "timestamp": datetime.now()
                    }
                }
            }
        )
        
        # Release tables
        if "table_ids" in reservation:
            for table_id in reservation["table_ids"]:
                try:
                    self.db.tables.update_one(
                        {"_id": ObjectId(table_id)},
                        {
                            "$set": {
                                "status": TableStatus.VACANT,
                                "occupied_since": None,
                                "reserved_until": None,
                                "employee_id": None,
                                "updated_at": datetime.now()
                            }
                        }
                    )
                except Exception as e:
                    logging.error(f"Error releasing table {table_id}: {str(e)}")
                    
        # Return updated reservation
        return self.get_reservation_by_id(reservation_id)
    
    def mark_no_show(self, reservation_id: str) -> Dict:
        """
        Mark a reservation as NO_SHOW
        
        Args:
            reservation_id: ID of the reservation
            
        Returns:
            Updated reservation document
        """
        # Get current reservation
        reservation = self.db.reservations.find_one({"_id": ObjectId(reservation_id)})
        if not reservation:
            raise ValueError(f"Reservation not found: {reservation_id}")
            
        # Update reservation status
        update_data = {
            "status": ReservationStatus.NO_SHOW,
            "no_show_time": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.db.reservations.update_one(
            {"_id": ObjectId(reservation_id)},
            {
                "$set": update_data,
                "$push": {
                    "status_history": {
                        "status": ReservationStatus.NO_SHOW,
                        "timestamp": datetime.now()
                    }
                }
            }
        )
        
        # Release tables
        if "table_ids" in reservation:
            for table_id in reservation["table_ids"]:
                try:
                    self.db.tables.update_one(
                        {"_id": ObjectId(table_id)},
                        {
                            "$set": {
                                "status": TableStatus.VACANT,
                                "reserved_until": None,
                                "updated_at": datetime.now()
                            }
                        }
                    )
                except Exception as e:
                    logging.error(f"Error releasing table {table_id}: {str(e)}")
                    
        # Return updated reservation
        return self.get_reservation_by_id(reservation_id)
    
    def search_reservations(self, query: str) -> List[Dict]:
        """
        Search for reservations by customer name, phone, or reservation code
        
        Args:
            query: Search query string
            
        Returns:
            List of matching reservation documents
        """
        # Build search query for different fields
        search_query = {
            "$or": [
                {"customer_name": {"$regex": query, "$options": "i"}},
                {"customer_phone": {"$regex": query, "$options": "i"}},
                {"reservation_code": {"$regex": query, "$options": "i"}},
                {"customer_email": {"$regex": query, "$options": "i"}}
            ]
        }
        
        # Get matching reservations
        reservations = list(self.db.reservations.find(search_query).sort("reservation_date", -1).limit(20))
        
        # Process each reservation
        result = []
        for reservation in reservations:
            # Convert ObjectId to string
            reservation["id"] = str(reservation["_id"])
            del reservation["_id"]
            
            # Add table information if available
            if "table_ids" in reservation:
                tables_info = []
                for table_id in reservation["table_ids"]:
                    try:
                        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
                        if table:
                            # tables_info.append({
                            #     "id": str(table["_id"]),
                            #     "table_number": table["table_number"],
                            #     "capacity": table["capacity"],
                            #     "section": table.get("section")
                            # })
                            tables_info.append(self._get_enhanced_table_info(table))
                    except Exception as e:
                        logging.error(f"Error fetching table {table_id}: {str(e)}")
                        
                reservation["tables"] = tables_info
            
            result.append(reservation)
        
        return result
    
    def send_confirmation_email(self, reservation_id: str) -> bool:
        """
        Send reservation confirmation email
        
        Args:
            reservation_id: ID of the reservation
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get reservation details
            reservation = self.get_reservation_by_id(reservation_id)
            
            # Skip if no email provided
            if not reservation.get("customer_email"):
                return False
                
            # Set up email
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_SENDER
            msg['To'] = reservation["customer_email"]
            msg['Subject'] = f"Reservation Confirmation - {reservation['reservation_code']}"
            
            # Format date for email
            reservation_date = reservation["reservation_date"]
            formatted_date = reservation_date.strftime("%A, %B %d, %Y at %I:%M %p")
            
            # Build email content
            email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Your Reservation is Confirmed!</h2>
                    <p>Dear {reservation['customer_name']},</p>
                    <p>Thank you for your reservation. We look forward to serving you.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Reservation Details:</h3>
                        <p><strong>Reservation Code:</strong> {reservation['reservation_code']}</p>
                        <p><strong>Date & Time:</strong> {formatted_date}</p>
                        <p><strong>Party Size:</strong> {reservation['party_size']} people</p>
                        
                        {f"<p><strong>Special Requests:</strong> {reservation['special_requests']}</p>" if reservation.get('special_requests') else ""}
                    </div>
                    
                    <p>If you need to modify or cancel your reservation, please contact us at your earliest convenience.</p>
                    <p>We're excited to welcome you soon!</p>
                    
                    <p>Best regards,<br>The Team</p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(email_content, 'html'))
            
            # Send email
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            # Update reservation
            self.db.reservations.update_one(
                {"_id": ObjectId(reservation_id)},
                {"$set": {"notification_sent": True}}
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error sending confirmation email: {str(e)}")
            return False
    
    def send_reminder_email(self, reservation_id: str) -> bool:
        """
        Send reservation reminder email
        
        Args:
            reservation_id: ID of the reservation
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get reservation details
            reservation = self.get_reservation_by_id(reservation_id)
            
            # Skip if no email provided or already checked in/completed
            if not reservation.get("customer_email") or reservation["status"] in [ReservationStatus.CHECKED_IN, ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
                return False
                
            # Set up email
            msg = MIMEMultipart()
            msg['From'] = settings.EMAIL_SENDER
            msg['To'] = reservation["customer_email"]
            msg['Subject'] = f"Reservation Reminder - {reservation['reservation_code']}"
            
            # Format date for email
            reservation_date = reservation["reservation_date"]
            formatted_date = reservation_date.strftime("%A, %B %d, %Y at %I:%M %p")
            
            # Build email content
            email_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Reservation Reminder</h2>
                    <p>Dear {reservation['customer_name']},</p>
                    <p>This is a friendly reminder about your upcoming reservation.</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0;">Reservation Details:</h3>
                        <p><strong>Reservation Code:</strong> {reservation['reservation_code']}</p>
                        <p><strong>Date & Time:</strong> {formatted_date}</p>
                        <p><strong>Party Size:</strong> {reservation['party_size']} people</p>
                    </div>
                    
                    <p>We look forward to seeing you soon!</p>
                    
                    <p>Best regards,<br>The Team</p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(email_content, 'html'))
            
            # Send email
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            # Update reservation
            self.db.reservations.update_one(
                {"_id": ObjectId(reservation_id)},
                {"$set": {"reminder_sent": True}}
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Error sending reminder email: {str(e)}")
            return False
        


    def get_upcoming_reservations(self, hours: int = 24) -> List[Dict]:
        """
        Get all upcoming reservations within the next X hours
        
        Args:
            hours: Number of hours to look ahead
            
        Returns:
            List of upcoming reservation documents
        """
        # Calculate time range
        now = datetime.now()
        end_time = now + timedelta(hours=hours)
        
        # Query upcoming reservations
        query = {
            "reservation_date": {"$gte": now, "$lte": end_time},
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]}
        }
        
        # Get reservations
        reservations = list(self.db.reservations.find(query).sort("reservation_date", 1))
        
        # Process each reservation
        result = []
        for reservation in reservations:
            reservation["id"] = str(reservation["_id"])
            del reservation["_id"]
            
            # Add table information
            if "table_ids" in reservation:
                tables_info = []
                for table_id in reservation["table_ids"]:
                    try:
                        table = self.db.tables.find_one({"_id": ObjectId(table_id)})
                        if table:
                            # tables_info.append({
                            #     "id": str(table["_id"]),
                            #     "table_number": table["table_number"],
                            #     "capacity": table["capacity"],
                            #     "section": table.get("section")
                            # })
                            tables_info.append(self._get_enhanced_table_info(table))
                    except Exception as e:
                        logging.error(f"Error fetching table {table_id}: {str(e)}")
                        
                reservation["tables"] = tables_info
            
            result.append(reservation)
        
        return result
        
    def get_pending_reminders(self) -> List[Dict]:
        """
        Get reservations that need reminder emails
        (24 hours before reservation time and no reminder sent yet)
        
        Returns:
            List of reservations needing reminders
        """
        # Calculate time range (reservations coming up in 23-25 hours)
        now = datetime.now()
        start_time = now + timedelta(hours=23)
        end_time = now + timedelta(hours=25)
        
        # Query reservations needing reminders
        query = {
            "reservation_date": {"$gte": start_time, "$lte": end_time},
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]},
            "reminder_sent": False,
            "customer_email": {"$ne": None, "$ne": ""}
        }
        
        # Get reservations
        return list(self.db.reservations.find(query))
        
    def process_overdue_reservations(self) -> int:
        """
        Process reservations that are past their time without check-in
        (Mark as NO_SHOW if more than 30 minutes late)
        
        Returns:
            Number of reservations marked as no-show
        """
        # Calculate cutoff time (30 minutes past reservation time)
        cutoff_time = datetime.now() - timedelta(minutes=30)
        
        # Query overdue reservations
        query = {
            "reservation_date": {"$lt": cutoff_time},
            "status": {"$in": [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]}
        }
        
        # Get overdue reservations
        overdue_reservations = list(self.db.reservations.find(query))
        
        # Mark each as NO_SHOW
        count = 0
        for reservation in overdue_reservations:
            try:
                self.mark_no_show(str(reservation["_id"]))
                count += 1
            except Exception as e:
                logging.error(f"Error processing overdue reservation {reservation['_id']}: {str(e)}")
                
        return count
        
    def get_stats_by_date_range(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Get reservation statistics for a date range
        
        Args:
            start_date: Start date for statistics
            end_date: End date for statistics
            
        Returns:
            Dictionary with reservation statistics
        """
        # Query reservations in date range
        query = {
            "reservation_date": {"$gte": start_date, "$lte": end_date}
        }
        
        # Get all reservations in range
        reservations = list(self.db.reservations.find(query))
        
        # Calculate statistics
        total = len(reservations)
        completed = sum(1 for r in reservations if r.get("status") == ReservationStatus.COMPLETED)
        cancelled = sum(1 for r in reservations if r.get("status") == ReservationStatus.CANCELLED)
        no_shows = sum(1 for r in reservations if r.get("status") == ReservationStatus.NO_SHOW)
        total_party_size = sum(r.get("party_size", 0) for r in reservations)
        
        # Calculate completion rate
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        return {
            "total_reservations": total,
            "completed": completed,
            "cancelled": cancelled,
            "no_shows": no_shows,
            "average_party_size": round(total_party_size / total, 1) if total > 0 else 0,
            "completion_rate": round(completion_rate, 1)
        }
        
    def get_reservation_by_code(self, reservation_code: str) -> Dict:
        """
        Get a reservation by its unique code
        
        Args:
            reservation_code: The reservation code
            
        Returns:
            The reservation document
        """
        reservation = self.db.reservations.find_one({"reservation_code": reservation_code})
        if not reservation:
            raise ValueError(f"Reservation not found with code: {reservation_code}")
            
        # Convert ObjectId to string
        reservation["id"] = str(reservation["_id"])
        del reservation["_id"]
        
        # Add table information
        if "table_ids" in reservation:
            tables_info = []
            for table_id in reservation["table_ids"]:
                try:
                    table = self.db.tables.find_one({"_id": ObjectId(table_id)})
                    if table:
                        # tables_info.append({
                        #     "id": str(table["_id"]),
                        #     "table_number": table["table_number"],
                        #     "capacity": table["capacity"],
                        #     "section": table.get("section")
                        # })
                        tables_info.append(self._get_enhanced_table_info(table))
                except Exception as e:
                    logging.error(f"Error fetching table {table_id}: {str(e)}")
                    
            reservation["tables"] = tables_info
        
        return reservation





