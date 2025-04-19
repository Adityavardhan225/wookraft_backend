from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from bson import ObjectId
from configurations.config import client

logger = logging.getLogger(__name__)
db = client["wookraft_db"]
customer_collection = db["customer_order_history"]

def get_day_of_week(date_value):
    """Convert date to day of week (0=Monday, 6=Sunday)"""
    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return None
    return date_value.weekday()

def get_hour_of_day(date_value):
    """Extract hour from datetime"""
    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return None
    return date_value.hour

def calculate_days_since(date_value):
    """Calculate days since the given date"""
    if not date_value:
        return None
    if isinstance(date_value, str):
        try:
            date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        except:
            return None
    return (datetime.now() - date_value).days

def calculate_avg_order_value(orders):
    """Calculate average order value from orders"""
    if not orders or len(orders) == 0:
        return 0
    total = sum(order.get('total', 0) for order in orders)
    return total / len(orders)

def calculate_visit_frequency(visit_dates):
    """Determine visit frequency pattern (daily, weekly, monthly, etc.)"""
    if not visit_dates or len(visit_dates) < 3:
        return "irregular"
    
    # Sort dates
    sorted_dates = sorted(visit_dates)
    
    # Calculate average days between visits
    intervals = [(sorted_dates[i] - sorted_dates[i-1]).days for i in range(1, len(sorted_dates))]
    avg_interval = sum(intervals) / len(intervals)
    
    if avg_interval <= 2:
        return "daily"
    elif 2 < avg_interval <= 10:
        return "weekly"
    elif 10 < avg_interval <= 40:
        return "monthly"
    else:
        return "quarterly"

def calculate_spending_trend(orders, days=90):
    """Calculate spending trend (increasing, stable, decreasing)"""
    if not orders or len(orders) < 3:
        return "insufficient_data"
    
    # Get orders within period
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_orders = [o for o in orders if o.get('date') > cutoff_date]
    
    if len(recent_orders) < 3:
        return "insufficient_data"
    
    # Divide into two periods
    mid_point = cutoff_date + timedelta(days=days/2)
    period1 = [o.get('total', 0) for o in recent_orders if o.get('date') <= mid_point]
    period2 = [o.get('total', 0) for o in recent_orders if o.get('date') > mid_point]
    
    if not period1 or not period2:
        return "insufficient_data"
    
    avg1 = sum(period1) / len(period1)
    avg2 = sum(period2) / len(period2)
    
    change_pct = (avg2 - avg1) / avg1 if avg1 > 0 else 0
    
    if change_pct > 0.15:
        return "increasing"
    elif change_pct < -0.15:
        return "decreasing"
    else:
        return "stable"

def is_weekday_customer(visit_dates, threshold=0.7):
    """Determine if customer primarily visits on weekdays"""
    if not visit_dates or len(visit_dates) < 3:
        return None
    
    weekday_visits = sum(1 for d in visit_dates if d.weekday() < 5)
    return (weekday_visits / len(visit_dates)) > threshold

def is_weekend_customer(visit_dates, threshold=0.7):
    """Determine if customer primarily visits on weekends"""
    if not visit_dates or len(visit_dates) < 3:
        return None
    
    weekend_visits = sum(1 for d in visit_dates if d.weekday() >= 5)
    return (weekend_visits / len(visit_dates)) > threshold

def get_time_period_preference(visit_dates, threshold=0.6):
    """Determine customer's preferred time period"""
    if not visit_dates or len(visit_dates) < 3:
        return None
    
    morning = sum(1 for d in visit_dates if 5 <= d.hour < 12)
    lunch = sum(1 for d in visit_dates if 12 <= d.hour < 15)
    dinner = sum(1 for d in visit_dates if 17 <= d.hour < 22)
    late_night = sum(1 for d in visit_dates if 22 <= d.hour or d.hour < 5)
    
    counts = {
        "morning": morning / len(visit_dates),
        "lunch": lunch / len(visit_dates),
        "dinner": dinner / len(visit_dates),
        "late_night": late_night / len(visit_dates)
    }
    
    max_period = max(counts, key=counts.get)
    if counts[max_period] > threshold:
        return max_period
    return "mixed"