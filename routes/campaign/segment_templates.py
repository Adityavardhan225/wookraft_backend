from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_template_definitions() -> List[Dict[str, Any]]:
    """
    Get all available segment template definitions.
    
    Returns:
        List of template definitions
    """
    return [
        # Spending-Based Segments
        {
            "id": "big_spenders",
            "name": "Big Spenders",
            "description": "Customers who spent above a custom threshold",
            "category": "spending",
            "parameters": [
                {
                    "name": "min_spend",
                    "label": "Minimum Spend",
                    "type": "number",
                    "default": 10000
                }
            ]
        },
        {
            "id": "mid_range_spenders",
            "name": "Mid-Range Spenders",
            "description": "Customers within specific spending brackets",
            "category": "spending",
            "parameters": [
                {
                    "name": "min_spend",
                    "label": "Minimum Spend",
                    "type": "number",
                    "default": 5000
                },
                {
                    "name": "max_spend",
                    "label": "Maximum Spend",
                    "type": "number",
                    "default": 10000
                }
            ]
        },
        {
            "id": "high_aov",
            "name": "High Average Order Value",
            "description": "Customers with high per-order average",
            "category": "spending",
            "parameters": [
                {
                    "name": "min_aov",
                    "label": "Minimum Average Order Value",
                    "type": "number",
                    "default": 1000
                }
            ]
        },
        {
            "id": "increasing_spend",
            "name": "Increasing Spend Trend",
            "description": "Customers whose spending is growing",
            "category": "spending",
            "parameters": []
        },
        
        # Frequency-Based Segments
        {
            "id": "daily_visitors",
            "name": "Daily Visitors",
            "description": "Customers who visit almost every day",
            "category": "frequency",
            "parameters": []
        },
        {
            "id": "weekly_regulars",
            "name": "Weekly Regulars",
            "description": "Customers who visit at least once a week",
            "category": "frequency",
            "parameters": []
        },
        {
            "id": "one_time_visitors",
            "name": "One-Time Visitors",
            "description": "Customers who only visited once",
            "category": "frequency",
            "parameters": []
        },
        
        # Recency-Based Segments
        {
            "id": "new_customers",
            "name": "Brand New Customers",
            "description": "First visit in last 7 days",
            "category": "recency",
            "parameters": [
                {
                    "name": "days",
                    "label": "Days",
                    "type": "number",
                    "default": 7
                }
            ]
        },
        {
            "id": "returning_after_absence",
            "name": "Returning After Absence",
            "description": "Inactive customers who recently returned",
            "category": "recency",
            "parameters": [
                {
                    "name": "inactive_days",
                    "label": "Inactive Days",
                    "type": "number",
                    "default": 60
                },
                {
                    "name": "return_days",
                    "label": "Return Within Days",
                    "type": "number",
                    "default": 30
                }
            ]
        },
        {
            "id": "at_risk",
            "name": "About to Become Inactive",
            "description": "Haven't visited in 60-90 days",
            "category": "recency",
            "parameters": [
                {
                    "name": "min_days",
                    "label": "Minimum Days Since Last Visit",
                    "type": "number",
                    "default": 60
                },
                {
                    "name": "max_days",
                    "label": "Maximum Days Since Last Visit",
                    "type": "number",
                    "default": 90
                }
            ]
        },
        
        # Visit Pattern Segments
        {
            "id": "weekday_customers",
            "name": "Weekday Customers",
            "description": "Primarily visit on weekdays",
            "category": "visit_pattern",
            "parameters": []
        },
        {
            "id": "weekend_customers",
            "name": "Weekend Customers",
            "description": "Primarily visit on weekends",
            "category": "visit_pattern",
            "parameters": []
        },
        {
            "id": "lunch_crowd",
            "name": "Lunch Crowd",
            "description": "Primarily visit during lunch hours",
            "category": "visit_pattern",
            "parameters": []
        },
        {
            "id": "dinner_patrons",
            "name": "Dinner Patrons",
            "description": "Primarily visit during dinner hours",
            "category": "visit_pattern",
            "parameters": []
        },
        
        # Loyalty/Tenure Segments
        {
            "id": "long_term_loyal",
            "name": "Long-Term Loyal",
            "description": "Customers for over 1 year",
            "category": "loyalty",
            "parameters": [
                {
                    "name": "min_years",
                    "label": "Minimum Years",
                    "type": "number",
                    "default": 1
                }
            ]
        },
        
        # Combined Behavior Segments
        {
            "id": "high_value_regulars",
            "name": "High-Value Regulars",
            "description": "Frequent + high spend customers",
            "category": "combined",
            "parameters": [
                {
                    "name": "min_visits",
                    "label": "Minimum Visits",
                    "type": "number",
                    "default": 10
                },
                {
                    "name": "min_spend",
                    "label": "Minimum Total Spend",
                    "type": "number",
                    "default": 10000
                }
            ]
        },
        {
            "id": "at_risk_high_value",
            "name": "At-Risk High-Value",
            "description": "High-value customers with declining visit frequency",
            "category": "combined",
            "parameters": [
                {
                    "name": "min_spend",
                    "label": "Minimum Total Spend",
                    "type": "number",
                    "default": 10000
                },
                {
                    "name": "days_since_last_visit",
                    "label": "Minimum Days Since Last Visit",
                    "type": "number",
                    "default": 30
                }
            ]
        }
    ]

