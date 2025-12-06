from dataclasses import dataclass
from typing import Optional

@dataclass
class CropProfile:
    name: str
    default_season: str  # "winter", "summer", etc.
    rooting_depth_m: Optional[float] = None
    notes: str = ""
