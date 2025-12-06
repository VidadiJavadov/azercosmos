import numpy as np

def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    return (nir - red) / (nir + red + 1e-6)

def ndmi(nir: np.ndarray, swir: np.ndarray) -> np.ndarray:
    return (nir - swir) / (nir + swir + 1e-6)
