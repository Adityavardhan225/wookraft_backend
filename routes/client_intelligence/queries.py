from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryBuilder:
    """
    Class for building MongoDB aggregation pipelines for analytics queries
    """
    
    @staticmethod
    def sales_by_period(start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        period: str = "daily") -> List[Dict]:
        """
        Build pipeline for sales aggregated by time period
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            period: Aggregation period (daily, weekly, monthly)
            
        Returns:
            MongoDB aggregation pipeline
        """
        # Build match stage for date filtering
        match_stage = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            match_stage = {"$match": {"date": date_filter}}
        
        # Build group stage based on period
        group_stage = {"$group": {"_id": None}}
        
        if period == "daily":
            group_stage["$group"]["_id"] = {"$dateToString": {"format": "%Y-%m-%d", "date": "$date"}}
        elif period == "weekly":
            group_stage["$group"]["_id"] = {"$week": "$date"}
        elif period == "monthly":
            group_stage["$group"]["_id"] = {"$dateToString": {"format": "%Y-%m", "date": "$date"}}
        elif period == "yearly":
            group_stage["$group"]["_id"] = {"$year": "$date"}
        
        # Add metrics to group stage
        group_stage["$group"].update({
            "total_sales": {"$sum": "$total_amount"},
            "average_bill": {"$avg": "$total_amount"},
            "bill_count": {"$sum": 1},
            "item_count": {"$sum": {"$size": "$items"}}
        })
        
        # Build the pipeline
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            group_stage,
            {"$sort": {"_id": 1}},
            {"$project": {
                "period": "$_id",
                "total_sales": 1,
                "average_bill": 1,
                "bill_count": 1,
                "item_count": 1,
                "_id": 0
            }}
        ])
        
        return pipeline
    
    @staticmethod
    def sales_by_category(start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict]:
        """
        Build pipeline for sales aggregated by item category
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            MongoDB aggregation pipeline
        """
        # Build match stage for date filtering
        match_stage = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            match_stage = {"$match": {"date": date_filter}}
        
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.category",
                "total_sales": {"$sum": {"$multiply": ["$items.quantity", "$items.unit_price"]}},
                "item_count": {"$sum": "$items.quantity"},
                "order_count": {"$sum": 1}
            }},
            {"$sort": {"total_sales": -1}},
            {"$project": {
                "category": "$_id",
                "total_sales": 1,
                "item_count": 1,
                "order_count": 1,
                "average_item_price": {"$divide": ["$total_sales", "$item_count"]},
                "_id": 0
            }}
        ])
        
        return pipeline
    
    @staticmethod
    def top_selling_items(start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         limit: int = 10) -> List[Dict]:
        """
        Build pipeline for top selling items by quantity
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            limit: Number of items to return
            
        Returns:
            MongoDB aggregation pipeline
        """
        # Build match stage for date filtering
        match_stage = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            match_stage = {"$match": {"date": date_filter}}
        
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            {"$unwind": "$items"},
            {"$group": {
                "_id": {
                    "name": "$items.name",
                    "category": "$items.category"
                },
                "quantity": {"$sum": "$items.quantity"},
                "revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.unit_price"]}},
                "order_count": {"$sum": 1}
            }},
            {"$sort": {"quantity": -1}},
            {"$limit": limit},
            {"$project": {
                "name": "$_id.name",
                "category": "$_id.category",
                "quantity": 1,
                "revenue": 1,
                "order_count": 1,
                "average_price": {"$divide": ["$revenue", "$quantity"]},
                "_id": 0
            }}
        ])
        
        return pipeline
    
    @staticmethod
    def customer_insights(limit: int = 10) -> List[Dict]:
        """
        Build pipeline for customer insights
        
        Args:
            limit: Number of top customers to return
            
        Returns:
            MongoDB aggregation pipeline
        """
        return [
            {"$sort": {"total_spent": -1}},
            {"$limit": limit},
            {"$project": {
                "_id": 0,
                "name": 1,
                "email": 1,
                "first_visit": 1,
                "last_visit": 1,
                "total_visits": 1,
                "total_spent": 1,
                "average_order_value": {"$divide": ["$total_spent", "$total_visits"]},
                "days_since_last_visit": {
                    "$divide": [
                        {"$subtract": [datetime.now(), "$last_visit"]},
                        24 * 60 * 60 * 1000
                    ]
                }
            }}
        ]
    
    @staticmethod
    def menu_performance() -> List[Dict]:
        """
        Build pipeline for menu item performance
        
        Returns:
            MongoDB aggregation pipeline
        """
        return [
            {"$sort": {"total_revenue": -1}},
            {"$project": {
                "_id": 0,
                "name": 1,
                "category": 1,
                "type": 1,
                "total_orders": 1,
                "total_quantity": 1,
                "total_revenue": 1,
                "average_price": {"$divide": ["$total_revenue", "$total_quantity"]},
                "daily_average": {
                    "$divide": [
                        "$total_quantity",
                        {"$size": "$daily_sales"}
                    ]
                }
            }}
        ]
    
    @staticmethod
    def table_utilization(start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> List[Dict]:
        """
        Build pipeline for table utilization analysis
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            MongoDB aggregation pipeline
        """
        # Get reservations for the period
        match_stage = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            match_stage = {"$match": {"reservation_date": date_filter}}
        
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            {"$unwind": "$table_ids"},
            {"$lookup": {
                "from": "tables",
                "localField": "table_ids",
                "foreignField": "_id",
                "as": "table"
            }},
            {"$unwind": "$table"},
            {"$group": {
                "_id": {
                    "table_id": "$table_ids",
                    "table_number": "$table.table_number",
                    "capacity": "$table.capacity",
                    "section": "$table.section"
                },
                "reservation_count": {"$sum": 1},
                "customer_count": {"$sum": "$party_size"},
                "utilization": {
                    "$sum": {
                        "$divide": ["$party_size", "$table.capacity"]
                    }
                }
            }},
            {"$project": {
                "table_number": "$_id.table_number",
                "capacity": "$_id.capacity",
                "section": "$_id.section",
                "reservation_count": 1,
                "customer_count": 1,
                "average_party_size": {"$divide": ["$customer_count", "$reservation_count"]},
                "utilization_rate": {"$divide": ["$utilization", "$reservation_count"]},
                "_id": 0
            }},
            {"$sort": {"table_number": 1}}
        ])
        
        return pipeline
    
    @staticmethod
    def reservation_status_breakdown(start_date: Optional[str] = None,
                                    end_date: Optional[str] = None) -> List[Dict]:
        """
        Build pipeline for reservation status breakdown
        
        Args:
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            MongoDB aggregation pipeline
        """
        # Build match stage for date filtering
        match_stage = {}
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            if end_date:
                date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            match_stage = {"$match": {"reservation_date": date_filter}}
        
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        
        pipeline.extend([
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "average_party_size": {"$avg": "$party_size"}
            }},
            {"$project": {
                "status": "$_id",
                "count": 1,
                "average_party_size": 1,
                "_id": 0
            }},
            {"$sort": {"count": -1}}
        ])
        
        return pipeline
    
    @staticmethod
    def dynamic_query(
        collection: str,
        dimensions: List[Dict],
        measures: List[Dict],
        filters: List[Dict] = None,
        sort: List[Dict] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        Build a dynamic aggregation pipeline based on request parameters
        
        Args:
            collection: Collection name to query
            dimensions: List of dimensions to group by
            measures: List of measures to calculate
            filters: List of filters to apply
            sort: Sort configuration
            limit: Result limit
            
        Returns:
            MongoDB aggregation pipeline
        """
        pipeline = []
        
        # Add match stage if filters exist
        if filters:
            match_conditions = {}
            for filter_item in filters:
                field = filter_item.get("field")
                operator = filter_item.get("operator")
                value = filter_item.get("value")
                
                if operator == "eq":
                    match_conditions[field] = value
                elif operator == "ne":
                    match_conditions[field] = {"$ne": value}
                elif operator == "gt":
                    match_conditions[field] = {"$gt": value}
                elif operator == "gte":
                    match_conditions[field] = {"$gte": value}
                elif operator == "lt":
                    match_conditions[field] = {"$lt": value}
                elif operator == "lte":
                    match_conditions[field] = {"$lte": value}
                elif operator == "in":
                    match_conditions[field] = {"$in": value}
                elif operator == "not_in":
                    match_conditions[field] = {"$nin": value}
                elif operator == "contains":
                    match_conditions[field] = {"$regex": value, "$options": "i"}
                elif operator == "not_contains":
                    match_conditions[field] = {"$not": {"$regex": value, "$options": "i"}}
                elif operator == "between":
                    match_conditions[field] = {"$gte": value[0], "$lte": value[1]}
            
            if match_conditions:
                pipeline.append({"$match": match_conditions})
        
        # Add unwind stage if needed
        for dimension in dimensions:
            field = dimension.get("field")
            if "." in field and not field.endswith("."):
                array_field = field.split(".")[0]
                pipeline.append({"$unwind": f"${array_field}"})
        
        # Build group stage
        group_stage = {"_id": {}}
        for dimension in dimensions:
            field = dimension.get("field")
            label = dimension.get("label", field)
            
            # Handle date formatting
            if dimension.get("dataType") == "date" and dimension.get("format", {}).get("pattern"):
                pattern = dimension.get("format").get("pattern")
                group_stage["_id"][label] = {"$dateToString": {"format": pattern, "date": f"${field}"}}
            else:
                group_stage["_id"][label] = f"${field}"
        
        # Add measures to group stage
        for measure in measures:
            field = measure.get("field")
            label = measure.get("label", field)
            aggregation = measure.get("aggregation", "sum")
            
            if aggregation == "sum":
                group_stage[label] = {"$sum": f"${field}"}
            elif aggregation == "avg":
                group_stage[label] = {"$avg": f"${field}"}
            elif aggregation == "min":
                group_stage[label] = {"$min": f"${field}"}
            elif aggregation == "max":
                group_stage[label] = {"$max": f"${field}"}
            elif aggregation == "count":
                group_stage[label] = {"$sum": 1}
            elif aggregation == "count_distinct":
                group_stage[label] = {"$addToSet": f"${field}"}
        
        # Add group stage if we have dimensions or measures
        if dimensions or measures:
            pipeline.append({"$group": group_stage})
            
            # For count_distinct, add a project stage to get the actual count
            has_count_distinct = False
            for measure in measures:
                if measure.get("aggregation") == "count_distinct":
                    has_count_distinct = True
                    break
            
            if has_count_distinct:
                project_stage = {"_id": 0}
                for dimension in dimensions:
                    label = dimension.get("label", dimension.get("field"))
                    project_stage[label] = f"$_id.{label}"
                
                for measure in measures:
                    label = measure.get("label", measure.get("field"))
                    if measure.get("aggregation") == "count_distinct":
                        project_stage[label] = {"$size": f"${label}"}
                    else:
                        project_stage[label] = 1
                
                pipeline.append({"$project": project_stage})
        
        # Add sort stage if sort exists
        if sort:
            sort_stage = {}
            for sort_item in sort:
                field = sort_item.get("field")
                direction = -1 if sort_item.get("direction") == "desc" else 1
                sort_stage[field] = direction
            
            pipeline.append({"$sort": sort_stage})
        
        # Add limit stage
        if limit:
            pipeline.append({"$limit": limit})
        
        # Add project stage to flatten response
        if dimensions and not has_count_distinct:
            project_stage = {"_id": 0}
            for dimension in dimensions:
                label = dimension.get("label", dimension.get("field"))
                project_stage[label] = f"$_id.{label}"
            
            for measure in measures:
                label = measure.get("label", measure.get("field"))
                project_stage[label] = 1
            
            pipeline.append({"$project": project_stage})
        
        return pipeline