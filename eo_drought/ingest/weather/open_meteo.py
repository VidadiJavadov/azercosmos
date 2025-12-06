from datetime import date, datetime
from typing import List, Tuple

import requests

from eo_drought.core.domain_metrics import RainfallSummary


def fetch_rainfall_time_series(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
) -> RainfallSummary:
    """
    Fetch daily rainfall from Open-Meteo archive API and summarise it.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = (
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
        "&daily=precipitation_sum"
        "&timezone=UTC"
    )
    url = base_url + params

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})
        precip = daily.get("precipitation_sum") or []
        times = daily.get("time") or []

        vals: List[float] = [float(v) if v is not None else 0.0 for v in precip]
        dates: List[date] = [datetime.fromisoformat(t).date() for t in times]

        total_mm = float(sum(vals))
        return RainfallSummary(
            total_mm=total_mm,
            daily_values=vals,
            dates=dates,
            ok=True,
        )
    except Exception:
        # Fallback: mark rainfall as unavailable, but don't crash.
        return RainfallSummary(
            total_mm=0.0,
            daily_values=[],
            dates=[],
            ok=False,
        )


def fetch_rain_and_et0_timeseries(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
) -> Tuple[List[date], List[float], List[float]]:
    """
    Fetch daily rainfall and FAO-56 ET0 from Open-Meteo archive API.

    Returns:
        dates: list of date objects
        rain_mm: daily precipitation_sum [mm]
        et0_mm: daily et0_fao_evapotranspiration [mm]
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = (
        f"?latitude={lat}"
        f"&longitude={lon}"
        f"&start_date={start_date.isoformat()}"
        f"&end_date={end_date.isoformat()}"
        "&daily=precipitation_sum,et0_fao_evapotranspiration"
        "&timezone=UTC"
    )
    url = base_url + params

    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        daily = data.get("daily", {})

        times = daily.get("time") or []
        precip = daily.get("precipitation_sum") or []
        et0 = daily.get("et0_fao_evapotranspiration") or []

        if not (len(times) == len(precip) == len(et0)):
            return [], [], []

        dates: List[date] = [datetime.fromisoformat(t).date() for t in times]
        rain_mm: List[float] = [
            float(v) if v is not None else 0.0 for v in precip
        ]
        et0_mm: List[float] = [
            float(v) if v is not None else 0.0 for v in et0
        ]

        return dates, rain_mm, et0_mm

    except Exception:
        return [], [], []
