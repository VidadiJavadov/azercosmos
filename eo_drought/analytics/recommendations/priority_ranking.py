from typing import List
from eo_drought.core.domain_fields import Field
from eo_drought.core.domain_metrics import RiskResult

def rank_fields_by_urgency(
    fields: List[Field],
    risks: List[RiskResult],
) -> List[int]:
    """
    Returns indices of fields sorted from most to least urgent.
    Initial logic: sort by risk.score_0_100 descending.
    """
    raise NotImplementedError
