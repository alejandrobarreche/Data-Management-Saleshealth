"""Vista 03 · Segmentación (PCA + KMeans)."""
from __future__ import annotations

import html as _html

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .. import helpers as h
from .. import theme

FEATURE_COLS = [
    "net_revenue", "margin_rate", "frequency", "retention_rate",
    "aov", "recency_days", "return_rate", "cltv",
]

# Etiquetas amigables para gráficos (no romper el nombre de la columna real
# en `FEATURE_COLS`, sólo lo que ve el lector).
FEATURE_LABELS = {
    "net_revenue":   "Ingresos",
    "margin_rate":   "Margen",
    "frequency":     "Frecuencia",
    "retention_rate": "Retención",
    "aov":           "Ticket medio",
    "recency_days":  "Recencia",
    "return_rate":   "Devolución",
    "cltv":          "CLTV",
}


def _compute_prototype(sub: pd.DataFrame) -> dict | None:
    """Cliente más cercano al centroide del cluster en el espacio PCA."""
    if sub.empty or "pc1" not in sub.columns or "pc2" not in sub.columns:
        return None
    cx, cy = float(sub["pc1"].mean()), float(sub["pc2"].mean())
    d = np.sqrt((sub["pc1"] - cx) ** 2 + (sub["pc2"] - cy) ** 2)
    idx = d.idxmin()
    p = sub.loc[idx]
    return {
        "customer_id":  int(p["customer_id"]),
        "full_name":    str(p.get("full_name") or "—"),
        "cltv_str":     theme.fmt_money(float(p["cltv"]), short=True),
        "frequency":    int(p["frequency"]),
        "recency_days": int(p["recency_days"]),
    }


def _cluster_overview_cards(df: pd.DataFrame) -> str:
    cards = []
    n_total = len(df)
    cltv_total = df["cltv"].sum() if "cltv" in df else 0
    for c in sorted(df["cluster"].unique()):
        s = df[df["cluster"] == c]
        n = len(s)
        cards.append(h.cluster_card(
            int(c),
            n=n,
            base_pct=n / n_total if n_total else 0,
            cltv_pct=(s["cltv"].sum() / cltv_total) if cltv_total else 0,
            cltv_med=theme.fmt_money(s["cltv"].median(), short=True),
            freq_med=theme.fmt_num(s["frequency"].median(), decimals=0),
            recency_med=f"{int(s['recency_days'].median())} d",
            return_med=theme.fmt_pct(s["return_rate"].median()),
            prototype=_compute_prototype(s),
            clickable=True,
        ))
    return h.grid(cards, cols=3)


def _scatter_pca(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for c in sorted(df["cluster"].unique()):
        s = df[df["cluster"] == c]
        # customdata: nombre, cltv, freq, recency, customer_id (el último es el que
        # usa el JS para navegar a la ficha).
        fig.add_trace(go.Scatter(
            x=s["pc1"], y=s["pc2"], mode="markers",
            marker=dict(color=theme.CLUSTER_COLORS.get(c, theme.PRIMARY),
                        size=7, opacity=0.6, line=dict(width=0)),
            name=theme.CLUSTER_LABELS.get(c, f"Cluster {c}"),
            customdata=np.stack([
                s["full_name"].fillna("—").values,
                s["cltv"].values,
                s["frequency"].values,
                s["recency_days"].values,
                s["customer_id"].astype(int).values,
            ], axis=1),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "PC1=%{x:.2f} · PC2=%{y:.2f}<br>"
                "CLTV: %{customdata[1]:,.0f} €<br>"
                "Compras: %{customdata[2]:.0f}<br>"
                "Recencia: %{customdata[3]:.0f} d<br>"
                "<i>click → abre ficha</i><extra></extra>"
            ),
        ))
    theme.apply_chart(fig, title=" ", height=460, hovermode="closest")
    fig.update_layout(
        xaxis_title="PC1 — monetario + frecuencia",
        yaxis_title="PC2 — recencia − devolución",
        # Leyenda ARRIBA del gráfico, fuera del área del plot —
        # el suelo queda libre para el título del eje X.
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font=dict(size=12),
        ),
        margin=dict(l=20, r=20, t=70, b=60),
    )
    return fig


