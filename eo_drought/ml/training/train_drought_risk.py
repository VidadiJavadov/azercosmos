from pathlib import Path
import joblib

from eo_drought.ml.datasets.dataset_builder import build_drought_dataset
from eo_drought.ml.models.classical_models import make_default_drought_model
from eo_drought.io.paths import MODELS_DIR

def train_and_save_default_model():
    dataset = build_drought_dataset(field_ids=[])  # fill later
    # split X, y; train; save to MODELS_DIR / "drought_risk" / "latest" / "model.pkl"
    raise NotImplementedError
