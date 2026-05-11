"""Paleta SalesHealth + plantilla Plotly para el dashboard HTML.

Para cambiar colores o tipografías de las gráficas, edita este archivo.
Para cambiar la UI no-gráfica (cards, KPIs, tablas, hero…), edita style.css.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio


# ── Tokens (deben coincidir con :root en style.css) ─────────────────────────
PRIMARY     = "#2563EB"
ACCENT_TEAL = "#0EA5A5"
SUCCESS     = "#16A34A"
WARNING     = "#F59E0B"
DANGER      = "#EF4444"
INFO        = "#3B82F6"

INK         = "#0B1F33"
INK_MUTED   = "#4A5A6A"
INK_SOFT    = "#8A97A6"
BORDER      = "#E6EAEF"
BORDER_STR  = "#D5DCE4"

CLUSTER_COLORS = {0: "#94A3B8", 1: "#0EA5A5", 2: "#F97316"}
CLUSTER_LABELS = {0: "Ocasionales", 1: "VIP / Recurrentes", 2: "Devoluciones"}

CATEGORY_COLORS = {
    "Diagnóstico":    "#0EA5A5",
    "Wellness":       "#3B82F6",
    "Movilidad":      "#A855F7",
    "Rehabilitación": "#F59E0B",
    "Tratamiento":    "#EF4444",
}

QUAL = [PRIMARY, ACCENT_TEAL, "#A855F7", WARNING, "#F97316", SUCCESS, DANGER, "#EC4899"]

# Escalas SECUENCIALES — paleta unificada azul mono (claro → oscuro).
# Para lo que NO es semántico (clusters, categorías), usar SEQ_BLUE en todo.
SEQ_BLUE = ["#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6", "#2563EB", "#1D4ED8"]
PRIMARY_LIGHT = "#60A5FA"   # azul claro — para segundos planos en charts azules

# Legacy (mantenidas por si queremos restaurar el look anterior). NO usar
# por defecto en gráficos nuevos — sustituir por SEQ_BLUE.
SEQ_TEAL = ["#E6F7F7", "#B5E5E5", "#7ED2D2", "#3FB8B8", "#0EA5A5", "#0B7A7A"]
SEQ_TEAL_CORAL = ["#0EA5A5", "#5BC4B0", "#A8DCB6", "#F4DDB1", "#F8B98E", "#F97316"]


# ── Plotly template "saleshealth" ───────────────────────────────────────────
PLOTLY_TEMPLATE = go.layout.Template()
PLOTLY_TEMPLATE.layout = dict(
    font=dict(family="Inter, system-ui, sans-serif", size=12, color=INK_MUTED),
    title=dict(
        text="",
        font=dict(family="Inter, sans-serif", size=15, color=INK),
        x=0.0, xanchor="left", y=0.97, yanchor="top",
        pad=dict(t=4, l=4),
    ),
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    colorway=QUAL,
    margin=dict(l=16, r=16, t=56, b=40),
    xaxis=dict(
        gridcolor=BORDER, zerolinecolor=BORDER_STR, linecolor=BORDER_STR,
        tickcolor=BORDER_STR, tickfont=dict(color=INK_SOFT, size=11),
        showgrid=False,
    ),
    yaxis=dict(
        gridcolor=BORDER, zerolinecolor=BORDER_STR, linecolor=BORDER_STR,
        tickcolor=BORDER_STR, tickfont=dict(color=INK_SOFT, size=11),
        showgrid=True, automargin=True,
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.9)", bordercolor=BORDER, borderwidth=0,
        font=dict(color=INK_MUTED, size=11),
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
    ),
    hoverlabel=dict(
        bgcolor="white", bordercolor=ACCENT_TEAL,
        font=dict(color=INK, family="Inter, sans-serif", size=12),
    ),
)
pio.templates["saleshealth"] = PLOTLY_TEMPLATE
pio.templates.default = "saleshealth"


def apply_chart(
    fig: go.Figure,
    *,
    title: str = " ",
    height: int | None = None,
    margin: dict | None = None,
    hovermode: str | bool = "x unified",
) -> go.Figure:
    """Aplica el template SalesHealth + título obligatorio (puede ser ' ')."""
    fig.update_layout(template="saleshealth", title_text=title, hovermode=hovermode)
    if margin:
        fig.update_layout(margin=margin)
    if height is not None:
        fig.update_layout(height=height)
    return fig


# ── Formatters ──────────────────────────────────────────────────────────────
def fmt_money(v: float, *, currency: str = "€", short: bool = False) -> str:
    if v is None:
        return "—"
    if short:
        if abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f} M{currency}".replace(",", " ").replace(".", ",")
        if abs(v) >= 1_000:     return f"{v/1_000:,.1f} k{currency}".replace(",", " ").replace(".", ",")
    return f"{v:,.2f} {currency}".replace(",", " ").replace(".", ",")


def fmt_int(v: float | int) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}".replace(",", " ")


def fmt_pct(v: float, *, decimals: int = 1) -> str:
    if v is None:
        return "—"
    s = f"{v*100:,.{decimals}f}%"
    return s.replace(",", "X").replace(".", ",").replace("X", " ")


def fmt_num(v: float, *, decimals: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", " ")
