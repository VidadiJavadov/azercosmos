from eo_drought.core.domain_metrics import (
    SatelliteMetrics,
    RainfallSummary,
    Indicators,
)
from eo_drought.analytics.baselines.crop_ndvi_baselines import BaselineContext


def compute_vegetation_indicators(
    s2_summary: SatelliteMetrics,
    rainfall: RainfallSummary,
    baseline: BaselineContext,
) -> Indicators:
    """
    Turn raw EO + rainfall + baseline into normalized indicators.

    - s2_summary: Sentinel-2 NDVI / NDMI summary over AOI & window
    - rainfall:  RainfallSummary from Open-Meteo
    - baseline:  Expected NDVI / NDMI / rainfall for crop + season + window
    """

    ndvi_mean = s2_summary.median_ndvi
    ndmi_mean = s2_summary.median_ndmi

    # NDVI anomaly in percent vs expected
    if baseline.expected_ndvi > 0:
        ndvi_anom_pct = (
            (ndvi_mean - baseline.expected_ndvi)
            / baseline.expected_ndvi
            * 100.0
        )
    else:
        ndvi_anom_pct = 0.0

    # NDMI anomaly (absolute difference)
    ndmi_anom = ndmi_mean - baseline.expected_ndmi

    # Rainfall deficit (expected - actual)
    rainfall_deficit = baseline.expected_rain_mm - rainfall.total_mm

    # Moisture index from NDMI:
    # Map NDMI from [-0.2, 0.4] → [0, 100]
    ndmi_clamped = max(-0.2, min(0.4, ndmi_mean))
    moisture_index = (ndmi_clamped + 0.2) / 0.6 * 100.0

    return Indicators(
        ndvi_mean=ndvi_mean,
        ndmi_mean=ndmi_mean,
        ndvi_anomaly_pct=ndvi_anom_pct,
        ndmi_anomaly=ndmi_anom,
        rainfall_deficit_mm=rainfall_deficit,
        moisture_index_0_100=moisture_index,
    )
