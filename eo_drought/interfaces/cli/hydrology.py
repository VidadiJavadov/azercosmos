import argparse
from datetime import date, timedelta

from eo_drought.core.domain_fields import Field, FieldAnalysisWindow
from eo_drought.ingest.weather.open_meteo import fetch_rain_and_et0_timeseries
from eo_drought.hydrology.crop_params import (
    get_soil_profile_for_crop,
    simple_kc_for_crop,
)
from eo_drought.hydrology.soil_water_balance import run_root_zone_water_balance
from eo_drought.hydrology.irrigation_scheduler import (
    IrrigationConstraints,
    make_irrigation_recommendation,
)


def analyze_field_hydrology_cli() -> None:
    parser = argparse.ArgumentParser(
        description="EO Drought – Hydrology & Irrigation Engine (root-zone water balance CLI)",
    )
    parser.add_argument("--name", required=True, help="Field name")
    parser.add_argument("--crop", required=True, help="Crop name (e.g. wheat)")
    parser.add_argument("--lat", type=float, required=True, help="Latitude (WGS84)")
    parser.add_argument("--lon", type=float, required=True, help="Longitude (WGS84)")
    parser.add_argument(
        "--days-back",
        type=int,
        default=10,
        help="Number of days back from today for hydrology window",
    )

    args = parser.parse_args()

    # 1. Define field & analysis window
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

    # 2. Fetch daily rainfall + ET0
    dates, rain_mm, et0_mm = fetch_rain_and_et0_timeseries(
        field.lat,
        field.lon,
        start,
        end,
    )

    if not dates:
        print("⚠️  No rainfall/ET0 data available for this period; cannot run hydrology.")
        return

    # 3. Soil & crop parameters
    soil = get_soil_profile_for_crop(field.crop)
    kc = simple_kc_for_crop(field.crop)

    # 4. Run root-zone water balance (rainfed only)
    wb = run_root_zone_water_balance(
        dates=dates,
        rainfall_mm=rain_mm,
        et0_mm=et0_mm,
        soil=soil,
        kc=kc,
        initial_depletion_mm=None,  # start at field capacity
    )

    latest_state = wb.states[-1]
    Dr = latest_state.depletion_mm
    depletion_frac = Dr / soil.taw_mm if soil.taw_mm > 0 else 0.0

    # 5. Irrigation recommendation based on hydrology
    constraints = IrrigationConstraints()
    rec = make_irrigation_recommendation(wb, constraints)

    # 6. Print a concise hydrology & irrigation brief
    print(f"HYDROLOGY BRIEF – {field.name} ({field.crop}) – {start} to {end}\n")

    print("Root-zone Water Status:")
    print(f"- Total Available Water (TAW): {soil.taw_mm:.1f} mm")
    print(f"- Readily Available Water (RAW): {soil.raw_mm:.1f} mm")
    print(f"- Latest depletion Dr: {Dr:.1f} mm "
          f"({depletion_frac*100:.1f}% of TAW)")
    print(f"- Latest ET0: {latest_state.et0_mm:.2f} mm/day")
    print(f"- Latest ETc (actual): {latest_state.etc_mm:.2f} mm/day")
    print(f"- Latest Ks (water-stress coeff.): {latest_state.ks:.2f}\n")

    print("Irrigation Recommendation (hydrology-only):")
    print(f"- Recommended depth: {rec.recommended_depth_mm:.1f} mm")
    print(f"- Urgency: {rec.urgency_0_100}/100")
    print(f"- Days until critical if no irrigation: {rec.days_until_critical}")
    print(f"- Comment: {rec.comment}")


if __name__ == "__main__":
    analyze_field_hydrology_cli()
