import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Shadow Settings Loader
    Pulls configuration from environment variables or .env file.
    """
    # Environment Setup
    MODE: str = "PROD"  # DEV | PROD
    DOMAIN_NAME: str = "localhost"

    # Databases
    MONGO_URL: str
    REDIS_URL: str

    # Telegram (Super Admin)
    TG_API_ID: int
    TG_API_HASH: str
    TG_BOT_TOKEN: str
    TG_OWNER_ID: int

    # Security
    JWT_SECRET: str
    SECURE_LINK_SECRET: str

    model_config = SettingsConfigDict(
        # Point to the root .env file relative to apps/manager/
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore" # Ignore extra env variables not defined here
    )

# Instantiate settings singleton
settings = Settings()