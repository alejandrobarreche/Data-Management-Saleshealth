"""Build del dashboard SalesHealth como HTML estático.

Uso:
    conda run -n UAX python -m dashboard.html.build

Genera:
    dashboard/html/index.html

Para personalizar:
- Estilos UI:        edita dashboard/html/style.css
- Colores Plotly:    edita dashboard/html/theme.py
- Layout / copy:     edita dashboard/html/views/<vista>.py
- Estructura página: edita HTML_TEMPLATE en este archivo
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.html import dwh_loader, views  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "index.html"

NAV_ITEMS = [
    ("01", "Visión General",  "overview"),
    ("02", "Clientes",        "clientes"),
    ("03", "Segmentación",    "segmentacion"),
    ("04", "Productos",       "productos"),
    ("05", "Ficha Cliente",   "ficha"),
    ("06", "Metodología",     "metodologia"),
]

FEATURE_COLS = [
    "net_revenue", "margin_rate", "frequency", "retention_rate",
    "aov", "recency_days", "return_rate", "cltv",
]


def _load_artifacts() -> dict:
    cltv = pd.read_parquet(ROOT / "data" / "processed" / "cltv.parquet")
    cm   = pd.read_parquet(ROOT / "data" / "processed" / "customer_metrics.parquet")
    seg  = pd.read_parquet(ROOT / "models" / "customer_segments.parquet")

    pca    = joblib.load(ROOT / "models" / "pca.joblib")
    scaler = joblib.load(ROOT / "models" / "scaler.joblib")

    pca_explained = list(getattr(pca, "explained_variance_ratio_", [0.0, 0.0]))

    X = seg[FEATURE_COLS].astype(float).fillna(0).to_numpy()
    Xs = scaler.transform(X)
    Xp = pca.transform(Xs)
    elbow = {k: float(KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xp).inertia_)
             for k in range(2, 9)}

    return {"cltv": cltv, "cm": cm, "seg": seg, "pca_explained": pca_explained, "elbow": elbow}


HTML_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Estudio de negocio · SalesHealth</title>
  <link rel="stylesheet" href="style.css">
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
</head>
<body>
  <div class="page">
    <!-- OLD proj-hero (título 64px "Estudio de negocio…") — DESACTIVADO
         Para restaurar el hero antiguo, borra esta línea de comentario y la
         "PROJ-HERO END" de abajo.
    <header class="proj-hero">
      <div class="proj-hero-eyebrow">GESTIÓN DE DATOS · UAX 2025/26</div>
      <h1 class="proj-hero-title">Estudio de negocio de SalesHealth</h1>
    </header>
    PROJ-HERO END -->

    <!-- NEW · masthead (línea fina arriba) -->
    <header class="masthead">
      <div class="masthead-mark">SalesHealth<span class="dot">.</span></div>
      <div class="masthead-meta">
        <span class="status {status_cls}"><span class="dot"></span>{mode_label}</span>
        <span>Gestión de Datos · UAX 2025/26</span>
      </div>
    </header>

    <!-- NEW · opener (título neutro, no-insight) -->
    <section class="opener">
      <p class="kicker">SalesHealth — un estudio de</p>
      <h1 class="headline">Comportamiento de compra.</h1>
      <p class="deck">
        Sobre <strong>{n_clients}</strong> clientes y <strong>{n_compras}</strong>
        compras, entre <strong>{year_min}</strong> y <strong>{year_max}</strong>.
        Seis capítulos.
      </p>
    </section>

    <!-- ACTIVE · OLD nav liquid pill -->
    <div class="tabs-liquid-wrap">
      <nav class="tabs-liquid no-anim" role="tablist" id="nav">
        <span class="tabs-liquid-pill" aria-hidden="true"></span>
        {nav_buttons}
      </nav>
    </div>

    <!-- NEW · chapter-index (nav editorial) — DESACTIVADO
         Para restaurar: borra esta línea y la "chapter-index END" de abajo.
         También hay que comentar el liquid-pill de arriba y conmutar la IIFE.
    <nav class="chapter-index" role="tablist" id="nav">
      {chapter_index}
    </nav>
    chapter-index END -->

    <main id="main">
      {views_html}
    </main>
  </div>

  <footer class="footer-sticky">
    <div class="l">
      <span>⚗</span>
      <span>Dataset sintético · no usar en producción</span>
    </div>
    <div class="pill-syn"><span class="dot"></span>Δ Dataset sintético · UAX 2025/26</div>
    <div class="r" id="footer-right">{footer_right}</div>
  </footer>

  <script>
  // ── ACTIVE · OLD nav liquid pill (port vanilla del componente TabsLiquid) ──
  (function() {{
    const wrap = document.getElementById('nav');
    if (!wrap) return;
    const pill = wrap.querySelector('.tabs-liquid-pill');
    const tabs = wrap.querySelectorAll('.tab-liquid');
    const views = document.querySelectorAll('.view');

    function movePill(el) {{
      if (!el) return;
      const wr = wrap.getBoundingClientRect();
      const er = el.getBoundingClientRect();
      const x = er.left - wr.left + wrap.scrollLeft;
      pill.style.transform = 'translateX(' + x + 'px)';
      pill.style.width = er.width + 'px';
    }}

    function show(slug, opts) {{
      opts = opts || {{}};
      let target = null;
      tabs.forEach(t => {{
        const on = t.dataset.view === slug;
        t.classList.toggle('active', on);
        t.setAttribute('aria-current', on ? 'page' : 'false');
        if (on) target = t;
      }});
      views.forEach(v => v.classList.toggle('active', v.id === 'view-' + slug));
      try {{ history.replaceState(null, '', '#' + slug); }} catch(e) {{}}
      requestAnimationFrame(() => {{
        movePill(target);
        // Resize de los plotly de la vista recién mostrada — cuando estaba
        // hidden (display:none), el ancho computado era 0 y los charts
        // nacieron pequeños. requestAnimationFrame() asegura que el layout
        // ya se aplicó antes de medir.
        const activeView = document.getElementById('view-' + slug);
        if (activeView && window.Plotly) {{
          activeView.querySelectorAll('.plotly-graph-div').forEach(g => {{
            try {{ Plotly.Plots.resize(g); }} catch(e) {{}}
          }});
        }}
      }});
    }}

    tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.view)));
    window.addEventListener('resize', () => {{
      const cur = wrap.querySelector('.tab-liquid.active');
      movePill(cur);
    }});

    const initial = (location.hash || '#overview').slice(1);
    show(initial);
    if (document.fonts && document.fonts.ready) {{
      document.fonts.ready.then(() => {{
        const cur = wrap.querySelector('.tab-liquid.active');
        movePill(cur);
        wrap.classList.remove('no-anim');
      }});
    }} else {{
      setTimeout(() => wrap.classList.remove('no-anim'), 50);
    }}
  }})();

  // ╔══════════════════════════════════════════════════════════════════════╗
  // ║ NEW chapter-index nav — DESACTIVADO                                  ║
  // ║ Para restaurar: borra los delimitadores /* NEW ... NEW END */ que    ║
  // ║ envuelven la IIFE, y comenta el liquid pill de arriba.               ║
  // ╚══════════════════════════════════════════════════════════════════════╝
  /* NEW
  (function() {{
    const nav = document.getElementById('nav');
    if (!nav) return;
    const chapters = nav.querySelectorAll('.chapter');
    const views = document.querySelectorAll('.view');

    function show(slug) {{
      chapters.forEach(c => {{
        const on = c.dataset.view === slug;
        c.classList.toggle('active', on);
        c.setAttribute('aria-current', on ? 'page' : 'false');
      }});
      views.forEach(v => v.classList.toggle('active', v.id === 'view-' + slug));
      try {{ history.replaceState(null, '', '#' + slug); }} catch(e) {{}}
    }}

    chapters.forEach(c => c.addEventListener('click', (e) => {{
      e.preventDefault();
      show(c.dataset.view);
    }}));
    const initial = (location.hash || '#overview').slice(1);
    show(initial);
  }})();
  NEW END */

  // ── Tabs (vista 02 - distribución del CLTV) ───────────────────────────────
  (function() {{
    document.querySelectorAll('.tabs-bar').forEach(bar => {{
      const buttons = bar.querySelectorAll('.tab-btn');
      const panels = bar.parentElement.querySelectorAll('.tab-panel');
      buttons.forEach(btn => {{
        btn.addEventListener('click', () => {{
          buttons.forEach(b => b.setAttribute('aria-selected', b === btn ? 'true' : 'false'));
          panels.forEach(p => p.hidden = (p.dataset.panel !== btn.dataset.tab));
          // Plotly necesita resize cuando se le hace visible un div oculto
          panels.forEach(p => {{
            if (!p.hidden) {{
              p.querySelectorAll('.plotly-graph-div').forEach(g => {{
                if (window.Plotly) Plotly.Plots.resize(g);
              }});
            }}
          }});
        }});
      }});
    }});
  }})();

  // ── Selector de ficha de cliente (vista 05) ───────────────────────────────
  (function() {{
    const sel = document.getElementById('ficha-select');
    if (!sel) return;
    const panels = document.querySelectorAll('.ficha-panel');
    sel.addEventListener('change', () => {{
      panels.forEach(p => p.hidden = (p.dataset.ficha !== sel.value));
      // resize de los plotly visibles
      panels.forEach(p => {{
        if (!p.hidden) {{
          p.querySelectorAll('.plotly-graph-div').forEach(g => {{
            if (window.Plotly) Plotly.Plots.resize(g);
          }});
        }}
      }});
    }});
  }})();

  // ── Resize global (cinturón de seguridad: corrige el chart que nace
  //    pequeño cuando el flex/grid aún no tenía ancho calculado) ─────────────
  // Solo resizea los charts VISIBLES — disparar Plotly.Plots.resize sobre un
  // elemento display:none lo colapsa a 0px y queda roto cuando se muestre.
  function resizeVisiblePlotly() {{
    if (!window.Plotly) return;
    document.querySelectorAll('.plotly-graph-div').forEach(g => {{
      if (g.offsetParent === null) return;     // hidden: skip
      try {{ Plotly.Plots.resize(g); }} catch(e) {{}}
    }});
  }}
  window.addEventListener('load', () => {{
    // dos pasadas: una inmediata, otra tras el primer paint completo
    resizeVisiblePlotly();
    requestAnimationFrame(() => requestAnimationFrame(resizeVisiblePlotly));
  }});
  window.addEventListener('resize', resizeVisiblePlotly);
  </script>

  <style>
  /* ── Tabs (overrides puntuales — viven aquí porque son sólo de la vista 02) ── */
  .tab-btn {{
    background: var(--bg-subtle); border: 1px solid var(--border);
    color: var(--ink-muted); font-family: var(--font-text); font-size: 13px;
    padding: 6px 14px; border-radius: 7px; cursor: pointer;
  }}
  .tab-btn[aria-selected="true"] {{
    background: var(--bg-card); color: var(--ink); box-shadow: var(--shadow-sm);
  }}
  </style>
</body>
</html>
"""


