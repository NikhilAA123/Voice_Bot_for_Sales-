import os
from pathlib import Path
from pydantic import BaseSettings, Field, SecretStr

class Settings(BaseSettings):
    LOG_LEVEL: str = Field("info", env="LOG_LEVEL")
    DATABASE_URL: str = Field(..., env="DATABASE_URL")

    TWILIO_ACCOUNT_SID: SecretStr = Field(..., env="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: SecretStr = Field(..., env="TWILIO_AUTH_TOKEN")
    CLAUDE_API_KEY: SecretStr = Field(..., env="CLAUDE_API_KEY")
    ELEVENLABS_API_KEY: SecretStr = Field(..., env="ELEVENLABS_API_KEY")
    RETELL_API_KEY: SecretStr = Field(..., env="RETELL_API_KEY")
    MY_MOBILE: str = Field(..., env="MY_MOBILE")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
