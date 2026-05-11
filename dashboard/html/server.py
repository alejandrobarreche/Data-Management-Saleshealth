"""Backend Flask para la ficha de cliente en vivo.

Arrancar:
    conda run -n UAX python -m dashboard.html.server

Por defecto en http://localhost:8001 — sirve el index.html y los endpoints:

    GET /                              → index.html (dashboard estático)
    GET /style.css                     → CSS
    GET /api/customers/search?q=...    → lista filtrada (búsqueda + filtros)
    GET /api/customer/<customer_id>    → ficha completa (incluye timeline DWH)
    GET /api/health                    → ping
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent

FEATURE_COLS = [
    "net_revenue", "margin_rate", "frequency", "retention_rate",
    "aov", "recency_days", "return_rate", "cltv",
]

app = Flask(__name__, static_folder=None)


# ── Cargas perezosas (singleton) ───────────────────────────────────────────
_segments: pd.DataFrame | None = None
_models: dict | None = None


def _load_segments() -> pd.DataFrame:
    global _segments
    if _segments is None:
        df = pd.read_parquet(ROOT / "models" / "customer_segments.parquet")
        # Asegura tipos serializables
        for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        df = df.replace({np.nan: None})
        _segments = df
    return _segments


def _load_models() -> dict:
    global _models
    if _models is None:
        import joblib
        _models = {
            "scaler": joblib.load(ROOT / "models" / "scaler.joblib"),
            "pca":    joblib.load(ROOT / "models" / "pca.joblib"),
            "kmeans": joblib.load(ROOT / "models" / "kmeans.joblib"),
        }
    return _models


def _row_to_dict(row: pd.Series) -> dict:
    """Limpia NaN para JSON."""
    out = row.to_dict()
    for k, v in out.items():
        if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
            out[k] = None
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.floating,)):
            out[k] = float(v)
    return out


# ── Static (sirve los archivos del propio dashboard) ───────────────────────
@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    target = HERE / filename
    if target.is_file():
        return send_from_directory(HERE, filename)
    return ("not found", 404)


# ── API ────────────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    df = _load_segments()
    try:
        from src.db.engine import read_sql
        n = read_sql("select count(*) as n from dwh.fact_sales").iloc[0]["n"]
        dwh_ok = int(n) > 0
    except Exception:
        dwh_ok = False
    return jsonify({"ok": True, "n_customers": len(df), "dwh": dwh_ok})


@app.route("/api/customers/search")
def search_customers():
    """Búsqueda + filtros sobre el parquet de segmentos.

    Query params:
        q             — texto libre (busca en full_name e ID)
        cluster       — entero 0/1/2 (filtra)
        cltv_min      — float (≥)
        cltv_max      — float (≤)
        freq_min      — int (≥)
        freq_max      — int (≤)
        sort          — 'cltv' (default) | 'recency' | 'frequency' | 'name'
        order         — 'desc' (default) | 'asc'
        limit         — int, default 60
    """
    df = _load_segments().copy()
    q = (request.args.get("q") or "").strip().lower()
    if q:
        mask_name = df["full_name"].fillna("").str.lower().str.contains(q, na=False)
        mask_id = df["customer_id"].astype(str).str.contains(q, na=False)
        df = df[mask_name | mask_id]

    if (cluster := request.args.get("cluster")) not in (None, ""):
        try:
            df = df[df["cluster"] == int(cluster)]
        except ValueError:
            pass

    for arg, col, op in [
        ("cltv_min", "cltv", "ge"),
        ("cltv_max", "cltv", "le"),
        ("freq_min", "frequency", "ge"),
        ("freq_max", "frequency", "le"),
    ]:
        v = request.args.get(arg)
        if v not in (None, ""):
            try:
                v_num = float(v)
                df = df[df[col] >= v_num] if op == "ge" else df[df[col] <= v_num]
            except ValueError:
                pass

    sort_col = {"cltv": "cltv", "recency": "recency_days",
                "frequency": "frequency", "name": "full_name"}.get(
        request.args.get("sort", "cltv"), "cltv"
    )
    asc = request.args.get("order", "desc") == "asc"
    df = df.sort_values(sort_col, ascending=asc, na_position="last")

    total = len(df)
    try:
        limit = max(1, min(int(request.args.get("limit", 60)), 500))
    except ValueError:
        limit = 60

    keep_cols = ["customer_id", "customer_sk", "full_name", "cluster",
                 "cltv", "frequency", "recency_days", "last_purchase"]
    out = df.head(limit)[keep_cols].apply(_row_to_dict, axis=1).tolist()
    return jsonify({"total": total, "showing": len(out), "results": out})


@app.route("/api/customer/<int:customer_id>")
def get_customer(customer_id: int):
    """Ficha completa: header + comparativas + timeline de compras (DWH si disponible)."""
    df = _load_segments()
    match = df[df["customer_id"] == customer_id]
    if match.empty:
        return jsonify({"error": "customer not found"}), 404
    row = match.iloc[0]
    customer = _row_to_dict(row)

    # Comparativas: medianas globales y de su cluster
    global_med = df.median(numeric_only=True)
    cluster_med = df[df["cluster"] == row["cluster"]].median(numeric_only=True)

    # Rankings percentiles (para el radar)
    radar_axes = [
        ("cltv",           False, "CLTV"),
        ("aov",            False, "AOV"),
        ("frequency",      False, "Frecuencia"),
        ("retention_rate", False, "Retención"),
        ("margin_rate",    False, "Margen"),
        ("recency_days",   True,  "Recencia⁻¹"),
    ]
    radar = []
    for col, invert, label in radar_axes:
        if col not in df.columns:
            continue
        ranks = df[col].rank(pct=True, method="average")
        if invert:
            ranks = 1 - ranks
        # cliente
        idx = match.index[0]
        client_v = float(ranks.loc[idx]) if idx in ranks.index else 0.5
        # cluster
        c_med_v = cluster_med.get(col, df[col].median())
        cluster_v = float(ranks[df[col] <= c_med_v].max()) if (df[col] <= c_med_v).any() else 0.5
        g_med_v = global_med.get(col, df[col].median())
        global_v = float(ranks[df[col] <= g_med_v].max()) if (df[col] <= g_med_v).any() else 0.5
        radar.append({"axis": label, "client": client_v, "cluster": cluster_v, "global": global_v})

    # Timeline desde DWH si Postgres está disponible
    timeline = []
    try:
        from src.db.engine import read_sql
        rows = read_sql(
            """
            select d.full_date::date as fecha,
                   coalesce(s.name, 'tienda?') as tienda,
                   coalesce(s.city, '—') as ciudad,
                   coalesce(p.name, 'producto?') as producto,
                   coalesce(p.category, 'sin categoría') as categoria,
                   f.quantity as cantidad,
                   f.subtotal::float as ingresos,
                   f.margin::float as margen
            from dwh.fact_sales f
            join dwh.dim_date d on d.date_id = f.sale_date_id
            left join dwh.dim_product p on p.product_sk = f.product_sk
            left join dwh.dim_store   s on s.store_sk   = f.store_sk
            where f.customer_sk = :csk
            order by d.full_date asc
            """,
            csk=int(row["customer_sk"]),
        )
        rows["fecha"] = pd.to_datetime(rows["fecha"]).dt.strftime("%Y-%m-%d")
        timeline = rows.replace({np.nan: None}).to_dict(orient="records")
    except Exception as exc:
        timeline = []
        app.logger.warning("DWH offline para timeline cliente %s: %s", customer_id, exc)

    payload = {
        "customer": customer,
        "comparison": {
            "cluster_median": _row_to_dict(cluster_med),
            "global_median":  _row_to_dict(global_med),
        },
        "radar": radar,
        "timeline": timeline,
        "timeline_available": len(timeline) > 0,
    }
    return jsonify(payload)


# ── Cluster: drill-down (B) ────────────────────────────────────────────────
@app.route("/api/cluster/<int:cluster_id>")
def get_cluster(cluster_id: int):
    df = _load_segments()
    if cluster_id not in df["cluster"].unique():
        return jsonify({"error": "cluster not found"}), 404
    sub = df[df["cluster"] == cluster_id]

    # Perfil estadístico — quantiles por feature + global p50 para comparar
    profile = {}
    for col in FEATURE_COLS:
        profile[col] = {
            "p10": float(sub[col].quantile(0.10)),
            "p25": float(sub[col].quantile(0.25)),
            "p50": float(sub[col].quantile(0.50)),
            "p75": float(sub[col].quantile(0.75)),
            "p90": float(sub[col].quantile(0.90)),
            "global_p50": float(df[col].quantile(0.50)),
        }

    # Top clientes por CLTV
    keep = ["customer_id", "customer_sk", "full_name", "cltv",
            "frequency", "recency_days", "return_rate"]
    top_customers = (
        sub.sort_values("cltv", ascending=False)
        .head(10)[keep]
        .apply(_row_to_dict, axis=1).tolist()
    )

    # Top productos consumidos por este cluster (DWH si disponible)
    top_products = []
    try:
        from src.db.engine import read_sql
        sks = [int(x) for x in sub["customer_sk"].tolist()]
        rows = read_sql(
            """
            select coalesce(p.name, 'producto?') as producto,
                   coalesce(p.category, '—')    as categoria,
                   sum(f.subtotal)::float       as ingresos,
                   sum(f.quantity)::int         as unidades,
                   count(distinct f.customer_sk) as compradores
            from dwh.fact_sales f
            join dwh.dim_product p on p.product_sk = f.product_sk
            where f.customer_sk = any(:sks)
            group by 1, 2
            order by ingresos desc limit 10
            """,
            sks=sks,
        )
        top_products = rows.replace({np.nan: None}).to_dict(orient="records")
    except Exception as exc:
        app.logger.warning("Top productos cluster %s no disponible: %s", cluster_id, exc)

    return jsonify({
        "cluster": cluster_id,
        "size": int(len(sub)),
        "share":      float(len(sub) / len(df)) if len(df) else 0.0,
        "cltv_share": float(sub["cltv"].sum() / df["cltv"].sum()) if df["cltv"].sum() else 0.0,
        "profile": profile,
        "top_customers": top_customers,
        "top_products": top_products,
    })


# ── Cluster predict — simulador (F) ────────────────────────────────────────
@app.route("/api/cluster/predict")
def predict_cluster():
    """GET con query params para cada feature. Devuelve cluster + coords PCA + distancias."""
    feats = []
    for col in FEATURE_COLS:
        try:
            feats.append(float(request.args.get(col, 0)))
        except ValueError:
            feats.append(0.0)
    m = _load_models()
    X = np.array([feats], dtype=float)
    Xs = m["scaler"].transform(X)
    Xp = m["pca"].transform(Xs)
    cluster = int(m["kmeans"].predict(Xp)[0])
    centers = m["kmeans"].cluster_centers_
    distances = np.linalg.norm(centers - Xp, axis=1)
    return jsonify({
        "cluster": cluster,
        "pc1": float(Xp[0, 0]),
        "pc2": float(Xp[0, 1]),
        "distances": [float(d) for d in distances],
    })


# ── Slider ranges para el simulador (calculados desde data real) ──────────
@app.route("/api/cluster/feature_ranges")
def feature_ranges():
    df = _load_segments()
    out = {}
    for col in FEATURE_COLS:
        s = df[col].dropna()
        out[col] = {
            "min": float(s.quantile(0.01)),
            "max": float(s.quantile(0.99)),
            "median": float(s.median()),
        }
    return jsonify(out)


# ── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8001)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()

    print(f"[server] http://{args.host}:{args.port}")
    print("[server] /api/customers/search · /api/customer/<id>")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
