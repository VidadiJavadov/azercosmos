from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    stac_url: str = "https://earth-search.aws.element84.com/v1"
    open_meteo_url: str = "https://archive-api.open-meteo.com/v1/era5"
    default_max_s2_items: int = 6

    class Config:
        env_prefix = "EO_DROUGHT_"

settings = Settings()
