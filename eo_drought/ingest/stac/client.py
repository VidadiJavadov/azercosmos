from datetime import date
from typing import List

from pystac_client import Client
from shapely.geometry.base import BaseGeometry

from eo_drought.config.settings import settings


def make_stac_client() -> Client:
    return Client.open(settings.stac_url)


def search_sentinel2_items(
    aoi: BaseGeometry,
    start: date,
    end: date,
    max_items: int,
    collection: str = "sentinel-2-l2a",
) -> List:
    """
    Search Sentinel-2 items over an AOI and time range.
    Uses the modern `items()` iterator (not deprecated `get_items()`).
    """
    client = make_stac_client()
    search = client.search(
        collections=[collection],
        intersects=aoi.__geo_interface__,
        datetime=f"{start.isoformat()}/{end.isoformat()}",
    )

    # THIS is the important line – no more get_items()
    items = list(search.items())

    return items[:max_items]
