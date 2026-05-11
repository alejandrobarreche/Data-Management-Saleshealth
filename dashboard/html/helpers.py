"""Componentes HTML reutilizables del dashboard.

Cada función devuelve un str de HTML. Las clases CSS usadas viven en
style.css — para cambiar el aspecto, edita allí.
"""
from __future__ import annotations

import html as _html
import itertools

import plotly.graph_objects as go

from . import theme


_FIG_COUNTER = itertools.count(1)


def fig_html(fig: go.Figure, *, height: int | None = None, frame: bool = True) -> str:
    """Embebe una Plotly figure como <div> que llena el ancho del padre.

    `default_width='100%'` evita el bug clásico de Plotly que renderiza al
    ancho por defecto (700 px) cuando el contenedor flex/grid aún no tiene
    layout calculado. El `Plotly.Plots.resize()` que dispara `build.py` en
    window.load es el segundo cinturón de seguridad.
    """
    if height is not None:
        fig.update_layout(height=height)
    fig.update_layout(autosize=True)
    n = next(_FIG_COUNTER)
    div = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        div_id=f"fig-{n}",
        default_width="100%",
        default_height=f"{height}px" if isinstance(height, int) else "400px",
        config={"displaylogo": False, "responsive": True},
    )
    cls = "fig" if frame else "fig no-frame"
    return f'<div class="{cls}">{div}</div>'


def hero(eyebrow: str, h1: str, sub: str) -> str:
    """OLD · cabecera de vista estilo dashboard (texto plano, sans-serif).

    Mantenida para compat. Las vistas usan ``chapter_opener`` ahora.
    Para volver al look anterior en una vista concreta, sustituye su
    llamada a ``chapter_opener(...)`` por ``hero(eyebrow, h1, sub)``.
    """
    return (
        f'<header class="hero">'
        f'  <div class="eyebrow">{_html.escape(eyebrow)}</div>'
        f'  <h1>{_html.escape(h1)}</h1>'
        f'  <p class="sub">{_html.escape(sub)}</p>'
        f'</header>'
    )


def chapter_opener(
    *,
    marker: str | None = None,        # ej. "Capítulo II" o "§2"
    eyebrow: str,                     # ej. "II · CLIENTES & CLTV"
    headline: str,                    # HTML válido (no se escapa)
    headline_em: str | None = None,   # frase italic en azul al final
    deck: str,                        # HTML válido (puede llevar <strong>)
) -> str:
    """Cabecera editorial de una vista — análoga al opener general.

    headline y deck se inyectan como HTML; el llamador debe escaparlos si
    proceden de input externo. Para SalesHealth todo el contenido lo
    controla build.py y las vistas — no hay riesgo de inyección.
    """
    marker_html = f'<div class="marker">{marker}</div>' if marker else ""
    em_html = f'<em>{headline_em}</em>' if headline_em else ""
    return (
        '<header class="chapter-opener">'
        f'{marker_html}'
        f'<p class="eyebrow">{eyebrow}</p>'
        f'<h1>{headline}{em_html}</h1>'
        f'<p class="deck">{deck}</p>'
        '</header>'
    )


def lede(text_html: str, *, muted: bool = False) -> str:
    """Entradilla en serif justo antes de un gráfico — sustituye al `explain`
    cuando queremos que el texto tenga peso editorial (más grande, con énfasis).
    Acepta HTML (puede contener <strong>, <em>, etc.)."""
    cls = "lede" + (" muted" if muted else "")
    return f'<p class="{cls}">{text_html}</p>'


def section_h(num: str, title: str, kicker: str = "") -> str:
    k = f'<div class="kicker">{_html.escape(kicker)}</div>' if kicker else ""
    return (
        f'<div class="section-h">'
        f'  <span class="num">{_html.escape(num)}</span>'
        f'  <h2>{_html.escape(title)}</h2>{k}'
        f'</div>'
    )


def explain(text: str) -> str:
    """Texto explicativo que aparece justo debajo de un gráfico o sección."""
    return f'<p class="explain">{_html.escape(text)}</p>'


def caption(text: str) -> str:
    return f'<div class="caption">{_html.escape(text)}</div>'