def _nav_buttons() -> str:
    """OLD — usado por el nav liquid pill desactivado."""
    parts = []
    for num, label, slug in NAV_ITEMS:
        parts.append(
            f'<button class="tab-liquid" data-view="{slug}" type="button">'
            f'<span class="num">{num}</span><span>{label}</span>'
            f'</button>'
        )
    return "\n        ".join(parts)


_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _chapter_index() -> str:
    """NEW — nav editorial: capítulos con número romano + label en serif."""
    parts = []
    for (num, label, slug), roman in zip(NAV_ITEMS, _ROMAN):
        parts.append(
            f'<a class="chapter" data-view="{slug}" href="#{slug}">'
            f'<span class="num">{roman}.</span>'
            f'<span class="label">{label}</span>'
            f'</a>'
        )
    return "\n      ".join(parts)


def _format_int_es(n: int) -> str:
    """5750 → '5 750' (separador de miles a la española)."""
    return f"{int(n):,}".replace(",", " ")


def _opener_data(seg) -> dict:
    """Cifras reales del hallazgo principal — leídas del parquet."""
    n_total = len(seg)
    n_freq1 = int((seg["frequency"] == 1).sum())
    pct_freq1 = round(n_freq1 / n_total * 100) if n_total else 0
    n_compras = int(seg["frequency"].sum())
    first = seg["first_purchase"]
    last = seg["last_purchase"]
    import pandas as _pd
    year_min = int(_pd.to_datetime(first).min().year)
    year_max = int(_pd.to_datetime(last).max().year)
    return {
        "pct_freq1": pct_freq1,
        "pct_remaining": 100 - pct_freq1,
        "n_clients": _format_int_es(n_total),
        "n_compras": _format_int_es(n_compras),
        "year_min": year_min,
        "year_max": year_max,
    }