def _donut_size(df: pd.DataFrame) -> go.Figure:
    grp = df.groupby("cluster").size().reset_index(name="n")
    grp["label"] = grp["cluster"].map(theme.CLUSTER_LABELS)
    fig = go.Figure(go.Pie(
        labels=grp["label"], values=grp["n"], hole=0.55,
        marker=dict(colors=[theme.CLUSTER_COLORS[c] for c in grp["cluster"]],
                    line=dict(color="#fff", width=2)),
        textinfo="percent", textposition="inside",
        insidetextfont=dict(color="#fff", size=12, family="Inter, sans-serif"),
        hovertemplate="<b>%{label}</b><br>%{value:,} clientes (%{percent})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{len(df):,}</b><br><span style='font-size:11px;color:{theme.INK_SOFT}'>clientes</span>",
                       showarrow=False, x=0.5, y=0.5, font=dict(color=theme.INK, size=18))
    theme.apply_chart(fig, title=" ", height=380, hovermode="closest")
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", font=dict(size=12)),
        margin=dict(l=10, r=10, t=20, b=80),
    )
    return fig


def _donut_variance(pca_explained: list[float]) -> go.Figure:
    pc1 = float(pca_explained[0]) if len(pca_explained) > 0 else 0.0
    pc2 = float(pca_explained[1]) if len(pca_explained) > 1 else 0.0
    total = pc1 + pc2
    rest = max(0.0, 1.0 - total)
    fig = go.Figure(go.Pie(
        labels=["PC1", "PC2", "Resto"],
        values=[pc1, pc2, rest], hole=0.55,
        marker=dict(colors=[theme.PRIMARY, theme.PRIMARY_LIGHT, theme.BORDER_STR],
                    line=dict(color="#fff", width=2)),
        textinfo="percent", textposition="inside",
        insidetextfont=dict(color="#fff", size=12, family="Inter, sans-serif"),
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{total*100:.1f}%</b><br><span style='font-size:11px;color:{theme.INK_SOFT}'>cubierta</span>",
                       showarrow=False, x=0.5, y=0.5, font=dict(color=theme.INK, size=18))
    theme.apply_chart(fig, title=" ", height=380, hovermode="closest")
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0.5, xanchor="center", font=dict(size=12)),
        margin=dict(l=10, r=10, t=20, b=80),
    )
    return fig


def _loadings_heatmap(loadings: np.ndarray, feature_cols: list[str]) -> go.Figure:
    """Heatmap 8×2 de cargas factoriales — Carga = vᵢⱼ · √λⱼ.

    Las cargas leen qué variable pesa en cada componente. Color rojo/azul:
    correlación positiva/negativa entre la feature y la componente.
    """
    labels_y = [FEATURE_LABELS.get(c, c) for c in feature_cols]
    fig = go.Figure(go.Heatmap(
        z=loadings, x=["PC1", "PC2"], y=labels_y,
        colorscale="RdBu", zmid=0,
        colorbar=dict(title="carga", thickness=10, len=0.8, tickfont=dict(size=10)),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>",
        text=np.round(loadings, 2), texttemplate="%{text}",
        textfont=dict(size=12, color=theme.INK),
    ))
    theme.apply_chart(fig, title=" ", height=360, hovermode="closest")
    fig.update_layout(
        xaxis=dict(side="top", tickfont=dict(size=13, color=theme.INK), tickangle=0),
        yaxis=dict(tickfont=dict(size=12), autorange="reversed"),
        margin=dict(l=10, r=80, t=40, b=20),
    )
    return fig


def _z_heatmap(df: pd.DataFrame) -> go.Figure:
    means = df[FEATURE_COLS].mean()
    stds = df[FEATURE_COLS].std().replace(0, 1)
    profile = df.groupby("cluster")[FEATURE_COLS].mean()
    z = (profile - means) / stds
    labels_y = [theme.CLUSTER_LABELS.get(c, f"C{c}") for c in z.index]
    labels_x = [FEATURE_LABELS.get(c, c) for c in FEATURE_COLS]

    fig = go.Figure(go.Heatmap(
        z=z.values, x=labels_x, y=labels_y,
        colorscale="RdBu", zmid=0,
        colorbar=dict(title="z-score", thickness=10, len=0.8, tickfont=dict(size=10)),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>",
        text=z.round(2).values, texttemplate="%{text}",
        textfont=dict(size=12, color=theme.INK),
    ))
    theme.apply_chart(fig, title=" ", height=320, hovermode="closest")
    fig.update_layout(
        xaxis=dict(side="bottom", tickfont=dict(size=12), tickangle=0),
        yaxis=dict(tickfont=dict(size=12)),
        margin=dict(l=10, r=80, t=20, b=40),
    )
    return fig


