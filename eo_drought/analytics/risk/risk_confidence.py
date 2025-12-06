from eo_drought.core.domain_metrics import RainfallSummary


def compute_confidence(
    *,
    n_s2_items: int,
    avg_cloud_cover: float,
    rainfall_ok: bool,
    aoi_from_point_box: bool = True,
) -> float:
    """
    Compute an overall confidence (0–1) in the risk assessment.
    Logic adapted from the MVP, simplified to pure numeric inputs.
    """
    conf = 1.0

    # Number of Sentinel-2 images
    if n_s2_items == 1:
        conf -= 0.20
    elif n_s2_items == 2:
        conf -= 0.10
    elif n_s2_items >= 3:
        conf += 0.0

    # Cloud cover
    if avg_cloud_cover > 60:
        conf -= 0.25
    elif avg_cloud_cover > 30:
        conf -= 0.10

    # AOI geometry: we currently use point_box around lat/lon
    if aoi_from_point_box:
        conf -= 0.10

    # Rainfall availability
    if not rainfall_ok:
        conf -= 0.30

    conf = max(0.0, min(1.0, conf))
    return conf
