from typing import Iterable
from dataclasses import dataclass

@dataclass
class LabeledExample:
    features: dict
    label: int  # or float

def build_drought_dataset(
    field_ids: Iterable[str],
) -> list[LabeledExample]:
    """
    Orchestrate: read historical metrics & labels → dataset.
    Stub now, implement when you have historical labels.
    """
    raise NotImplementedError
