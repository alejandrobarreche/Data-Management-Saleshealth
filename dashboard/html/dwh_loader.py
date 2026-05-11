"""Acceso al DWH para el build del dashboard HTML.

Reproduce las funciones de dashboard/data_access.py sin la dependencia de
Streamlit (cache, st.session_state). Se ejecuta en build time —
los DataFrames resultantes se inyectan en las vistas.

`probe_postgres()` decide si seguimos en modo online o caemos a OFFLINE.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def probe_postgres() -> bool:
    """¿Postgres responde y el DWH tiene datos?"""
    try:
        from src.db.engine import read_sql
        n = read_sql("select count(*) as n from dwh.fact_sales").iloc[0]["n"]
        return int(n) > 0
    except Exception:
        return False


def _read(sql: str, **params) -> pd.DataFrame:
    from src.db.engine import read_sql
    return read_sql(sql, **params)


# ── Filter options + KPIs base ───────────────────────────────────────────────
def load_filter_options() -> dict:
    dates = _read("""
        select min(d.full_date) as min_d, max(d.full_date) as max_d
        from dwh.fact_sales f
        join dwh.dim_date d on d.date_id = f.sale_date_id
    """).iloc[0]
    return {
        "min_date": pd.to_datetime(dates["min_d"]).date(),
        "max_date": pd.to_datetime(dates["max_d"]).date(),
    }


def _date_range_default() -> tuple:
    """Por defecto: desde el 1-ene del año más reciente del DWH hasta max_date."""
    opts = load_filter_options()
    return (pd.Timestamp(year=opts["max_date"].year, month=1, day=1).date(),
            opts["max_date"])


def _prev_window(date_from, date_to) -> tuple:
    n = (pd.Timestamp(date_to) - pd.Timestamp(date_from)).days
    new_to = pd.Timestamp(date_from) - pd.Timedelta(days=1)
    new_from = new_to - pd.Timedelta(days=n)
    return new_from.date(), new_to.date()


def load_kpis(date_from, date_to) -> dict:
    sql = """
        with sales as (
            select f.*
            from dwh.fact_sales f
            join dwh.dim_date d on d.date_id = f.sale_date_id
            where d.full_date between :df and :dt
        ),
        ret as (
            select coalesce(sum(r.returned_value), 0)::float as v
            from dwh.fact_returns r
            join dwh.dim_date d on d.date_id = r.return_date_id
            where d.full_date between :df and :dt
        )
        select count(distinct s.sale_id)              as tickets,
               count(*)                               as line_items,
               coalesce(sum(s.subtotal), 0)::float    as gross_revenue,
               coalesce(sum(s.margin), 0)::float      as total_margin,
               coalesce(sum(s.quantity), 0)::int      as units,
               count(distinct s.customer_sk)          as active_customers,
               (select v from ret)                    as returns_value
        from sales s
    """
    row = _read(sql, df=date_from, dt=date_to).iloc[0].to_dict()
    row["net_revenue"] = row["gross_revenue"] - row["returns_value"]
    row["aov"] = row["gross_revenue"] / row["tickets"] if row["tickets"] else 0.0
    row["margin_rate"] = (
        row["total_margin"] / row["gross_revenue"] if row["gross_revenue"] else 0.0
    )
    row["return_rate"] = (
        row["returns_value"] / row["gross_revenue"] if row["gross_revenue"] else 0.0
    )
    return row


# ── Series para Overview D/E/F/G/H ───────────────────────────────────────────
def load_daily_sales(date_from, date_to) -> pd.DataFrame:
    df = _read(
        """
        select d.full_date::date         as day,
               sum(f.subtotal)::float    as revenue,
               sum(f.margin)::float      as margin,
               count(distinct f.sale_id) as tickets
        from dwh.fact_sales f
        join dwh.dim_date d on d.date_id = f.sale_date_id
        where d.full_date between :df and :dt
        group by 1 order by 1
        """,
        df=date_from, dt=date_to,
    )
    if not df.empty:
        df["day"] = pd.to_datetime(df["day"])
        df["rev_ma7"] = df["revenue"].rolling(7, min_periods=1).mean()
    return df


def load_revenue_by_category(date_from, date_to) -> pd.DataFrame:
    return _read(
        """
        select coalesce(p.category, 'Sin categoría') as category,
               sum(f.subtotal)::float                as revenue,
               sum(f.margin)::float                  as margin,
               sum(f.quantity)::int                  as units
        from dwh.fact_sales f
        join dwh.dim_date    d on d.date_id    = f.sale_date_id
        join dwh.dim_product p on p.product_sk = f.product_sk
        where d.full_date between :df and :dt
        group by 1 order by revenue desc
        """,
        df=date_from, dt=date_to,
    )


def load_revenue_by_brand(date_from, date_to) -> pd.DataFrame:
    return _read(
        """
        select coalesce(p.brand, 'Sin marca')  as brand,
               coalesce(p.category, 's/c')     as category,
               sum(f.subtotal)::float          as revenue
        from dwh.fact_sales f
        join dwh.dim_date    d on d.date_id    = f.sale_date_id
        join dwh.dim_product p on p.product_sk = f.product_sk
        where d.full_date between :df and :dt
        group by 1, 2 order by revenue desc
        """,
        df=date_from, dt=date_to,
    )


def load_monthly_year(date_from, date_to) -> pd.DataFrame:
    return _read(
        """
        select d.year::int          as year,
               d.month::int         as month,
               sum(f.subtotal)::float as revenue
        from dwh.fact_sales f
        join dwh.dim_date d on d.date_id = f.sale_date_id
        where d.full_date between :df and :dt
        group by 1, 2 order by 1, 2
        """,
        df=date_from, dt=date_to,
    )


def load_top_stores(date_from, date_to) -> pd.DataFrame:
    return _read(
        """
        select s.name                       as store,
               s.city, s.area_type,
               sum(f.subtotal)::float       as revenue,
               sum(f.margin)::float         as margin,
               count(distinct f.sale_id)    as tickets,
               count(distinct f.customer_sk) as customers
        from dwh.fact_sales f
        join dwh.dim_date    d on d.date_id  = f.sale_date_id
        join dwh.dim_store   s on s.store_sk = f.store_sk
        where d.full_date between :df and :dt
        group by 1, 2, 3 order by revenue desc
        """,
        df=date_from, dt=date_to,
    )


# ── Productos ────────────────────────────────────────────────────────────────
def load_top_products(date_from, date_to, limit: int = 15) -> pd.DataFrame:
    return _read(
        f"""
        select p.name              as product,
               p.category, p.brand,
               sum(f.subtotal)::float as revenue,
               sum(f.quantity)::int   as units,
               sum(f.margin)::float   as margin
        from dwh.fact_sales f
        join dwh.dim_date    d on d.date_id    = f.sale_date_id
        join dwh.dim_product p on p.product_sk = f.product_sk
        where d.full_date between :df and :dt
        group by 1, 2, 3 order by revenue desc limit {int(limit)}
        """,
        df=date_from, dt=date_to,
    )


def load_returns_breakdown(date_from, date_to) -> pd.DataFrame:
    return _read(
        """
        select coalesce(rr.reason, 'Desconocido') as reason,
               sum(r.returned_value)::float       as value,
               sum(r.quantity)::int               as units
        from dwh.fact_returns r
        join dwh.dim_date d on d.date_id = r.return_date_id
        left join dwh.dim_return_reason rr on rr.reason_sk = r.reason_sk
        where d.full_date between :df and :dt
        group by 1 order by value desc
        """,
        df=date_from, dt=date_to,
    )


def load_returns_by_product(date_from, date_to, limit: int = 15) -> pd.DataFrame:
    return _read(
        f"""
        with rev_p as (
            select f.product_sk, sum(f.subtotal)::float as revenue
            from dwh.fact_sales f
            join dwh.dim_date d on d.date_id = f.sale_date_id
            where d.full_date between :df and :dt
            group by 1
        )
        select p.name                      as product,
               p.category,
               sum(r.returned_value)::float as value,
               sum(r.quantity)::int          as units,
               count(*)                      as n_returns,
               coalesce(rev.revenue, 0)::float as revenue,
               case when coalesce(rev.revenue, 0) > 0
                    then sum(r.returned_value)/rev.revenue
                    else null end             as ratio
        from dwh.fact_returns r
        join dwh.dim_date d on d.date_id    = r.return_date_id
        join dwh.dim_product p on p.product_sk = r.product_sk
        left join rev_p rev on rev.product_sk = r.product_sk
        where d.full_date between :df and :dt
        group by p.name, p.category, rev.revenue
        order by value desc limit {int(limit)}
        """,
        df=date_from, dt=date_to,
    )


# ── Inventory counts (verificación DWH) ──────────────────────────────────────
def load_inventory_counts() -> dict:
    counts = {}
    for tbl in ("dim_customer", "dim_product", "dim_store",
                "dim_date", "dim_return_reason", "fact_sales", "fact_returns"):
        try:
            counts[tbl] = int(_read(f"select count(*) as n from dwh.{tbl}").iloc[0]["n"])
        except Exception:
            counts[tbl] = 0
    return counts


def load_zero_cost_skus() -> list[str]:
    try:
        df = _read("""
            select name
            from dwh.dim_product
            where coalesce(unit_cost, 0) = 0
            order by name
        """)
        return df["name"].tolist()
    except Exception:
        return []


def load_default_period() -> tuple:
    return _date_range_default()
