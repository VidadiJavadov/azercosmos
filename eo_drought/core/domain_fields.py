from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class Field:
    id: str
    name: str
    crop: str
    lat: float
    lon: float
    aoi_size_m: int = 500  # square AOI side length in meters


@dataclass
class FieldAnalysisWindow:
    days_back: int
    end_date: Optional[date] = None

    @property
    def start_date(self) -> date:
        end = self.end_date or date.today()
        return end - timedelta(days=self.days_back)
