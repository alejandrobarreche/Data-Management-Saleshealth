"""Vista 06 · Metodología & trazabilidad."""
from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .. import helpers as h
from .. import theme


KPI_MAP = [
    ("Ingresos netos",     "gross_revenue − returns_value",            "dwh.fact_sales / fact_returns",  "—"),
    ("CLTV",               "net_revenue × margin × frequency × retention", "(notebook 03)",                "cltv.parquet"),
    ("Tasa devolución",    "returns_value / gross_revenue",            "dwh.fact_returns / fact_sales",   "—"),
    ("AOV",                "gross_revenue / tickets",                  "dwh.fact_sales",                  "customer_metrics.parquet"),
    ("Cluster",            "KMeans(k=3) sobre PCA(2)",                 "models/customer_segments.parquet", "—"),
    ("Recencia",           "max(today) − last_purchase",               "dwh.fact_sales",                  "customer_metrics.parquet"),
    ("Margen bruto",       "Σ margin / Σ subtotal",                    "dwh.fact_sales (margin = subtotal − cost)", "—"),
    ("Frecuencia",         "count(distinct sale_id) por cliente",       "dwh.fact_sales",                  "cltv.parquet"),
    ("Retención",          "active_months / window_months",            "(notebook 03)",                   "cltv.parquet"),
    ("PC1 / PC2",          "PCA(2) sobre 8 features estandarizadas",   "models/pca.joblib",               "models/customer_segments.parquet"),
]


FEATURES = [
    ("net_revenue",     "Ingresos netos por cliente — escala monetaria base."),
    ("margin_rate",     "Margen relativo — separa volumen de rentabilidad."),
    ("frequency",       "Recompra — tickets distintos del cliente."),
    ("retention_rate",  "Retención — meses activos sobre ventana total."),
    ("aov",             "Ticket medio — rev / nº tickets."),
    ("recency_days",    "Recencia — días desde la última compra."),
    ("return_rate",     "Tasa devolución — fricción del cliente."),
    ("cltv",            "CLTV calculado — el output también entra como feature de estabilidad."),
]


def _elbow(elbow: dict[int, float]) -> go.Figure:
    ks = sorted(elbow.keys())
    vals = [elbow[k] for k in ks]
    colors = [theme.PRIMARY if k == 3 else theme.INK_SOFT for k in ks]
    sizes = [12 if k == 3 else 7 for k in ks]
    fig = go.Figure(go.Scatter(
        x=ks, y=vals, mode="lines+markers",
        line=dict(color=theme.INK_SOFT, width=2),
        marker=dict(color=colors, size=sizes, line=dict(color="#fff", width=1)),
        hovertemplate="k=%{x}<br>inertia=%{y:,.1f}<extra></extra>",
        name="inertia",
    ))
    fig.add_vline(x=3, line_dash="dash", line_color=theme.PRIMARY,
                  annotation_text="k = 3 elegida", annotation_position="top",
                  annotation_font_color=theme.PRIMARY)
    theme.apply_chart(fig, title=" ", height=320, hovermode="closest")
    fig.update_layout(xaxis_title="k (clusters)", yaxis_title="inertia",
                      xaxis=dict(tickmode="linear"), showlegend=False)
    return fig