def kpi_hero(
    *,
    label: str,                          # ej. "Ingresos netos"
    value: str,                          # ej. "1,58 M€"
    delta: str | None = None,            # ej. "12,3 %"
    delta_dir: str = "flat",             # "up" | "down" | "flat"
    delta_label: str | None = "vs ventana previa",
    breakdown: list[tuple[str, str]] | None = None,  # [(k, v), ...] inline bajo la hairline
    src: str | None = None,
) -> str:
    """KPI hero — el «titular» de la sección de Indicadores. Más grande que
    una `kpi_card` normal, con un desglose inline (label/value separados por ·).

    El breakdown es una lista de pares (clave, valor). Ej.:
        [("BRUTO", "1,58 M€"), ("DEVUELTO", "53 k€"), ("MARGEN", "40,2 %")]
    """
    delta_html = ""
    if delta:
        dl = f'<span class="kpi-hero-delta-label">{_html.escape(delta_label)}</span>' if delta_label else ""
        delta_html = f'<span class="kpi-hero-delta {delta_dir}">{_html.escape(delta)}</span>{dl}'

    breakdown_html = ""
    if breakdown:
        items = "".join(
            f'<span class="it"><span class="k">{_html.escape(k)}</span>'
            f'<span class="v">{_html.escape(v)}</span></span>'
            for k, v in breakdown
        )
        breakdown_html = f'<div class="kpi-hero-breakdown">{items}</div>'

    # NOTE: el parámetro `src` se acepta por compat pero ya no se renderiza.
    # La trazabilidad de origen vive en la vista 06 (Metodología), no en cada KPI.

    return (
        f'<div class="kpi-hero">'
        f'  <div class="kpi-hero-top">'
        f'    <span class="kpi-hero-label">{_html.escape(label)}</span>'
        f'    <span class="kpi-hero-meta">{delta_html}</span>'
        f'  </div>'
        f'  <div class="kpi-hero-value">{_html.escape(value)}</div>'
        f'  {breakdown_html}'
        f'</div>'
    )


def kpi_card(
    label: str,
    value: str,
    *,
    unit: str | None = None,
    delta: str | None = None,
    delta_dir: str = "flat",        # "up" | "down" | "flat"
    delta_label: str | None = None,
    src: str | None = None,
) -> str:
    # NOTE: `src` se acepta por compat pero ya no se renderiza (chip técnico).
    unit_html = f'<span class="unit">{_html.escape(unit)}</span>' if unit else ""
    delta_html = ""
    if delta:
        dl = f'<span class="kpi-delta-label">{_html.escape(delta_label)}</span>' if delta_label else ""
        delta_html = f'<span class="kpi-delta {delta_dir}">{_html.escape(delta)}</span>{dl}'
    return (
        f'<div class="kpi">'
        f'  <div class="kpi-top"><span>{_html.escape(label)}</span></div>'
        f'  <div class="kpi-val">{_html.escape(value)}{unit_html}</div>'
        f'  <div class="kpi-bot">{delta_html}</div>'
        f'</div>'
    )


def card(*, header: str | None = None, meta: str | None = None,
         body_html: str = "", tight: bool = False, no_pad: bool = False) -> str:
    cls = "card" + (" tight" if tight else "") + (" no-pad" if no_pad else "")
    head_html = ""
    if header is not None:
        meta_html = f'<div class="meta">{_html.escape(meta)}</div>' if meta else ""
        head_html = f'<div class="card-h"><h3>{_html.escape(header)}</h3>{meta_html}</div>'
    return f'<div class="{cls}">{head_html}{body_html}</div>'


def cluster_chip(c: int) -> str:
    label = theme.CLUSTER_LABELS.get(c, f"Cluster {c}")
    return f'<span class="chip c{c}"><span class="dot"></span>{_html.escape(label)}</span>'


