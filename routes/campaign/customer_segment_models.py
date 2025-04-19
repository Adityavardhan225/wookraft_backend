from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

class FilterCondition(BaseModel):
    field: str
    operator: str
    value: Any

class FilterCriteria(BaseModel):
    operator: str = "AND"
    conditions: List[Union[FilterCondition, "FilterCriteria"]] = []

class SegmentStatistics(BaseModel):
    customer_count: int = 0
    average_spend: Optional[float] = None
    retention_rate: Optional[float] = None
    growth_rate: Optional[float] = None

class RefreshSettings(BaseModel):
    frequency: str = "daily"  # daily, hourly, weekly, manual
    last_refresh: Optional[datetime] = None
    next_scheduled: Optional[datetime] = None
    average_duration_ms: Optional[int] = None

class SegmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: FilterCriteria
    
class SegmentCreate(SegmentBase):
    pass

class SegmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    criteria: Optional[FilterCriteria] = None
    refresh_settings: Optional[RefreshSettings] = None

class Segment(SegmentBase):
    id: str
    type: str = "custom"  # system or custom
    statistics: SegmentStatistics = SegmentStatistics()
    refresh_settings: RefreshSettings = RefreshSettings()
    creation_method: str = "user"  # system, user, import
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None

class SegmentMembership(BaseModel):
    segment_id: str
    customer_ids: List[str] = []
    refreshed_at: datetime
    calculation_duration_ms: int = 0
    customer_count: int = 0

class CustomerSegmentMembership(BaseModel):
    customer_id: str
    segment_ids: List[str] = []
    refreshed_at: datetime

class CombinedCriteriaRequest(BaseModel):
    segmentIds: List[str] = []
    customFilters: List[FilterCondition] = []
    operator: str = "AND"