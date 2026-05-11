"""Vista 02 · Clientes & CLTV."""
from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .. import helpers as h
from .. import theme


def _gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = x.size
    if n == 0 or x.sum() == 0:
        return 0.0
    cum = np.cumsum(x) / x.sum()
    lorenz = np.concatenate([[0.0], cum])
    return float(1 - 2 * np.trapezoid(lorenz, dx=1 / n))


def _kpis_block(df: pd.DataFrame, df_total: pd.DataFrame) -> str:
    n_filt = len(df)
    n_total = len(df_total)
    cltv_med = df["cltv"].median() if n_filt else 0.0
    cltv_mean = df["cltv"].mean() if n_filt else 0.0
    ratio = (cltv_mean / cltv_med) if cltv_med else 0.0
    if n_filt:
        topn = max(1, int(0.20 * n_filt))
        top_concentration = df.nlargest(topn, "cltv")["cltv"].sum() / df["cltv"].sum()
    else:
        top_concentration = 0.0

    cards = [
        h.kpi_card("Clientes con CLTV", f"{n_filt:,}".replace(",", " "),
                   delta=f"de {n_total:,}".replace(",", " "), delta_dir="flat",
                   src="customer_segments"),
        h.kpi_card("CLTV mediana · P50", theme.fmt_money(cltv_med, short=True),
                   src="cltv.parquet"),
        h.kpi_card("CLTV media", theme.fmt_money(cltv_mean, short=True),
                   delta=f"× {ratio:.1f} mediana", delta_dir="up",
                   delta_label="(asimetría)", src="cltv.parquet"),
        h.kpi_card("Concentración Top 20%", theme.fmt_pct(top_concentration),
                   delta="del CLTV total", delta_dir="flat", src="derived"),
    ]
    return h.grid(cards, cols=4)


def _finding(df_total: pd.DataFrame) -> str:
    pct = (df_total["frequency"] == 1).mean() if len(df_total) else 0.0
    n = int((df_total["frequency"] == 1).sum())
    return h.finding_banner(
        big_pct=pct,
        frac=f"{n:,} / {len(df_total):,} clientes con una sola compra".replace(",", " "),
        h3="La mediana es baja porque la mayoría son one-shot",
        p="La media de CLTV está distorsionada por el Cluster 1 (VIP), que genera ~99,8% del CLTV total. "
          "Por eso esta vista usa la mediana como medida central y muestra el Top 20% para evidenciar la concentración.",
        micro="Origen: customer_segments.parquet · cálculo derivado.",
    )


def _hist_log(df: pd.DataFrame) -> go.Figure:
    sub = df[df["cltv"] > 0].copy()
    sub["log_cltv"] = np.log10(sub["cltv"])
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=sub["log_cltv"], nbinsx=60,
        marker_color=theme.PRIMARY, marker_line_color="#fff", marker_line_width=0.5,
        hovertemplate="log10(CLTV)=%{x:.2f}<br>n=%{y}<extra></extra>",
        name="clientes",
    ))
    pcts = {"P50": 50, "P75": 75, "P90": 90, "P99": 99}
    # Paleta unificada: cuanto más alto el percentil, más oscuro el azul.
    colors = {"P50": "#93C5FD", "P75": "#60A5FA", "P90": theme.PRIMARY, "P99": "#1D4ED8"}
    for lbl, q in pcts.items():
        v = float(np.log10(np.percentile(sub["cltv"], q)))
        fig.add_vline(x=v, line_dash="dash", line_color=colors[lbl],
                      annotation_text=lbl, annotation_position="top",
                      annotation_font_color=colors[lbl])
    theme.apply_chart(fig, title=" ", height=380, hovermode="x")
    fig.update_layout(xaxis_title="log10(CLTV)", yaxis_title="clientes",
                      bargap=0.05, showlegend=False)
    return fig


