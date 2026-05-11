"""Cálculo de CLTV por cliente.

Fórmula del enunciado:
    CLTV = Ingresos_t × Margen_t × Frecuencia_t × R_t

Donde, en la ventana temporal t:
    - Ingresos_t   = ingresos netos del cliente (ventas - devoluciones).
    - Margen_t     = (ingresos − coste) / ingresos  (proporción).
    - Frecuencia_t = nº de tickets distintos del cliente.
    - R_t          = retención = meses_activos / meses_de_la_ventana.
"""
from __future__ import annotations

import pandas as pd

def compute_cltv(df : pd.DataFrame) -> pd.DataFrame:
    """Calcula el CLTV de cada cliente con compras."""
    df["cltv"] = (
        df["net_revenue"].astype(float)
        * df["margin_rate"].astype(float)
        * df["frequency"].astype(float)
        * df["retention_rate"].astype(float)
    )
    return df.sort_values("cltv", ascending=False).reset_index(drop=True)
