from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/url_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    db_echo: bool = False
    
    SECRET_KEY: str = "secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()