from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from configurations.config import client

logger = logging.getLogger(__name__)

# Database access
db = client["wookraft_db"]
customer_collection = db["customer_order_history"]
segment_collection = db["customer_segments"]

async def analyze_segment_overlap(segment_ids: List[str]) -> Dict[str, Any]:
    """
    Analyze overlap between segments.
    
    Args:
        segment_ids: List of segment IDs to analyze
        
    Returns:
        Dictionary with overlap analysis results
    """
    try:
        from .segment_membership_services import segment_membership_collection
        
        # Get segment info
        segments = []
        for segment_id in segment_ids:
            segment = segment_collection.find_one({"id": segment_id})
            if not segment:
                continue
                
            # Get customer count
            membership = segment_membership_collection.find_one({"segment_id": segment_id})
            count = membership.get("customer_count", 0) if membership else 0
                
            segments.append({
                "id": segment_id,
                "name": segment.get("name", ""),
                "count": count
            })
            
        # Calculate overlap for each pair
        overlap_matrix = {}
        for i, segment1 in enumerate(segments):
            overlap_matrix[segment1["id"]] = {}
            
            for j, segment2 in enumerate(segments):
                if i == j:
                    # Same segment, overlap is 100%
                    overlap_matrix[segment1["id"]][segment2["id"]] = segment1["count"]
                    continue
                    
                # Build query to find customers in both segments
                from .customer_segment_services import build_combined_query
                query = await build_combined_query(
                    segment_ids=[segment1["id"], segment2["id"]],
                    operator="AND"
                )
                
                # Count customers in both segments
                count = customer_collection.count_documents(query)
                overlap_matrix[segment1["id"]][segment2["id"]] = count
        
        # Calculate percentages
        percentage_matrix = {}
        for segment1_id, overlaps in overlap_matrix.items():
            percentage_matrix[segment1_id] = {}
            segment1 = next((s for s in segments if s["id"] == segment1_id), None)
            segment1_count = segment1["count"] if segment1 else 0
            
            for segment2_id, count in overlaps.items():
                segment2 = next((s for s in segments if s["id"] == segment2_id), None)
                segment2_count = segment2["count"] if segment2 else 0
                
                if segment1_count > 0:
                    pct_of_segment1 = count / segment1_count
                else:
                    pct_of_segment1 = 0
                    
                if segment2_count > 0:
                    pct_of_segment2 = count / segment2_count
                else:
                    pct_of_segment2 = 0
                    
                percentage_matrix[segment1_id][segment2_id] = {
                    "count": count,
                    "pct_of_segment1": pct_of_segment1,
                    "pct_of_segment2": pct_of_segment2
                }
        
        return {
            "segments": segments,
            "overlap_matrix": overlap_matrix,
            "percentage_matrix": percentage_matrix
        }
        
    except Exception as e:
        logger.error(f"Error analyzing segment overlap: {str(e)}")
        raise ValueError(f"Failed to analyze segment overlap: {str(e)}")

async def analyze_customer_lifecycle(customer_id: str) -> Dict[str, Any]:
    """
    Analyze customer lifecycle and spending patterns.
    
    Args:
        customer_id: Customer ID
        
    Returns:
        Dictionary with customer lifecycle analysis
    """
    try:
        # Get customer
        customer = customer_collection.find_one({"_id": ObjectId(customer_id)})
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
            
        # Get visit dates
        visit_dates = []
        for order in customer.get("orders", []):
            if "date" in order:
                visit_dates.append(order["date"])
                
        if not visit_dates:
            return {
                "customer_id": customer_id,
                "lifecycle_stage": "unknown",
                "analysis": "Not enough data for analysis"
            }
            
        # Sort dates
        visit_dates.sort()
        
        # Calculate key metrics
        first_visit = visit_dates[0]
        last_visit = visit_dates[-1]
        days_since_first = (datetime.now() - first_visit).days
        days_since_last = (datetime.now() - last_visit).days
        total_visits = len(visit_dates)
        
        # Calculate tenure in days
        tenure_days = (last_visit - first_visit).days if len(visit_dates) > 1 else 0
        
        # Calculate average days between visits
        if len(visit_dates) > 1:
            intervals = [(visit_dates[i] - visit_dates[i-1]).days for i in range(1, len(visit_dates))]
            avg_interval = sum(intervals) / len(intervals)
        else:
            avg_interval = None
            
        # Get spending data
        total_spent = customer.get("total_spent", 0)
        
        # Calculate average order value
        order_values = [order.get("total", 0) for order in customer.get("orders", [])]
        avg_order_value = sum(order_values) / len(order_values) if order_values else 0
        
        # Determine lifecycle stage
        lifecycle_stage = "unknown"
        
        if total_visits == 1 and days_since_last <= 90:
            lifecycle_stage = "new_single"
        elif total_visits > 1 and days_since_last <= 30:
            lifecycle_stage = "active"
        elif 30 < days_since_last <= 90:
            lifecycle_stage = "at_risk"
        elif days_since_last > 90:
            lifecycle_stage = "inactive"
            
        # Check if they're a high-value customer
        if avg_order_value > 1000 or total_spent > 10000:
            lifecycle_stage += "_high_value"
            
        # Check loyalty
        if tenure_days > 365 and total_visits > 10:
            lifecycle_stage += "_loyal"
            
        # Analyze spending trend
        from .segment_calculated_fields import calculate_spending_trend
        spending_trend = calculate_spending_trend(customer.get("orders", []))
        
        # Analyze visit frequency
        from .segment_calculated_fields import calculate_visit_frequency
        visit_frequency = calculate_visit_frequency(visit_dates)
        
        return {
            "customer_id": customer_id,
            "lifecycle_stage": lifecycle_stage,
            "tenure_days": tenure_days,
            "total_visits": total_visits,
            "days_since_first": days_since_first,
            "days_since_last": days_since_last,
            "avg_interval_days": avg_interval,
            "total_spent": total_spent,
            "avg_order_value": avg_order_value,
            "spending_trend": spending_trend,
            "visit_frequency": visit_frequency
        }
        
    except Exception as e:
        logger.error(f"Error analyzing customer lifecycle: {str(e)}")
        raise ValueError(f"Failed to analyze customer lifecycle: {str(e)}")