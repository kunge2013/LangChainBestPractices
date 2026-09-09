"""
Application configuration module.
"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    app_name: str = "权责销账系统"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./ledger.db",
    )
    pg_database_url: str = os.getenv(
        "PG_DATABASE_URL",
        "postgresql://user:pass@localhost:5432/bill",
    )
    batch_size: int = 1000
    query_limit: int = 5000
    refresh_batch_size: int = 100
    system_staff_id: int = -1

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url


settings = Settings()
