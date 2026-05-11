"""Carga la configuración del proyecto desde el archivo .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env situado en la raíz del proyecto.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Variables de configuración tipadas y centralizadas."""

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_schema_raw: str
    db_schema_staging: str
    db_schema_dwh: str

    @property
    def database_url(self) -> str:
        """URL de conexión SQLAlchemy para PostgreSQL."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @classmethod
    def from_env(cls) -> "Settings":
        """Construye Settings leyendo las variables de entorno cargadas."""
        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_port=int(os.getenv("DB_PORT", "5433")),
            db_name=os.getenv("DB_NAME", "saleshealth"),
            db_user=os.getenv("DB_USER", ""),
            db_password=os.getenv("DB_PASSWORD", ""),
            db_schema_raw=os.getenv("DB_SCHEMA_RAW", "public"),
            db_schema_staging=os.getenv("DB_SCHEMA_STAGING", "staging"),
            db_schema_dwh=os.getenv("DB_SCHEMA_DWH", "dwh"),
        )


# Instancia única reutilizable.
settings = Settings.from_env()