from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ttm_db"

    class Config:
        env_file = ".env"

settings = Settings()
