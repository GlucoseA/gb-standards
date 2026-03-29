from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ScraperStatus(BaseModel):
    is_running: bool
    last_run: Optional[datetime] = None
    total_standards: int
    message: str
