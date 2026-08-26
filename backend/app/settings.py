import os
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")
    DATABASE_URL: str = Field("sqlite+aiosqlite:///./voice_sales.db", env="DATABASE_URL")

    TWILIO_ACCOUNT_SID: SecretStr = Field(..., env="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: SecretStr = Field(..., env="TWILIO_AUTH_TOKEN")
    # WhatsApp sender: sandbox number while testing, approved number in production.
    TWILIO_WHATSAPP_FROM: str = Field("whatsapp:+14155238886", env="TWILIO_WHATSAPP_FROM")
    # Meta WhatsApp Cloud API (free test tier) – preferred when both are present.
    META_WHATSAPP_TOKEN: SecretStr = Field("", env="META_WHATSAPP_TOKEN")
    META_WHATSAPP_PHONE_NUMBER_ID: str = Field("", env="META_WHATSAPP_PHONE_NUMBER_ID")
    GROQ_API_KEY: SecretStr = Field("", env="GROQ_API_KEY")
    CLAUDE_API_KEY: SecretStr = Field("", env="CLAUDE_API_KEY")
    # Optional – premium TTS voices only; Retell platform voices are 60% cheaper.
    ELEVENLABS_API_KEY: SecretStr = Field("", env="ELEVENLABS_API_KEY")
    RETELL_API_KEY: SecretStr = Field("", env="RETELL_API_KEY")
    RETELL_AGENT_ID: str = Field("", env="RETELL_AGENT_ID")
    RETELL_FROM_NUMBER: str = Field("", env="RETELL_FROM_NUMBER")
    MY_MOBILE: str = Field(..., env="MY_MOBILE")

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), case_sensitive=True)

settings = Settings()