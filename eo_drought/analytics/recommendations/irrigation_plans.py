from eo_drought.core.domain_fields import Field
from eo_drought.core.domain_metrics import RiskResult


def simple_irrigation_recommendation(
    field: Field,
    risk: RiskResult,
) -> str:
    """
    Rule-based irrigation recommendation based purely on the risk engine output.

    It uses:
      - risk.level:  "LOW" / "MEDIUM" / "HIGH"
      - risk.score:  0–100
      - risk.components.dryness / rainfall / vigor (0–100)
      - risk.confidence: 0–1

    The return value is a short, human-readable recommendation string, e.g.:
      - "No irrigation required now; re-check in 7–10 days."
      - "Plan a light irrigation (20–30 mm) in the next 3–5 days."
      - "Urgent irrigation (40–60 mm) within the next 48 hours is advised."
    """

    level = (risk.level or "").upper()

    # Extract components if present; fall back to neutral values if not.
    try:
        dryness = float(risk.components.dryness)
        rainfall = float(risk.components.rainfall)
        vigor = float(risk.components.vigor)
    except Exception:
        dryness = rainfall = vigor = 50.0

    score = int(risk.score)
    conf = float(risk.confidence)

    # --- Confidence modifier -------------------------------------------------
    # If the engine is uncertain, we keep the language softer.
    high_conf = conf >= 0.75
    medium_conf = 0.5 <= conf < 0.75
    low_conf = conf < 0.5

    # --- Base qualitative band ----------------------------------------------
    # We define three main bands and then nuance using components.
    if level == "HIGH":
        # Very dry or very high score → heavy & urgent.
        if dryness >= 80 or score >= 85:
            base = (
                f"For field '{field.name}', the drought risk is HIGH and root-zone "
                "conditions likely very dry. Urgent irrigation (around 40–60 mm) "
                "within the next 24–48 hours is advised, if water is available."
            )
        else:
            base = (
                f"For field '{field.name}', drought risk is HIGH. An irrigation "
                "event (around 30–50 mm) in the next 2–3 days is recommended "
                "to prevent further stress."
            )

    elif level == "MEDIUM":
        # Medium risk: timing and depth depend on dryness & rainfall signals.
        if dryness >= 70 or rainfall >= 70:
            base = (
                f"For field '{field.name}', drought risk is MEDIUM with notable "
                "dryness signal. Plan a moderate irrigation (20–35 mm) within "
                "the next 3–5 days, prioritising this field if water is limited."
            )
        elif vigor >= 70:
            base = (
                f"For field '{field.name}', drought risk is MEDIUM but crop vigor "
                "is still acceptable. A light irrigation (15–25 mm) within the "
                "next 5–7 days can help stabilise the field."
            )
        else:
            base = (
                f"For field '{field.name}', drought risk is MEDIUM. No emergency "
                "action is required, but planning a light irrigation in the next "
                "week is prudent if conditions stay dry."
            )

    else:  # LOW or anything else
        if dryness >= 60 or rainfall >= 60:
            base = (
                f"For field '{field.name}', overall risk is LOW but there are "
                "early signs of dryness. No immediate irrigation is required; "
                "consider a light irrigation (10–20 mm) in the next 7–10 days "
                "if rainfall remains below normal."
            )
        else:
            base = (
                f"For field '{field.name}', drought risk is LOW and current "
                "conditions do not justify irrigation. Maintain normal "
                "monitoring and re-check within 7–10 days."
            )

    # --- Confidence language overlay ----------------------------------------
    if high_conf:
        suffix = " Confidence in this recommendation is high based on current data."
    elif medium_conf:
        suffix = (
            " Confidence in this recommendation is moderate; if critical decisions "
            "depend on this field, consider cross-checking with local observations."
        )
    else:
        suffix = (
            " Confidence in this recommendation is limited due to data quality "
            "or coverage; combine this guidance with local field inspections."
        )

    return base + suffix