def _characterization_table(df: pd.DataFrame) -> str:
    n_total = len(df)
    cltv_total = df["cltv"].sum()
    rows = []
    for c in sorted(df["cluster"].unique()):
        s = df[df["cluster"] == c]
        rows.append((
            int(c),
            len(s),
            len(s) / n_total if n_total else 0,
            (s["cltv"].sum() / cltv_total) if cltv_total else 0,
            s["cltv"].median(),
            s["frequency"].median(),
            s["recency_days"].median(),
            s["return_rate"].median(),
        ))
    body = []
    for c, n, base, cltv, cm, fm, rm, retm in rows:
        body.append(
            f"<tr>"
            f"<td>{h.cluster_chip(c)}</td>"
            f"<td class='num'>{n:,}</td>"
            f"<td class='num'>{base*100:.1f}%</td>"
            f"<td class='num'>{cltv*100:.1f}%</td>"
            f"<td class='num'>{theme.fmt_money(cm, short=True)}</td>"
            f"<td class='num'>{theme.fmt_num(fm, decimals=0)}</td>"
            f"<td class='num'>{int(rm)} d</td>"
            f"<td class='num'>{theme.fmt_pct(retm)}</td>"
            f"</tr>"
        )
    return (
        f'<div class="tbl-wrap">'
        f'<table class="tbl">'
        f'<thead><tr>'
        f'<th>Cluster</th>'
        f'<th class="num">Tamaño</th><th class="num">% base</th><th class="num">% CLTV</th>'
        f'<th class="num">CLTV mediana</th><th class="num">Frecuencia</th>'
        f'<th class="num">Recencia</th><th class="num">Tasa dev.</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(body)}</tbody>'
        f'</table>'
        f'</div>'
    )


