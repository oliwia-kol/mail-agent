from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAIL_AGENT_", extra="ignore")
    ollama_url: str = "http://localhost:11434"
    model: str = "gemma4:12b-it-q4_K_M"
    model_timeout: float = 120
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_timeout: float = 10

    langfuse_enabled: bool = False
    langfuse_url: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")
    langfuse_capture_content: bool = False

    @model_validator(mode="after")
    def local_monitoring(self):
        if self.langfuse_enabled:
            url = urlparse(self.langfuse_url)
            if url.scheme != "http" or url.hostname not in {
                "localhost",
                "127.0.0.1",
                "::1",
                "langfuse-web",
            }:
                raise ValueError("Adres musi wskazywać lokalny serwer Langfuse")
            if not self.langfuse_public_key or not self.langfuse_secret_key.get_secret_value():
                raise ValueError("Podaj klucze lokalnego projektu Langfuse, aby włączyć monitoring")
        return self
