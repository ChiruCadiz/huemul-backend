from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    university_auth_url: str

    class Config:
        env_file = ".env"

settings = Settings()