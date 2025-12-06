from datetime import date
from typing import List, Dict, Any

import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom
from shapely.geometry import Polygon, mapping

from eo_drought.core.domain_metrics import SatelliteMetrics
from eo_drought.ingest.stac.client import search_sentinel2_items
from eo_drought.ingest.stac.asset_resolver import resolve_asset


def safe_index(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """
    Compute num / den safely, avoiding division by zero and propagating NaNs.
    """
    out = np.full_like(num, np.nan, dtype="float32")
    mask_valid = (den != 0) & ~np.isnan(num) & ~np.isnan(den)
    out[mask_valid] = num[mask_valid] / den[mask_valid]
    return out


def read_band_with_aoi(asset, geom_wgs84: Dict[str, Any]) -> np.ndarray:
    """
    Read a band clipped to the AOI; if clipping fails, fall back to full band.
    """
    with rasterio.open(asset.href) as src:
        dst_crs = src.crs
        geom_proj = transform_geom("EPSG:4326", dst_crs, geom_wgs84)

        try:
            out_image, _ = mask(src, [geom_proj], crop=True)
            arr = out_image[0].astype("float32")
        except Exception:
            # Fallback: read full band
            arr = src.read(1).astype("float32")

        nodata = src.nodata
        if nodata is not None:
            arr[arr == nodata] = np.nan
        return arr


def _align_to_shape(arr: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    """
    Align arr to target_shape using simple nearest-neighbor up/down-sampling.

    - If shapes are equal: return as is.
    - If target is integer multiple bigger: upsample with np.repeat.
    - If arr is integer multiple bigger: downsample by averaging blocks.
    - Otherwise: crop/pad to the overlapping region.
    """
    h, w = arr.shape
    th, tw = target_shape

    if (h, w) == (th, tw):
        return arr

    # Upsample case: arr smaller than target
    if th >= h and tw >= w:
        sy = th / h
        sx = tw / w
        if abs(sy - round(sy)) < 1e-6 and abs(sx - round(sx)) < 1e-6:
            sy = int(round(sy))
            sx = int(round(sx))
            return np.repeat(np.repeat(arr, sy, axis=0), sx, axis=1)

    # Downsample case: arr larger than target
    if h >= th and w >= tw:
        sy = h / th
        sx = w / tw
        if abs(sy - round(sy)) < 1e-6 and abs(sx - round(sx)) < 1e-6:
            sy = int(round(sy))
            sx = int(round(sx))
            arr = arr[: th * sy, : tw * sx]
            arr = arr.reshape(th, sy, tw, sx).mean(axis=(1, 3))
            return arr

    # Fallback: crop or pad with NaNs
    out = np.full(target_shape, np.nan, dtype=arr.dtype)
    ch = min(h, th)
    cw = min(w, tw)
    out[:ch, :cw] = arr[:ch, :cw]
    return out


def fetch_satellite_metrics_for_aoi(
    aoi: Polygon,
    start: date,
    end: date,
    max_items: int = 3,
    max_cloud_cover: float = 80.0,
) -> SatelliteMetrics:
    """
    Fetch up to `max_items` Sentinel-2 L2A images over AOI and date range,
    apply SCL cloud mask, compute NDVI & NDMI means, and summarize.
    """

    # STAC needs GeoJSON-like geometry in WGS84
    geom_wgs84 = mapping(aoi)

    # Get a pool of items, then filter by cloud cover ourselves
    raw_items = search_sentinel2_items(aoi, start, end, max_items=20)

    items = [
        it
        for it in raw_items
        if it.properties.get("eo:cloud_cover", 100.0) <= max_cloud_cover
    ]
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100.0))
    items = items[:max_items]

    if not items:
        raise RuntimeError("No suitable Sentinel-2 items found in given period and AOI.")

    ndvi_values: List[float] = []
    ndmi_values: List[float] = []
    cloud_covers: List[float] = []
    item_ids: List[str] = []

    # SCL cloud classes we treat as "bad"
    bad_scl_classes = {3, 8, 9, 10, 11}  # shadow, cloud, cirrus, snow

    for item in items:
        cloud_cover = float(item.properties.get("eo:cloud_cover", 100.0))
        cloud_covers.append(cloud_cover)
        item_ids.append(item.id)

        # Try multiple candidate asset names for each band
        red_asset = resolve_asset(item, ["red", "red-jp2", "B04", "B04_10m"])
        nir_asset = resolve_asset(
            item, ["nir", "nir-jp2", "nir08", "nir08-jp2", "B08", "B08_10m"]
        )
        swir_asset = resolve_asset(
            item,
            [
                "swir16",
                "swir16-jp2",
                "swir22",
                "swir22-jp2",
                "B11",
                "B11_20m",
                "B12",
                "B12_20m",
            ],
        )
        scl_asset = resolve_asset(item, ["scl", "SCL", "scl-jp2"])

        scl = read_band_with_aoi(scl_asset, geom_wgs84)
        red = read_band_with_aoi(red_asset, geom_wgs84)
        nir = read_band_with_aoi(nir_asset, geom_wgs84)
        swir = read_band_with_aoi(swir_asset, geom_wgs84)

        # Align everything to red's shape
        target_shape = red.shape
        scl = _align_to_shape(scl, target_shape)
        nir = _align_to_shape(nir, target_shape)
        swir = _align_to_shape(swir, target_shape)

        cloud_mask = np.isin(scl, list(bad_scl_classes))

        # Apply cloud mask: bad pixels → NaN
        red[cloud_mask] = np.nan
        nir[cloud_mask] = np.nan
        swir[cloud_mask] = np.nan

        ndvi_arr = safe_index(nir - red, nir + red)
        ndmi_arr = safe_index(nir - swir, nir + swir)

        ndvi_mean = float(np.nanmean(ndvi_arr))
        ndmi_mean = float(np.nanmean(ndmi_arr))

        ndvi_values.append(ndvi_mean)
        ndmi_values.append(ndmi_mean)

    median_ndvi = float(np.nanmedian(np.array(ndvi_values)))
    median_ndmi = float(np.nanmedian(np.array(ndmi_values)))
    mean_cloud_cover = float(np.mean(cloud_covers))
    num_items = len(items)

    return SatelliteMetrics(
        item_ids=item_ids,
        ndvi_values=ndvi_values,
        ndmi_values=ndmi_values,
        median_ndvi=median_ndvi,
        median_ndmi=median_ndmi,
        mean_cloud_cover=mean_cloud_cover,
        num_items=num_items,
    )