def _ecdf(df: pd.DataFrame) -> go.Figure:
    sub = df[df["cltv"] > 0]["cltv"].sort_values().values
    n = sub.size
    y = np.arange(1, n + 1) / n
    fig = go.Figure(go.Scatter(
        x=sub, y=y, mode="lines",
        line=dict(color=theme.PRIMARY, width=2, shape="hv"),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.10)",
        hovertemplate="CLTV ≤ %{x:,.0f} €<br>%{y:.1%} de clientes<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=380, hovermode="x")
    fig.update_layout(xaxis_title="CLTV (€) · log",
                      yaxis_title="P(CLTV ≤ x)",
                      xaxis_type="log", showlegend=False,
                      yaxis_tickformat=".0%")
    return fig


def _violin_by_cluster(df: pd.DataFrame) -> go.Figure:
    sub = df[df["cltv"] > 0].copy()
    sub["log_cltv"] = np.log10(sub["cltv"])
    fig = go.Figure()
    for c in sorted(sub["cluster"].unique()):
        s = sub[sub["cluster"] == c]
        fig.add_trace(go.Violin(
            x=s["log_cltv"], name=theme.CLUSTER_LABELS.get(c, f"Cluster {c}"),
            line_color=theme.CLUSTER_COLORS.get(c, theme.PRIMARY),
            fillcolor=theme.CLUSTER_COLORS.get(c, theme.PRIMARY),
            opacity=0.55, box_visible=True, meanline_visible=True,
            orientation="h", side="positive",
        ))
    theme.apply_chart(fig, title=" ", height=380, hovermode="closest")
    fig.update_layout(xaxis_title="log10(CLTV)", showlegend=False, violingap=0.1)
    return fig


def _lorenz(df: pd.DataFrame) -> tuple[go.Figure, float]:
    sub = df[df["cltv"] > 0]["cltv"].values
    if sub.size == 0:
        return go.Figure(), 0.0
    s = np.sort(sub)
    n = s.size
    cum = np.cumsum(s) / s.sum()
    x = np.linspace(0, 1, n + 1)
    y = np.concatenate([[0.0], cum])
    g = _gini(s)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1], mode="lines",
        line=dict(color=theme.INK_SOFT, dash="dash"), name="Igualdad perfecta",
        hovertemplate="<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=theme.PRIMARY, width=2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.16)",
        name="Curva real",
        hovertemplate="%{x:.1%} clientes → %{y:.1%} CLTV<extra></extra>",
    ))
    fig.add_annotation(
        x=0.05, y=0.95, xanchor="left", yanchor="top",
        text=f"<b>Gini = {g:.3f}</b>", showarrow=False,
        font=dict(color=theme.INK, size=14),
        bgcolor="rgba(255,255,255,0.85)", bordercolor=theme.BORDER_STR, borderwidth=1, borderpad=6,
    )
    theme.apply_chart(fig, title=" ", height=340, hovermode="closest")
    fig.update_layout(xaxis_title="% clientes (acumulado)",
                      yaxis_title="% CLTV (acumulado)",
                      xaxis_tickformat=".0%", yaxis_tickformat=".0%",
                      showlegend=False)
    return fig, g


