import math
from shapely.geometry import Polygon

# Approximate meters per degree of latitude.
# For field-scale boxes this is more than good enough.
METERS_PER_DEGREE_LAT = 111_320.0  # ~111.32 km

def _meters_to_deg_lat(meters: float) -> float:
    return meters / METERS_PER_DEGREE_LAT

def _meters_to_deg_lon(meters: float, lat_deg: float) -> float:
    """
    Convert meters to degrees of longitude at a given latitude.
    We account for cos(latitude) so that east–west size in meters is preserved.
    """
    # Avoid division by zero at the poles (not your use-case anyway)
    cos_lat = math.cos(math.radians(lat_deg))
    if abs(cos_lat) < 1e-6:
        cos_lat = 1e-6
    meters_per_degree_lon = METERS_PER_DEGREE_LAT * cos_lat
    return meters / meters_per_degree_lon

def build_square_aoi(lat: float, lon: float, size_m: int) -> Polygon:
    """
    Build a square AOI around (lat, lon) with side length ≈ `size_m` meters.

    - We construct a square in *meters* around the center.
    - Then convert the half-side to degrees in lat and lon.
    - Returns a Shapely Polygon in (lon, lat) coordinates suitable for STAC queries.
    """
    half_side_m = size_m / 2.0

    half_deg_lat = _meters_to_deg_lat(half_side_m)
    half_deg_lon = _meters_to_deg_lon(half_side_m, lat)

    return Polygon(
        [
            (lon - half_deg_lon, lat - half_deg_lat),
            (lon + half_deg_lon, lat - half_deg_lat),
            (lon + half_deg_lon, lat + half_deg_lat),
            (lon - half_deg_lon, lat + half_deg_lat),
            (lon - half_deg_lon, lat - half_deg_lat),
        ]
    )
