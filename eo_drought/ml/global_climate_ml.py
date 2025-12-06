from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Tuple

import numpy as np
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error


# ===============================================================
# Domain objects
# ===============================================================

@dataclass
class FieldConfig:
    name: str
    crop: str
    latitude: float
    longitude: float
    start_date: date
    end_date: date


@dataclass
class DailyRecord:
    date: date
    precip_mm: float          # merged precip (Open-Meteo + NASA POWER)
    precip_om_mm: float       # Open-Meteo precip
    precip_np_mm: float       # NASA POWER precip
    et0_mm: float             # FAO ET0 from Open-Meteo
    dryness_daily: float      # 0–1 dryness per day
    demand_daily: float       # 0–1 evaporative demand per day


@dataclass
class AggregatedFeatures:
    # Climate features (always finite)
    mean_precip_mm: float
    total_precip_mm: float
    mean_et0_mm: float
    precip_variation_ratio: float
    et0_variation_ratio: float
    dryness_index: float
    rainfall_deficit_index: float
    vigor_proxy_index: float
    drought_risk_score: float         # 0–100
    irrigation_priority_score: float  # 0–100

    # Sentinel-2 vegetation features (EO-aware layer)
    mean_ndvi: float = 0.0
    median_ndvi: float = 0.0
    latest_ndvi: float = 0.0
    ndvi_trend: float = 0.0           # slope over acquisitions
    mean_ndmi: float = 0.0
    median_ndmi: float = 0.0
    latest_ndmi: float = 0.0
    ndmi_trend: float = 0.0           # slope over acquisitions


@dataclass
class FieldReport:
    field: FieldConfig
    daily: List[DailyRecord]
    features: AggregatedFeatures


# ===============================================================
# Data connectors – real global datasets
# ===============================================================

