from pydantic import BaseModel, HttpUrl, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class URLBase(BaseModel):
    original_url: HttpUrl
    short_code: Optional[str] = None

class URLCreate(URLBase):
    tags: Optional[List[str]] = []

class URLUpdate(BaseModel):
    original_url: Optional[HttpUrl] = None
    tags: Optional[List[str]] = None


class URLResponse(URLBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    short_code: str
    click_count: int = 0
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[str] = []

class URLListResponse(BaseModel):
    urls: List[URLResponse]
    total: int
    page: int
    per_page: int

# Схеми для тегів
class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

class TagCreate(TagBase):
    pass

class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    urls_count: int = 0

class URLStats(BaseModel):
    url_id: int
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    recent_clicks: int = 0
    tags: List[str] = []

class AdvancedStats(BaseModel):
    total_urls: int
    total_clicks: int
    recent_urls: int
    avg_clicks_per_url: float
    most_clicked_url: Optional[URLResponse] = None
    most_used_tags: List[dict] = []
    clicks_by_date: List[dict] = []

class URLFilter(BaseModel):
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    min_clicks: Optional[int] = None
    max_clicks: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sort_by: Optional[str] = Field("created_at", pattern="^(created_at|click_count|short_code)$")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"

class ExportRequest(BaseModel):
    format: ExportFormat
    filters: Optional[URLFilter] = None
    include_stats: bool = True

class ClickAnalytics(BaseModel):
    url_id: int
    short_code: str
    total_clicks: int
    clicks_by_hour: List[dict] = []
    clicks_by_day: List[dict] = []


class SearchResult(BaseModel):
    urls: List[URLResponse]
    total_found: int
    search_query: str
    filters_applied: dict