def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get template definition by ID.
    
    Args:
        template_id: Template ID
        
    Returns:
        Template definition or None if not found
    """
    templates = get_template_definitions()
    for template in templates:
        if template["id"] == template_id:
            return template
    return None

def build_criteria_from_template(template_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Build segment criteria from template.
    
    Args:
        template_id: Template ID
        params: Custom parameters for the template
        
    Returns:
        Criteria dictionary for the segment
    """
    if params is None:
        params = {}
        
    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
        
    # Use default params if not provided
    for param in template.get("parameters", []):
        param_name = param["name"]
        if param_name not in params and "default" in param:
            params[param_name] = param["default"]
    
    # Build criteria based on template
    if template_id == "big_spenders":
        min_spend = params.get("min_spend", 10000)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "total_spent",
                    "operator": "gte",
                    "value": min_spend
                }
            ]
        }
        
    elif template_id == "mid_range_spenders":
        min_spend = params.get("min_spend", 5000)
        max_spend = params.get("max_spend", 10000)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "total_spent",
                    "operator": "gte",
                    "value": min_spend
                },
                {
                    "field": "total_spent",
                    "operator": "lte",
                    "value": max_spend
                }
            ]
        }
        
    elif template_id == "high_aov":
        min_aov = params.get("min_aov", 1000)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "avg_order_value",
                    "operator": "gte",
                    "value": min_aov
                }
            ]
        }
        
    elif template_id == "increasing_spend":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "spending_trend",
                    "operator": "equals",
                    "value": "increasing"
                }
            ]
        }
        
    elif template_id == "daily_visitors":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "visit_frequency",
                    "operator": "equals",
                    "value": "daily"
                }
            ]
        }
        
    elif template_id == "weekly_regulars":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "visit_frequency",
                    "operator": "equals",
                    "value": "weekly"
                }
            ]
        }
        
    elif template_id == "one_time_visitors":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "total_visits",
                    "operator": "equals",
                    "value": 1
                }
            ]
        }
        
    elif template_id == "new_customers":
        days = params.get("days", 7)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "first_visit",
                    "operator": "inLast",
                    "value": days
                }
            ]
        }
        
    elif template_id == "returning_after_absence":
        inactive_days = params.get("inactive_days", 60)
        return_days = params.get("return_days", 30)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "last_visit",
                    "operator": "inLast",
                    "value": return_days
                },
                {
                    "operator": "AND",
                    "conditions": [
                        {
                            "field": "previous_visit",
                            "operator": "before",
                            "value": datetime.now() - timedelta(days=inactive_days)
                        }
                    ]
                }
            ]
        }
        
    elif template_id == "at_risk":
        min_days = params.get("min_days", 60)
        max_days = params.get("max_days", 90)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "days_since_last_visit",
                    "operator": "between",
                    "value": [min_days, max_days]
                }
            ]
        }
        
    elif template_id == "weekday_customers":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "is_weekday_customer",
                    "operator": "equals",
                    "value": True
                }
            ]
        }
        
    elif template_id == "weekend_customers":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "is_weekend_customer",
                    "operator": "equals",
                    "value": True
                }
            ]
        }
        
    elif template_id == "lunch_crowd":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "time_of_day",
                    "operator": "equals",
                    "value": "lunch"
                }
            ]
        }
        
    elif template_id == "dinner_patrons":
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "time_of_day",
                    "operator": "equals",
                    "value": "dinner"
                }
            ]
        }
        
    elif template_id == "long_term_loyal":
        min_years = params.get("min_years", 1)
        days = min_years * 365
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "first_visit",
                    "operator": "before",
                    "value": datetime.now() - timedelta(days=days)
                }
            ]
        }
        
    elif template_id == "high_value_regulars":
        min_visits = params.get("min_visits", 10)
        min_spend = params.get("min_spend", 10000)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "total_visits",
                    "operator": "gte",
                    "value": min_visits
                },
                {
                    "field": "total_spent",
                    "operator": "gte",
                    "value": min_spend
                }
            ]
        }
        
    elif template_id == "at_risk_high_value":
        min_spend = params.get("min_spend", 10000)
        days_since = params.get("days_since_last_visit", 30)
        return {
            "operator": "AND",
            "conditions": [
                {
                    "field": "total_spent",
                    "operator": "gte",
                    "value": min_spend
                },
                {
                    "field": "days_since_last_visit",
                    "operator": "gte",
                    "value": days_since
                }
            ]
        }
    
    # Default empty criteria if template not implemented
    return {
        "operator": "AND",
        "conditions": []
    }

async def build_segment_from_template(template_id: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Build a complete segment from template.
    
    Args:
        template_id: Template ID
        params: Custom parameters for the template
        
    Returns:
        Complete segment definition
    """
    if params is None:
        params = {}
        
    template = get_template_by_id(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
        
    criteria = build_criteria_from_template(template_id, params)
    
    # Build segment from template
    segment = {
        "name": params.get("name", template["name"]),
        "description": params.get("description", template["description"]),
        "criteria": criteria,
        "creation_method": "template",
        "template_id": template_id,
        "template_params": params
    }
    
    return segment