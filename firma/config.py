import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
load_dotenv(ROOT / ".env")


@dataclass
class Settings:
    data_dir: Path
    database_url: str = ""
    cloud: bool = False
    password: str = ""
    secret: str = ""
    provider: str = "serpapi"
    api_key: str = ""

    @classmethod
    def from_env(cls):
        provider = os.getenv("SEARCH_PROVIDER", "serpapi")
        return cls(
            data_dir=Path(os.getenv("FIRMA_DATA_DIR", str(ROOT / "data"))),
            database_url=os.getenv("DATABASE_URL", ""),
            cloud=os.getenv("VERCEL") == "1" or os.getenv("FIRMA_CLOUD") == "1",
            password=os.getenv("APP_PASSWORD", ""), secret=os.getenv("APP_SECRET", ""),
            provider=provider, api_key=os.getenv("BRAVE_API_KEY" if provider == "brave" else "SERPAPI_KEY", ""),
        )

    def validate(self):
        if self.cloud:
            if not self.database_url.startswith(("postgres://", "postgresql://")):
                raise RuntimeError("Vercel için kalıcı PostgreSQL DATABASE_URL gerekli.")
            if len(self.password) < 16 or len(self.secret) < 32:
                raise RuntimeError("APP_PASSWORD en az 16, APP_SECRET en az 32 karakter olmalı.")
