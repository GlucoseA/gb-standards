from pydantic import BaseModel
from datetime import date as DateType, datetime
from typing import Optional


class StandardBase(BaseModel):
    standard_number: str
    cn_name: str
    status: str
    standard_type: str


class StandardBrief(StandardBase):
    id: int
    publish_date: Optional[DateType] = None
    implement_date: Optional[DateType] = None

    model_config = {"from_attributes": True}


class StandardDetail(StandardBase):
    id: int
    hcno: str
    en_name: str
    ics_code: str
    ccs_code: str
    publish_date: Optional[DateType] = None
    implement_date: Optional[DateType] = None
    abolish_date: Optional[DateType] = None
    replaced_by: str
    category: str
    scraped_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StandardBrief]


class CalendarItem(BaseModel):
    id: int
    standard_number: str
    cn_name: str
    status: str
    standard_type: str = ""
    publish_date: Optional[DateType] = None
    implement_date: Optional[DateType] = None
    date: Optional[DateType] = None
    event_type: str  # "implement" 或 "abolish"

    model_config = {"from_attributes": True}


class ScraperStatus(BaseModel):
    is_running: bool
    last_run: Optional[datetime] = None
    total_standards: int
    message: str
