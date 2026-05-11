"""Validan que el DWH esté coherente respecto al raw."""
import pytest

from src.db import read_sql

# Si no hay BD disponible, saltamos todos los tests de integridad.
try:
    read_sql("select 1 as ok")
except Exception as e:  # pragma: no cover
    pytest.skip(f"DB no disponible: {e}", allow_module_level=True)


def test_fact_sales_matches_raw_sale_item_count():
    raw = read_sql("select count(*) as n from public.sale_item").iloc[0]["n"]
    dwh = read_sql("select count(*) as n from dwh.fact_sales").iloc[0]["n"]
    assert int(raw) == int(dwh)


def test_fact_returns_matches_raw_return_item_count():
    raw = read_sql("select count(*) as n from public.return_item").iloc[0]["n"]
    dwh = read_sql("select count(*) as n from dwh.fact_returns").iloc[0]["n"]
    assert int(raw) == int(dwh)


def test_dim_customer_unique_business_key():
    df = read_sql(
        "select customer_id, count(*) c from dwh.dim_customer group by 1 having count(*) > 1"
    )
    assert df.empty


def test_no_dangling_dim_date_in_facts():
    bad = read_sql("""
        select count(*) as n from dwh.fact_sales f
        where not exists (select 1 from dwh.dim_date d where d.date_id = f.sale_date_id)
    """).iloc[0]["n"]
    assert int(bad) == 0


def test_revenue_matches_between_staging_and_dwh():
    # staging ya recomputa los 8 subtotales inconsistentes detectados en raw,
    # así que comparamos DWH frente a staging (su fuente real).
    stg = read_sql("select sum(subtotal) as v from staging.sale_item").iloc[0]["v"]
    dwh = read_sql("select sum(subtotal) as v from dwh.fact_sales").iloc[0]["v"]
    assert abs(float(stg) - float(dwh)) < 0.01
