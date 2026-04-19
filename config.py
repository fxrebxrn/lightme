from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_TOKEN: str
    ADMIN_ID: int
    CHANNEL_USERNAME: str
    CHANNEL_URL: str
    SUPPORT_USERNAME: str
    DONATE_URL: str
    DATABASE_NAME: str
    DATABASE_PATH: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()