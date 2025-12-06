from typing import List

from eo_drought.core.domain_fields import Field
from eo_drought.analytics.baselines.crop_ndvi_baselines import BaselineContext
from eo_drought.core.domain_metrics import (
    SatelliteMetrics,
    RainfallSummary,
    Indicators,
    RiskResult,
)


def format_confidence(conf: float) -> str:
    if conf >= 0.8:
        label = "high"
    elif conf >= 0.5:
        label = "medium"
    else:
        label = "low"
    return f"{label} ({conf:.2f})"


def generate_report(
    field: Field,
    baseline: BaselineContext,
    s2: SatelliteMetrics,
    rain: RainfallSummary,
    ind: Indicators,
    risk: RiskResult,
    period_label: str,
    report_mode: str = "farmer",  # "farmer" or "expert"
) -> str:
    lines: List[str] = []

    header = f"FIELD BRIEF – {field.name} ({field.crop}) – {period_label}"
    lines.append(header)
    lines.append("")

    # Status
    lines.append("Status:")
    lines.append(f"- Mean NDVI over AOI: {ind.ndvi_mean:.3f}.")
    lines.append(f"- Mean NDMI over AOI: {ind.ndmi_mean:.3f}.")
    lines.append(
        f"- NDVI anomaly vs expected for crop & season: {ind.ndvi_anomaly_pct:.1f} %."
    )  # negative = lower
    lines.append(f"- NDMI anomaly vs expected: {ind.ndmi_anomaly:.2f}.")
    lines.append(
        f"- Rainfall deficit vs expected for this window: {ind.rainfall_deficit_mm:.1f} mm."
    )
    lines.append(
        f"- Moisture index: {ind.moisture_index_0_100:.0f} / 100 "
        "(0 = very dry, 100 = very wet)."
    )
    lines.append("")

    # Risk
    lines.append("Risk Assessment:")
    lines.append(
        f"- Drought / water-stress risk: {risk.level} "
        f"({risk.score}/100, confidence {format_confidence(risk.confidence)})."
    )
    lines.append(
        f"  • Components (0–100): dryness={risk.components.dryness:.0f}, "
        f"rainfall={risk.components.rainfall:.0f}, "
        f"vigor={risk.components.vigor:.0f}."
    )
    for r in risk.reasons:
        lines.append(f"  • {r}")
    lines.append("")

    # Recommendations
    lines.append("Recommendations:")
    if risk.level == "HIGH":
        lines.append(
            "- Prioritise irrigation for this field in the next 3–5 days, if water is available."
        )
        lines.append(
            "- Monitor shallow soils, elevated areas, and known weak spots for severe stress."
        )
    elif risk.level == "MEDIUM":
        lines.append("- Monitor this field closely over the next week.")
        lines.append("- Plan irrigation if dry conditions persist and resources allow.")
    else:
        lines.append("- No immediate drought priority detected for this field.")
        lines.append("- Maintain routine monitoring and normal irrigation schedule.")
    lines.append("")

    # Additional expert details
    if report_mode.lower() == "expert":
        lines.append("Baseline & Context:")
        lines.append(
            f"- Crop: {baseline.crop}, Season phase: {baseline.season_phase}."
        )
        lines.append(
            f"- Expected NDVI: {baseline.expected_ndvi:.2f}, "
            f"expected NDMI: {baseline.expected_ndmi:.2f}."
        )
        lines.append(
            f"- Expected rainfall for window: {baseline.expected_rain_mm:.1f} mm."
        )
        lines.append(
            f"- Sentinel-2 items used: {s2.num_items} "
            f"(mean cloud cover: {s2.mean_cloud_cover:.1f}%)."
        )
        lines.append(f"- S2 item IDs: {', '.join(s2.item_ids)}.")
        lines.append(
            f"- Rainfall data OK: {rain.ok}, total rainfall: {rain.total_mm:.1f} mm."
        )
        lines.append("")

    # Data notes (always)
    lines.append("Data Notes:")
    lines.append("- Optical EO: Sentinel-2 L2A via Earth Search STAC.")
    lines.append("- Rainfall: Open-Meteo archive (daily precipitation_sum).")
    lines.append(
        "- Baselines: crop- and season-aware heuristics (hackathon MVP; tunable in future)."
    )

    return "\n".join(lines)
