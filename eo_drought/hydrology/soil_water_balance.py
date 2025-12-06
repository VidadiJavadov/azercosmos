from datetime import date
from typing import Iterable, List, Optional

from eo_drought.core.domain_hydrology import (
    SoilProfile,
    RootZoneState,
    WaterBalanceResult,
)


def _compute_ks(depletion_mm: float, soil: SoilProfile) -> float:
    """
    FAO-56 style water stress coefficient Ks.

      Dr < RAW  → Ks = 1 (no stress)
      Dr > TAW  → Ks = 0 (full stress)
      RAW <= Dr <= TAW → linear ramp between 1 and 0.
    """
    if depletion_mm <= soil.raw_mm:
        return 1.0
    if depletion_mm >= soil.taw_mm:
        return 0.0
    # linear in between
    return max(
        0.0,
        min(
            1.0,
            (soil.taw_mm - depletion_mm) / (soil.taw_mm - soil.raw_mm),
        ),
    )


def run_root_zone_water_balance(
    dates: Iterable[date],
    rainfall_mm: Iterable[float],
    et0_mm: Iterable[float],
    soil: SoilProfile,
    kc: float,
    initial_depletion_mm: Optional[float] = None,
) -> WaterBalanceResult:
    """
    Simple daily root-zone water balance using a single bucket.

    Assumptions:
      - No capillary rise from groundwater.
      - Runoff is negligible for moderate rain (can be extended later).
      - Deep percolation occurs only when the bucket refills beyond FC
        (we treat it as overflow that does not affect Dr directly).

    Implemented in depletion space:

        Dr(i) = Dr(i-1) - (P + I - Roff - DP) + ETc

    Here:
      - we set I = 0 (irrigation scheduled separately),
      - Roff ≈ 0,
      - DP only when storage > field capacity.
    """
    date_list: List[date] = list(dates)
    rain_list: List[float] = list(rainfall_mm)
    et0_list: List[float] = list(et0_mm)

    if not (len(date_list) == len(rain_list) == len(et0_list)):
        raise ValueError("dates, rainfall_mm, et0_mm must have the same length")

    if initial_depletion_mm is None:
        # start at field capacity (no depletion)
        depletion = 0.0
    else:
        depletion = max(0.0, min(soil.taw_mm, float(initial_depletion_mm)))

    states: List[RootZoneState] = []
    theta = soil.field_capacity_mm - depletion  # absolute water in root-zone [mm]

    for d, p_mm, et0 in zip(date_list, rain_list, et0_list):
        # 1) Ks and ETc
        ks = _compute_ks(depletion, soil)
        etc_potential = kc * et0
        etc_actual = ks * etc_potential

        # 2) Add rainfall
        infiltration = max(0.0, p_mm)
        theta += infiltration

        # 3) Deep percolation if above field capacity
        deep_perc = 0.0
        if theta > soil.field_capacity_mm:
            deep_perc = theta - soil.field_capacity_mm
            theta = soil.field_capacity_mm

        # 4) Remove ETc, but not below wilting point
        max_extractable = max(0.0, theta - soil.wilting_point_mm)
        etc_actual = min(etc_actual, max_extractable)
        theta -= etc_actual

        # 5) Update depletion
        depletion = soil.field_capacity_mm - theta
        depletion = max(0.0, min(soil.taw_mm, depletion))

        state = RootZoneState(
            date=d,
            depletion_mm=depletion,
            theta_mm=theta,
            et0_mm=et0,
            kc=kc,
            etc_mm=etc_actual,
            rainfall_mm=p_mm,
            irrigation_mm=0.0,  # no automatic irrigation in this engine
            runoff_mm=0.0,
            deep_perc_mm=deep_perc,
            ks=ks,
        )
        states.append(state)

    return WaterBalanceResult(soil=soil, states=states)
