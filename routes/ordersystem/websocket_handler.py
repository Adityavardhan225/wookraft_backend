

import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pymongo.database import Database
from typing import Dict, List, Optional
import json
from routes.security.protected_authorise import get_current_user
from routes.ordersystem.sorting_utils import get_filtered_orders, get_orders_by_table

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, role: str, employee_id: Optional[str] = None):
        await websocket.accept()
        if role not in self.active_connections:
            self.active_connections[role] = []
        self.active_connections[role].append(websocket)
        if employee_id:
            if employee_id not in self.active_connections:
                self.active_connections[employee_id] = []
            self.active_connections[employee_id].append(websocket)

    def disconnect(self, websocket: WebSocket, role: str, employee_id: Optional[str] = None):
        if role in self.active_connections and websocket in self.active_connections[role]:
            self.active_connections[role].remove(websocket)
        if employee_id and employee_id in self.active_connections and websocket in self.active_connections[employee_id]:
            self.active_connections[employee_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, roles: List[str] = None, employee_id: Optional[str] = None):
        if roles:
            for role in roles:
                for connection in self.active_connections.get(role, []):
                    try:
                        await connection.send_text(message)
                    except RuntimeError:
                        self.disconnect(connection, role)
        if employee_id:
            for connection in self.active_connections.get(employee_id, []):
                try:
                    await connection.send_text(message)
                except RuntimeError:
                    self.disconnect(connection, employee_id)

    async def notify_kds_cancellation(self, order_id: str, item_name: str, reason: str):
        message = {
            "type": "cancellation_request",
            "order_id": order_id,
            "item_name": item_name,
            "reason": reason
        }
        await self.broadcast(json.dumps(message), roles=["kds"])

manager = ConnectionManager()

filter_criteria = {
    "food_types": [],
    "food_categories": []
}

def update_filter_criteria(food_types: Optional[List[str]], food_categories: Optional[List[str]]):
    filter_criteria["food_types"] = food_types if food_types is not None else []
    filter_criteria["food_categories"] = food_categories if food_categories is not None else []

