from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    groq_api_key: str
    database_url: str = "postgresql://postgres:postgres@db:5432/crm"
    groq_primary_model: str = "gemma2-9b-it"
    groq_large_model: str = "llama-3.3-70b-versatile"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
