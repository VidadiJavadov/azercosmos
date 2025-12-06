import argparse
from datetime import date

from eo_drought.core.domain_fields import Field, FieldAnalysisWindow
from eo_drought.core.geo import build_square_aoi
from eo_drought.ingest.satellite.sentinel2 import fetch_satellite_metrics_for_aoi
from eo_drought.ingest.weather.open_meteo import fetch_rainfall_time_series

from eo_drought.analytics.baselines.crop_ndvi_baselines import expected_baselines
from eo_drought.analytics.indicators.vegetation_health import compute_vegetation_indicators
from eo_drought.analytics.risk.risk_components import compute_risk_components
from eo_drought.analytics.risk.risk_scoring import compute_overall_risk
from eo_drought.analytics.explainability.textual_explanations import generate_report

import warnings

# keep imports below this
warnings.filterwarnings("ignore", category=FutureWarning, module="pystac_client.item_search")

def analyze_field_cli() -> None:
    parser = argparse.ArgumentParser(
        description="EO Drought & Irrigation Intelligence – Single-field analysis CLI"
    )
    parser.add_argument("--name", required=True, help="Field name")
    parser.add_argument("--crop", required=True, help="Crop name (e.g. wheat)")
    parser.add_argument("--lat", type=float, required=True, help="Latitude (WGS84)")
    parser.add_argument("--lon", type=float, required=True, help="Longitude (WGS84)")
    parser.add_argument(
        "--days-back",
        type=int,
        default=10,
        help="Number of days back from today for analysis window",
    )
    parser.add_argument(
        "--report-mode",
        choices=["farmer", "expert"],
        default="farmer",
        help="Report detail level",
    )

    args = parser.parse_args()

    field = Field(
        id=args.name,
        name=args.name,
        crop=args.crop,
        lat=args.lat,
        lon=args.lon,
    )

    window = FieldAnalysisWindow(days_back=args.days_back, end_date=date.today())
    start = window.start_date
    end = window.end_date

    # AOI
    aoi = build_square_aoi(field.lat, field.lon, field.aoi_size_m)

    # Satellite metrics
    sat = fetch_satellite_metrics_for_aoi(aoi, start, end, max_items=6)

    # Rainfall
    rain = fetch_rainfall_time_series(field.lat, field.lon, start, end)

    # Baseline expectations
    baseline = expected_baselines(
        crop=field.crop,
        lat=field.lat,
        today=end,
        days_back=window.days_back,
    )

    # Indicators
    indicators = compute_vegetation_indicators(sat, rain, baseline)

    # Risk components + overall risk
    components = compute_risk_components(indicators)
    risk = compute_overall_risk(
        indicators,
        components,
        n_s2_items=sat.num_items,
        avg_cloud_cover=sat.mean_cloud_cover,
        rainfall_ok=rain.ok,
    )

    period_label = f"{start.isoformat()} to {end.isoformat()}"

    report = generate_report(
        field=field,
        baseline=baseline,
        s2=sat,
        rain=rain,
        ind=indicators,
        risk=risk,
        period_label=period_label,
        report_mode=args.report_mode,
    )

    print(report)


if __name__ == "__main__":
    analyze_field_cli()
