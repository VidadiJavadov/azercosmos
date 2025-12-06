from datetime import date
from typing import Iterable

from eo_drought.core.domain_fields import Field
from eo_drought.interfaces.cli.main import analyze_field_cli  # or a shared analyze_field() function

def run_daily_pipeline_for_fields(fields: Iterable[Field], run_date: date) -> None:
    """
    Loops over all fields, runs the analysis pipeline, stores outputs.
    """
    raise NotImplementedError