def render(
    segments: pd.DataFrame,
    pca_explained: list[float] | None = None,
    *,
    loadings: np.ndarray | None = None,
    feature_cols: list[str] | None = None,
) -> str:
    df = segments.copy()
    pca_explained = pca_explained or [0.0, 0.0]
    total_var = (pca_explained[0] + pca_explained[1]) if len(pca_explained) >= 2 else 0.0

    var_str = theme.fmt_num(total_var * 100, decimals=1)

    parts: list[str] = []
    parts.append(h.chapter_opener(
        marker="Capítulo III",
        eyebrow="III · SEGMENTACIÓN",
        headline="Segmentación.",
        deck=(
            f"PCA(2) sobre 8 features estandarizadas (cobertura "
            f"<strong>{var_str}&nbsp;%</strong>), KMeans con k = 3 y "
            "caracterización por cluster en heatmap z-score."
        ),
        analytics=["diagnostic", "predictive"],
    ))

    parts.append(h.section_h("A", "Cluster overview", "click en una card para drill-down"))
    parts.append(_cluster_overview_cards(df))
    parts.append(h.explain(
        "Cada cluster lleva su prototipo — el cliente más cercano al centroide. "
        "Click en la card abre el panel detallado abajo; «Ver ficha» te lleva al cliente."
    ))
    # Panel drill-down (vacío hasta que el usuario hace click)
    parts.append('<div id="cluster-detail" class="cluster-detail" hidden></div>')

    parts.append(h.section_h("B", "Mapa PCA y composición", "PCA(2) · KMeans(k=3)"))
    # PCA scatter a ancho completo — necesita el espacio para las leyendas y los puntos
    parts.append(h.card(
        header="Mapa PCA — separación geométrica",
        body_html=h.fig_html(_scatter_pca(df), frame=False) +
                  h.explain("PC1 ≈ monetario + frecuencia; PC2 ≈ recencia − tasa devolución. "
                            "La posición de cada cliente en el plano resume las 8 features."),
    ))
    # Heatmap de cargas factoriales — la "lectura" de qué significa cada eje.
    # Sólo se renderiza si build.py pasa la matriz de cargas (pca.components_.T · √λ).
    if loadings is not None and feature_cols is not None:
        parts.append(h.card(
            header="Cargas factoriales — qué significa cada eje",
            meta="Carga = vᵢⱼ · √λⱼ",
            body_html=h.fig_html(_loadings_heatmap(loadings, feature_cols), frame=False) +
                      h.explain(
                          "Cada celda es la correlación entre la feature y la componente. "
                          "PC1 carga alto en Ingresos, CLTV y Frecuencia → eje «valor». "
                          "PC2 carga alto en Devolución y Recencia → eje «fricción». "
                          "Así se justifica por qué la separación geométrica del scatter de arriba "
                          "tiene sentido de negocio."),
        ))
    # Los dos donuts en su propia fila — leyendas no se aprietan
    parts.append(h.grid([
        h.card(header="Tamaño de cluster",
               body_html=h.fig_html(_donut_size(df), frame=False)),
        h.card(header="Varianza explicada",
               body_html=h.fig_html(_donut_variance(pca_explained), frame=False) +
                         h.explain(f"PCA(2) cubre el {total_var*100:.1f}%. El resto de la varianza "
                                   "vive en dimensiones que no se ven en este plano — un coste asumido del 2D.")),
    ], cols=2))

    parts.append(h.section_h("C", "Caracterización + heatmap z-score", "8 features"))
    # Tabla y heatmap apilados (full width cada uno) — la tabla cabe sin apretar
    # las cabeceras y el heatmap deja respirar a las 8 features.
    parts.append(h.card(
        header="Tabla de caracterización",
        body_html=_characterization_table(df) +
                  h.explain("Tabla para lectura literal: tamaño, % base, peso en CLTV y "
                            "medianas de los KPIs clave por cluster."),
    ))
    parts.append(h.card(
        header="Heatmap z-score por cluster",
        body_html=h.fig_html(_z_heatmap(df), frame=False) +
                  h.explain("Patrón rápido: colores cálidos = cluster por encima de la media "
                            "global; fríos = por debajo. Una mancha roja en (CLTV, Frecuencia, "
                            "Retención) revela inmediatamente al cluster VIP."),
    ))

    # ── Simulador (F): sliders para las 8 features → predict cluster ──
    parts.append(h.section_h("D", "Simulador — ¿a qué cluster pertenecerías?",
                             "modelo cargado en server"))
    parts.append('''
    <div class="card" id="simulator-card">
      <div class="card-h"><h3>Mueve los sliders para componer un cliente ficticio</h3>
        <div class="meta">scaler → PCA(2) → KMeans(k=3)</div>
      </div>
      <div class="simulator-grid" id="sim-grid">
        <div class="sim-loading">Cargando rangos…</div>
      </div>
      <div class="simulator-result" id="sim-result">
        <div class="sim-result-empty">Mueve cualquier slider para ver el cluster predicho.</div>
      </div>
    </div>
    ''')

    # ── JS de la vista (drill-down + scatter click + simulador) ──
    parts.append(_SEGMENTACION_JS)

    return '<section id="view-segmentacion" class="view">' + "".join(parts) + "</section>"


