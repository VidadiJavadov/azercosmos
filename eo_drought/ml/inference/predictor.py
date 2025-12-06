from pathlib import Path
import joblib

from eo_drought.core.domain_metrics import Indicators

class DroughtPredictor:
    def __init__(self, model_path: Path):
        self.model = joblib.load(model_path)

    def predict_probability(self, indicators: Indicators) -> float:
        """
        Map Indicators → feature vector → model probability.
        """
        raise NotImplementedError
