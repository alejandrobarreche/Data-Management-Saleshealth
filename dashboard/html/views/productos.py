"""Vista 04 · Productos & Devoluciones.

Cuando hay DWH, renderiza top productos, donut + barras de motivos de
devolución, y top productos por valor devuelto coloreados por ratio.
En modo OFFLINE muestra el placeholder honesto.
"""
from __future__ import annotations

import html as _html
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .. import helpers as h
from .. import theme


def _kpis(kpis: dict) -> str:
    cards = [
        h.kpi_card("Líneas de venta", f"{int(kpis.get('line_items', 0)):,}".replace(",", " "),
                   src="fact_sales"),
        h.kpi_card("Devoluciones (€)", theme.fmt_money(kpis.get("returns_value", 0), short=True),
                   src="fact_returns"),
        h.kpi_card("Tasa devolución", theme.fmt_pct(kpis.get("return_rate", 0)),
                   delta="(devuelto / bruto)", delta_dir="flat"),
        h.kpi_card("AOV", theme.fmt_money(kpis.get("aov", 0), short=True),
                   delta="(rev / nº tickets)", delta_dir="flat"),
    ]
    return h.grid(cards, cols=4)


def _zero_cost_warning(skus: list[str]) -> str:
    if not skus:
        return ""
    n = len(skus)
    visible = ", ".join(skus[:8])
    extra = f" + {n - 8} más" if n > 8 else ""
    return h.alert_warn(
        f'<div class="ico">⚠</div>'
        f'<div class="body"><strong>{n} producto(s) con coste unitario = 0</strong>. '
        f"El margen calculado para esas líneas asume coste 0, así que el agregado "
        f"<strong>«Margen bruto»</strong> es un techo, no la cifra real.<br>"
        f'<span class="caption">SKUs: {visible}{extra}</span></div>'
    )


def _top_products_chart(prods: pd.DataFrame) -> go.Figure:
    df = prods.copy().sort_values("revenue", ascending=True)
    colors = [theme.CATEGORY_COLORS.get(c, theme.PRIMARY) for c in df["category"]]
    fig = go.Figure(go.Bar(
        x=df["revenue"], y=df["product"], orientation="h",
        marker=dict(color=colors),
        customdata=np.stack([df["category"], df["brand"], df["units"], df["margin"]], axis=1),
        text=[theme.fmt_money(v, short=True) for v in df["revenue"]],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "%{customdata[0]} · %{customdata[1]}<br>"
            "Ingresos: %{x:,.0f} €<br>"
            "Unidades: %{customdata[2]:,}<br>"
            "Margen: %{customdata[3]:,.0f} €<extra></extra>"
        ),
    ))
    theme.apply_chart(fig, title=" ", height=440, hovermode="closest")
    fig.update_layout(xaxis_title="Ingresos (€)", yaxis_title="", showlegend=False,
                      margin=dict(l=10, r=60, t=20, b=40))
    return fig


def _returns_donut(rets: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=rets["reason"], values=rets["value"], hole=0.55,
        marker=dict(colors=theme.SEQ_BLUE[2:], line=dict(color="#fff", width=2)),
        textinfo="percent", textposition="inside",
        insidetextfont=dict(color="#fff", size=11, family="Inter, sans-serif"),
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} €<br>%{percent}<extra></extra>",
        sort=False,
    ))
    fig.add_annotation(text=f"<b>{theme.fmt_money(rets['value'].sum(), short=True)}</b>"
                            f"<br><span style='font-size:10px;color:{theme.INK_SOFT}'>devuelto</span>",
                       showarrow=False, x=0.5, y=0.5, font=dict(color=theme.INK, size=14))
    theme.apply_chart(fig, title=" ", height=340, hovermode="closest")
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center", font=dict(size=11)),
        margin=dict(l=10, r=10, t=20, b=50),
    )
    return fig


def _returns_bars(rets: pd.DataFrame) -> go.Figure:
    df = rets.sort_values("value", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["value"], y=df["reason"], orientation="h",
        marker=dict(color=df["value"], colorscale=theme.SEQ_BLUE,
                    colorbar=dict(thickness=10, len=0.7, tickfont=dict(size=10))),
        text=[theme.fmt_money(v, short=True) for v in df["value"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} €<extra></extra>",
    ))
    theme.apply_chart(fig, title=" ", height=320, hovermode="closest")
    fig.update_layout(xaxis_title="Valor devuelto (€)", yaxis_title="", showlegend=False,
                      margin=dict(l=10, r=50, t=20, b=40))
    return fig


