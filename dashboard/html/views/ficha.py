"""Vista 05 · Ficha de cliente — shell HTML/JS que se conecta al backend.

La búsqueda, los filtros y el render de la ficha viven en JS. Los datos los
pone `dashboard.html.server` (Flask) en `/api/customers/search` y
`/api/customer/<id>`.

Esta vista NO precomputa nada — la lógica es 100% client-side + fetch.
"""
from __future__ import annotations

import pandas as pd

from .. import helpers as h
from .. import theme


def render(segments: pd.DataFrame) -> str:
    n_total = len(segments)

    parts = [
        h.chapter_opener(
            marker="Capítulo V",
            eyebrow="V · FICHA DE CLIENTE",
            headline="Ficha de cliente.",
            deck=(
                f"Búsqueda en vivo sobre <strong>{theme.fmt_int(n_total)}</strong> clientes. "
                "Filtra por cluster, CLTV o frecuencia, y selecciona uno para ver su radar, "
                "su comparativa con el cluster y el historial de compras desde el DWH."
            ),
        ),

        # ── Search bar + filtros ──────────────────────────────────────────
        '''
        <div class="ficha-search">
          <div class="ficha-search-box">
            <span class="ficha-search-icon">⌕</span>
            <input id="ficha-q"
                   type="text"
                   placeholder="Buscar por nombre o ID..."
                   autocomplete="off" />
            <span class="ficha-search-shortcut">↵</span>
          </div>
          <div class="ficha-filters">
            <div class="ficha-filter-group">
              <span class="ficha-filter-label">Cluster</span>
              <button class="ficha-chip active" data-filter="cluster" data-value="">
                Todos
              </button>
              <button class="ficha-chip ficha-chip-c0" data-filter="cluster" data-value="0">
                Ocasionales
              </button>
              <button class="ficha-chip ficha-chip-c1" data-filter="cluster" data-value="1">
                VIP / Recurrentes
              </button>
              <button class="ficha-chip ficha-chip-c2" data-filter="cluster" data-value="2">
                Devoluciones
              </button>
            </div>
            <div class="ficha-filter-group">
              <span class="ficha-filter-label">Ordenar por</span>
              <button class="ficha-chip active" data-filter="sort" data-value="cltv">CLTV</button>
              <button class="ficha-chip" data-filter="sort" data-value="frequency">Frecuencia</button>
              <button class="ficha-chip" data-filter="sort" data-value="recency">Recencia</button>
              <button class="ficha-chip" data-filter="sort" data-value="name">Nombre</button>
            </div>
          </div>
          <div class="ficha-results-meta" id="ficha-results-meta">Cargando…</div>
        </div>

        <div class="ficha-layout">
          <aside class="ficha-list" id="ficha-list" aria-label="Resultados">
            <!-- las cards de resultados se inyectan vía JS -->
          </aside>
          <section class="ficha-detail" id="ficha-detail">
            <div class="ficha-detail-empty">
              <p class="ficha-detail-hint">Selecciona un cliente de la lista.</p>
            </div>
          </section>
        </div>

        <script>
        (function() {
          const API = '/api';
          const state = {
            q: '',
            cluster: '',
            sort: 'cltv',
            order: 'desc',
            limit: 80,
            selectedId: null,
          };

          // ── Helpers de formato ────────────────────────────────────────
          const fmtMoney = (v) => {
            if (v == null) return '—';
            const abs = Math.abs(v);
            if (abs >= 1_000_000) return (v/1_000_000).toFixed(2).replace('.', ',') + ' M€';
            if (abs >= 1_000)     return (v/1_000).toFixed(1).replace('.', ',') + ' k€';
            return v.toFixed(2).replace('.', ',') + ' €';
          };
          const fmtInt = (v) => v == null ? '—' : Math.round(v).toLocaleString('es-ES').replace(/,/g, ' ');
          const fmtPct = (v) => v == null ? '—' : (v*100).toFixed(1).replace('.', ',') + '%';
          const initials = (name) => {
            if (!name) return '—';
            const p = name.trim().split(/\\s+/);
            if (p.length === 1) return p[0].slice(0,2).toUpperCase();
            return (p[0][0] + p[1][0]).toUpperCase();
          };
          const clusterLabel = (c) => ({0:'Ocasionales', 1:'VIP / Recurrentes', 2:'Devoluciones'})[c] ?? `C${c}`;
          const clusterColor = (c) => ({0:'#94A3B8', 1:'#0EA5A5', 2:'#F97316'})[c] ?? '#94A3B8';

          // ── DOM refs ───────────────────────────────────────────────────
          const $q = document.getElementById('ficha-q');
          const $list = document.getElementById('ficha-list');
          const $detail = document.getElementById('ficha-detail');
          const $meta = document.getElementById('ficha-results-meta');

          // Debounce sencillo
          let searchTimer = null;
          const debounceSearch = () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(doSearch, 220);
          };

          // ── Búsqueda ───────────────────────────────────────────────────
          async function doSearch() {
            const params = new URLSearchParams();
            if (state.q) params.set('q', state.q);
            if (state.cluster !== '') params.set('cluster', state.cluster);
            params.set('sort',  state.sort);
            params.set('order', state.order);
            params.set('limit', state.limit);
            $meta.textContent = 'Buscando…';
            try {
              const r = await fetch(`${API}/customers/search?${params.toString()}`);
              if (!r.ok) throw new Error(`HTTP ${r.status}`);
              const data = await r.json();
              renderList(data);
            } catch (e) {
              $meta.textContent = 'Error: ' + e.message + '. ¿Está el server corriendo? python -m dashboard.html.server';
              $list.innerHTML = '';
            }
          }

          function renderList(data) {
            const total = data.total ?? 0;
            const showing = data.showing ?? 0;
            $meta.textContent = total === showing
              ? `${total} resultado${total === 1 ? '' : 's'}`
              : `Mostrando ${showing} de ${total}`;

            $list.innerHTML = (data.results || []).map(c => `
              <button class="ficha-result" data-cid="${c.customer_id}" data-cluster="${c.cluster}">
                <span class="ficha-result-avatar" style="background:${clusterColor(c.cluster)}">
                  ${initials(c.full_name)}
                </span>
                <span class="ficha-result-body">
                  <span class="ficha-result-name">${escapeHtml(c.full_name || '—')}</span>
                  <span class="ficha-result-meta">
                    <span class="ficha-result-id">ID ${c.customer_id}</span>
                    <span class="ficha-result-cluster" style="color:${clusterColor(c.cluster)}">
                      ${clusterLabel(c.cluster)}
                    </span>
                  </span>
                </span>
                <span class="ficha-result-cltv">${fmtMoney(c.cltv)}</span>
              </button>
            `).join('');

            // Marca seleccionado si sigue en resultados
            if (state.selectedId != null) {
              const sel = $list.querySelector(`[data-cid="${state.selectedId}"]`);
              if (sel) sel.classList.add('active');
            }
          }

          function escapeHtml(s) {
            return String(s).replace(/[&<>"']/g, m => ({
              '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
            })[m]);
          }

          // ── Detalle (al click) ─────────────────────────────────────────
          $list.addEventListener('click', (ev) => {
            const btn = ev.target.closest('.ficha-result');
            if (!btn) return;
            const cid = parseInt(btn.dataset.cid, 10);
            $list.querySelectorAll('.ficha-result.active').forEach(el => el.classList.remove('active'));
            btn.classList.add('active');
            loadCustomer(cid);
          });

          async function loadCustomer(customerId) {
            state.selectedId = customerId;
            $detail.innerHTML = '<div class="ficha-detail-loading">Cargando ficha…</div>';
            try {
              const r = await fetch(`${API}/customer/${customerId}`);
              if (!r.ok) throw new Error(`HTTP ${r.status}`);
              const data = await r.json();
              renderDetail(data);
            } catch (e) {
              $detail.innerHTML = `<div class="ficha-detail-error">No se pudo cargar la ficha: ${e.message}</div>`;
            }
          }

          // ── Render de la ficha ──────────────────────────────────────────
          function renderDetail(data) {
            const c = data.customer;
            const cm = data.comparison.cluster_median || {};
            const gm = data.comparison.global_median || {};
            const tl = data.timeline || [];
            const radarData = data.radar || [];

            // Header
            const headerHtml = `
              <header class="ficha-card-head" style="border-left:4px solid ${clusterColor(c.cluster)}">
                <div class="ficha-card-avatar" style="background:linear-gradient(135deg, ${clusterColor(c.cluster)}, var(--primary))">
                  ${initials(c.full_name)}
                </div>
                <div class="ficha-card-id">
                  <h2>${escapeHtml(c.full_name || '—')}</h2>
                  <div class="ficha-card-tags">
                    <span class="chip c${c.cluster}"><span class="dot"></span>${clusterLabel(c.cluster)}</span>
                    <span class="ficha-card-handle">ID ${c.customer_id}</span>
                  </div>
                </div>
                <div class="ficha-card-window">
                  <div><span class="k">Alta</span><span class="v">${c.first_purchase || '—'}</span></div>
                  <div><span class="k">Última</span><span class="v">${c.last_purchase || '—'}</span></div>
                  <div><span class="k">Compras</span><span class="v">${fmtInt(c.frequency)}</span></div>
                </div>
              </header>
            `;

            // KPIs comparados
            const kpiCmp = (val, ref, lower_better=false) => {
              if (val == null || ref == null || ref === 0) return {txt: '—', cls: 'flat'};
              const r = val / ref;
              if (r >= 0.95 && r <= 1.05) return {txt: '≈ cluster', cls: 'flat'};
              const better = lower_better ? r < 1 : r > 1;
              return {txt: '× ' + r.toFixed(2).replace('.', ',') + ' mediana', cls: better ? 'up' : 'down'};
            };
            const kCltv = kpiCmp(c.cltv, cm.cltv);
            const kFreq = kpiCmp(c.frequency, cm.frequency);
            const kRec  = kpiCmp(c.recency_days, cm.recency_days, true);
            const kRet  = kpiCmp(c.return_rate, gm.return_rate, true);
            const kpisHtml = `
              <div class="grid grid-4">
                ${kpiBlock('CLTV', fmtMoney(c.cltv), kCltv)}
                ${kpiBlock('Frecuencia', fmtInt(c.frequency), kFreq)}
                ${kpiBlock('Recencia', c.recency_days != null ? c.recency_days + ' d' : '—', kRec)}
                ${kpiBlock('Tasa devolución', fmtPct(c.return_rate), kRet, 'vs base global')}
              </div>
            `;

            // Tabla comparativa
            const cmpRows = [
              ['CLTV',           c.cltv,           cm.cltv,           gm.cltv,           false, 'money'],
              ['AOV',            c.aov,            cm.aov,            gm.aov,            false, 'money'],
              ['Frecuencia',     c.frequency,      cm.frequency,      gm.frequency,      false, 'int'],
              ['Retención',      c.retention_rate, cm.retention_rate, gm.retention_rate, false, 'pct'],
              ['Margen',         c.margin_rate,    cm.margin_rate,    gm.margin_rate,    false, 'pct'],
              ['Recencia (días)',c.recency_days,   cm.recency_days,   gm.recency_days,   true,  'int'],
              ['Tasa devolución',c.return_rate,    cm.return_rate,    gm.return_rate,    true,  'pct'],
            ];
            const fmt = (v, t) => t==='money' ? fmtMoney(v) : t==='pct' ? fmtPct(v) : fmtInt(v);
            const cmpHtml = `
              <div class="tbl-wrap">
                <table class="tbl">
                  <thead><tr>
                    <th>Métrica</th><th class="num">Cliente</th>
                    <th class="num">Mediana cluster</th><th class="num">Mediana global</th>
                    <th class="num">vs cluster</th>
                  </tr></thead>
                  <tbody>${cmpRows.map(([lbl, vc, vcl, vg, lb, t]) => {
                    const c1 = kpiCmp(vc, vcl, lb);
                    return `<tr>
                      <td>${escapeHtml(lbl)}</td>
                      <td class="num">${fmt(vc, t)}</td>
                      <td class="num">${fmt(vcl, t)}</td>
                      <td class="num">${fmt(vg, t)}</td>
                      <td class="num cmp-${c1.cls}">${escapeHtml(c1.txt)}</td>
                    </tr>`;
                  }).join('')}</tbody>
                </table>
              </div>
            `;

            // Layout de la ficha
            $detail.innerHTML = `
              ${headerHtml}
              ${kpisHtml}
              <div class="grid grid-2-asym" style="margin-top:18px">
                <div class="card">
                  <div class="card-h"><h3>Radar — rank percentil [0, 1]</h3></div>
                  <div id="ficha-radar" style="height:380px"></div>
                  <p class="explain">El radar usa rankings normalizados — la posición «hacia afuera» siempre significa mejor (incluida la recencia, invertida).</p>
                </div>
                <div class="card">
                  <div class="card-h"><h3>Tabla comparativa</h3></div>
                  ${cmpHtml}
                </div>
              </div>
              ${tl.length > 0 ? `
                <div class="card" style="margin-top:18px">
                  <div class="card-h">
                    <h3>Historial de compras</h3>
                    <div class="meta">${tl.length} registros · DWH live</div>
                  </div>
                  <div id="ficha-timeline" style="height:280px"></div>
                  ${renderTimelineSummary(tl)}
                </div>
              ` : `
                <div class="alert-info" style="margin-top:18px">
                  <strong>Historial no disponible.</strong> El timeline requiere que el DWH (Postgres) esté en línea.
                </div>
              `}
            `;

            // Plot del radar
            renderRadar(radarData);
            if (tl.length > 0) renderTimeline(tl);
          }

          function kpiBlock(label, value, cmp, deltaLabel='vs cluster') {
            return `
              <div class="kpi">
                <div class="kpi-top"><span>${escapeHtml(label)}</span></div>
                <div class="kpi-val">${value}</div>
                <div class="kpi-bot">
                  <span class="kpi-delta ${cmp.cls}">${escapeHtml(cmp.txt)}</span>
                  <span class="kpi-delta-label">${escapeHtml(deltaLabel)}</span>
                </div>
              </div>
            `;
          }

          function renderRadar(radar) {
            if (!window.Plotly) return;
            const cats = radar.map(r => r.axis).concat([radar[0]?.axis]);
            const closed = (vals) => vals.concat([vals[0]]);
            const traces = [
              {
                type: 'scatterpolar',
                r: closed(radar.map(r => r.global)), theta: cats,
                line: {color: '#8A97A6', dash: 'dot'},
                fill: 'toself', fillcolor: 'rgba(138,151,166,0.10)',
                name: 'Base global',
              },
              {
                type: 'scatterpolar',
                r: closed(radar.map(r => r.cluster)), theta: cats,
                line: {color: '#60A5FA', dash: 'dash'},
                fill: 'toself', fillcolor: 'rgba(96,165,250,0.12)',
                name: 'Mediana cluster',
              },
              {
                type: 'scatterpolar',
                r: closed(radar.map(r => r.client)), theta: cats,
                line: {color: '#2563EB', width: 3},
                fill: 'toself', fillcolor: 'rgba(37,99,235,0.22)',
                name: 'Cliente',
              },
            ];
            Plotly.react('ficha-radar', traces, {
              polar: {
                bgcolor: '#FAFBFC',
                radialaxis: {visible: true, range: [0,1], showticklabels: false,
                             gridcolor: '#E6EAEF', linecolor: '#E6EAEF'},
                angularaxis: {tickfont: {color: '#4A5A6A', size: 12},
                              linecolor: '#E6EAEF', gridcolor: '#E6EAEF'},
              },
              legend: {orientation: 'h', y: -0.05, x: 0.5, xanchor: 'center'},
              margin: {l: 30, r: 30, t: 30, b: 50},
              paper_bgcolor: '#FFFFFF',
              font: {family: 'Inter, sans-serif', size: 12, color: '#4A5A6A'},
            }, {responsive: true, displaylogo: false});
          }

          function renderTimeline(tl) {
            if (!window.Plotly) return;
            const byCat = {};
            tl.forEach(r => {
              if (!byCat[r.categoria]) byCat[r.categoria] = [];
              byCat[r.categoria].push(r);
            });
            const CAT = {
              'Diagnóstico':    '#0EA5A5',
              'Wellness':       '#3B82F6',
              'Movilidad':      '#A855F7',
              'Rehabilitación': '#F59E0B',
              'Tratamiento':    '#EF4444',
            };
            const traces = Object.keys(byCat).map(cat => {
              const rows = byCat[cat];
              return {
                type: 'scatter', mode: 'markers',
                x: rows.map(r => r.fecha),
                y: rows.map(_ => 1),
                name: cat,
                marker: {
                  size: 14, color: CAT[cat] || '#94A3B8',
                  line: {color: '#fff', width: 1},
                },
                customdata: rows.map(r => [r.producto, r.tienda, r.cantidad, r.ingresos]),
                hovertemplate: '<b>%{customdata[0]}</b><br>'+
                               '%{customdata[1]}<br>'+
                               '%{x|%Y-%m-%d}<br>'+
                               '%{customdata[2]} ud · %{customdata[3]:,.0f} €<extra></extra>',
              };
            });
            Plotly.react('ficha-timeline', traces, {
              yaxis: {visible: false, range: [0.7, 1.3]},
              xaxis: {showgrid: false, tickfont: {color: '#8A97A6', size: 11}},
              showlegend: true,
              legend: {orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center', font: {size: 11}},
              margin: {l: 10, r: 10, t: 10, b: 60},
              paper_bgcolor: '#FFFFFF', plot_bgcolor: '#FFFFFF',
              shapes: [{type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 1, y1: 1,
                        line: {color: '#E6EAEF', dash: 'dot', width: 1}}],
            }, {responsive: true, displaylogo: false});
          }

          function renderTimelineSummary(tl) {
            // Top categoría + tienda más frecuente
            const sumByCat = {};
            const cntByStore = {};
            tl.forEach(r => {
              sumByCat[r.categoria] = (sumByCat[r.categoria] || 0) + (r.ingresos || 0);
              cntByStore[r.tienda]  = (cntByStore[r.tienda] || 0) + 1;
            });
            const topCat = Object.entries(sumByCat).sort((a,b) => b[1]-a[1])[0];
            const topStore = Object.entries(cntByStore).sort((a,b) => b[1]-a[1])[0];
            const total = tl.reduce((s,r) => s + (r.ingresos || 0), 0);
            return `<p class="caption" style="margin-top:8px">
              Top categoría: <strong>${escapeHtml(topCat?.[0] || '—')}</strong>
              (${fmtMoney(topCat?.[1] || 0)}, ${((topCat?.[1] || 0)/total*100).toFixed(0)}% del gasto)
              · Tienda más frecuente: <strong>${escapeHtml(topStore?.[0] || '—')}</strong>
              (${topStore?.[1] || 0} compras)
            </p>`;
          }

          // ── Eventos UI ─────────────────────────────────────────────────
          $q.addEventListener('input', (e) => {
            state.q = e.target.value;
            debounceSearch();
          });

          document.querySelectorAll('.ficha-chip').forEach(chip => {
            chip.addEventListener('click', () => {
              const f = chip.dataset.filter;
              const v = chip.dataset.value;
              state[f] = v;
              // Visual: resaltar el activo de su grupo
              document.querySelectorAll(`.ficha-chip[data-filter="${f}"]`).forEach(c => c.classList.remove('active'));
              chip.classList.add('active');
              doSearch();
            });
          });

          // Inicial
          doSearch();

          // ── API pública: otras vistas pueden navegar a un cliente concreto.
          //    Ej. desde el scatter PCA: window.Ficha.load(213).
          window.Ficha = {
            load: (cid) => {
              if (cid == null) return;
              state.selectedId = parseInt(cid, 10);
              loadCustomer(state.selectedId);
            },
          };
        })();
        </script>
        ''',
    ]

    return '<section id="view-ficha" class="view">' + "".join(parts) + "</section>"
