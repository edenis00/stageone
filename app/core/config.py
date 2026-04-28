from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    
    GENDERIZE_URL: str
    AGIFY_URL: str
    NATIONALIZE_URL: str
    
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_TIME: int
    REFRESH_TOKEN_TIME: int
    
    GITHUB_CLIENT_ID: str
    GITHUB_REDIRECT_URI: str
    GITHUB_CLIENT_SECRET: str
    
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )

settings = Settings()
