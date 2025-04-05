# app/main_bot/config/config.py

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv(".env")

class Settings(BaseSettings):
    bot_token: str
    database_url: str
    alembic_database_url: str
    admin_chat_id: str
    support_username: str

    class Config:
        env_file = ".env"


settings = Settings()
