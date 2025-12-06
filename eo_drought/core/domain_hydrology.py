from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class SoilProfile:
    """
    Root-zone soil water parameters for a field.

    All depths are integrated over the current rooting depth.
    Units: mm of water.
    """
    taw_mm: float        # Total Available Water  = (theta_fc - theta_wp) * root_depth
    raw_mm: float        # Readily Available Water = p * TAW
    field_capacity_mm: float
    wilting_point_mm: float


@dataclass
class RootZoneState:
    """
    Daily state of the root-zone water bucket.
    """
    date: date
    depletion_mm: float        # Dr (0 = field capacity, TAW = wilting)
    theta_mm: float            # Absolute water content in root-zone [mm]
    et0_mm: float              # Reference ET0 for the day [mm]
    kc: float                  # Crop coefficient used to scale ET0
    etc_mm: float              # Actual crop evapotranspiration [mm]
    rainfall_mm: float         # Rainfall [mm]
    irrigation_mm: float       # Irrigation applied [mm]
    runoff_mm: float           # Runoff [mm]
    deep_perc_mm: float        # Deep percolation [mm]
    ks: float                  # Water stress coefficient (0–1)


@dataclass
class WaterBalanceResult:
    """
    Full water balance over a time window.
    """
    soil: SoilProfile
    states: List[RootZoneState]


@dataclass
class IrrigationRecommendation:
    """
    Numeric + semantic irrigation recommendation for a single field.
    """
    recommended_depth_mm: float
    urgency_0_100: int
    days_until_critical: int
    comment: str
