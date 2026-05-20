from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    environment: str = "development"
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_ttl_hours: int = 24
    # Ollama
    ollama_base_url: str = "http://localhost:11434"

settings = Settings()