def cluster_card(c: int, *, n: int, base_pct: float, cltv_pct: float,
                 cltv_med: str, freq_med: str, recency_med: str, return_med: str,
                 prototype: dict | None = None,
                 clickable: bool = False) -> str:
    """`prototype`: dict con customer_id, full_name, cltv_str, frequency, recency_days.
       `clickable`: si True, añade data-cluster=c y cursor:pointer (JS lo conecta)."""
    label = theme.CLUSTER_LABELS.get(c, f"Cluster {c}")

    proto_html = ""
    if prototype:
        proto_html = (
            '<div class="cc-prototype">'
            '<div class="cc-prototype-head">'
            '<span class="cc-prototype-tag">PROTOTIPO</span>'
            '<span class="cc-prototype-hint">cliente más cercano al centroide</span>'
            '</div>'
            f'<div class="cc-prototype-name">{_html.escape(str(prototype.get("full_name") or "—"))}</div>'
            f'<div class="cc-prototype-meta">'
            f'<span>ID {int(prototype["customer_id"])}</span>'
            f'<span class="sep">·</span>'
            f'<span>{_html.escape(prototype.get("cltv_str", "—"))}</span>'
            f'<span class="sep">·</span>'
            f'<span>{int(prototype["frequency"])} compras</span>'
            f'<span class="sep">·</span>'
            f'<span>{int(prototype["recency_days"])}d</span>'
            f'</div>'
            f'<button class="cc-prototype-link" data-prototype-id="{int(prototype["customer_id"])}">'
            'Ver ficha →'
            '</button>'
            '</div>'
        )

    cls = f"cluster-card c{c}" + (" cluster-card-clickable" if clickable else "")
    data = f'data-cluster="{c}"' if clickable else ""

    return (
        f'<div class="{cls}" {data}>'
        f'  <div class="cc-head">'
        f'    <span class="cc-swatch">{c}</span>'
        f'    <div>'
        f'      <div class="cc-name">{_html.escape(label)}</div>'
        f'      <div class="cc-tag">Cluster {c}</div>'
        f'    </div>'
        f'  </div>'
        f'  <div class="cc-share">'
        f'    <span><span class="pct">{n:,}</span> clientes</span>'
        f'    <span><span class="pct">{base_pct*100:.1f}%</span> base</span>'
        f'    <span><span class="pct">{cltv_pct*100:.1f}%</span> CLTV</span>'
        f'  </div>'
        f'  <div class="cc-stats">'
        f'    <div class="cc-stat"><div class="k">CLTV mediana</div><div class="v">{_html.escape(cltv_med)}</div></div>'
        f'    <div class="cc-stat"><div class="k">Frecuencia</div><div class="v">{_html.escape(freq_med)}</div></div>'
        f'    <div class="cc-stat"><div class="k">Recencia</div><div class="v">{_html.escape(recency_med)}</div></div>'
        f'    <div class="cc-stat"><div class="k">Tasa dev.</div><div class="v">{_html.escape(return_med)}</div></div>'
        f'  </div>'
        f'  {proto_html}'
        f'</div>'
    )


def alert_warn(message_html: str) -> str:
    return f'<div class="alert-warn">{message_html}</div>'


def alert_info(message_html: str) -> str:
    return f'<div class="alert-info">{message_html}</div>'


def offline_banner(message: str) -> str:
    return f'<div class="offline-banner">⚠ {_html.escape(message)}</div>'


def finding_banner(*, big_pct: float, frac: str, h3: str, p: str, micro: str = "") -> str:
    micro_html = f'<div class="micro">{_html.escape(micro)}</div>' if micro else ""
    return (
        f'<div class="finding">'
        f'  <div class="finding-num">'
        f'    <div class="big"><span class="pct">{big_pct*100:.1f}%</span></div>'
        f'    <div class="frac">{_html.escape(frac)}</div>'
        f'  </div>'
        f'  <div class="finding-body">'
        f'    <h3>{_html.escape(h3)}</h3>'
        f'    <p>{_html.escape(p)}</p>'
        f'    {micro_html}'
        f'  </div>'
        f'</div>'
    )


def grid(items: list[str], *, cols: int = 4, asym: str | None = None) -> str:
    """Envuelve items en un .grid grid-N. Pasa asym='2-asym' o '3-asym' para layouts asimétricos."""
    cls = "grid"
    if asym:
        cls += f" grid-{asym}"
    else:
        cls += f" grid-{cols}"
    return f'<div class="{cls}">{"".join(items)}</div>'


def inv_card(name: str, value: int | str, src: str = "") -> str:
    """OLD — inventario en cards verdes (sin uso ahora). Mantenida para compat."""
    v = f"{value:,}".replace(",", " ") if isinstance(value, (int, float)) else str(value)
    src_html = f'<div class="src">{_html.escape(src)}</div>' if src else ""
    return (
        f'<div class="inv-card">'
        f'  <div class="head">{_html.escape(name)}</div>'
        f'  <div class="v">{v}</div>'
        f'  {src_html}'
        f'</div>'
    )