async def websocket_handler(websocket: WebSocket, token: str, role: str, db: Database, employee_id: Optional[str] = None):
    if not token:
        await websocket.close(code=1008)
        return
    
    try:
        current_user = get_current_user(db=db, token=token)
    except HTTPException:
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket, role=role, employee_id=employee_id)
    stop_event = asyncio.Event()

    async def check_unacknowledged_orders():
        while not stop_event.is_set():
            await asyncio.sleep(300)
            try:
                current_time = datetime.now()
                unacknowledged = db.orders.find({"status": "active", "received": False})
                unack_list = [
                    order["id"] for order in unacknowledged 
                    if (current_time - order["timestamp"]).total_seconds() > 300
                ]
                if unack_list:
                    await websocket.send_text(json.dumps({
                        "type": "notification",
                        "message": "Unacknowledged orders present",
                        "orders": unack_list
                    }))
            except Exception as e:
                print(f"Error checking unacknowledged orders: {e}")

    if role == "kds":
        task = asyncio.create_task(check_unacknowledged_orders())

    try:
        # Initial orders load
        active_orders = (
            get_filtered_orders(db, filter_criteria["food_types"], filter_criteria["food_categories"])
            if role == "kds"
            else list(db.orders.find({"status": "active"}).sort([("prepared", 1), ("timestamp", 1)]))
        )
        if role == "kds":
            # Retrieve all active orders from the database with current filter criteria
            active_orders = get_filtered_orders(db, filter_criteria["food_types"], filter_criteria["food_categories"])
        else:
            active_orders = list(db.orders.find({"status": "active"}).sort([("prepared", 1), ("timestamp", 1)]))


        for order in active_orders:
            await websocket.send_text(json.dumps(order, default=str))

        while True:
            
            data = await websocket.receive_text()
            message = json.loads(data)
            message_type = message.get("type", "")

            if message_type == "filter" and role == "kds":
                active_orders = get_filtered_orders(
                    db, 
                    filter_criteria["food_types"], 
                    filter_criteria["food_categories"]
                )
                await websocket.send_text(json.dumps({
                    "type": "filtered_orders",
                    "orders": active_orders
                }, default=str))

            elif message_type == "update_order" and role == "waiter":
                order_id = message["order_id"]
                updates = message["updates"]
                order = db.orders.find_one({"id": order_id})
                
                if order.get("prepared"):
                    updates.update({
                        "prepared": False,
                        "items.$[].prepared": False
                    })
                
                db.orders.update_one({"id": order_id}, {"$set": updates})
                await manager.broadcast(json.dumps({
                    "type": "order_updated",
                    "order_id": order_id,
                    "updates": updates
                }), roles=["kds"])
                
                # Refresh KDS view
                await manager.broadcast(json.dumps({"type": "refresh_kds"}), roles=["kds"])

            elif message_type == "cancel_item" and role == "waiter":
                await manager.notify_kds_cancellation(
                    message["order_id"],
                    message["item_name"],
                    message.get("reason", "")
                )

            elif message_type == "approve_cancellation" and role == "kds":
                order_id = message["order_id"]
                item_name = message["item_name"]
                
                db.orders.update_one(
                    {"id": order_id},
                    {"$pull": {"items": {"name": item_name}}}
                )
                
                await manager.broadcast(json.dumps({
                    "type": "cancellation_approved",
                    "order_id": order_id,
                    "item_name": item_name
                }), roles=["waiter"])
                
                # Refresh KDS view
                await manager.broadcast(json.dumps({"type": "refresh_kds"}), roles=["kds"])

            elif message_type == "reject_cancellation" and role == "kds":
                await manager.broadcast(json.dumps({
                    "type": "cancellation_rejected",
                    "order_id": message["order_id"],
                    "item_name": message["item_name"],
                    "reason": message.get("reason", "")
                }), roles=["waiter"])

            elif message_type == "add_items" and role == "waiter":
                order_id = message["order_id"]
                new_items = message["items"]
                order = db.orders.find_one({"id": order_id})
                
                if order.get("prepared"):
                    db.orders.update_one(
                        {"id": order_id},
                        {"$set": {
                            "prepared": False,
                            "items.$[].prepared": False
                        }}
                    )
                
                db.orders.update_one(
                    {"id": order_id},
                    {"$push": {"items": {"$each": new_items}}}
                )
                
                await manager.broadcast(json.dumps({
                    "type": "items_added",
                    "order_id": order_id,
                    "items": new_items
                }), roles=["kds"])
                
                # Refresh KDS view
                await manager.broadcast(json.dumps({"type": "refresh_kds"}), roles=["kds"])






            elif message.get("type") == "acknowledgment" and role == "kds":
                order_id = message.get("order_id")
                try:
                    db.orders.update_one({"id": order_id}, {"$set": {"received": True}})
                    print(f"Order {order_id} acknowledged by KDS user")
                except Exception as e:
                    print(f"Error acknowledging order {order_id}: {e}")
            elif message.get("type") == "prepare_item" and role == "kds":
                order_id = message.get("order_id")
                item_name = message.get("item_name")
                try:
                    db.orders.update_one(
                        {"id": order_id, "items.name": item_name},
                        {"$set": {"items.$.prepared_items": True}}
                    )
                    print(f"Item {item_name} in order {order_id} marked as prepared by KDS user")
                    await manager.broadcast(json.dumps({"type": "order_update", "order_id": order_id, "item_name": item_name, "status": "prepared"}), roles=["kds"])
                    # Notify the specific waiter
                    employee_id = db.orders.find_one({"id": order_id})["employee_id"]
                    await manager.broadcast(json.dumps({"type": "order_update", "order_id": order_id, "item_name": item_name, "status": "prepared"}), employee_id=employee_id)
                except Exception as e:
                    print(f"Error marking item {item_name} as prepared in order {order_id}: {e}")
            elif message.get("type") == "prepare_order" and role == "kds":
                order_id = message.get("order_id")
                try:
                    db.orders.update_one({"id": order_id}, {"$set": {"prepared": True}})
                    db.orders.update_many({"id": order_id}, {"$set": {"items.$[].prepared": True}})
                    print(f"Order {order_id} marked as prepared by KDS user")
                    await manager.broadcast(json.dumps({"type": "order_update", "order_id": order_id, "status": "prepared"}), roles=["kds"])
                    # Notify the specific waiter
                    employee_id = db.orders.find_one({"id": order_id})["employee_id"]
                    await manager.broadcast(json.dumps({"type": "order_update", "order_id": order_id, "status": "prepared"}), employee_id=employee_id)
                except Exception as e:
                    print(f"Error marking order {order_id} as prepared: {e}")






    except WebSocketDisconnect:
        manager.disconnect(websocket, role=role, employee_id=employee_id)
        stop_event.set()
        if role == "kds":
            task.cancel()
    except Exception as e:
        print(f"Error: {e}")
        stop_event.set()
        if role == "kds":
            task.cancel()












































































































