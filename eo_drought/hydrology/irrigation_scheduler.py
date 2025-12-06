from dataclasses import dataclass
from typing import Optional

from eo_drought.core.domain_hydrology import WaterBalanceResult, IrrigationRecommendation


@dataclass
class IrrigationConstraints:
    """
    Simple constraints for scheduling.
    """
    max_depth_per_event_mm: float = 60.0     # do not recommend > 60 mm in one go
    target_depletion_fraction: float = 0.5   # aim to refill to 50% of TAW
    critical_depletion_fraction: float = 0.8 # above this → 'critical' stress


def make_irrigation_recommendation(
    wb: WaterBalanceResult,
    constraints: Optional[IrrigationConstraints] = None,
) -> IrrigationRecommendation:
    """
    Derive a single-field irrigation recommendation from a WaterBalanceResult.

    Strategy:
      - Look at the *last day* state (today).
      - If Dr < RAW → no irrigation; low urgency.
      - If RAW <= Dr < critical_depletion → recommend irrigation with moderate urgency.
      - If Dr >= critical_depletion → high urgency + larger depth.

    Depth is chosen so that, if applied today, depletion would drop to
    target_depletion_fraction * TAW.
    """
    if constraints is None:
        constraints = IrrigationConstraints()

    soil = wb.soil
    if not wb.states:
        return IrrigationRecommendation(
            recommended_depth_mm=0.0,
            urgency_0_100=0,
            days_until_critical=0,
            comment="No hydrology state available for this field.",
        )

    latest = wb.states[-1]
    Dr = latest.depletion_mm

    taw = soil.taw_mm
    raw = soil.raw_mm
    critical = constraints.critical_depletion_fraction * taw
    target = constraints.target_depletion_fraction * taw

    if Dr <= raw:
        # Fully safe, no irrigation needed now.
        return IrrigationRecommendation(
            recommended_depth_mm=0.0,
            urgency_0_100=10,
            days_until_critical=3,
            comment="Root-zone water depletion is below RAW; irrigation not required immediately.",
        )

    # Compute how much water would be needed to move from Dr → target depletion.
    desired_drop = max(0.0, Dr - target)
    depth_needed = min(desired_drop, constraints.max_depth_per_event_mm)

    if Dr >= critical:
        urgency = 90
        days_until_critical = 0
        comment = (
            "Root-zone depletion is above the critical threshold; "
            "strong irrigation is recommended as soon as possible."
        )
    else:
        urgency = 60
        days_until_critical = 1
        comment = (
            "Root-zone depletion is between RAW and critical; "
            "an irrigation within the next few days is advised."
        )

    return IrrigationRecommendation(
        recommended_depth_mm=depth_needed,
        urgency_0_100=urgency,
        days_until_critical=days_until_critical,
        comment=comment,
    )