def fetch_openmeteo_archive(
    lat: float,
    lon: float,
    start: date,
    end: date,
    timezone: str = "UTC",
) -> Dict[str, Any]:
    """
    Open-Meteo ERA5-Land historical archive.
    Uses daily precipitation_sum + et0_fao_evapotranspiration.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum,et0_fao_evapotranspiration",
        "timezone": timezone,
    }
    r = requests.get(base_url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_nasapower_precip(
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> Dict[date, float]:
    """
    NASA POWER Daily API (Agroclimatology community).
    PRECTOT (daily precipitation, mm/day).
    """
    base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "latitude": lat,
        "longitude": lon,
        "community": "AG",
        "parameters": "PRECTOT",
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    r = requests.get(base_url, params=params, timeout=60)
    r.raise_for_status()
    j = r.json()

    out: Dict[date, float] = {}
    try:
        params_block = j["properties"]["parameter"]["PRECTOT"]
    except KeyError:
        return out

    for datestr, val in params_block.items():
        d = datetime.strptime(datestr, "%Y%m%d").date()
        try:
            v = float(val)
        except (TypeError, ValueError):
            v = float("nan")
        out[d] = v
    return out


# ===============================================================
# Helpers – safe arrays and normalization
# ===============================================================

def _safe_array(values: List[float]) -> np.ndarray:
    """
    Convert to float array and replace any NaNs/inf with neutral 0.0.
    Guarantees finite arrays.
    """
    arr = np.array(values, dtype=float)
    arr[~np.isfinite(arr)] = 0.0
    return arr


def _norm_0_1(arr: np.ndarray) -> np.ndarray:
    """
    Normalize to [0,1]. If constant or empty -> 0.5 (neutral).
    """
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.full_like(arr, 0.5)
    mn, mx = float(finite.min()), float(finite.max())
    if mx - mn < 1e-9:
        return np.full_like(arr, 0.5)
    return (arr - mn) / (mx - mn)


def _truncate_0_1(x: float) -> float:
    if math.isnan(x):
        return 0.5
    return max(0.0, min(1.0, float(x)))


# ===============================================================
# Merge datasets into daily records
# ===============================================================

def build_daily_records(field: FieldConfig) -> List[DailyRecord]:
    # Open-Meteo
    om = fetch_openmeteo_archive(
        field.latitude,
        field.longitude,
        field.start_date,
        field.end_date,
        timezone="UTC",
    )
    daily_block = om.get("daily", {})
    daily_dates_iso = daily_block.get("time", [])
    daily_precip = daily_block.get("precipitation_sum", [])
    daily_et0 = daily_block.get("et0_fao_evapotranspiration", [])

    # NASA POWER
    np_precip_map = fetch_nasapower_precip(
        field.latitude,
        field.longitude,
        field.start_date,
        field.end_date,
    )

    records: List[DailyRecord] = []

    for iso, p_om, et0 in zip(daily_dates_iso, daily_precip, daily_et0):
        d = datetime.fromisoformat(iso).date()

        try:
            precip_om = float(p_om)
        except (TypeError, ValueError):
            precip_om = float("nan")

        try:
            et0_val = float(et0)
        except (TypeError, ValueError):
            et0_val = float("nan")

        precip_np = np_precip_map.get(d, float("nan"))

        # merge precip: average if both present, else whichever exists, else 0
        if math.isfinite(precip_om) and math.isfinite(precip_np):
            precip_mm = 0.5 * (precip_om + precip_np)
        elif math.isfinite(precip_om):
            precip_mm = precip_om
        elif math.isfinite(precip_np):
            precip_mm = precip_np
        else:
            precip_mm = 0.0

        if not math.isfinite(et0_val):
            et0_val = 0.0

        records.append(
            DailyRecord(
                date=d,
                precip_mm=float(precip_mm),
                precip_om_mm=float(precip_om if math.isfinite(precip_om) else 0.0),
                precip_np_mm=float(precip_np if math.isfinite(precip_np) else 0.0),
                et0_mm=float(et0_val),
                dryness_daily=0.0,
                demand_daily=0.0,
            )
        )

    return records


# ===============================================================
# Analytic indices (drought, vigor, irrigation priority)
# ===============================================================

def compute_aggregated_features(daily: List[DailyRecord]) -> AggregatedFeatures:
    if not daily:
        raise ValueError("No daily records to aggregate.")

    precip = _safe_array([d.precip_mm for d in daily])
    et0 = _safe_array([d.et0_mm for d in daily])

    mean_precip_mm = float(np.mean(precip))
    total_precip_mm = float(np.sum(precip))
    mean_et0_mm = float(np.mean(et0))

    def _variation_ratio(arr: np.ndarray) -> float:
        m = float(np.mean(arr))
        s = float(np.std(arr))
        if abs(m) < 1e-9:
            return 0.0
        return float(s / (abs(m) + 1e-6))

    precip_var = _variation_ratio(precip)
    et0_var = _variation_ratio(et0)

    precip_variation_ratio = _truncate_0_1(precip_var / 3.0)
    et0_variation_ratio = _truncate_0_1(et0_var / 3.0)

    # Daily normalized fields
    precip_norm_inv = 1.0 - _norm_0_1(precip)  # less rain -> higher dryness
    et0_norm = _norm_0_1(et0)                  # more ET0 -> higher demand

    # Dryness & demand (0–1 per day)
    dryness_daily = 0.6 * precip_norm_inv + 0.4 * et0_norm
    demand_daily = et0_norm

    dryness_daily = np.clip(dryness_daily, 0.0, 1.0)
    demand_daily = np.clip(demand_daily, 0.0, 1.0)

    # Write back into DailyRecord
    for i, rec in enumerate(daily):
        rec.dryness_daily = float(dryness_daily[i])
        rec.demand_daily = float(demand_daily[i])

    dryness_index = float(np.mean(dryness_daily))

    # Internal rainfall deficit using p75 baseline
    finite_precip = precip
    if finite_precip.size > 0:
        p75 = float(np.percentile(finite_precip, 75))
        expected_total = p75 * len(daily)
        if expected_total <= 0:
            rainfall_deficit_index = 0.5
        else:
            deficit = (expected_total - total_precip_mm) / (expected_total + 1e-6)
            rainfall_deficit_index = _truncate_0_1(deficit)
    else:
        rainfall_deficit_index = 0.5

    # Vigor proxy: balance between precip and ET0
    ratio = precip / (et0 + 1e-3)
    ratio_norm = _norm_0_1(ratio)
    vigor_from_balance = 1.0 - np.abs(ratio_norm - 0.5) * 2.0
    vigor_from_balance = np.clip(vigor_from_balance, 0.0, 1.0)
    vigor_proxy_index = float(np.mean(vigor_from_balance))

    # Final analytic drought risk & irrigation priority (0–100)
    dryness_component = dryness_index
    deficit_component = rainfall_deficit_index
    vigor_risk_component = 1.0 - vigor_proxy_index

    drought_risk = (
        0.45 * dryness_component
        + 0.35 * deficit_component
        + 0.20 * vigor_risk_component
    )
    drought_risk_score = float(_truncate_0_1(drought_risk) * 100.0)

    irrigation_priority = (
        0.6 * drought_risk
        + 0.4 * (1.0 - precip_variation_ratio)
    )
    irrigation_priority_score = float(_truncate_0_1(irrigation_priority) * 100.0)

    return AggregatedFeatures(
        mean_precip_mm=mean_precip_mm,
        total_precip_mm=total_precip_mm,
        mean_et0_mm=mean_et0_mm,
        precip_variation_ratio=precip_variation_ratio,
        et0_variation_ratio=et0_variation_ratio,
        dryness_index=_truncate_0_1(dryness_index),
        rainfall_deficit_index=rainfall_deficit_index,
        vigor_proxy_index=_truncate_0_1(vigor_proxy_index),
        drought_risk_score=drought_risk_score,
        irrigation_priority_score=irrigation_priority_score,
    )


# ===============================================================
# Sentinel-2 NDVI/NDMI augmentation
# ===============================================================

def _augment_features_with_satellite(field: FieldConfig, features: AggregatedFeatures) -> AggregatedFeatures:
    """
    Enrich AggregatedFeatures with Sentinel-2 NDVI/NDMI stats for the field AOI.

    - Uses fetch_satellite_metrics_for_aoi(aoi, start_date, end_date, max_items=20)
    - Calls build_square_aoi with positional arguments (lat, lon, size_m) so it
      matches your existing signature (no 'aoi_size_m' keyword).
    - If anything fails (no module, no data, etc.), returns features unchanged.
    """
    try:
        from eo_drought.core.geo import build_square_aoi
        from eo_drought.ingest.satellite.sentinel2 import fetch_satellite_metrics_for_aoi
    except ImportError:
        # Satellite stack not available in this environment
        return features

    try:
        # IMPORTANT FIX: use positional argument for size (no aoi_size_m=...)
        # Adjust 200.0 to whatever AOI size (in meters) you prefer for S2.
        aoi = build_square_aoi(field.latitude, field.longitude, 200.0)

        s2_items = fetch_satellite_metrics_for_aoi(
            aoi=aoi,
            start_date=field.start_date,
            end_date=field.end_date,
            max_items=20,
        )
    except Exception:
        # Any ingestion failure -> keep climate-only features, no crash
        return features

    if not s2_items:
        # No Sentinel-2 acquisitions in this window
        return features

    # -------------------------------------------------------------------------
    # Flexible extraction of NDVI / NDMI values
    # -------------------------------------------------------------------------
    ndvi_candidate_names = [
        "ndvi_mean",
        "ndvi",
        "mean_ndvi",
        "ndvi_aoi_mean",
        "ndvi_mean_aoi",
        "ndvi_mean_over_aoi",
        "ndvi_over_aoi",
    ]
    ndmi_candidate_names = [
        "ndmi_mean",
        "ndmi",
        "mean_ndmi",
        "ndmi_aoi_mean",
        "ndmi_mean_aoi",
        "ndmi_mean_over_aoi",
        "ndmi_over_aoi",
    ]

    def _extract_first_present(item: Any, names: List[str]):
        """Try multiple attribute / key names in both dict and object."""
        if isinstance(item, dict):
            for name in names:
                if name in item and item[name] is not None:
                    return item[name]
        else:
            for name in names:
                if hasattr(item, name):
                    v = getattr(item, name)
                    if v is not None:
                        return v
        return None

    def _extract_date(item: Any):
        """Try a few common date field names so that 'latest' is meaningful."""
        candidates = ["acquisition_date", "sensing_date", "date", "dt"]
        if isinstance(item, dict):
            for name in candidates:
                if name in item and item[name] is not None:
                    return item[name]
        else:
            for name in candidates:
                if hasattr(item, name):
                    return getattr(item, name)
        return None

    # Sort by date if possible (so "latest" is meaningful); silently fall back if not
    try:
        s2_items_sorted = sorted(s2_items, key=_extract_date)
    except Exception:
        s2_items_sorted = list(s2_items)

    ndvi_vals: List[float] = []
    ndmi_vals: List[float] = []

    for item in s2_items_sorted:
        ndvi = _extract_first_present(item, ndvi_candidate_names)
        ndmi = _extract_first_present(item, ndmi_candidate_names)

        if ndvi is None:
            continue

        try:
            ndvi_f = float(ndvi)
        except (TypeError, ValueError):
            continue

        if ndmi is None:
            ndmi_f = float("nan")
        else:
            try:
                ndmi_f = float(ndmi)
            except (TypeError, ValueError):
                ndmi_f = float("nan")

        ndvi_vals.append(ndvi_f)
        ndmi_vals.append(ndmi_f)

    if not ndvi_vals:
        # Could not extract NDVI → keep climate-only features
        return features

    ndvi_arr = np.array(ndvi_vals, dtype=float)
    ndmi_arr = np.array(ndmi_vals, dtype=float)
    ndvi_arr[~np.isfinite(ndvi_arr)] = 0.0
    ndmi_arr[~np.isfinite(ndmi_arr)] = 0.0

    # Basic stats
    features.mean_ndvi = float(ndvi_arr.mean())
    features.median_ndvi = float(np.median(ndvi_arr))
    features.latest_ndvi = float(ndvi_arr[-1])

    features.mean_ndmi = float(ndmi_arr.mean())
    features.median_ndmi = float(np.median(ndmi_arr))
    features.latest_ndmi = float(ndmi_arr[-1])

    # Simple linear trend (slope) over acquisitions
    if len(ndvi_arr) >= 2:
        t = np.arange(len(ndvi_arr), dtype=float)
        try:
            slope_ndvi, _ = np.polyfit(t, ndvi_arr, 1)
            slope_ndmi, _ = np.polyfit(t, ndmi_arr, 1)
        except Exception:
            slope_ndvi = 0.0
            slope_ndmi = 0.0
        features.ndvi_trend = float(slope_ndvi)
        features.ndmi_trend = float(slope_ndmi)
    else:
        features.ndvi_trend = 0.0
        features.ndmi_trend = 0.0

    return features





# ===============================================================
# End-to-end field analysis (analytic core + EO)
# ===============================================================

def analyze_field(
    name: str,
    crop: str,
    lat: float,
    lon: float,
    days_back: int = 10,
) -> FieldReport:
    end_d = date.today()
    start_d = end_d - timedelta(days=days_back)

    field = FieldConfig(
        name=name,
        crop=crop,
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
    )

    daily_records = build_daily_records(field)
    features = compute_aggregated_features(daily_records)

    # Enrich climate features with Sentinel-2 NDVI/NDMI time-series, if available
    features = _augment_features_with_satellite(field, features)

    return FieldReport(field=field, daily=daily_records, features=features)


def print_report(report: FieldReport) -> None:
    f = report.field
    fe = report.features

    print(f"FIELD BRIEF – {f.name} ({f.crop}) – {f.start_date.isoformat()} to {f.end_date.isoformat()}")
    print()
    print("Status (analytic climate core):")
    print(f"- Mean merged precipitation: {fe.mean_precip_mm:.1f} mm/day "
          f"(total {fe.total_precip_mm:.1f} mm).")
    print(f"- Mean FAO ET0 (Open-Meteo): {fe.mean_et0_mm:.1f} mm/day.")
    print(f"- Precip variation ratio (0–1): {fe.precip_variation_ratio:.2f}.")
    print(f"- ET0 variation ratio (0–1): {fe.et0_variation_ratio:.2f}.")
    print()
    print("Composite climate indices (0–1):")
    print(f"- Dryness index: {fe.dryness_index:.2f}.")
    print(f"- Rainfall-deficit index: {fe.rainfall_deficit_index:.2f}.")
    print(f"- Vigor proxy index: {fe.vigor_proxy_index:.2f}.")
    print()
    print("Analytic risk (climate-driven):")
    print(f"- Drought / water-stress risk (analytic): {fe.drought_risk_score:.0f}/100.")
    print(f"- Irrigation priority (analytic): {fe.irrigation_priority_score:.0f}/100.")
    print()
    print("Vegetation (Sentinel-2, if available):")
    print(f"- Mean NDVI: {fe.mean_ndvi:.3f}, latest NDVI: {fe.latest_ndvi:.3f}, NDVI trend: {fe.ndvi_trend:.4f}")
    print(f"- Mean NDMI: {fe.mean_ndmi:.3f}, latest NDMI: {fe.latest_ndmi:.3f}, NDMI trend: {fe.ndmi_trend:.4f}")
    print()


# ===============================================================
# Real ML – build training set & train RandomForest
# ===============================================================

def make_feature_vector(fe: AggregatedFeatures) -> np.ndarray:
    """
    Features used by the global RandomForest ML model.
    Includes both climate and Sentinel-2 vegetation stats.
    """
    return np.array(
        [
            # Climate features
            fe.mean_precip_mm,
            fe.total_precip_mm,
            fe.mean_et0_mm,
            fe.precip_variation_ratio,
            fe.et0_variation_ratio,
            fe.dryness_index,
            fe.rainfall_deficit_index,
            fe.vigor_proxy_index,

            # Sentinel-2 vegetation features
            fe.mean_ndvi,
            fe.median_ndvi,
            fe.latest_ndvi,
            fe.ndvi_trend,
            fe.mean_ndmi,
            fe.median_ndmi,
            fe.latest_ndmi,
            fe.ndmi_trend,
        ],
        dtype=float,
    )


def build_training_dataset(
    num_samples: int = 25,
    days_back: int = 10,
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Sample random global fields, compute analytic risk, and build
    an ML dataset (features X, target y = analytic drought risk).
    Uses both climate & NDVI/NDMI where available.
    """
    rng = np.random.default_rng(seed)
    X_list: List[np.ndarray] = []
    y_list: List[float] = []

    for i in range(num_samples):
        lat = float(rng.uniform(-50.0, 50.0))
        lon = float(rng.uniform(-120.0, 120.0))
        try:
            report = analyze_field(
                name=f"train_field_{i}",
                crop="generic",
                lat=lat,
                lon=lon,
                days_back=days_back,
            )
            fe = report.features
            x = make_feature_vector(fe)
            y = fe.drought_risk_score
            X_list.append(x)
            y_list.append(y)
            print(f"[{i+1}/{num_samples}] ({lat:.2f},{lon:.2f}) -> risk={y:.1f}")
        except Exception as e:
            print(f"[{i+1}/{num_samples}] Error at ({lat:.2f},{lon:.2f}): {e}. Skipping.")
            continue

    if not X_list:
        raise RuntimeError("No training samples collected (check network/API).")

    X = np.vstack(X_list)
    y = np.array(y_list, dtype=float)
    return X, y


