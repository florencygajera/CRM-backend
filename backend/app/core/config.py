from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "SmartServeAI"
    ENV: str = "dev"
    DATABASE_URL: str

    JWT_SECRET: str
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 14

settings = Settings()
