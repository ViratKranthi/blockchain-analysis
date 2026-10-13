"""Application configuration — 12-factor, env-overridable."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
CACHE_DIR = APP_DIR / "cache"
DATA_JS = APP_DIR / "data.js"


class Settings(BaseSettings):
    """All knobs in one place. Override via .env or environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="KFLOW_",
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # server
    host: str = "127.0.0.1"
    port: int = 8765
    cors_origins: list[str] = ["http://localhost:8765", "http://127.0.0.1:8765"]

    # cache TTLs (seconds)
    ttl_intraday: int = 300          # 5 min
    ttl_etf: int = 6 * 3600          # 6 h
    ttl_cot: int = 24 * 3600         # 24 h
    ttl_snapshot: int = 30           # in-process /api/today cache
    cache_max_bytes: int = 900_000   # disk-cache ceiling

    # database
    db_path: Path = CACHE_DIR / "history.db"

    # external timeouts
    http_timeout: int = 15
    okx_timeout: int = 6

    # features
    enable_websocket: bool = True
    enable_scheduler: bool = False   # Week 3
    discord_webhook_url: str = ""    # set via KFLOW_DISCORD_WEBHOOK_URL


settings = Settings()

# ensure cache dir exists on import
CACHE_DIR.mkdir(parents=True, exist_ok=True)
