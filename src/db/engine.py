"""Conexión a Postgres y helpers para ejecutar SQL."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from config.settings import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine SQLAlchemy reutilizable (singleton)."""
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)


def run_sql(sql: str, **params) -> None:
    """Ejecuta una sentencia SQL (DDL o DML) con autocommit."""
    eng = get_engine()
    with eng.begin() as conn:
        conn.execute(text(sql), params or None)


def run_sql_file(path: str | Path) -> None:
    """Ejecuta un archivo .sql completo. Asume sentencias separadas por ';'.

    Compatible con bloques DO $$ ... $$ porque ejecuta el archivo entero
    en una sola transacción usando exec_driver_sql.
    """
    raw = Path(path).read_text(encoding="utf-8")
    eng = get_engine()
    with eng.begin() as conn:
        conn.exec_driver_sql(raw)


def read_sql(sql: str, **params) -> pd.DataFrame:
    """Devuelve un DataFrame desde una consulta."""
    eng = get_engine()
    return pd.read_sql(text(sql), eng, params=params or None)
