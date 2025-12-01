from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://hub_user:hub_password@localhost:5432/model_hub"
    REDIS_URL: str = "redis://localhost:6379"
    MODEL_STORE_PATH: str = "/data/model-store"
    HF_TOKEN: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
