from datetime import datetime
from typing import Dict, List, Any, Optional
from pymongo.database import Database
from bson import ObjectId
import traceback

class BillStorage:
    """
    Handles storage of bill data in bills collection using synchronous operations
    """
    
    def __init__(self, db):
        """Initialize with database instance"""
        self.db = db
        print(f"[BILL-STORAGE] Using database: {db.name}")
    
    def ensure_indexes(self):
        """Create necessary indexes for efficient queries"""
        self.db.bills.create_index("timestamp")
        self.db.bills.create_index({"customer.phone": 1})
        self.db.bills.create_index("date")
        self.db.bills.create_index("order_id")
        self.db.customer_order_history.create_index("last_visit")
        self.db.customer_order_history.create_index("total_spent")
        self.db.customer_order_history.create_index("total_visits")
        self.db.item_analytics.create_index("category")
        self.db.item_analytics.create_index([("total_orders", -1)])
        self.db.item_analytics.create_index([("total_revenue", -1)])
        print("[BILL-STORAGE] Created indexes for bills and analytics collections")
    
    def _format_items_for_bill(self, items: List[Dict]) -> List[Dict]:
        """Format order items for storage with all details preserved"""
        formatted_items = []
        
        for item in items:
            # Create a clean copy with proper structure
            formatted_item = {
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "unit_price": item.get("base_price", 0),
                "total_price": item.get("total_price", 0),
                "discounted_price": item.get("total_discounted_price", item.get("total_price", 0)),
                "category": item.get("food_category", ""),
                "type": item.get("food_type", ""),
            }
            
            # Add customization if present
            if "customization_details" in item:
                customization = item["customization_details"]
                
                # Handle text customization
                if customization.get("text"):
                    formatted_item["customization"] = {
                        "text": customization.get("text", "")
                    }
                
                # Handle size information
                if customization.get("size"):
                    if "customization" not in formatted_item:
                        formatted_item["customization"] = {}
                    
                    formatted_item["customization"]["size"] = {
                        "name": customization["size"].get("name", ""),
                        "price": customization["size"].get("price", 0)
                    }
                
                # Handle addons
                addons = []
                for addon in customization.get("addons", []):
                    addons.append({
                        "name": addon.get("name", ""),
                        "quantity": addon.get("quantity", 0),
                        "unit_price": addon.get("unit_price", 0),
                        "total_price": addon.get("total_price", 0)
                    })
                
                if addons:
                    if "customization" not in formatted_item:
                        formatted_item["customization"] = {}
                    formatted_item["customization"]["addons"] = addons
            
            # Add promotion details if available
            if item.get("is_promotion_item") and "promotion_details" in item:
                promo = item["promotion_details"]
                formatted_item["promotion"] = {
                    "buy_item_name": promo.get("buy_item_name", ""),
                    "buy_quantity": promo.get("buy_quantity", 0),
                    "discounted_price": promo.get("discounted_price", 0)
                }
            
            formatted_items.append(formatted_item)
        
        return formatted_items
    
    def update_payment(self, bill_id: str, payment_data: Dict) -> bool:
        """Update payment information for a bill"""
        try:
            now = datetime.now()
            
            # Update payment fields
            result = self.db.bills.update_one(
                {"_id": ObjectId(bill_id)},
                {
                    "$set": {
                        "payment.status": payment_data.get("status", "COMPLETED"),
                        "payment.methods": payment_data.get("methods", []),
                        "payment.paid_amount": payment_data.get("paid_amount", 0),
                        "payment.payment_date": now.strftime("%Y-%m-%d"),
                        "payment.payment_time": now.strftime("%H:%M"),
                        "payment.updated_at": now
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"[ERROR] Failed to update payment: {str(e)}")
            return False
    
    # def update_feedback(self, bill_id: str, feedback_data: Dict) -> bool:
    #     """Update feedback information for a bill"""
    #     try:
    #         now = datetime.now()
            
    #         # Update feedback fields
    #         result = self.db.bills.update_one(
    #             {"_id": ObjectId(bill_id)},
    #             {
    #                 "$set": {
    #                     "feedback.overall_rating": feedback_data.get("overall_rating"),
    #                     "feedback.comments": feedback_data.get("comments", ""),
    #                     "feedback.item_ratings": feedback_data.get("item_ratings", []),
    #                     "feedback.service_rating": feedback_data.get("service_rating"),
    #                     "feedback.submitted_at": now
    #                 }
    #             }
    #         )
            
    #         return result.modified_count > 0
            
    #     except Exception as e:
    #         print(f"[ERROR] Failed to update feedback: {str(e)}")
    #         return False




    def update_feedback(self, bill_id: str, feedback_data: Dict) -> bool:
                """Update feedback information for a bill with enhanced structure"""
                try:
                    now = datetime.now()
                    
                    # Create comprehensive feedback structure
                    feedback_structure = {
                        "overall_rating": feedback_data.get("overall_rating"),
                        "comments": feedback_data.get("comments", ""),
                        "items": feedback_data.get("items", {}),  # Enhanced structure with per-item feedback
                        "submitted_at": now,
                        "email": feedback_data.get("email", "")
                    }
                    
                    # Update feedback fields with comprehensive structure
                    result = self.db.bills.update_one(
                        {"_id": ObjectId(bill_id)},
                        {"$set": {"feedback": feedback_structure}}
                    )
                    
                    print(f"[FEEDBACK] Updated comprehensive feedback for bill {bill_id}")
                    return result.modified_count > 0
                    
                except Exception as e:
                    print(f"[ERROR] Failed to update feedback: {str(e)}")
                    return False
    
    def update_customer_history(self, order_details: Dict, bill_id: str, total_amount: float) -> str:
        """Update or create customer order history record"""
        try:
            # Get order ID
            order_id = order_details.get("order_id", "")
            
            # Get customer details
            temp_customer = self.db.customer_temporary_details.find_one({"order_id": order_id})
            if not temp_customer or not temp_customer.get("phone"):
                print(f"[CUSTOMER-HISTORY] No customer phone found for order {order_id}")
                return None
            
            # Extract customer info
            customer_phone = temp_customer.get("phone", "")
            customer_name = temp_customer.get("name", "")
            customer_email = temp_customer.get("email", "")
            customer_address = temp_customer.get("address", "")
            
            # Create timestamp
            now = datetime.now()
            
            # Count items
            items_count = sum(item.get("quantity", 0) for item in order_details.get("items", []))
            
            # Create order summary
            order_summary = {
                "order_id": order_id,
                "bill_id": bill_id,
                "bill_number": f"INV-{order_id[-6:]}",
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M"),
                "timestamp": now,
                "amount": total_amount,
                "items_count": items_count,
                "table_number": order_details.get("table_number", 0),
                "item_names": [item.get("name") for item in order_details.get("items", [])],
                "feedback": None  # Will be updated later
            }
            
            # Process items for favorite tracking
            item_counts = {}
            for item in order_details.get("items", []):
                item_name = item.get("name", "")
                quantity = item.get("quantity", 0)
                
                if item_name in item_counts:
                    item_counts[item_name] += quantity
                else:
                    item_counts[item_name] = quantity
            
            # Update customer history
            result = self.db.customer_order_history.update_one(
                {"_id": customer_phone},
                {
                    "$set": {
                        "name": customer_name,
                        "email": customer_email,
                        "address": customer_address,
                        "last_visit": now
                    },
                    "$setOnInsert": {
                        "first_visit": now
                    },
                    "$inc": {
                        "total_visits": 1,
                        "total_spent": total_amount
                    },
                    "$push": {
                        "orders": {
                            "$each": [order_summary],
                            "$position": 0,
                            "$slice": 20  # Keep only 20 most recent orders
                        }
                    }
                },
                upsert=True
            )
            
            # Update item counts for favorite tracking
            for item_name, count in item_counts.items():
                self.db.customer_order_history.update_one(
                    {"_id": customer_phone},
                    {"$inc": {f"item_counts.{item_name}": count}}
                )
            
            # Update favorite items
            customer = self.db.customer_order_history.find_one({"_id": customer_phone})
            if customer and "item_counts" in customer:
                favorite_items = []
                for item, count in customer["item_counts"].items():
                    favorite_items.append({"name": item, "count": count})
                
                # Sort by count and take top 5
                favorite_items.sort(key=lambda x: x["count"], reverse=True)
                top_favorites = favorite_items[:5]
                
                # Update favorite_items field
                self.db.customer_order_history.update_one(
                    {"_id": customer_phone},
                    {"$set": {"favorite_items": top_favorites}}
                )
            
            print(f"[CUSTOMER-HISTORY] Updated history for customer: {customer_phone}")
            return customer_phone
            
        except Exception as e:
            print(f"[ERROR] Error updating customer history: {str(e)}")
            print(traceback.format_exc())
            return None
            
    def update_customer_feedback(self, bill_id: str, feedback_data: Dict) -> bool:
            """Update customer feedback in both bill and customer history with enhanced structure"""
            try:
                # First update feedback in the bill with comprehensive data
                self.update_feedback(bill_id, feedback_data)
                
                # Get bill details to find order_id and customer
                bill = self.db.bills.find_one({"_id": ObjectId(bill_id)})
                if not bill:
                    print(f"[ERROR] Bill {bill_id} not found")
                    return False
                
                order_id = bill.get("order_id")
                customer_phone = bill.get("customer", {}).get("phone")
                
                if not customer_phone or not order_id:
                    print(f"[ERROR] Missing customer phone or order ID for bill {bill_id}")
                    return False
                
                # Create enhanced feedback summary for customer history
                feedback_summary = {
                    "overall_rating": feedback_data.get("overall_rating"),
                    "comments": feedback_data.get("comments", ""),
                    "submitted_at": datetime.now(),
                    "items": {}
                }
                
                # Add item feedback data (ratings, issues, comments)
                for item_name, item_data in feedback_data.get("items", {}).items():
                    feedback_summary["items"][item_name] = {
                        "rating": item_data.get("rating", 0),
                        "issues": item_data.get("issues", []),
                        "comments": item_data.get("comments", "")
                    }
                
                # Update feedback in customer order history with enhanced structure
                result = self.db.customer_order_history.update_one(
                    {"_id": customer_phone, "orders.order_id": order_id},
                    {"$set": {"orders.$.feedback": feedback_summary}}
                )
                
                print(f"[CUSTOMER-HISTORY] Updated enhanced feedback for order {order_id} customer {customer_phone}")
                return result.modified_count > 0
                
            except Exception as e:
                print(f"[ERROR] Error updating customer feedback: {str(e)}")
                return False
    
    def store_bill(self, order_details: Dict, bill_items: List[Dict], calculations: List[Dict], total_amount: float) -> Dict:
        """Store bill data in bills collection and update customer history"""
        try:
            # Get order ID
            order_id = order_details.get("order_id", "")
            
            # Get customer details
            temp_customer = self.db.customer_temporary_details.find_one({"order_id": order_id})
            
            # Create timestamp
            now = datetime.now()
            
            # Calculate discount amounts
            item_discount = order_details.get("total_price", 0) - order_details.get("total_discounted_price", 0)
            bill_discount = order_details.get("bill_discount_amount", 0)
            total_discount = item_discount + bill_discount
            
            # Format items with proper structure
            formatted_items = self._format_items_for_bill(order_details.get("items", []))
            
            # Create bill document structure
            bill_record = {
                "bill_number": f"INV-{order_id[-6:]}",
                "order_id": order_id,
                "owner_id": order_details.get("owner_id", ""),
                "timestamp": now,
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M"),
                
                # Customer information
                "customer": {
                    "name": temp_customer.get("name", "") if temp_customer else "",
                    "phone": temp_customer.get("phone", "") if temp_customer else "",
                    "email": temp_customer.get("email", "") if temp_customer else "",
                    "address": temp_customer.get("address", "") if temp_customer else ""
                },
                
                # Table and employee info
                "table_number": order_details.get("table_number", 0),
                "employee_id": order_details.get("employee_id", ""),
                
                # Items from order details
                "items": formatted_items,
                
                # Bill items (simplified for bill display)
                "bill_items": bill_items,
                
                # Financial details
                "subtotal": order_details.get("total_price", 0),
                "item_discount_amount": item_discount,
                "bill_discount_amount": bill_discount,
                "bill_discounts": order_details.get("applied_bill_discounts", []),
                "calculations": calculations,
                "total_amount": total_amount,
                "total_discount": total_discount,
                
                # Payment details (to be updated later)
                "payment": {
                    "status": "PENDING",
                    "methods": [],
                    "paid_amount": 0,
                    "payment_date": None,
                    "payment_time": None
                },
                
                # Feedback (to be updated later)
                "feedback": {
                    "overall_rating": None,
                    "comments": "",
                    "item_ratings": [],
                    "service_rating": None,
                    "submitted_at": None
                },
                
                # Metadata
                "created_at": now
            }
            
            # Store in database
            result = self.db.bills.insert_one(bill_record)
            bill_id = str(result.inserted_id)
            
            # Update customer history
            customer_id = self.update_customer_history(
                order_details=order_details,
                bill_id=bill_id,
                total_amount=total_amount
            )
            
            # Update item analytics
            self.update_item_analytics(
                order_details=order_details,
                bill_id=bill_id
            )
            
            print(f"[BILL-STORAGE] Saved bill {bill_id} for customer {customer_id}")
            
            return {
                "bill_id": bill_id,
                "customer_id": customer_id
            }
            
        except Exception as e:
            print(f"[ERROR] Error storing bill data: {str(e)}")
            print(traceback.format_exc())
            return {
                "bill_id": None,
                "customer_id": None,
                "error": str(e)
            }
    
    def update_item_analytics(self, order_details: Dict, bill_id: str) -> None:
        """Update item analytics including sales data, addon popularity and time patterns"""
        try:
            # Get timestamp
            now = datetime.now()
            date = now.strftime("%Y-%m-%d")
            month = now.strftime("%Y-%m")
            hour = now.hour
            
            # Process each item in the order
            for item in order_details.get("items", []):
                # Skip if no item name
                item_name = item.get("name", "")
                if not item_name:
                    continue
                    
                # Get basic item information
                quantity = item.get("quantity", 0)
                base_price = item.get("base_price", 0)
                discounted_price = item.get("total_discounted_price", item.get("total_price", 0))
                revenue = discounted_price  # Use discounted price for revenue
                category = item.get("food_category", "Uncategorized")
                item_type = item.get("food_type", "")
                
                # Try to get item_id from menu collection
                menu_item = self.db.menu.find_one({"name": item_name})
                item_id = str(menu_item.get("_id")) if menu_item else f"item-{item_name.lower().replace(' ', '-')}"
                
                # Process addons if present
                addons = []
                addon_combinations = []
                
                if "customization_details" in item and "addons" in item["customization_details"]:
                    addons_data = item["customization_details"]["addons"]
                    
                    # Track addon names for combinations
                    addon_names = []
                    
                    # Process each addon
                    for addon in addons_data:
                        addon_name = addon.get("name", "")
                        if not addon_name:
                            continue
                            
                        addon_names.append(addon_name)
                        addon_qty = addon.get("quantity", 0)
                        addon_price = addon.get("unit_price", 0)
                        addon_revenue = addon_price * addon_qty
                        
                        # Update addons list for this item
                        addons.append({
                            "addon_id": f"addon-{addon_name.lower().replace(' ', '-')}",
                            "name": addon_name,
                            "quantity": addon_qty,
                            "revenue": addon_revenue
                        })
                    
                    # Create addon combinations (only if multiple addons)
                    if len(addon_names) > 1:
                        addon_combinations = [sorted(addon_names)]
                
                # Process customizations
                customization_text = ""
                size_name = ""
                
                if "customization_details" in item:
                    # Get customization text
                    customization_text = item["customization_details"].get("text", "")
                    
                    # Get size information
                    if item["customization_details"].get("size"):
                        size_name = item["customization_details"]["size"].get("name", "")
                
                # Update item analytics document
                # First update the core statistics
                update_result = self.db.item_analytics.update_one(
                    {"_id": item_id},
                    {
                        "$set": {
                            "name": item_name,
                            "category": category,
                            "type": item_type,
                            "updated_at": now
                        },
                        "$inc": {
                            "total_orders": 1,
                            "total_quantity": quantity,
                            "total_revenue": revenue
                        }
                    },
                    upsert=True
                )
                
                # Update daily sales
                self.db.item_analytics.update_one(
                    {"_id": item_id, "daily_sales.date": date},
                    {"$inc": {
                        "daily_sales.$.quantity": quantity,
                        "daily_sales.$.revenue": revenue
                    }}
                )
                
                # If date doesn't exist, add it
                self.db.item_analytics.update_one(
                    {"_id": item_id, "daily_sales.date": {"$ne": date}},
                    {"$push": {
                        "daily_sales": {
                            "date": date,
                            "quantity": quantity,
                            "revenue": revenue
                        }
                    }}
                )
                
                # Update monthly sales
                self.db.item_analytics.update_one(
                    {"_id": item_id, "monthly_sales.month": month},
                    {"$inc": {
                        "monthly_sales.$.quantity": quantity,
                        "monthly_sales.$.revenue": revenue
                    }}
                )
                
                # If month doesn't exist, add it
                self.db.item_analytics.update_one(
                    {"_id": item_id, "monthly_sales.month": {"$ne": month}},
                    {"$push": {
                        "monthly_sales": {
                            "month": month,
                            "quantity": quantity,
                            "revenue": revenue
                        }
                    }}
                )
                
                # Update peak hours
                self.db.item_analytics.update_one(
                    {"_id": item_id, "peak_hours.hour": hour},
                    {"$inc": {"peak_hours.$.count": 1}}
                )
                
                # If hour doesn't exist, add it
                self.db.item_analytics.update_one(
                    {"_id": item_id, "peak_hours.hour": {"$ne": hour}},
                    {"$push": {"peak_hours": {"hour": hour, "count": 1}}}
                )
                
                # Add size distribution if size is present
                if size_name:
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "size_distribution.size": size_name},
                        {"$inc": {"size_distribution.$.count": 1}}
                    )
                    
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "size_distribution.size": {"$ne": size_name}},
                        {"$push": {"size_distribution": {"size": size_name, "count": 1}}}
                    )
                
                # Add customization text if present
                if customization_text:
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "common_customizations.text": customization_text},
                        {"$inc": {"common_customizations.$.count": 1}}
                    )
                    
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "common_customizations.text": {"$ne": customization_text}},
                        {"$push": {"common_customizations": {"text": customization_text, "count": 1}}}
                    )
                
                # Update addon popularity
                for addon in addons:
                    addon_name = addon["name"]
                    addon_qty = addon["quantity"]
                    addon_revenue = addon["revenue"]
                    
                    # Update existing addon
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_popularity.name": addon_name},
                        {"$inc": {
                            "addon_popularity.$.total_occurrences": 1,
                            "addon_popularity.$.total_quantity": addon_qty,
                            "addon_popularity.$.revenue_contribution": addon_revenue
                        }}
                    )
                    
                    # Add new addon if it doesn't exist
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_popularity.name": {"$ne": addon_name}},
                        {"$push": {
                            "addon_popularity": {
                                "addon_id": f"addon-{addon_name.lower().replace(' ', '-')}",
                                "name": addon_name,
                                "total_occurrences": 1,
                                "total_quantity": addon_qty,
                                "revenue_contribution": addon_revenue,
                                "occurrence_percentage": 0  # Will be calculated later
                            }
                        }}
                    )
                
                # Update addon combinations
                for combo in addon_combinations:
                    combo_key = ",".join(sorted(combo))
                    
                    # Update existing combination
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_combinations.combination_key": combo_key},
                        {"$inc": {"addon_combinations.$.count": 1}}
                    )
                    
                    # Add new combination if it doesn't exist
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_combinations.combination_key": {"$ne": combo_key}},
                        {"$push": {
                            "addon_combinations": {
                                "combination_key": combo_key,
                                "combination": combo,
                                "count": 1,
                                "percentage": 0  # Will be calculated later
                            }
                        }}
                    )
                
                # Recalculate percentages for addon popularity and combinations
                self._recalculate_item_analytics_percentages(item_id)
                
                print(f"[ITEM-ANALYTICS] Updated analytics for item: {item_name}")
                
        except Exception as e:
            print(f"[ERROR] Error updating item analytics: {str(e)}")
            print(traceback.format_exc())
    
    def _recalculate_item_analytics_percentages(self, item_id: str) -> None:
        """Recalculate percentages for addon popularity and combinations"""
        try:
            # Get the current item analytics
            item_analytics = self.db.item_analytics.find_one({"_id": item_id})
            if not item_analytics:
                return
                
            total_orders = item_analytics.get("total_orders", 0)
            if total_orders == 0:
                return
                
            # Update addon popularity percentages
            if "addon_popularity" in item_analytics:
                for i, addon in enumerate(item_analytics["addon_popularity"]):
                    occurrence_percentage = (addon["total_occurrences"] / total_orders) * 100
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_popularity.name": addon["name"]},
                        {"$set": {"addon_popularity.$.occurrence_percentage": round(occurrence_percentage, 1)}}
                    )
            
            # Update addon combination percentages
            if "addon_combinations" in item_analytics:
                for i, combo in enumerate(item_analytics["addon_combinations"]):
                    percentage = (combo["count"] / total_orders) * 100
                    self.db.item_analytics.update_one(
                        {"_id": item_id, "addon_combinations.combination_key": combo["combination_key"]},
                        {"$set": {"addon_combinations.$.percentage": round(percentage, 1)}}
                    )
            
            # Update size distribution percentages
            if "size_distribution" in item_analytics:
                size_total = sum(size["count"] for size in item_analytics["size_distribution"])
                if size_total > 0:
                    for size in item_analytics["size_distribution"]:
                        percentage = (size["count"] / size_total) * 100
                        self.db.item_analytics.update_one(
                            {"_id": item_id, "size_distribution.size": size["size"]},
                            {"$set": {"size_distribution.$.percentage": round(percentage, 1)}}
                        )
        
        except Exception as e:
            print(f"[ERROR] Error recalculating percentages: {str(e)}")