def _returns_by_product_chart(prods: pd.DataFrame) -> go.Figure:
    df = prods.copy().sort_values("value", ascending=True)
    df["ratio_safe"] = df["ratio"].fillna(0)
    fig = go.Figure(go.Bar(
        x=df["value"], y=df["product"], orientation="h",
        marker=dict(
            color=df["ratio_safe"], colorscale=theme.SEQ_BLUE,
            cmin=0, cmax=max(0.1, float(df["ratio_safe"].max() or 0.1)),
            colorbar=dict(title="ratio dev/ventas", thickness=10, len=0.7,
                          tickformat=".0%", tickfont=dict(size=10)),
        ),
        customdata=np.stack([df["category"], df["units"], df["n_returns"], df["ratio_safe"]], axis=1),
        text=[theme.fmt_money(v, short=True) for v in df["value"]],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "%{customdata[0]}<br>"
            "Devuelto: %{x:,.0f} €<br>"
            "Unidades: %{customdata[1]:,}<br>"
            "Devoluciones: %{customdata[2]}<br>"
            "Ratio dev/ventas: %{customdata[3]:.1%}<extra></extra>"
        ),
    ))
    theme.apply_chart(fig, title=" ", height=440, hovermode="closest")
    fig.update_layout(xaxis_title="Valor devuelto (€)", yaxis_title="", showlegend=False,
                      margin=dict(l=10, r=60, t=20, b=40))
    return fig


def _category_chips() -> str:
    """Filtros visuales por categoría — el JS de la vista los conecta a la lista."""
    chips = [
        '<button class="product-chip active" data-category="">Todas</button>'
    ]
    for cat, color in theme.CATEGORY_COLORS.items():
        chips.append(
            f'<button class="product-chip" data-category="{_html.escape(cat)}" '
            f'style="--chip-color:{color}">'
            f'<span class="product-chip-dot" style="background:{color}"></span>'
            f'{_html.escape(cat)}</button>'
        )
    return (
        '<div class="product-filters">'
        '  <span class="product-filter-label">Categoría</span>'
        f'  {"".join(chips)}'
        '</div>'
    )


def _product_list(prods: pd.DataFrame) -> str:
    """Lista cards complementaria al bar chart — un row por producto, ordenado
    por revenue desc, con avatar de categoría, nombre, marca, unidades, margen
    y barra inline de ingresos. Los chips filtran por categoría (data-attr)."""
    df = prods.copy().sort_values("revenue", ascending=False)
    rev_max = float(df["revenue"].max() or 1)
    rows = []
    for _, p in df.iterrows():
        cat = str(p.get("category") or "—")
        color = theme.CATEGORY_COLORS.get(cat, theme.PRIMARY)
        bar_pct = (float(p["revenue"]) / rev_max) * 100
        margin_eur = float(p.get("margin", 0) or 0)
        margin_pct = (margin_eur / float(p["revenue"]) * 100) if p["revenue"] else 0
        avatar = _html.escape(cat[:1].upper() if cat else "—")
        rows.append(
            f'<div class="product-row" data-category="{_html.escape(cat)}">'
            f'  <span class="product-row-avatar" style="background:{color}">{avatar}</span>'
            f'  <div class="product-row-body">'
            f'    <span class="product-row-name">{_html.escape(str(p["product"]))}</span>'
            f'    <span class="product-row-meta">'
            f'      <span class="product-row-cat" style="color:{color}">{_html.escape(cat)}</span>'
            f'      <span class="product-row-sep">·</span>'
            f'      <span>{_html.escape(str(p.get("brand", "—")))}</span>'
            f'      <span class="product-row-sep">·</span>'
            f'      <span>{int(p["units"]):,} ud</span>'.replace(",", " ") +
            f'      <span class="product-row-sep">·</span>'
            f'      <span>{margin_pct:.1f}% margen</span>'
            f'    </span>'
            f'  </div>'
            f'  <div class="product-row-revenue">'
            f'    <span class="product-row-bar">'
            f'      <span class="product-row-fill" style="width:{bar_pct:.1f}%; background:{color}"></span>'
            f'    </span>'
            f'    <span class="product-row-rev-v">{theme.fmt_money(float(p["revenue"]), short=True)}</span>'
            f'  </div>'
            f'</div>'
        )
    return (
        '<div class="product-list" id="product-list">'
        + "".join(rows) +
        '</div>'
        '<div class="product-list-empty" id="product-list-empty" hidden>'
        'Ningún producto en esa categoría dentro del top 15.'
        '</div>'
    )


def _trace_cards() -> str:
    """Trazabilidad SQL como cards visuales (estilo ficha-card)."""
    items = [
        ("fact_sales",        "fs", theme.PRIMARY,
         "Movimiento — líneas de venta",
         "Base de Top productos, AOV, ingresos por categoría."),
        ("fact_returns",      "fr", "#F97316",
         "Movimiento — líneas de devolución",
         "Base de los breakdowns por motivo y por producto."),
        ("dim_product",       "dp", theme.ACCENT_TEAL,
         "Catálogo — productos",
         "Categoría, marca y unit_cost. De aquí salen los zero-cost."),
        ("dim_return_reason", "rr", "#A855F7",
         "Catálogo — motivos canónicos",
         "Diccionario que normaliza los motivos de devolución."),
    ]
    cards = []
    for tbl, ini, color, role, desc in items:
        cards.append(
            f'<div class="trace-card" style="--trace-color:{color}">'
            f'  <span class="trace-card-mark">{ini.upper()}</span>'
            f'  <div class="trace-card-body">'
            f'    <div class="trace-card-name">{tbl}</div>'
            f'    <div class="trace-card-role">{_html.escape(role)}</div>'
            f'    <div class="trace-card-desc">{_html.escape(desc)}</div>'
            f'  </div>'
            f'</div>'
        )
    return '<div class="grid grid-2">' + "".join(cards) + '</div>'


