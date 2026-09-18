from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://taskflow:taskflow@127.0.0.1:5432/taskflow"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"


settings = Settings()