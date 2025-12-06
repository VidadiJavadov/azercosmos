from eo_drought.core.domain_metrics import Indicators, RiskComponents


def compute_risk_components(ind: Indicators) -> RiskComponents:
    """
    Derive three component scores (0–100) from indicators:
    - dryness
    - rainfall
    - vigor
    """
    # Dryness: NDMI anomaly + moisture index
    dry_score = 50.0
    if ind.ndmi_anomaly < -0.20:
        dry_score += 30
    elif ind.ndmi_anomaly < -0.10:
        dry_score += 20
    elif ind.ndmi_anomaly > 0.05:
        dry_score -= 15

    if ind.moisture_index_0_100 < 30:
        dry_score += 25
    elif ind.moisture_index_0_100 < 50:
        dry_score += 10
    elif ind.moisture_index_0_100 > 70:
        dry_score -= 10

    dry_score = max(0, min(100, dry_score))

    # Rainfall: deficit vs expected
    rain_score = 50.0
    if ind.rainfall_deficit_mm > 0:
        if ind.rainfall_deficit_mm > 30:
            rain_score += 30
        elif ind.rainfall_deficit_mm > 15:
            rain_score += 20
        else:
            rain_score += 10
    elif ind.rainfall_deficit_mm < 0:
        rain_score -= 10
    rain_score = max(0, min(100, rain_score))

    # Vigor: NDVI anomaly vs expected
    vig_score = 50.0
    if ind.ndvi_anomaly_pct < -40:
        vig_score += 30
    elif ind.ndvi_anomaly_pct < -15:
        vig_score += 20
    elif ind.ndvi_anomaly_pct > 10:
        vig_score -= 15
    vig_score = max(0, min(100, vig_score))

    return RiskComponents(
        dryness=dry_score,
        rainfall=rain_score,
        vigor=vig_score,
    )
