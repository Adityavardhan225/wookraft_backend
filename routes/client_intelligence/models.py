from pydantic import BaseModel, Field as PydanticField
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from enum import Enum



# ======== Enum Definitions ========

# class ChartType(str, Enum):
#     BAR = "bar"
#     LINE = "line"
#     PIE = "pie"
#     SCATTER = "scatter"
#     TABLE = "table"
#     NUMBER = "number"
#     HEATMAP = "heatmap"
#     GAUGE = "gauge"
#     FUNNEL = "funnel"


class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    AREA = "area"  # New
    PIE = "pie"
    DOUGHNUT = "doughnut"  # New
    SCATTER = "scatter"
    BUBBLE = "bubble"  # New
    TABLE = "table"
    NUMBER = "number"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"  # New
    RADAR = "radar"  # New
    GAUGE = "gauge"
    FUNNEL = "funnel"
    SANKEY = "sankey"  # New
    WATERFALL = "waterfall"  # New
    QUADRANT_CHART = "quadrantChart"  # New
    PARETO = "pareto"  # New
    VENN = "venn"  # New
    GEOMAP = "geomap"  # New
    NETWORK = "network"  # New
    GANTT = "gantt"  # New
    COUNTER = "counter"



class ChartFieldMapping(BaseModel):
    """Field mapping for specialized chart types"""
    x: Optional[str] = None  # X-axis field
    y: Optional[str] = None  # Y-axis field
    series: Optional[str] = None  # Series/grouping field
    label: Optional[str] = None  # Label field for data points
    labels: Optional[str] = None  # Labels field for pie/doughnut
    values: Optional[str] = None  # Values field for pie/doughnut
    size: Optional[str] = None  # Size field for bubble/treemap
    color: Optional[str] = None  # Color field for treemap
    categories: Optional[str] = None  # Categories for radar
    hierarchy: Optional[str] = None  # Hierarchy field for treemap
    source: Optional[str] = None  # Source field for sankey/network
    target: Optional[str] = None  # Target field for sankey/network
    weight: Optional[str] = None  # Weight field for network
    rows: Optional[str] = None  # Rows field for heatmap
    columns: Optional[List[Dict[str, Any]]] = None  # Columns config for table
    # rowField: Optional[str] = None  # Row field for table
    # rowSort: Optional[Dict[str, Any]] = None  # Row sorting for table
    # rowLimit: Optional[int] = None  # Row limit for table
    sets: Optional[str] = None  # Sets field for venn
    region: Optional[str] = None  # Region field for geomap
    nodes: Optional[str] = None  # Nodes field for network
    links: Optional[str] = None  # Links field for network
    task: Optional[str] = None  # Task field for gantt
    start: Optional[str] = None  # Start field for gantt
    end: Optional[str] = None  # End field for gantt
    progress: Optional[str] = None  # Progress field for gantt
    type: Optional[str] = None  # Type field for waterfall
    value: Optional[str] = None  # Value field for counter/number/pareto
    comparison: Optional[str] = None  # Comparison value for counter
    category: Optional[str] = None  # Category field for pareto

