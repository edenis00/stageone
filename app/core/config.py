from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    GENDERIZE_URL: str
    AGIFY_URL: str
    NATIONALIZE_URL: str
    
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )

settings = Settings()
