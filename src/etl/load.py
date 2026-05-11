"""Helpers de carga: ejecutar SQL en orden y resetear esquemas."""
from __future__ import annotations

from pathlib import Path

from src.db import run_sql, run_sql_file
from src.utils import get_logger

log = get_logger("etl.load")


def run_sql_directory(directory: str | Path) -> list[Path]:
    """Ejecuta los .sql de un directorio en orden alfabético."""
    files = sorted(Path(directory).glob("*.sql"))
    for f in files:
        log.info("Ejecutando %s", f.name)
        run_sql_file(f)
    return files
