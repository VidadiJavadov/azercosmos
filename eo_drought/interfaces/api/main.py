from fastapi import FastAPI
from pydantic import BaseModel

from eo_drought.core.domain_fields import Field
# and your pipeline function (which you can extract from CLI main)

app = FastAPI(title="EO Drought & Irrigation Intelligence")

class AnalyzeRequest(BaseModel):
    name: str
    crop: str
    lat: float
    lon: float
    days_back: int = 10

@app.post("/analyze-field")
def analyze_field_endpoint(req: AnalyzeRequest):
    # call your shared analyze_field(field, window) function
    # return risk + maybe a farmer report
    raise NotImplementedError
