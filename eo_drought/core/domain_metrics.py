from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class SatelliteMetrics:
    """
    Summary of multi-date Sentinel-2 data over the AOI and time window.
    """
    item_ids: List[str]
    ndvi_values: List[float]
    ndmi_values: List[float]
    median_ndvi: float
    median_ndmi: float
    mean_cloud_cover: float
    num_items: int


@dataclass
class RainfallSummary:
    total_mm: float
    daily_values: List[float]
    dates: List[date]
    ok: bool


@dataclass
class Indicators:
    ndvi_mean: float
    ndmi_mean: float
    ndvi_anomaly_pct: float        # vs expected NDVI for crop+season
    ndmi_anomaly: float            # vs expected NDMI
    rainfall_deficit_mm: float     # expected - actual
    moisture_index_0_100: float    # 0 = very dry, 100 = very wet


@dataclass
class RiskComponents:
    dryness: float   # 0–100
    rainfall: float  # 0–100
    vigor: float     # 0–100


@dataclass
class RiskResult:
    level: str               # "LOW" / "MEDIUM" / "HIGH"
    score: int               # 0–100
    confidence: float        # 0–1
    components: RiskComponents
    reasons: List[str]