def _load_dwh_bundle() -> dict:
    """Carga TODO lo que necesitan Overview D-H y Productos. Devuelve None si Postgres falla."""
    if not dwh_loader.probe_postgres():
        return None
    period = dwh_loader.load_default_period()
    period_prev = dwh_loader._prev_window(*period)
    return {
        "online": True,
        "period": period,
        "kpis":      dwh_loader.load_kpis(*period),
        "kpis_prev": dwh_loader.load_kpis(*period_prev),
        "daily":       dwh_loader.load_daily_sales(*period),
        "by_category": dwh_loader.load_revenue_by_category(*period),
        "by_brand":    dwh_loader.load_revenue_by_brand(*period),
        "monthly":     dwh_loader.load_monthly_year(*period),
        "top_stores":  dwh_loader.load_top_stores(*period),
        "top_products": dwh_loader.load_top_products(*period, limit=15),
        "returns_breakdown":  dwh_loader.load_returns_breakdown(*period),
        "returns_by_product": dwh_loader.load_returns_by_product(*period, limit=15),
        "zero_cost_skus": dwh_loader.load_zero_cost_skus(),
        "dwh_counts":     dwh_loader.load_inventory_counts(),
    }


def main() -> None:
    art = _load_artifacts()

    cltv, cm, seg = art["cltv"], art["cm"], art["seg"]
    pca_explained = art["pca_explained"]
    elbow = art["elbow"]

    # asegura que segments tiene aov / margin_rate (algunos parquets podrían no tenerlo)
    if "aov" not in seg.columns and "frequency" in seg.columns:
        seg = seg.copy()
        seg["aov"] = seg["gross_revenue"] / seg["frequency"].replace(0, np.nan)

    dwh = _load_dwh_bundle()
    online = dwh is not None
    print(f"[mode] {'ONLINE — DWH disponible' if online else 'OFFLINE — Postgres no responde'}")

    if online:
        overview_html = views.render_overview(
            cltv=cltv, cm=cm, seg=seg,
            offline=False,
            kpis=dwh["kpis"], kpis_prev=dwh["kpis_prev"], period=dwh["period"],
            daily=dwh["daily"], by_category=dwh["by_category"],
            by_brand=dwh["by_brand"], monthly=dwh["monthly"],
            top_stores=dwh["top_stores"], dwh_counts=dwh["dwh_counts"],
        )
        productos_html = views.render_productos(
            offline=False,
            kpis=dwh["kpis"], period=dwh["period"],
            top_products=dwh["top_products"],
            returns_breakdown=dwh["returns_breakdown"],
            returns_by_product=dwh["returns_by_product"],
            zero_cost_skus=dwh["zero_cost_skus"],
        )
    else:
        overview_html = views.render_overview(cltv=cltv, cm=cm, seg=seg, offline=True)
        productos_html = views.render_productos(offline=True)

    views_html = "\n".join([
        overview_html,
        views.render_clientes(segments=seg),
        views.render_segmentacion(segments=seg, pca_explained=pca_explained),
        productos_html,
        views.render_ficha(segments=seg),
        views.render_metodologia(segments=seg, pca_explained=pca_explained, elbow=elbow),
    ])

    period = (
        f"{pd.to_datetime(seg['first_purchase']).min():%Y-%m} → "
        f"{pd.to_datetime(seg['last_purchase']).max():%Y-%m}"
    )
    n_lineas = int(seg["frequency"].sum())
    footer_right = (
        f"{period} · {len(seg):,} clientes · {n_lineas:,} líneas".replace(",", " ")
    )

    op = _opener_data(seg)
    mode_label = "vivo" if online else "offline"
    status_cls = "" if online else "offline"

    html_out = HTML_TEMPLATE.format(
        nav_buttons=_nav_buttons(),       # legacy — solo se usa si descomentas el OLD nav
        chapter_index=_chapter_index(),
        views_html=views_html,
        footer_right=footer_right,
        mode_label=mode_label,
        status_cls=status_cls,
        pct_freq1=op["pct_freq1"],
        pct_remaining=op["pct_remaining"],
        n_clients=op["n_clients"],
        n_compras=op["n_compras"],
        year_min=op["year_min"],
        year_max=op["year_max"],
    )
    OUT_PATH.write_text(html_out, encoding="utf-8")
    print(f"[OK] Generado {OUT_PATH}  ({OUT_PATH.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