def schema_diagram(
    *,
    dim_customer: int, dim_product: int, dim_store: int, dim_date: int,
    fact_sales: int, fact_returns: int,
    mart_cltv: int, mart_segments: int,
) -> str:
    """SVG inline del modelo en estrella con counts en vivo.

    Layout: 4 dimensiones en cardinal points (Calendario arriba, Clientes
    izq, Productos der, Tiendas abajo), VENTAS en el centro (con
    devoluciones inline), y un bloque "DERIVADOS DE VENTAS" debajo con
    CLTV + Segmentos.

    Para tocar tamaños/colores, edita .schema-svg en style.css. Para mover
    cajas, edita las coords <g transform="translate(x,y)"> aquí abajo.
    """
    def _f(v: int) -> str:
        return f"{int(v):,}".replace(",", " ")

    return (
        '<div class="schema-card">'
        '<svg viewBox="0 0 800 430" class="schema-svg" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">'
        # Edges (primero para que vayan detrás de las cajas)
        '<line x1="400" y1="83"  x2="400" y2="125" class="edge"/>'
        '<line x1="190" y1="180" x2="300" y2="180" class="edge"/>'
        '<line x1="610" y1="180" x2="500" y2="180" class="edge"/>'
        '<line x1="400" y1="235" x2="400" y2="277" class="edge"/>'
        # Calendario (top)
        '<g transform="translate(320, 37)">'
        '  <rect width="160" height="46" class="node-dim"/>'
        '  <text x="80" y="20" class="node-name">CALENDARIO</text>'
        f'  <text x="80" y="38" class="node-count">{_f(dim_date)} días</text>'
        '</g>'
        # Clientes (left)
        '<g transform="translate(30, 157)">'
        '  <rect width="160" height="46" class="node-dim"/>'
        '  <text x="80" y="20" class="node-name">CLIENTES</text>'
        f'  <text x="80" y="38" class="node-count">{_f(dim_customer)}</text>'
        '</g>'
        # Productos (right)
        '<g transform="translate(610, 157)">'
        '  <rect width="160" height="46" class="node-dim"/>'
        '  <text x="80" y="20" class="node-name">PRODUCTOS</text>'
        f'  <text x="80" y="38" class="node-count">{_f(dim_product)}</text>'
        '</g>'
        # Ventas (fact center)
        '<g transform="translate(300, 125)">'
        '  <rect width="200" height="110" class="node-fact"/>'
        '  <text x="100" y="34" class="fact-name">VENTAS</text>'
        f'  <text x="100" y="68" class="fact-count">{_f(fact_sales)}</text>'
        f'  <text x="100" y="92" class="fact-meta">+ {_f(fact_returns)} devoluciones</text>'
        '</g>'
        # Tiendas (bottom)
        '<g transform="translate(320, 277)">'
        '  <rect width="160" height="46" class="node-dim"/>'
        '  <text x="80" y="20" class="node-name">TIENDAS</text>'
        f'  <text x="80" y="38" class="node-count">{_f(dim_store)}</text>'
        '</g>'
        # Caption "Derivados de Ventas"
        '<text x="400" y="348" class="downstream-label">DERIVADOS DE VENTAS</text>'
        # Modelos (CLTV + Segmentos)
        '<g transform="translate(180, 360)">'
        '  <rect width="440" height="60" class="node-model"/>'
        '  <line x1="220" y1="12" x2="220" y2="48" class="model-sep"/>'
        '  <text x="110" y="28" class="model-name">CLTV</text>'
        f'  <text x="110" y="46" class="model-count">{_f(mart_cltv)}</text>'
        '  <text x="330" y="28" class="model-name">SEGMENTOS</text>'
        f'  <text x="330" y="46" class="model-count">{_f(mart_segments)}</text>'
        '</g>'
        '</svg>'
        '</div>'
    )


def inv_groups(groups: list[tuple[str, list[tuple[int | str, str]]]]) -> str:
    """Inventario editorial: lista de grupos. Cada grupo es:
        (nombre_del_grupo, [(value, noun), (value, noun), ...])
    Ej.:
        [
          ("Catálogos", [(5750, "clientes"), (50, "productos"), (20, "tiendas")]),
          ("Movimientos", [(42555, "ventas"), (2330, "devoluciones")]),
        ]
    """
    def _fmt(v) -> str:
        if isinstance(v, (int, float)):
            return f"{int(v):,}".replace(",", " ")
        return str(v)

    rows = []
    for head, items in groups:
        body_parts = []
        for i, (v, noun) in enumerate(items):
            if i > 0:
                body_parts.append('<span class="sep">·</span>')
            body_parts.append(
                f'<span class="it"><span class="v">{_fmt(v)}</span>'
                f'{_html.escape(noun)}</span>'
            )
        rows.append(
            f'<div class="inv-group">'
            f'  <div class="inv-group-head">{_html.escape(head)}</div>'
            f'  <div class="inv-group-body">{"".join(body_parts)}</div>'
            f'</div>'
        )
    return f'<div class="inv-groups">{"".join(rows)}</div>'
