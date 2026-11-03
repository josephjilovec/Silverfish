"""Small, explicit resource envelopes. No external service is enabled by default."""
from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Limits:
    max_cases: int = 200
    max_messages: int = 80
    max_message_bytes: int = 8192
    max_case_bytes: int = 131072
    max_request_bytes: int = 262144
    max_model_calls: int = 4
    model_context_bytes: int = 20000
    max_database_bytes: int = 200 * 1024 * 1024


@dataclass(frozen=True)
class Config:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8787
    operator_token: str = ""
    webhook_secret: str = ""
    ollama_model: str = ""
    limits: Limits = Limits()

    @classmethod
    def from_env(cls):
        return cls(
            data_dir=Path(os.environ.get("SILVERTRAP_DATA_DIR", "./data")).resolve(),
            host=os.environ.get("SILVERTRAP_HOST", "127.0.0.1"),
            port=int(os.environ.get("SILVERTRAP_PORT", "8787")),
            operator_token=os.environ.get("SILVERTRAP_OPERATOR_TOKEN", ""),
            webhook_secret=os.environ.get("SILVERTRAP_WEBHOOK_SECRET", ""),
            ollama_model=os.environ.get("SILVERTRAP_OLLAMA_MODEL", ""),
        )