class AggregationType(str, Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"

class FilterOperator(str, Enum):
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUALS = "gte"
    LESS_THAN = "lt"
    LESS_THAN_EQUALS = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    BETWEEN = "between"

class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"

class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    ARRAY = "array"

# ======== Base Models ========

class Format(BaseModel):
    """Format configuration for display values"""
    type: Optional[str] = None  # e.g., number, currency, percent
    pattern: Optional[str] = None  # e.g., #,###.00
    currency: Optional[str] = None  # e.g., USD
    decimals: Optional[int] = None

class Field(BaseModel):
    """Field definition for dimensions and measures"""
    field: str
    label: str
    dataType: FieldType
    aggregation: Optional[AggregationType] = None
    format: Optional[Format] = None

class FilterCondition(BaseModel):
    """Filter condition for queries"""
    field: str
    operator: FilterOperator
    value: Any

class OrderBy(BaseModel):
    """Sort configuration"""
    field: str
    direction: SortDirection = SortDirection.ASC

class DataSource(BaseModel):
    """Data source configuration"""
    id: str
    type: Optional[str] = "mongodb"
    endpoint: Optional[str] = None

# ======== Query Models ========

class QueryRequest(BaseModel):
    """Query request configuration"""
    dataset_id: str
    dimensions: List[Field] = []
    measures: List[Field] = []
    filters: List[FilterCondition] = []
    order_by: Optional[List[OrderBy]] = []
    limit: Optional[int] = 1000
    
    def estimate_size(self) -> int:
        """Estimate the result size based on dimensions and measures"""
        # This is a very simplistic estimation
        return len(self.dimensions) * len(self.measures) * 100

class QueryResponse(BaseModel):
    """Query response"""
    data: List[Dict]
    count: int
    query: Dict

# ======== Dataset Models ========

class Dataset(BaseModel):
    """Dataset configuration"""
    id: str
    name: str
    description: Optional[str] = None
    fields: List[Dict]

class DatasetField(BaseModel):
    """Dataset field definition"""
    name: str
    type: FieldType
    description: Optional[str] = None

class DatasetResponse(BaseModel):
    """Dataset response with metadata"""
    id: str
    name: str
    description: Optional[str] = None
    last_updated: datetime
    record_count: int
    fields: List[Dict]
    available_aggregations: List[str]
    available_filters: List[str]

# ======== Chart Models ========

class ChartOptions(BaseModel):
    """Chart display options"""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    legend: Optional[Dict] = None
    colors: Optional[List[str]] = None
    axes: Optional[Dict] = None

class ChartConfig(BaseModel):
    """Chart configuration"""
    type: ChartType
    name: str
    description: Optional[str] = None
    data_source: DataSource
    dimensions: List[Field] = []
    measures: List[Field] = []
    filters: List[FilterCondition] = []
    fields: Optional[ChartFieldMapping] = None  # New field for specialized mappings
    options: Optional[ChartOptions] = None
    question_id: Optional[str] = None  # Support for question-based queries

class ChartCreate(ChartConfig):
    """Chart creation model"""
    pass

class ChartUpdate(BaseModel):
    """Chart update model - all fields optional"""
    type: Optional[ChartType] = None
    name: Optional[str] = None
    description: Optional[str] = None
    data_source: Optional[DataSource] = None
    dimensions: Optional[List[Field]] = None
    measures: Optional[List[Field]] = None
    filters: Optional[List[FilterCondition]] = None
    fields: Optional[ChartFieldMapping] = None  # New field
    options: Optional[ChartOptions] = None
    question_id: Optional[str] = None  # New field

class ChartResponse(ChartConfig):
    """Chart response model"""
    id: str
    created_at: datetime
    updated_at: datetime

# ======== Dashboard Models ========

class DashboardItemPosition(BaseModel):
    """Dashboard item position and size"""
    x: int
    y: int
    w: int
    h: int

class DashboardItem(BaseModel):
    """Dashboard item (charts, tables, etc.)"""
    id: str
    type: str  # Type of item (chart, table, etc.)
    component_id: str  # ID of the component (chart_id, etc.)
    x: int = 0
    y: int = 0
    w: int = 4
    h: int = 4
    config: Optional[Dict] = None  # Extra configuration for this item

class DashboardSettings(BaseModel):
    """Dashboard layout and display settings"""
    columns: int = 12
    row_height: int = 100
    margin: List[int] = [10, 10]
    container_padding: List[int] = [10, 10]
    is_draggable: bool = True
    is_resizable: bool = True
    compact_type: Optional[str] = "vertical"
    prevent_collision: bool = False
    theme: Optional[str] = "light"
    background_color: Optional[str] = "#f5f5f5"
    refresh_interval: Optional[int] = None  # in seconds

class Dashboard(BaseModel):
    """Dashboard configuration"""
    name: str
    description: Optional[str] = None
    items: List[DashboardItem] = []
    # settings: DashboardSettings = Field(default_factory=DashboardSettings)
    settings: DashboardSettings = PydanticField(default_factory=lambda: DashboardSettings())
    is_favorite: bool = False
    is_template: bool = False
    tags: List[str] = []

class DashboardCreate(Dashboard):
    """Dashboard creation model"""
    pass

class DashboardUpdate(BaseModel):
    """Dashboard update model - all fields optional"""
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[DashboardItem]] = None
    settings: Optional[DashboardSettings] = None
    is_favorite: Optional[bool] = None
    is_template: Optional[bool] = None
    tags: Optional[List[str]] = None

class DashboardResponse(Dashboard):
    """Dashboard response model"""
    id: str
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None



# Add these models to models.py

# ======== Dashboard History Models ========

class VersionHistoryEntry(BaseModel):
    """Version history entry for dashboard changes"""
    timestamp: datetime
    user: Optional[str] = None
    action: str  # e.g., "create", "update", "delete"
    snapshot: Optional[Dict] = None  # Full dashboard state at this version

class DashboardHistory(BaseModel):
    """Dashboard change history response"""
    dashboard_id: str
    entries: List[VersionHistoryEntry]

# ======== Dashboard Permissions Models ========

class UserPermissions(BaseModel):
    """User permissions for a dashboard"""
    can_view: bool = True
    can_edit: bool = False
    can_delete: bool = False
    can_share: bool = False

class DashboardPermissionsResponse(BaseModel):
    """Dashboard permissions response"""
    dashboard_id: str
    permissions: UserPermissions

# ======== Dashboard Editing State Models ========

class EditingState(BaseModel):
    """Dashboard editing state"""
    is_editing: bool
    edited_by: Optional[str] = None
    edited_since: Optional[datetime] = None
    has_unsaved_changes: bool = False

class DashboardEditingStateResponse(BaseModel):
    """Dashboard editing state response"""
    dashboard_id: str
    state: EditingState

# ======== Dashboard Item Selection Models ========

class DashboardItemsSelectionRequest(BaseModel):
    """Request to set selected dashboard items"""
    item_ids: List[str]

class DashboardItemsSelectionResponse(BaseModel):
    """Response with selected dashboard items"""
    dashboard_id: str
    selected_items: List[str]

class DashboardFocusedItemRequest(BaseModel):
    """Request to set focused dashboard item"""
    item_id: Optional[str] = None

class DashboardFocusedItemResponse(BaseModel):
    """Response with focused dashboard item"""
    dashboard_id: str
    focused_item: Optional[str] = None

# ======== Dashboard Data Models ========

class DashboardWithDataResponse(DashboardResponse):
    """Dashboard response with preloaded chart data"""
    # This extends DashboardResponse to include data in each item
    # No need to add extra fields as the data will be in the items
    pass

# ======== User Preferences Models ========

class UserPreferences(BaseModel):
    """User preferences for analytics"""
    default_dashboard_id: Optional[str] = None
    color_scheme: str = "default"
    date_format: str = "MM/DD/YYYY"
    number_format: Dict = {
        "decimal_places": 2,
        "thousands_separator": ","
    }
    last_visited_dashboards: List[str] = []


class FilterCondition(BaseModel):
    field: str
    operator: str  # "eq", "gt", "lt", "contains", etc.
    value: Any