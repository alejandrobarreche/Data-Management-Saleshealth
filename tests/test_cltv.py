"""Validan la lógica de CLTV y métricas."""
import pytest

from src.db import read_sql

try:
    read_sql("select 1")
except Exception as e:  # pragma: no cover
    pytest.skip(f"DB no disponible: {e}", allow_module_level=True)

from src.analytics import compute_cltv, compute_customer_metrics


def test_cltv_columns_present():
    df = compute_cltv()
    expected = {
        "customer_id", "full_name", "gross_revenue", "net_revenue",
        "margin_rate", "frequency", "retention_rate", "cltv",
    }
    assert expected.issubset(df.columns)


def test_cltv_formula_consistency():
    df = compute_cltv().head(50).copy()
    expected = (
        df["net_revenue"].astype(float)
        * df["margin_rate"].astype(float)
        * df["frequency"].astype(float)
        * df["retention_rate"].astype(float)
    )
    assert ((df["cltv"] - expected).abs() < 1e-6).all()


def test_metrics_aov_matches_revenue_div_frequency():
    m = compute_customer_metrics().head(100).copy()
    pos = m[m["frequency"] > 0]
    expected = pos["net_revenue"].astype(float) / pos["frequency"].astype(float)
    assert ((pos["aov"].astype(float) - expected).abs() < 1e-6).all()


def test_recency_is_non_negative():
    m = compute_customer_metrics()
    assert (m["recency_days"] >= 0).all()
