from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class CampaignStatus(str, Enum):
    """Campaign status options"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class FilterOperator(str, Enum):
    """Filter operators for conditions"""
    EQUALS = "equals"
    NOT_EQUALS = "notEquals"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"
    STARTS_WITH = "startsWith"
    ENDS_WITH = "endsWith"

class LogicalOperator(str, Enum):
    """Logical operators for combining conditions"""
    AND = "AND"
    OR = "OR"

class FilterCondition(BaseModel):
    """Single filter condition for customer segmentation"""
    field: str
    operator: FilterOperator
    value: Any

class FilterGroup(BaseModel):
    """Group of filter conditions with a logical operator"""
    operator: LogicalOperator = LogicalOperator.AND
    conditions: List[Union[FilterCondition, 'FilterGroup']]

class EmailTemplateBase(BaseModel):
    """Base model for email templates with common fields"""
    name: str
    subject: str
    description: Optional[str] = None
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Template name cannot be empty')
        return v.strip()
    
    @validator('subject')
    def subject_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Subject cannot be empty')
        return v.strip()

class EmailTemplateCreate(EmailTemplateBase):
    """Model for creating a new email template"""
    html_content: str
    variables: Dict[str, Any] = {}
    @validator('html_content')
    def html_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('HTML content cannot be empty')
        return v

class EmailTemplateResponse(EmailTemplateBase):
    """Model for template response with IDs and timestamps"""
    id: str
    html_content: str
    logo_url: Optional[HttpUrl] = None
    background_url: Optional[HttpUrl] = None
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class EmailCampaignBase(BaseModel):
    """Base model for email campaigns with common fields"""
    name: str
    subject: str
    template_id: str
    segment_ids: List[str] = []
    custom_filters: List[Dict[str, Any]] = []
    operator: LogicalOperator = LogicalOperator.AND
    schedule_time: Optional[datetime] = None
    custom_variables: Dict[str, Any] = {}
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Campaign name cannot be empty')
        return v.strip()
    
    @validator('template_id')
    def template_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Template ID cannot be empty')
        return v
    
    @validator('segment_ids', 'custom_filters')
    def validate_targeting(cls, v, values):
        # At least one of segment_ids or custom_filters must be provided
        if 'segment_ids' in values and not values['segment_ids'] and not v:
            raise ValueError('Either segment IDs or custom filters must be provided')
        return v

class EmailCampaignCreate(EmailCampaignBase):
    """Model for creating a new email campaign"""
    pass

class EmailCampaignUpdate(BaseModel):
    """Model for updating an existing email campaign"""
    name: Optional[str] = None
    subject: Optional[str] = None
    template_id: Optional[str] = None
    segment_ids: Optional[List[str]] = None
    custom_filters: Optional[List[Dict[str, Any]]] = None
    operator: Optional[LogicalOperator] = None
    schedule_time: Optional[datetime] = None
    custom_variables: Optional[Dict[str, Any]] = None

class BatchStats(BaseModel):
    """Statistics for a batch of emails"""
    batch_index: int
    total: int
    sent: int
    failed: int
    duration_seconds: float
    completed_at: datetime

class CampaignStatistics(BaseModel):
    """Overall campaign statistics"""
    total_recipients: int = 0
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    failed: int = 0

class EmailCampaignResponse(EmailCampaignBase):
    """Model for campaign response with IDs, status and timestamps"""
    id: str
    status: CampaignStatus
    statistics: CampaignStatistics
    batches: Optional[List[BatchStats]] = None
    created_by: str
    created_at: datetime
    processing_started: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        orm_mode = True

class TestEmailRequest(BaseModel):
    """Request model for sending a test email"""
    email: EmailStr
    name: Optional[str] = None
    variables: Dict[str, Any] = {}