_PRODUCT_FILTER_JS = """
<script>
(function() {
  const chips = document.querySelectorAll('#view-productos .product-chip');
  const rows = document.querySelectorAll('#view-productos .product-row');
  const empty = document.getElementById('product-list-empty');
  if (!chips.length) return;
  chips.forEach(c => c.addEventListener('click', () => {
    chips.forEach(x => x.classList.toggle('active', x === c));
    const cat = c.dataset.category || '';
    let visible = 0;
    rows.forEach(r => {
      const ok = !cat || r.dataset.category === cat;
      r.hidden = !ok;
      if (ok) visible++;
    });
    if (empty) empty.hidden = visible !== 0;
  }));
})();
</script>
"""


def render(
    *,
    offline: bool = True,
    kpis: Optional[dict] = None,
    period: Optional[tuple] = None,
    top_products: Optional[pd.DataFrame] = None,
    returns_breakdown: Optional[pd.DataFrame] = None,
    returns_by_product: Optional[pd.DataFrame] = None,
    zero_cost_skus: Optional[list[str]] = None,
) -> str:
    parts: list[str] = []

    if offline:
        parts.append(h.chapter_opener(
            marker="Capítulo IV",
            eyebrow="IV · PRODUCTOS &amp; DEVOLUCIONES",
            headline="Productos y devoluciones.",
            deck=(
                "Vista íntegramente alimentada por Postgres — fuera de alcance en modo "
                "OFFLINE. Cuando el DWH esté disponible, esta sección vuelve a la vida."
            ),
        ))
        parts.append(h.offline_banner(
            "Modo OFFLINE — Esta vista no tiene contraparte en parquet (todos los breakdowns por SKU, "
            "motivo y categoría se computan en la base)."
        ))
        parts.append(h.section_h("A", "Cuando el DWH está disponible — qué muestra"))
        parts.append(h.card(body_html=
            "<p><strong>KPIs (4)</strong> — Líneas de venta · devoluciones (€) · tasa devolución · AOV.</p>"
            "<p><strong>A · Top 15 productos por ingresos</strong> — barras horizontales coloreadas por categoría.</p>"
            "<p><strong>B · Devoluciones — motivo y producto</strong> — donut por motivo, barras por motivo, top productos por valor devuelto.</p>"
        ))
        return '<section id="view-productos" class="view">' + "".join(parts) + "</section>"

    period_str = f"{period[0]:%Y-%m-%d} → {period[1]:%Y-%m-%d}" if period else ""

    parts.append(h.chapter_opener(
        marker="Capítulo IV",
        eyebrow="IV · PRODUCTOS &amp; DEVOLUCIONES",
        headline="Productos y devoluciones.",
        deck=(
            f"Ventana <strong>{period_str}</strong>. Top de ingresos, motivos de "
            "devolución (donut + barras) y los SKUs con peor relación devolución/venta."
        ),
    ))

    parts.append(_kpis(kpis or {}))
    parts.append(_zero_cost_warning(zero_cost_skus or []))

    parts.append(h.section_h("A", "Top 15 productos por ingresos", "color = categoría"))
    parts.append(_category_chips())
    parts.append(h.card(body_html=h.fig_html(_top_products_chart(top_products), frame=False) +
                        h.explain("Identifica los caballos de batalla. Cruzando mentalmente con la sección B se detecta cuáles son también los más devueltos.")))
    # Lista complementaria al bar chart — mismos productos, formato leíble
    parts.append(h.card(
        header="Detalle por producto",
        meta="filtra por categoría con los chips de arriba",
        body_html=_product_list(top_products),
    ))

    parts.append(h.section_h("B", "Devoluciones — motivo y producto"))
    parts.append(h.grid([
        h.card(header="Distribución por motivo (%)",
               body_html=h.fig_html(_returns_donut(returns_breakdown), frame=False) +
                         h.explain("¿Qué motivo manda en porcentaje? La centralidad relativa.")),
        h.card(header="Valor por motivo (€)",
               body_html=h.fig_html(_returns_bars(returns_breakdown), frame=False) +
                         h.explain("Mismos motivos en valor absoluto. La duplicación con el donut es intencionada — sirven a conversaciones distintas (% vs €).")),
    ], cols=2))

    parts.append(h.card(header="Top productos por valor devuelto",
                        meta="color = ratio dev/ventas",
                        body_html=h.fig_html(_returns_by_product_chart(returns_by_product), frame=False) +
                                  h.explain("Cruza volumen devuelto con relevancia comercial. Un producto pequeño con ratio 80% es un fuego, aunque pierda en absoluto. Los rojos son los focos a investigar.")))

    parts.append(h.section_h("C", "Trazabilidad SQL"))
    parts.append(_trace_cards())

    parts.append(_PRODUCT_FILTER_JS)
    return '<section id="view-productos" class="view">' + "".join(parts) + "</section>"