# JS aislado al final del archivo para no enredar el render. Las llamadas
# son a la API Flask: /api/cluster/<id>, /api/cluster/predict, /api/cluster/feature_ranges.
_SEGMENTACION_JS = """
<script>
(function() {
  const $detail = document.getElementById('cluster-detail');
  const $simGrid = document.getElementById('sim-grid');
  const $simRes = document.getElementById('sim-result');

  const CLUSTER_COLORS = {0:'#94A3B8', 1:'#0EA5A5', 2:'#F97316'};
  const CLUSTER_LABELS = {0:'Ocasionales', 1:'VIP / Recurrentes', 2:'Devoluciones'};
  const FEATURE_LABELS = {
    net_revenue: 'Ingresos netos',
    margin_rate: 'Margen',
    frequency: 'Frecuencia (compras)',
    retention_rate: 'Retención',
    aov: 'Ticket medio (AOV)',
    recency_days: 'Recencia (días)',
    return_rate: 'Tasa devolución',
    cltv: 'CLTV',
  };
  const FEATURE_FORMAT = {
    net_revenue: 'money', margin_rate: 'pct', frequency: 'int',
    retention_rate: 'pct', aov: 'money', recency_days: 'int',
    return_rate: 'pct', cltv: 'money',
  };

  const fmtMoney = (v) => v == null ? '—' : (
    Math.abs(v) >= 1e6 ? (v/1e6).toFixed(2).replace('.', ',') + ' M€' :
    Math.abs(v) >= 1e3 ? (v/1e3).toFixed(1).replace('.', ',') + ' k€' :
                         v.toFixed(2).replace('.', ',') + ' €');
  const fmtPct = (v) => v == null ? '—' : (v*100).toFixed(1).replace('.', ',') + '%';
  const fmtInt = (v) => v == null ? '—' : Math.round(v).toLocaleString('es-ES').replace(/,/g, ' ');
  const fmtFeat = (col, v) => {
    const t = FEATURE_FORMAT[col] || 'int';
    return t === 'money' ? fmtMoney(v) : t === 'pct' ? fmtPct(v) : fmtInt(v);
  };
  const escapeHtml = (s) => String(s).replace(/[&<>\"']/g, m => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '\"':'&quot;', \"'\":'&#39;'
  })[m]);

  // ────────────────────────────────────────────────────────────────────
  // (B) Drill-down: click en cluster card → fetch /api/cluster/<id>
  // ────────────────────────────────────────────────────────────────────
  document.querySelectorAll('.cluster-card-clickable').forEach(card => {
    card.addEventListener('click', (ev) => {
      // evita que el botón "Ver ficha" dispare el drill-down
      if (ev.target.closest('.cc-prototype-link')) return;
      const cid = card.dataset.cluster;
      loadClusterDetail(parseInt(cid, 10));
      document.querySelectorAll('.cluster-card-clickable').forEach(c =>
        c.classList.toggle('cluster-card-active', c === card));
    });
  });

  // Botón "Ver ficha" del prototipo
  document.querySelectorAll('.cc-prototype-link').forEach(btn => {
    btn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const cid = btn.dataset.prototypeId;
      navigateToFicha(parseInt(cid, 10));
    });
  });

  async function loadClusterDetail(clusterId) {
    $detail.hidden = false;
    $detail.innerHTML = '<div class=\"cluster-detail-loading\">Cargando cluster…</div>';
    try {
      const r = await fetch(`/api/cluster/${clusterId}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      renderClusterDetail(d);
      $detail.scrollIntoView({behavior: 'smooth', block: 'start'});
    } catch (e) {
      $detail.innerHTML = `<div class=\"cluster-detail-error\">No se pudo cargar el cluster: ${escapeHtml(e.message)}</div>`;
    }
  }

  function renderClusterDetail(d) {
    const c = d.cluster;
    const color = CLUSTER_COLORS[c];
    const label = CLUSTER_LABELS[c];

    // Top customers
    const topCustHtml = (d.top_customers || []).map((p, i) => `
      <button class=\"cluster-detail-row\" data-cid=\"${p.customer_id}\">
        <span class=\"cluster-detail-rank\">${i+1}</span>
        <span class=\"cluster-detail-name\">${escapeHtml(p.full_name || '—')}</span>
        <span class=\"cluster-detail-meta\">
          <span>ID ${p.customer_id}</span>
          <span class=\"sep\">·</span>
          <span>${fmtMoney(p.cltv)}</span>
          <span class=\"sep\">·</span>
          <span>${fmtInt(p.frequency)} compras</span>
        </span>
      </button>
    `).join('');

    // Top products
    const topProdHtml = (d.top_products || []).length === 0
      ? '<div class=\"cluster-detail-empty\">Sin datos del DWH (Postgres offline).</div>'
      : (d.top_products || []).map((p, i) => `
        <div class=\"cluster-detail-row\">
          <span class=\"cluster-detail-rank\">${i+1}</span>
          <span class=\"cluster-detail-name\">${escapeHtml(p.producto || '—')}</span>
          <span class=\"cluster-detail-meta\">
            <span>${escapeHtml(p.categoria || '—')}</span>
            <span class=\"sep\">·</span>
            <span>${fmtMoney(p.ingresos)}</span>
            <span class=\"sep\">·</span>
            <span>${fmtInt(p.unidades)} ud</span>
            <span class=\"sep\">·</span>
            <span>${fmtInt(p.compradores)} compradores</span>
          </span>
        </div>
      `).join('');

    // Profile bars: para cada feature, posición de p50 cluster vs p50 global
    const profileHtml = Object.entries(d.profile || {}).map(([col, q]) => {
      const lbl = FEATURE_LABELS[col] || col;
      const range = (q.p90 - q.p10) || 1;
      const clusterPct = ((q.p50 - q.p10) / range) * 100;
      const globalPct = ((q.global_p50 - q.p10) / range) * 100;
      return `
        <div class=\"cluster-detail-feat\">
          <div class=\"cluster-detail-feat-label\">
            <span>${escapeHtml(lbl)}</span>
            <span class=\"cluster-detail-feat-val\">${fmtFeat(col, q.p50)}</span>
          </div>
          <div class=\"cluster-detail-feat-bar\">
            <div class=\"cluster-detail-feat-fill\" style=\"width:${Math.max(2, Math.min(100, clusterPct))}%; background:${color}\"></div>
            <div class=\"cluster-detail-feat-tick global\" style=\"left:${Math.max(0, Math.min(100, globalPct))}%\"
                 title=\"Mediana global: ${fmtFeat(col, q.global_p50)}\"></div>
          </div>
        </div>
      `;
    }).join('');

    $detail.innerHTML = `
      <div class=\"cluster-detail-header\" style=\"border-left:4px solid ${color}\">
        <div class=\"cluster-detail-title\">
          <span class=\"chip c${c}\"><span class=\"dot\"></span>${escapeHtml(label)}</span>
          <h3>Cluster ${c} — ${escapeHtml(label).toLowerCase()}</h3>
        </div>
        <div class=\"cluster-detail-stats\">
          <div><span class=\"k\">Tamaño</span><span class=\"v\">${fmtInt(d.size)} clientes</span></div>
          <div><span class=\"k\">% base</span><span class=\"v\">${(d.share*100).toFixed(1)}%</span></div>
          <div><span class=\"k\">% CLTV</span><span class=\"v\">${(d.cltv_share*100).toFixed(1)}%</span></div>
        </div>
        <button class=\"cluster-detail-close\" aria-label=\"Cerrar\">×</button>
      </div>

      <div class=\"grid grid-2\" style=\"margin-top:14px\">
        <div class=\"card\">
          <div class=\"card-h\"><h3>Perfil del cluster</h3>
            <div class=\"meta\">barra: mediana del cluster · marca: mediana global</div>
          </div>
          ${profileHtml}
        </div>
        <div class=\"card\">
          <div class=\"card-h\"><h3>Top clientes</h3>
            <div class=\"meta\">click → abre ficha</div>
          </div>
          <div class=\"cluster-detail-list\">${topCustHtml}</div>
        </div>
      </div>

      <div class=\"card\" style=\"margin-top:14px\">
        <div class=\"card-h\"><h3>Top productos consumidos</h3>
          <div class=\"meta\">DWH live</div>
        </div>
        <div class=\"cluster-detail-list\">${topProdHtml}</div>
      </div>
    `;

    // Click en cliente del top → navega a ficha
    $detail.querySelectorAll('.cluster-detail-row[data-cid]').forEach(row => {
      row.addEventListener('click', () => navigateToFicha(parseInt(row.dataset.cid, 10)));
    });
    // Cerrar
    $detail.querySelector('.cluster-detail-close')?.addEventListener('click', () => {
      $detail.hidden = true;
      document.querySelectorAll('.cluster-card-clickable').forEach(c =>
        c.classList.remove('cluster-card-active'));
    });
  }

  // ────────────────────────────────────────────────────────────────────
  // (C) Click en punto del scatter PCA → abre ficha del cliente
  // ────────────────────────────────────────────────────────────────────
  function attachScatterHandler() {
    // El scatter PCA es la primera plotly-graph-div de la sección B
    const candidates = document.querySelectorAll('#view-segmentacion .plotly-graph-div');
    const scatter = candidates[0];  // PCA scatter es el primero
    if (!scatter || !scatter.on) {
      // Plotly aún no inicializado; reintenta
      setTimeout(attachScatterHandler, 200);
      return;
    }
    scatter.on('plotly_click', (e) => {
      const pt = e.points && e.points[0];
      if (!pt || !pt.customdata) return;
      const cid = pt.customdata[4];
      if (cid != null) navigateToFicha(parseInt(cid, 10));
    });
    // cursor:pointer en el área del plot
    scatter.style.cursor = 'pointer';
  }
  // Espera a que Plotly haya creado los charts
  setTimeout(attachScatterHandler, 400);

  // Helper: cambiar a vista ficha y cargar el cliente
  function navigateToFicha(cid) {
    const tab = document.querySelector('.tab-liquid[data-view=\"ficha\"]');
    if (tab) tab.click();
    // Espera a que la vista esté visible y la API expuesta
    setTimeout(() => {
      if (window.Ficha?.load) window.Ficha.load(cid);
    }, 80);
  }

  // ────────────────────────────────────────────────────────────────────
  // (F) Simulador — sliders para 8 features → /api/cluster/predict
  // ────────────────────────────────────────────────────────────────────
  let simRanges = null;
  let simState = {};
  let simTimer = null;

  async function initSimulator() {
    if (!$simGrid) return;
    try {
      const r = await fetch('/api/cluster/feature_ranges');
      simRanges = await r.json();
    } catch (e) {
      $simGrid.innerHTML = '<div class=\"sim-error\">No se pueden cargar los rangos: ' + e.message + '</div>';
      return;
    }
    const order = ['cltv','frequency','recency_days','aov','margin_rate','retention_rate','return_rate','net_revenue'];
    $simGrid.innerHTML = order.map(col => {
      const r = simRanges[col]; if (!r) return '';
      simState[col] = r.median;
      const t = FEATURE_FORMAT[col] || 'int';
      const step = t === 'pct' ? 0.01 : (t === 'money' ? Math.max(1, (r.max-r.min)/200) : 1);
      return `
        <div class=\"sim-row\" data-col=\"${col}\">
          <div class=\"sim-row-head\">
            <label>${escapeHtml(FEATURE_LABELS[col] || col)}</label>
            <span class=\"sim-row-value\" id=\"simv-${col}\">${fmtFeat(col, r.median)}</span>
          </div>
          <input type=\"range\" min=\"${r.min}\" max=\"${r.max}\" step=\"${step}\" value=\"${r.median}\" data-col=\"${col}\" />
          <div class=\"sim-row-range\">
            <span>${fmtFeat(col, r.min)}</span>
            <span>${fmtFeat(col, r.max)}</span>
          </div>
        </div>
      `;
    }).join('');

    $simGrid.querySelectorAll('input[type=range]').forEach(input => {
      input.addEventListener('input', () => {
        const col = input.dataset.col;
        const v = parseFloat(input.value);
        simState[col] = v;
        const $v = document.getElementById('simv-' + col);
        if ($v) $v.textContent = fmtFeat(col, v);
        clearTimeout(simTimer);
        simTimer = setTimeout(predict, 120);
      });
    });

    // Predicción inicial con la mediana
    predict();
  }

  async function predict() {
    if (!simRanges) return;
    const params = new URLSearchParams();
    Object.entries(simState).forEach(([k, v]) => params.set(k, v));
    try {
      const r = await fetch('/api/cluster/predict?' + params.toString());
      const d = await r.json();
      const c = d.cluster;
      const color = CLUSTER_COLORS[c];
      const label = CLUSTER_LABELS[c];
      const dist = d.distances || [];
      const distHtml = dist.map((dv, i) => `
        <div class=\"sim-distbar\">
          <span class=\"sim-distbar-label\">Cluster ${i} · ${escapeHtml(CLUSTER_LABELS[i])}</span>
          <div class=\"sim-distbar-track\">
            <div class=\"sim-distbar-fill\" style=\"width:${Math.max(0, 100 - (dv / Math.max(...dist)) * 100)}%; background:${CLUSTER_COLORS[i]}\"></div>
          </div>
          <span class=\"sim-distbar-value\">${dv.toFixed(2)}</span>
        </div>
      `).join('');
      $simRes.innerHTML = `
        <div class=\"sim-result-card\" style=\"border-left:4px solid ${color}\">
          <div class=\"sim-result-head\">
            <span class=\"sim-result-eyebrow\">Cluster predicho</span>
            <h4>${escapeHtml(label)}</h4>
            <div class=\"sim-result-pca\">PC1=${d.pc1.toFixed(2)} · PC2=${d.pc2.toFixed(2)}</div>
          </div>
          <div class=\"sim-result-dist\">
            <div class=\"sim-result-dist-h\">Distancia a cada centroide (menor = más cerca)</div>
            ${distHtml}
          </div>
        </div>
      `;
    } catch (e) {
      $simRes.innerHTML = '<div class=\"sim-error\">Error al predecir: ' + escapeHtml(e.message) + '</div>';
    }
  }

  initSimulator();
})();
</script>
"""
