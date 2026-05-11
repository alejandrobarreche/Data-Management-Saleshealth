"""Vista 01 · Visión General. Cuando el DWH está disponible (`offline=False`)
renderiza KPIs reales + las secciones D-H con datos diarios. En modo OFFLINE
cae a un derivado-de-parquets sin filtros.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .. import helpers as h
from .. import theme


# ── KPI block (online) ──────────────────────────────────────────────────────
_ES_MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
              "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _format_es_date(d) -> str:
    """`2024-01-03` → `'3 de enero de 2024'`."""
    d = pd.Timestamp(d)
    return f"{d.day} de {_ES_MONTHS[d.month - 1]} de {d.year}"


def _prev_window(period: tuple) -> tuple:
    """Misma lógica que `dwh_loader._prev_window` (replicada para no
    importar fuera de build time): los N días inmediatamente anteriores."""
    p0 = pd.Timestamp(period[0])
    p1 = pd.Timestamp(period[1])
    n = (p1 - p0).days
    new_to = p0 - pd.Timedelta(days=1)
    new_from = new_to - pd.Timedelta(days=n)
    return new_from.date(), new_to.date()


def _is_full_year_window(period: tuple) -> bool:
    """¿La ventana actual es un año natural (empieza el 1 de enero)?"""
    if not period:
        return False
    p0 = pd.Timestamp(period[0])
    p1 = pd.Timestamp(period[1])
    return p0.month == 1 and p0.day == 1 and p0.year == p1.year


def _delta_label(period: tuple | None) -> str:
    """Etiqueta corta para los deltas. Si la ventana es un año natural,
    devuelve `'vs 2024'` (el anterior). Si no, fallback descriptivo."""
    if period and _is_full_year_window(period):
        return f"vs {pd.Timestamp(period[0]).year - 1}"
    return "vs periodo previo"


def _delta_explanation_html(period: tuple | None) -> str:
    """Línea explicativa que aparece debajo del bloque KPI."""
    if not period:
        return ""
    p0 = pd.Timestamp(period[0])
    p1 = pd.Timestamp(period[1])
    n_days = (p1 - p0).days + 1
    pv_from, pv_to = _prev_window(period)
    if _is_full_year_window(period):
        return (
            f"Las variaciones (↑↓) comparan los <strong>{n_days}&nbsp;días</strong> de "
            f"<strong>{p0.year}</strong> contra los mismos {n_days} días anteriores: "
            f"<strong>{_format_es_date(pv_from)}</strong> a "
            f"<strong>{_format_es_date(pv_to)}</strong>."
        )
    return (
        f"Las variaciones (↑↓) comparan los <strong>{n_days}&nbsp;días</strong> "
        f"de <strong>{_format_es_date(p0)}</strong> a <strong>{_format_es_date(p1)}</strong> "
        f"contra los mismos {n_days} días anteriores: "
        f"<strong>{_format_es_date(pv_from)}</strong> a "
        f"<strong>{_format_es_date(pv_to)}</strong>."
    )


def _delta_dir(curr: float, prev: float, *, lower_better: bool = False,
               flat_label: str = "≈ periodo previo") -> tuple[str, str]:
    if not prev:
        return "—", "flat"
    pct = (curr - prev) / prev
    if abs(pct) < 0.01:
        return flat_label, "flat"
    direction = ("up" if pct > 0 else "down")
    if lower_better:
        direction = "down" if direction == "up" else "up"
    return f"{pct*100:+.1f}%", direction


def _kpis_online(curr: dict, prev: dict, period: tuple | None = None) -> str:
    """Hero (Ingresos netos + breakdown) + 4 cards (Clientes / Tickets / Ticket medio / Unidades)."""
    delta_lbl = _delta_label(period)
    flat_lbl = "≈ " + delta_lbl[3:] if delta_lbl.startswith("vs ") else "≈ periodo previo"
    net = curr.get("net_revenue", 0) or 0
    gross = curr.get("gross_revenue", 0) or 0
    returns_value = curr.get("returns_value", 0) or 0
    return_rate = curr.get("return_rate", 0) or 0
    margin_rate = curr.get("margin_rate", 0) or 0

    delta_txt, delta_dir = _delta_dir(net, prev.get("net_revenue", 0) or 0, flat_label=flat_lbl)

    hero = h.kpi_hero(
        label="Ingresos netos",
        value=theme.fmt_money(net, short=True),
        delta=delta_txt, delta_dir=delta_dir,
        delta_label=delta_lbl,
        breakdown=[
            ("Bruto",     theme.fmt_money(gross, short=True)),
            ("Devuelto",  f"{theme.fmt_money(returns_value, short=True)} · {theme.fmt_pct(return_rate)}"),
            ("Margen",    theme.fmt_pct(margin_rate)),
        ],
        src="dwh.fact_sales − fact_returns",
    )

    # 4 cards de apoyo — volumen y ticket medio
    pairs = [
        ("Clientes activos", "active_customers", "int",   "dim_customer"),
        ("Tickets",          "tickets",          "int",   "fact_sales"),
        ("Ticket medio",     "aov",              "money", "derived"),
        ("Unidades",         "units",            "int",   "fact_sales"),
    ]
    cards = []
    for label, key, fmt, src in pairs:
        v = curr.get(key, 0) or 0
        if fmt == "money":
            value_str = theme.fmt_money(v, short=True)
        else:
            value_str = f"{int(v):,}".replace(",", " ")
        d_txt, d_dir = _delta_dir(v, prev.get(key, 0) or 0, flat_label=flat_lbl)
        cards.append(h.kpi_card(label, value_str, delta=d_txt, delta_dir=d_dir,
                                delta_label=delta_lbl, src=src))
    return hero + h.grid(cards, cols=4)


# ── KPI block (offline, derivado de parquets) ───────────────────────────────
def _kpis_offline(cltv: pd.DataFrame, cm: pd.DataFrame) -> str:
    n_cust = len(cm)
    gross = float(cltv["gross_revenue"].sum())
    net   = float(cltv["net_revenue"].sum())
    margin_total = float((cltv["gross_revenue"] - cltv["total_cost"]).sum())
    returns_value = gross - net
    return_rate = (returns_value / gross) if gross else 0
    margin_rate = (margin_total / gross) if gross else 0
    aov = (cm["gross_revenue"].sum() / cm["frequency"].sum()) if cm["frequency"].sum() else 0
    tickets_total = int(cm["frequency"].sum())

    hero = h.kpi_hero(
        label="Ingresos netos · acumulado del estudio",
        value=theme.fmt_money(net, short=True),
        breakdown=[
            ("Bruto",    theme.fmt_money(gross, short=True)),
            ("Devuelto", f"{theme.fmt_money(returns_value, short=True)} · {theme.fmt_pct(return_rate)}"),
            ("Margen",   theme.fmt_pct(margin_rate)),
        ],
        src="cltv.parquet",
    )

    cards = [
        h.kpi_card("Clientes", f"{n_cust:,}".replace(",", " "),
                   delta="con CLTV calculado", delta_dir="flat", src="customer_metrics"),
        h.kpi_card("Tickets", f"{tickets_total:,}".replace(",", " "),
                   delta="Σ frequency", delta_dir="flat", src="customer_metrics"),
        h.kpi_card("Ticket medio", theme.fmt_money(aov, short=True),
                   delta="rev / tickets", delta_dir="flat", src="customer_metrics"),
        h.kpi_card("Tickets/cliente", f"{tickets_total / n_cust:.1f}".replace(".", ","),
                   delta="frequency mean", delta_dir="flat", src="customer_metrics"),
    ]
    return hero + h.grid(cards, cols=4)


def _inventory_grid(cltv, cm, seg, dwh_counts: Optional[dict] = None) -> str:
    """Online: diagrama del modelo en estrella inline. Offline: inv_groups."""
    if dwh_counts:
        return h.schema_diagram(
            dim_customer=dwh_counts.get("dim_customer", 0),
            dim_product=dwh_counts.get("dim_product", 0),
            dim_store=dwh_counts.get("dim_store", 0),
            dim_date=dwh_counts.get("dim_date", 0),
            fact_sales=dwh_counts.get("fact_sales", 0),
            fact_returns=dwh_counts.get("fact_returns", 0),
            mart_cltv=len(cltv),
            mart_segments=len(seg),
        )
    else:
        # Modo OFFLINE: lo que hay en parquet + metadatos del modelo
        win_months = int(cltv["window_months"].iloc[0]) if "window_months" in cltv else 72
        freq_mean = float(cm["frequency"].mean())
        groups = [
            ("Datos", [
                (len(cm),   "clientes"),
                (len(cltv), "CLTV calculados"),
                (len(seg),  "clientes segmentados"),
            ]),
            ("Modelo", [
                (int(seg["cluster"].nunique()), "clusters"),
                (2, "componentes PCA"),
                (8, "features estandarizadas"),
            ]),
            ("Estadísticos", [
                (win_months, "meses de ventana"),
                (f"{freq_mean:.1f}".replace(".", ","), "compras por cliente (media)"),
            ]),
        ]
    return h.inv_groups(groups)


# ── Sección D · Evolución diaria ────────────────────────────────────────────
def _evolution_chart(daily: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["day"], y=daily["revenue"], mode="lines",
        line=dict(color=theme.PRIMARY_LIGHT, width=1),
        opacity=0.45, fill="tozeroy", fillcolor="rgba(37,99,235,0.06)",
        name="Diario",
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Bruto: %{y:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["day"], y=daily["rev_ma7"], mode="lines",
        line=dict(color=theme.PRIMARY, width=2),
        name="Media móvil 7d",
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>MA7: %{y:,.0f} €<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=340, hovermode="x unified")
    fig.update_layout(yaxis_title="Ingresos (€)", xaxis_title="",
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    return fig


# ── Sección E · Ingresos por categoría ──────────────────────────────────────
def _category_chart(cat: pd.DataFrame) -> go.Figure:
    df = cat.copy()
    df["margin_rate"] = df["margin"] / df["revenue"].replace(0, np.nan)
    df = df.sort_values("revenue", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["revenue"], y=df["category"], orientation="h",
        marker=dict(
            color=df["margin_rate"], colorscale=theme.SEQ_BLUE,
            cmin=df["margin_rate"].min(), cmax=df["margin_rate"].max(),
            colorbar=dict(title="Margen", thickness=10, len=0.7, tickformat=".0%", tickfont=dict(size=10)),
        ),
        text=[theme.fmt_money(v, short=True) for v in df["revenue"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Ingresos: %{x:,.0f} €<br>Margen: %{marker.color:.1%}<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=340, hovermode="closest")
    fig.update_layout(xaxis_title="Ingresos (€)", yaxis_title="", showlegend=False,
                      margin=dict(l=10, r=60, t=20, b=40))
    return fig


# ── Sección F · Treemap categoría → marca ───────────────────────────────────
def _brand_treemap(brand: pd.DataFrame) -> go.Figure:
    df = brand[brand["revenue"] > 0].copy()
    fig = px.treemap(df, path=["category", "brand"], values="revenue",
                     color="revenue", color_continuous_scale=theme.SEQ_BLUE,
                     hover_data={"revenue": ":,.0f"})
    theme.apply_chart(fig, title=" ", height=380, hovermode="closest")
    fig.update_traces(textinfo="label+value", texttemplate="%{label}<br>%{value:,.0f} €",
                      hovertemplate="<b>%{label}</b><br>Ingresos: %{value:,.0f} €<extra></extra>")
    fig.update_layout(coloraxis_showscale=False, margin=dict(l=4, r=4, t=10, b=4))
    return fig


# ── Sección G · Heatmap mes × año ──────────────────────────────────────────
def _seasonality_heatmap(monthly: pd.DataFrame) -> go.Figure:
    pivot = monthly.pivot_table(index="year", columns="month", values="revenue", aggfunc="sum")
    pivot = pivot.reindex(columns=range(1, 13))
    months_lbl = ["01","02","03","04","05","06","07","08","09","10","11","12"]
    z = pivot.values
    text = [[(theme.fmt_money(v, short=True) if pd.notna(v) else "—") for v in row] for row in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=months_lbl, y=[str(y) for y in pivot.index],
        colorscale=theme.SEQ_BLUE,
        colorbar=dict(title="€", thickness=10, len=0.7, tickfont=dict(size=10)),
        text=text, texttemplate="%{text}", textfont=dict(size=10, color=theme.INK),
        hovertemplate="Año %{y} · Mes %{x}<br>Ingresos: %{z:,.0f} €<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=320, hovermode="closest")
    fig.update_layout(yaxis_title="", xaxis_title="Mes", margin=dict(l=20, r=20, t=20, b=40))
    return fig


# ── Sección H · Top tiendas ────────────────────────────────────────────────
def _top_stores_chart(stores: pd.DataFrame) -> go.Figure:
    df = stores.head(10).copy()
    df["margin_rate"] = df["margin"] / df["revenue"].replace(0, np.nan)
    df = df.sort_values("revenue", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["revenue"], y=df["store"], orientation="h",
        marker=dict(
            color=df["margin_rate"], colorscale=theme.SEQ_BLUE,
            cmin=df["margin_rate"].min(), cmax=df["margin_rate"].max(),
            colorbar=dict(title="Margen", thickness=10, len=0.7, tickformat=".0%", tickfont=dict(size=10)),
        ),
        customdata=np.stack([df["city"], df["tickets"], df["customers"], df["margin_rate"]], axis=1),
        text=[theme.fmt_money(v, short=True) for v in df["revenue"]],
        textposition="outside",
        hovertemplate=("<b>%{y}</b> · %{customdata[0]}<br>"
                       "Ingresos: %{x:,.0f} €<br>"
                       "Tickets: %{customdata[1]:,}<br>"
                       "Clientes: %{customdata[2]:,}<br>"
                       "Margen: %{customdata[3]:.1%}<extra></extra>"),
    ))
    theme.apply_chart(fig, title=" ", height=380, hovermode="closest")
    fig.update_layout(xaxis_title="Ingresos (€)", yaxis_title="", showlegend=False,
                      margin=dict(l=10, r=60, t=20, b=40))
    return fig


# ── render principal ────────────────────────────────────────────────────────
def render(
    cltv: pd.DataFrame,
    cm: pd.DataFrame,
    seg: pd.DataFrame,
    *,
    offline: bool = True,
    kpis: Optional[dict] = None,
    kpis_prev: Optional[dict] = None,
    period: Optional[tuple] = None,
    daily: Optional[pd.DataFrame] = None,
    by_category: Optional[pd.DataFrame] = None,
    by_brand: Optional[pd.DataFrame] = None,
    monthly: Optional[pd.DataFrame] = None,
    top_stores: Optional[pd.DataFrame] = None,
    dwh_counts: Optional[dict] = None,
) -> str:
    parts: list[str] = []

    if offline:
        parts.append(h.chapter_opener(
            marker="Capítulo I",
            eyebrow="I · VISIÓN GENERAL",
            headline="Visión general.",
            deck=(
                "Postgres no responde — series temporales y agregados por categoría/tienda "
                "quedan fuera de alcance. KPIs derivados de los parquets a continuación."
            ),
            analytics="descriptive",
        ))
        parts.append(h.offline_banner(
            "Modo OFFLINE — Postgres no disponible. KPIs y secciones de evolución (D–H) en placeholder honesto. "
            "Las KPIs se derivan de los parquets, así que cubren el agregado total pero no permiten filtros por periodo, categoría o ciudad."
        ))
        parts.append(h.section_h("A", "Indicadores principales", "derivados de parquets"))
        parts.append(_kpis_offline(cltv, cm))
        parts.append(h.section_h("B", "Inventario verificado", "parquets + joblibs"))
        parts.append(_inventory_grid(cltv, cm, seg))
        parts.append(h.explain("Pone a la vista que «lo que ves» coincide con «lo que hay en disco». Es la prueba de vida de los artefactos del modelo."))
        parts.append(h.section_h("D–H", "Series temporales y agregados", "requieren DWH"))
        parts.append(h.alert_info(
            "<strong>Estas secciones requieren conexión a Postgres.</strong> Cuando el DWH está disponible, "
            "esta zona contiene: <strong>D</strong> evolución diaria de ingresos + media móvil; "
            "<strong>E</strong> ingresos por categoría con color por margen; <strong>F</strong> treemap "
            "categoría → marca; <strong>G</strong> heatmap mes × año; <strong>H</strong> top 10 tiendas."
        ))
        return '<section id="view-overview" class="view">' + "".join(parts) + "</section>"

    # ── ONLINE ──
    period_str = f"{period[0]:%Y-%m-%d} → {period[1]:%Y-%m-%d}" if period else ""

    parts.append(h.chapter_opener(
        marker="Capítulo I",
        eyebrow="I · VISIÓN GENERAL",
        headline="Visión general.",
        deck=(
            f"Ventana <strong>{period_str}</strong>. Indicadores principales del periodo, "
            "inventario del DWH y series temporales — ritmo diario, mezcla por categoría, "
            "estacionalidad y top de tiendas."
        ),
        analytics="descriptive",
    ))

    parts.append(h.section_h("A", "Indicadores del periodo", period_str))
    parts.append(_kpis_online(kpis or {}, kpis_prev or {}, period=period))
    parts.append(f'<p class="kpi-explainer">{_delta_explanation_html(period)}</p>')

    parts.append(h.section_h("B", "Inventario verificado del DWH"))
    parts.append(_inventory_grid(cltv, cm, seg, dwh_counts=dwh_counts))
    parts.append(h.explain("Counts en vivo de las tablas dwh.* + martz parquet. Es la prueba de vida del DWH."))

    parts.append(h.section_h("D", "Evolución de ingresos", "diario + MA7"))
    parts.append(h.card(body_html=h.fig_html(_evolution_chart(daily), frame=False) +
                        h.explain("La serie diaria es ruidosa; la MA7 deja ver tendencia y estacionalidad semanal. Mostrar ambas evita que el lector se quede sólo con la suavizada.")))

    parts.append(h.section_h("E", "Ingresos por categoría", "color = margen"))
    parts.append(h.card(body_html=h.fig_html(_category_chart(by_category), frame=False) +
                        h.explain("Mezcla volumen (longitud) con rentabilidad. Permite ver qué categorías son grandes pero «tóxicas».")))

    parts.append(h.section_h("F", "Mix por marca (treemap)", "categoría → marca"))
    parts.append(h.card(body_html=h.fig_html(_brand_treemap(by_brand), frame=False) +
                        h.explain("Jerarquía visual sin ocupar mucho espacio. Los rectángulos pequeños son intencionalmente difíciles de leer — el objetivo es ver concentración, no marcas individuales.")))

    parts.append(h.section_h("G", "Estacionalidad", "mes × año"))
    parts.append(h.card(body_html=h.fig_html(_seasonality_heatmap(monthly), frame=False) +
                        h.explain("Vista clásica: combina detección de tendencia año-a-año y patrones intra-anuales en un único gráfico.")))

    parts.append(h.section_h("H", "Top 10 tiendas", "color = margen"))
    parts.append(h.card(body_html=h.fig_html(_top_stores_chart(top_stores), frame=False) +
                        h.explain("Detecta tiendas que son «máquinas de ingresos sin margen» o pequeñas pero muy rentables. Usa la misma escala de color que la sección E para coherencia.")))

    return '<section id="view-overview" class="view">' + "".join(parts) + "</section>"