def train_ml_model(
    X: np.ndarray,
    y: np.ndarray,
    test_fraction: float = 0.2,
    seed: int = 0,
) -> Tuple[RandomForestRegressor, Dict[str, float]]:
    """
    Train RandomForest to approximate analytic drought risk.
    """
    n = X.shape[0]
    rng = np.random.default_rng(seed)
    indices = np.arange(n)
    rng.shuffle(indices)

    split = max(1, int(n * (1.0 - test_fraction)))
    train_idx = indices[:split]
    test_idx = indices[split:] if split < n else indices[:1]

    X_train, y_train = X[train_idx], y[train_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        random_state=seed,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred)) if len(y_test) > 1 else float("nan")
    mae = float(mean_absolute_error(y_test, y_pred))

    metrics = {
        "r2": r2,
        "mae": mae,
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
    }
    return model, metrics


# ===============================================================
# AI-driven irrigation recommender
# ===============================================================

def recommend_irrigation(report: FieldReport, ml_risk: float) -> str:
    """
    AI-backed recommendation:
    - Uses analytic drought risk + irrigation priority + ML risk.
    - Looks at recent dryness trend.
    - Returns human-readable action guidance.
    """
    fe = report.features
    analytic_risk = fe.drought_risk_score
    analytic_priority = fe.irrigation_priority_score

    # Combine analytic and ML risks
    combined_risk = 0.5 * analytic_risk + 0.5 * ml_risk
    combined_priority = 0.5 * analytic_priority + 0.5 * combined_risk

    # Risk level from combined risk
    if combined_risk >= 70:
        risk_level = "HIGH"
    elif combined_risk >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Recent dryness trend (last 3 days)
    dryness_vals = np.array([d.dryness_daily for d in report.daily], dtype=float)
    if dryness_vals.size >= 3:
        recent = dryness_vals[-3:]
        trend = float(recent[-1] - recent[0])  # last minus first
    else:
        trend = 0.0

    if trend > 0.1:
        trend_label = "increasing"
    elif trend < -0.1:
        trend_label = "decreasing"
    else:
        trend_label = "stable"

    # Approximate irrigation depth suggestion (mm)
    # 0 risk -> 0 mm, 100 risk -> ~35 mm
    suggested_depth_mm = max(0.0, min(35.0, 0.35 * combined_priority))

    # Time urgency
    if combined_priority >= 75:
        urgency = "IRRIGATE AS SOON AS POSSIBLE (next 1–3 days)"
    elif combined_priority >= 50:
        urgency = "PLAN IRRIGATION SOON (next 3–7 days)"
    else:
        urgency = "NO URGENT IRRIGATION, MONITOR CONDITIONS"

    lines = []
    lines.append("AI RECOMMENDATION")
    lines.append("-----------------")
    lines.append(f"- Combined drought risk (analytic+ML): {combined_risk:.1f}/100 ({risk_level}).")
    lines.append(f"- Combined irrigation priority: {combined_priority:.1f}/100.")
    lines.append(f"- Recent dryness trend: {trend_label} over last few days.")
    lines.append(f"- Urgency: {urgency}.")
    lines.append("")
    if suggested_depth_mm > 0:
        lines.append("Suggested action:")
        lines.append(
            f"- Apply approximately {suggested_depth_mm:.1f} mm of irrigation over the field, "
            f"adjusted to your system capacity and soil type."
        )
        if risk_level == "HIGH":
            lines.append("- Split into 1–2 applications if infiltration is low or soils are light.")
        else:
            lines.append("- One application may be sufficient; refine based on local experience.")
    else:
        lines.append("Suggested action:")
        lines.append("- Do not irrigate solely based on current climate/EO signal.")
        lines.append("- Continue monitoring rainfall, ET0 and vegetation; be ready to irrigate if conditions dry further.")

    return "\n".join(lines)