def _mean_vs_median_per_cluster(df: pd.DataFrame) -> go.Figure:
    grp = df[df["cltv"] > 0].groupby("cluster")["cltv"].agg(["mean", "median"]).reset_index()
    grp["label"] = grp["cluster"].map(theme.CLUSTER_LABELS)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=grp["mean"], y=grp["label"], orientation="h", name="Media",
        marker=dict(color=[theme.CLUSTER_COLORS[c] for c in grp["cluster"]]),
        opacity=0.4,
        hovertemplate="<b>%{y}</b><br>Media: %{x:,.0f} €<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=grp["median"], y=grp["label"], orientation="h", name="Mediana",
        marker=dict(color=[theme.CLUSTER_COLORS[c] for c in grp["cluster"]]),
        opacity=1.0,
        hovertemplate="<b>%{y}</b><br>Mediana: %{x:,.0f} €<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=340, hovermode="closest")
    fig.update_layout(barmode="group",
                      xaxis_type="log", xaxis_title="CLTV (€) · log",
                      yaxis_title="",
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    return fig


def _top20_table(df: pd.DataFrame) -> str:
    top = df.sort_values("cltv", ascending=False).head(20).copy()
    if top.empty:
        return h.alert_info("<strong>Sin clientes</strong> con los filtros actuales.")
    cltv_max = top["cltv"].max()

    rows = []
    for _, r in top.iterrows():
        bar_w = (r["cltv"] / cltv_max * 100) if cltv_max else 0
        chip = h.cluster_chip(int(r["cluster"]))
        last_dt = pd.to_datetime(r.get("last_purchase")).strftime("%Y-%m-%d") if pd.notna(r.get("last_purchase")) else "—"
        rows.append(
            f"<tr>"
            f"<td class='mono'>{int(r['customer_id'])}</td>"
            f"<td>{_html.escape(str(r.get('full_name', '—')))}</td>"
            f"<td>{chip}</td>"
            f"<td><div class='bar-cell'>"
            f"  <div class='barwrap'><div class='bar' style='width:{bar_w:.1f}%'></div></div>"
            f"  <div class='barv'>{theme.fmt_money(r['cltv'], short=True)}</div>"
            f"</div></td>"
            f"<td class='num'>{int(r['frequency']):,}</td>"
            f"<td class='num'>{theme.fmt_money(r.get('aov', 0), short=True) if 'aov' in r else '—'}</td>"
            f"<td class='num mono'>{last_dt}</td>"
            f"</tr>"
        )

    table = (
        f'<div class="tbl-wrap">'
        f'<table class="tbl">'
        f'<thead><tr>'
        f'<th>ID</th><th>Cliente</th><th>Cluster</th><th>CLTV</th>'
        f'<th class="num">Compras</th><th class="num">AOV</th><th class="num">Última compra</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
        f'</div>'
    )
    return table


def render(segments: pd.DataFrame) -> str:
    """Renderiza la vista 02 — Clientes & CLTV. `segments` ya trae cluster, aov y demás."""
    df = segments.copy()

    parts: list[str] = []
    parts.append(h.chapter_opener(
        marker="Capítulo II",
        eyebrow="II · CLIENTES &amp; CLTV",
        headline="Clientes y CLTV.",
        deck=(
            f"Distribución del valor por cliente sobre <strong>{theme.fmt_int(len(df))}</strong> "
            "registros: histograma logarítmico, ECDF, densidad por cluster, curva de Lorenz "
            "con coeficiente de Gini, y el top de la base."
        ),
    ))

    parts.append(_kpis_block(df, df))

    parts.append(h.section_h("A", "Hallazgo principal", "customer_segments.parquet"))
    parts.append(_finding(df))

    parts.append(h.section_h("B", "Distribución del CLTV", "cltv.parquet"))
    # Tabs HTML manual con JS — mismas 3 visualizaciones que en streamlit
    hist_div  = h.fig_html(_hist_log(df), frame=False)
    ecdf_div  = h.fig_html(_ecdf(df), frame=False)
    viol_div  = h.fig_html(_violin_by_cluster(df), frame=False)

    tabs_html = (
        '<div class="card">'
        '  <div class="tabs-bar" role="tablist" style="display:flex;gap:6px;margin-bottom:12px;">'
        '    <button class="tab-btn" data-tab="histlog" aria-selected="true">Histograma (log)</button>'
        '    <button class="tab-btn" data-tab="ecdf"    aria-selected="false">ECDF</button>'
        '    <button class="tab-btn" data-tab="violin"  aria-selected="false">Densidad por cluster</button>'
        '  </div>'
        f'  <div class="tab-panel" data-panel="histlog">{hist_div}'
        f'    {h.explain("Con asimetría tan severa, el log es la única forma de ver la distribución completa. Las líneas P50/P75/P90/P99 anclan al lector. Excluye CLTV ≤ 0 (artefacto del dataset sintético).")}'
        '  </div>'
        f'  <div class="tab-panel" data-panel="ecdf" hidden>{ecdf_div}'
        f'    {h.explain("Responde directamente: ¿qué porcentaje de clientes tiene CLTV ≤ X €? sin necesidad de bins.")}'
        '  </div>'
        f'  <div class="tab-panel" data-panel="violin" hidden>{viol_div}'
        f'    {h.explain("En una sola vista compara dispersión, mediana y outliers entre clusters. Hace evidente que el Cluster 1 vive dos órdenes de magnitud por encima del resto.")}'
        '  </div>'
        '</div>'
    )
    parts.append(tabs_html)

    parts.append(h.section_h("C", "Concentración del CLTV", "Lorenz · Gini · cluster"))
    fig_lor, gini = _lorenz(df)
    parts.append(h.grid([
        h.card(header="Curva de Lorenz",
               meta=f"Gini = {gini:.3f}",
               body_html=h.fig_html(fig_lor, frame=False) +
                         h.explain("El gold-standard para mostrar concentración: el área entre la diagonal de igualdad y la curva real es el Gini. Un valor cercano a 1 = altísima concentración del valor en pocos clientes.")),
        h.card(header="CLTV por cluster — mediana vs media",
               body_html=h.fig_html(_mean_vs_median_per_cluster(df), frame=False) +
                         h.explain("Donde la media supera mucho a la mediana, la cola es la que manda. El Cluster 1 enseña la asimetría más fuerte.")),
    ], cols=2))

    parts.append(h.section_h("D", "Top 20 clientes por CLTV", "cltv.parquet · ordenado desc"))
    parts.append(_top20_table(df))
    parts.append(h.explain("Pone cara y nombre a los outliers que dominan el Gini y la media. Cluster en chip; barra horizontal en CLTV para escala visual."))

    return '<section id="view-clientes" class="view">' + "".join(parts) + "</section>"
