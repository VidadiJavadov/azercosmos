from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass
class BaselineContext:
    crop: str
    season_phase: str
    expected_ndvi: float
    expected_ndmi: float
    expected_rain_mm: float  # expected rainfall over analysis window


def classify_season_phase(crop: str, d: date, lat: float) -> str:
    """
    Very simple seasonal phase classifier by day-of-year and crop.
    Assumes Northern Hemisphere temperate regime (good enough for MVP).
    """
    doy = d.timetuple().tm_yday
    crop_l = crop.lower()

    # Wheat
    if crop_l == "wheat":
        if 305 <= doy or doy <= 31:      # Nov–Jan: sowing / early
            return "sowing_early_growth"
        elif 32 <= doy <= 120:          # Feb–Apr: tillering / stem
            return "tillering_stem_elongation"
        elif 121 <= doy <= 180:         # May–Jun: heading / flowering
            return "heading_flowering"
        elif 181 <= doy <= 240:         # Jul–Aug: grain fill / maturity
            return "grain_fill_maturity"
        else:                           # Sep–Oct: post-harvest
            return "post_harvest"

    # Maize
    if crop_l == "maize":
        if 90 <= doy <= 140:
            return "emergence_early_veg"
        elif 141 <= doy <= 210:
            return "veg_reproductive"
        elif 211 <= doy <= 260:
            return "grain_fill_maturity"
        else:
            return "off_season"

    # Sunflower
    if crop_l == "sunflower":
        if 100 <= doy <= 150:
            return "emergence_vegetative"
        elif 151 <= doy <= 210:
            return "flowering"
        elif 211 <= doy <= 260:
            return "seed_fill_maturity"
        else:
            return "off_season"

    # Default
    return "generic_season"


def _baseline_for(crop: str, phase: str, days_back: int) -> BaselineContext:
    """
    Define expected NDVI, NDMI, rainfall per crop + phase.
    These are simple explicit tables – hackathon-grade but explainable.
    """
    crop_l = crop.lower()

    # Default values
    expected_ndvi = 0.4
    expected_ndmi = 0.25
    # Rough expectation: 3–4 mm/day
    expected_rain_mm = 3.5 * days_back

    if crop_l == "wheat":
        if phase == "sowing_early_growth":
            expected_ndvi = 0.25
            expected_ndmi = 0.20
        elif phase == "tillering_stem_elongation":
            expected_ndvi = 0.45
            expected_ndmi = 0.28
        elif phase == "heading_flowering":
            expected_ndvi = 0.60
            expected_ndmi = 0.30
        elif phase == "grain_fill_maturity":
            expected_ndvi = 0.50
            expected_ndmi = 0.27
        elif phase == "post_harvest":
            expected_ndvi = 0.15
            expected_ndmi = 0.18

    elif crop_l == "maize":
        if phase == "emergence_early_veg":
            expected_ndvi = 0.30
            expected_ndmi = 0.22
        elif phase == "veg_reproductive":
            expected_ndvi = 0.65
            expected_ndmi = 0.32
        elif phase == "grain_fill_maturity":
            expected_ndvi = 0.55
            expected_ndmi = 0.28
        elif phase == "off_season":
            expected_ndvi = 0.10
            expected_ndmi = 0.18

    elif crop_l == "sunflower":
        if phase == "emergence_vegetative":
            expected_ndvi = 0.35
            expected_ndmi = 0.24
        elif phase == "flowering":
            expected_ndvi = 0.65
            expected_ndmi = 0.33
        elif phase == "seed_fill_maturity":
            expected_ndvi = 0.55
            expected_ndmi = 0.29
        elif phase == "off_season":
            expected_ndvi = 0.12
            expected_ndmi = 0.18

    return BaselineContext(
        crop=crop,
        season_phase=phase,
        expected_ndvi=expected_ndvi,
        expected_ndmi=expected_ndmi,
        expected_rain_mm=expected_rain_mm,
    )


def expected_baselines(
    crop: str,
    lat: float,
    today: date,
    days_back: int,
) -> BaselineContext:
    """
    Convenience wrapper used by the pipeline: crop + location + analysis window.
    """
    phase = classify_season_phase(crop, today, lat)
    return _baseline_for(crop, phase, days_back)
