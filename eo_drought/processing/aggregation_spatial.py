import numpy as np

from eo_drought.core.domain_metrics import SatelliteMetrics

def aggregate_satellite_indices(
    ndvi_stack: np.ndarray,
    ndmi_stack: np.ndarray,
    mask_stack: np.ndarray,
) -> SatelliteMetrics:
    """
    Implement your per-field NDVI/NDMI median logic here.
    """
    raise NotImplementedError
