from typing import List

from eo_drought.core.domain_metrics import (
    Indicators,
    RiskComponents,
    RiskResult,
)
from eo_drought.analytics.risk.risk_confidence import compute_confidence


def compute_overall_risk(
    indicators: Indicators,
    components: RiskComponents,
    *,
    n_s2_items: int,
    avg_cloud_cover: float,
    rainfall_ok: bool,
) -> RiskResult:
    """
    Combine components + data quality into final risk & reasons.
    """

    confidence = compute_confidence(
        n_s2_items=n_s2_items,
        avg_cloud_cover=avg_cloud_cover,
        rainfall_ok=rainfall_ok,
    )

    # Weighted combination
    overall = (
        0.4 * components.dryness +
        0.35 * components.rainfall +
        0.25 * components.vigor
    )
    overall = max(0.0, min(100.0, overall))
    score_int = int(round(overall))

    if score_int >= 75:
        level = "HIGH"
    elif score_int >= 45:
        level = "MEDIUM"
    else:
        level = "LOW"

    reasons: List[str] = []

    if indicators.ndmi_anomaly < -0.20:
        reasons.append(
            f"NDMI anomaly is strongly below expected ({indicators.ndmi_anomaly:.2f})."
        )
    elif indicators.ndmi_anomaly < -0.10:
        reasons.append(
            f"NDMI anomaly is moderately below expected ({indicators.ndmi_anomaly:.2f})."
        )

    if indicators.rainfall_deficit_mm > 0:
        reasons.append(
            f"Rainfall deficit is {indicators.rainfall_deficit_mm:.1f} mm vs typical."
        )

    if indicators.ndvi_anomaly_pct < -40:
        reasons.append(
            f"NDVI is much lower than expected ({indicators.ndvi_anomaly_pct:.1f}% below)."
        )
    elif indicators.ndvi_anomaly_pct < -15:
        reasons.append(
            f"NDVI is somewhat lower than expected ({indicators.ndvi_anomaly_pct:.1f}% below)."
        )

    if indicators.moisture_index_0_100 < 30:
        reasons.append(
            f"Moisture index is low ({indicators.moisture_index_0_100:.0f}/100)."
        )

    if not reasons:
        reasons.append("Indicators show no strong drought/water-stress signal.")

    return RiskResult(
        level=level,
        score=score_int,
        confidence=confidence,
        components=components,
        reasons=reasons,
    )