def _pca_bar(pca_explained: list[float]) -> go.Figure:
    pcs = ["PC1", "PC2"]
    vals = pca_explained[:2]
    fig = go.Figure(go.Bar(
        x=pcs, y=[v * 100 for v in vals],
        marker=dict(color=[theme.PRIMARY, theme.PRIMARY_LIGHT]),
        text=[f"{v*100:.1f}%" for v in vals], textposition="outside",
        hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dash", line_color=theme.WARNING,
                  annotation_text="objetivo 80%", annotation_position="right",
                  annotation_font_color=theme.WARNING)
    theme.apply_chart(fig, title=" ", height=300, hovermode="closest")
    fig.update_layout(yaxis_title="% varianza explicada",
                      yaxis_range=[0, 100], showlegend=False)
    return fig


def _kpi_map_table() -> str:
    body = []
    for label, formula, source, intermediate in KPI_MAP:
        body.append(
            f"<tr>"
            f"<td><strong>{_html.escape(label)}</strong></td>"
            f"<td class='mono'>{_html.escape(formula)}</td>"
            f"<td class='mono'>{_html.escape(source)}</td>"
            f"<td class='mono'>{_html.escape(intermediate)}</td>"
            f"</tr>"
        )
    return (
        f'<div class="tbl-wrap"><table class="tbl">'
        f'<thead><tr><th>KPI</th><th>Fórmula</th><th>Origen DWH</th><th>Parquet intermediario</th></tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


def _features_list() -> str:
    items = []
    for i, (name, why) in enumerate(FEATURES, 1):
        items.append(
            f"<li><span class='n'>{i:02d}</span><span class='name'>{_html.escape(name)}</span>"
            f"<span class='why'>{_html.escape(why)}</span></li>"
        )
    return f'<ul class="feat-list">{"".join(items)}</ul>'


def _limitations(df: pd.DataFrame, pca_explained: list[float]) -> str:
    pca_var = (pca_explained[0] + pca_explained[1]) * 100 if len(pca_explained) >= 2 else 0
    n_freq1 = int((df["frequency"] == 1).sum())
    n_ret_gt1 = int((df["return_rate"] > 1).sum()) if "return_rate" in df else 0
    items = [
        f"<strong>PCA(2)</strong> explica el {pca_var:.1f}% de la varianza. El resto se pierde en el plano.",
        f"<strong>{n_ret_gt1} clientes con return_rate &gt; 1</strong> — artefacto del Cluster 2 (devoluciones de unidades no contabilizadas como venta).",
        f"<strong>{n_freq1:,} clientes con frequency = 1</strong> ({n_freq1/len(df)*100:.1f}%) — sesgan la mediana hacia abajo y son transparentes en el dashboard.".replace(",", " "),
        "<strong>Dataset 100% sintético</strong> — los hallazgos son consistentes pero no transferibles a operación real.",
        "<strong>Ventana fija de 72 meses</strong> — los clientes nuevos quedan castigados en retention_rate (denominador rígido).",
    ]
    return '<ol class="limits">' + "".join(
        f"<li><span class='badge'>{i}</span><span>{txt}</span></li>"
        for i, txt in enumerate(items, 1)
    ) + "</ol>"


def _cltv_stats(df: pd.DataFrame) -> str:
    s = df[df["cltv"] > 0]["cltv"]
    rows = [
        ("N clientes con CLTV > 0", f"{len(s):,}".replace(",", " ")),
        ("Mediana", theme.fmt_money(s.median())),
        ("Media", theme.fmt_money(s.mean())),
        ("P75", theme.fmt_money(s.quantile(0.75))),
        ("P90", theme.fmt_money(s.quantile(0.90))),
        ("P99", theme.fmt_money(s.quantile(0.99))),
        ("Máximo", theme.fmt_money(s.max())),
        ("Clientes con freq = 1", f"{int((df['frequency']==1).sum()):,}".replace(",", " ")),
    ]
    body = "".join(
        f"<tr><td>{_html.escape(k)}</td><td class='num mono'>{v}</td></tr>"
        for k, v in rows
    )
    return f'<div class="tbl-wrap"><table class="tbl"><tbody>{body}</tbody></table></div>'


def render(segments: pd.DataFrame, *, pca_explained: list[float], elbow: dict[int, float]) -> str:
    parts: list[str] = []
    parts.append(h.chapter_opener(
        marker="Capítulo VI",
        eyebrow="VI · METODOLOGÍA",
        headline="Metodología.",
        deck=(
            "Pipeline ETL, modelo dimensional, trazabilidad de cada KPI a su SQL, "
            "justificación de k = 3 y de PCA(2), y limitaciones declaradas."
        ),
    ))

    parts.append(h.section_h("A", "Pipeline ETL", "public → staging → dwh"))
    parts.append(h.alert_info(
        "<strong>Tres pasos secuenciales</strong> — orquestados por los notebooks "
        "<code>01_etl_staging</code> → <code>02_etl_dwh</code> → <code>03_cltv_calculation</code> → "
        "<code>04_customer_metrics</code> → <code>05_pca_clustering</code>. El esquema "
        "<code>public</code> contiene los datos crudos; <code>staging</code> los normaliza; "
        "<code>dwh</code> aplica el modelo dimensional en estrella (ver sección B)."
    ))

    parts.append(h.section_h("B", "Modelo dimensional (estrella)", "dwh schema"))
    parts.append(h.card(body_html=
        '<pre class="caption" style="font-family:var(--font-mono); line-height:1.6; padding:8px 0; margin:0;">'
        '                  ┌──────────────────┐\n'
        '                  │  dim_customer    │\n'
        '                  └────────┬─────────┘\n'
        '                           │\n'
        '   ┌──────────────────┐    │    ┌──────────────────┐\n'
        '   │  dim_product     │────┼────│  dim_store       │\n'
        '   └──────────────────┘    │    └──────────────────┘\n'
        '                           │\n'
        '                ┌──────────┴───────────┐\n'
        '                │   fact_sales         │\n'
        '                │   fact_returns       │\n'
        '                └──────────┬───────────┘\n'
        '                           │\n'
        '                  ┌────────┴─────────┐\n'
        '                  │  dim_date        │\n'
        '                  └──────────────────┘\n'
        '</pre>' +
        h.explain("Dos hechos (ventas y devoluciones) en el centro y cuatro dimensiones en las esquinas. La estrella se carga incrementalmente desde staging.")
    ))

    parts.append(h.section_h("C", "Mapa KPI → fórmula → origen"))
    parts.append(_kpi_map_table())
    parts.append(h.explain("Ningún KPI sin papeleta: si alguien pregunta «¿de dónde sale el AOV?», la respuesta está aquí, no en una conversación."))

    parts.append(h.section_h("D", "Justificación de k = 3 (curva del codo)"))
    parts.append(h.card(header="Inertia ~ k", body_html=
        h.fig_html(_elbow(elbow), frame=False) +
        h.explain("Inertia decrece monótonamente con k. El codo es donde la mejora marginal por añadir un cluster cae bruscamente — en este dataset, k=3. Defender la elección con un gráfico es preferible a afirmarla.")
    ))

    parts.append(h.section_h("E", "PCA(2)", "models/pca.joblib"))
    var_pc1 = pca_explained[0] * 100 if len(pca_explained) > 0 else 0
    var_pc2 = pca_explained[1] * 100 if len(pca_explained) > 1 else 0
    var_total = var_pc1 + var_pc2
    parts.append(h.grid([
        h.card(header="Varianza explicada por componente",
               body_html=h.fig_html(_pca_bar(pca_explained), frame=False)),
        h.card(header="Resumen",
               body_html=h.grid([
                   h.kpi_card("PC1", f"{var_pc1:.1f}%", src="explained_variance_"),
                   h.kpi_card("PC2", f"{var_pc2:.1f}%", src="explained_variance_"),
                   h.kpi_card("Total 2D", f"{var_total:.1f}%",
                              delta=f"objetivo 80% — {'cumplido' if var_total >= 80 else f'desviación: {var_total-80:+.1f} pp'}",
                              delta_dir="up" if var_total >= 80 else "down"),
               ], cols=3) +
               h.explain(f"PCA(2) cubre {var_total:.1f}% de la varianza. La elección de 2 componentes se evalúa contra el objetivo declarado.")),
    ], cols=2))

    parts.append(h.section_h("F", "Las 8 features + limitaciones"))
    parts.append(h.grid([
        h.card(header="Features usadas en el clustering", body_html=_features_list()),
        h.card(header="Limitaciones declaradas", body_html=_limitations(segments, pca_explained)),
    ], cols=2))

    parts.append(h.section_h("G", "Estadísticos clave del CLTV"))
    parts.append(_cltv_stats(segments))

    return '<section id="view-metodologia" class="view">' + "".join(parts) + "</section>"
