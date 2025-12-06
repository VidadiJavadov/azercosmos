from dataclasses import dataclass
from typing import Tuple

from eo_drought.core.domain_hydrology import SoilProfile


@dataclass
class CropSoilDefaults:
    """
    Default hydrology parameters for a crop type on a 'typical' medium-texture soil.

    This is deliberately simple and explicit. You can replace or refine per region.
    """
    root_depth_m: float            # Effective rooting depth [m]
    taw_mm_per_m: float            # TAW per meter of root depth [mm/m]
    p_readily_available: float     # Fraction of TAW that is 'readily' available


# Minimal table of defaults; extend as needed.
_CROP_DEFAULTS = {
    "wheat": CropSoilDefaults(
        root_depth_m=1.0,          # typical maximum rooting depth
        taw_mm_per_m=120.0,        # medium texture soil ~120 mm/m
        p_readily_available=0.45,  # FAO56 typical p for small grains
    ),
    "maize": CropSoilDefaults(
        root_depth_m=1.2,
        taw_mm_per_m=140.0,
        p_readily_available=0.55,
    ),
    "cotton": CropSoilDefaults(
        root_depth_m=1.2,
        taw_mm_per_m=130.0,
        p_readily_available=0.55,
    ),
}


def get_soil_profile_for_crop(crop: str) -> SoilProfile:
    """
    Return a SoilProfile for the given crop using very simple global defaults.

    This assumes:
      - uniform root-zone,
      - medium texture soil,
      - no explicit soil map.
    """
    key = crop.strip().lower()
    if key not in _CROP_DEFAULTS:
        # fall back to a generic medium-texture profile
        defaults = CropSoilDefaults(
            root_depth_m=1.0,
            taw_mm_per_m=120.0,
            p_readily_available=0.5,
        )
    else:
        defaults = _CROP_DEFAULTS[key]

    taw_mm = defaults.taw_mm_per_m * defaults.root_depth_m
    raw_mm = defaults.p_readily_available * taw_mm

    # We do not expose FC/WP directly since we only use TAW & RAW in the bucket.
    # For completeness, we assume an arbitrary split:
    #   FC water = TAW + WP; WP ~ 0.5 * TAW
    wilting_point_mm = 0.5 * taw_mm
    field_capacity_mm = wilting_point_mm + taw_mm

    return SoilProfile(
        taw_mm=taw_mm,
        raw_mm=raw_mm,
        field_capacity_mm=field_capacity_mm,
        wilting_point_mm=wilting_point_mm,
    )


def simple_kc_for_crop(crop: str) -> float:
    """
    Coarse, mid-season Kc for use when we don't know growth stage.
    These are broadly consistent with FAO-56 small cereals etc.
    """
    key = crop.strip().lower()
    if key == "wheat":
        return 1.15
    if key == "maize":
        return 1.20
    if key == "cotton":
        return 1.20
    # fallback generic
    return 1.05
