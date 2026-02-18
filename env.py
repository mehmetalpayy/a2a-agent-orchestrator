"""Environment-based configuration using Pydantic settings."""

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings


class SecretSettings(BaseSettings):
    """Loads required values from the .env file."""

    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_OPENAI_API_VERSION: str
    OPEN_WEATHER_API_KEY: str
    AGENT_BIND_HOST: str = "127.0.0.1"
    PORT: int = 10001
    AGENT_PUBLIC_BASE_URL: str | None = None
    REMOTE_AGENT_URLS: list[str] = ["http://127.0.0.1:10001"]

    @field_validator("REMOTE_AGENT_URLS", mode="before")
    @classmethod
    def _parse_remote_agent_urls(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return [item.strip() for item in value if item and item.strip()]
        if not value:
            return []
        raw = value.strip()
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


secrets = SecretSettings()
