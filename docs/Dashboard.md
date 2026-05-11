# Dashboard SalesHealth — Informe técnico

> Documento de referencia del dashboard Streamlit del proyecto **SalesHealth**
> (TFG · Gestión de Datos · UAX 2025/26).
> Detalla rutas, configuración, decisiones arquitectónicas y todas las
> visualizaciones, con justificación de cada gráfico.
>
> Generado a partir del código real en `dashboard/` — no contiene datos
> inventados. Todas las cifras dinámicas (counts, métricas) las calcula el
> propio dashboard en tiempo de ejecución.

---

## 1. Cómo se lanza

```bash
conda run -n UAX streamlit run dashboard/app.py
```

El entorno `UAX` es obligatorio (ver `CLAUDE.md`). Streamlit toma su
configuración de `.streamlit/config.toml`.

---

## 2. Estructura de archivos

```
dashboard/
├── app.py                  # Entry point · page_config + dispatch de vistas
├── data_access.py          # ÚNICA capa de I/O (parquets, joblibs, SQL)
├── health_check.py         # Verificaciones (a)–(e) al arranque
├── metrics.py              # Helpers puros de formateo (fmt_money, fmt_pct…)
├── smoke_test.py           # Test CLI: parquets + joblibs + predict dummy
├── theme.py                # Paleta + plantilla Plotly + bloque CSS global
├── components/
│   └── ui.py               # 14 helpers de UI: hero, KPI, tablas, radar…
└── views/
    ├── overview.py         # 01 · Visión General
    ├── clientes.py         # 02 · Clientes & CLTV
    ├── segmentacion.py     # 03 · Segmentación (PCA + KMeans)
    ├── productos.py        # 04 · Productos & Devoluciones
    ├── ficha.py            # 05 · Ficha de cliente
    └── metodologia.py      # 06 · Metodología & trazabilidad
```

Recursos externos consumidos por el dashboard (rutas absolutas relativas a
la raíz del repo):

| Recurso                                  | Productor                                   |
|------------------------------------------|---------------------------------------------|
| `data/processed/cltv.parquet`            | `notebooks/03_cltv_calculation.ipynb`       |
| `data/processed/customer_metrics.parquet`| `notebooks/04_customer_metrics.ipynb`       |
| `models/customer_segments.parquet`       | `notebooks/05_pca_clustering.ipynb`         |
| `models/scaler.joblib`                   | `notebooks/05_pca_clustering.ipynb`         |
| `models/pca.joblib`                      | `notebooks/05_pca_clustering.ipynb`         |
| `models/kmeans.joblib`                   | `notebooks/05_pca_clustering.ipynb`         |
| `dwh.fact_sales`, `dwh.fact_returns`, `dwh.dim_*` | Postgres `localhost:5433/saleshealth` |

---

## 3. Configuración

### 3.1 `.streamlit/config.toml`

```toml
[theme]
base = "light"
primaryColor          = "#2563EB"   # azul corporativo
backgroundColor       = "#F5F7FA"
secondaryBackgroundColor = "#FFFFFF"
textColor             = "#0F172A"
font = "sans serif"

[client]
toolbarMode = "minimal"     # oculta el menú de Streamlit

[server]
headless  = false
runOnSave = false           # NO recarga automática al guardar
```

### 3.2 `st.set_page_config` (en `dashboard/app.py`)

| Parámetro              | Valor                                |
|------------------------|--------------------------------------|
| `page_title`           | `Estudio de negocio · SalesHealth`   |
| `page_icon`            | `◈`                                  |
| `layout`               | `wide`                               |
| `initial_sidebar_state`| `expanded`                           |

Tras el `set_page_config` se inyecta `theme.CSS_BLOCK` con
`st.markdown(..., unsafe_allow_html=True)`. Ese bloque define las variables
CSS (`--ink`, `--primary`, `--c0/c1/c2`…), tipografías Inter + JetBrains
Mono y todas las clases del rediseño (`hero`, `kpi`, `chip`, `tbl`,
`cluster-card`, `etl-box`, `sticky`…).

### 3.3 Plantilla Plotly (`theme.PLOTLY_TEMPLATE` → `saleshealth`)

- `font`: Inter 12, color `#4A5A6A`.
- `paper_bgcolor` / `plot_bgcolor`: blanco.
- `colorway`: `[#2563EB, #0EA5A5, #A855F7, #F59E0B, #F97316, #16A34A, #EF4444, #EC4899]`.
- `hovermode` por defecto: `"x unified"`.
- Márgenes por defecto: `l=16, r=16, t=56, b=40`.
- Eje X sin grid; eje Y con grid `#E6EAEF`.

> Toda gráfica nueva pasa **obligatoriamente** por
> `theme.apply_chart(fig, title=…, height=…)`. El wrapper exige título
> explícito (un espacio si se quiere ocultar) para evitar el bug
> `"undefined"` que muestra Plotly cuando se omite.

### 3.4 Paletas semánticas

```python
CLUSTER_COLORS = {
    0: "#94A3B8",   # Ocasionales — gris azulado
    1: "#0EA5A5",   # VIP / Recurrentes — teal
    2: "#F97316",   # Devoluciones — naranja
}
CLUSTER_LABELS = {0: "Ocasionales", 1: "VIP / Recurrentes", 2: "Devoluciones"}

CATEGORY_COLORS = {
    "Diagnóstico":    "#0EA5A5",
    "Wellness":       "#3B82F6",
    "Movilidad":      "#A855F7",
    "Rehabilitación": "#F59E0B",
    "Tratamiento":    "#EF4444",
}
```

Estas paletas son **fijas en todo el dashboard** — Cluster 1 siempre teal,
Cluster 2 siempre naranja, etc., para que el ojo aprenda el color una vez.

### 3.5 Caché

| Función                        | Decorador                   | TTL    |
|--------------------------------|-----------------------------|--------|
| `load_scaler/pca/kmeans`       | `@st.cache_resource`        | sesión |
| `load_cltv/customer_metrics/segments` | `@st.cache_data(ttl=3600)` | 1 h |
| `compute_elbow_curve`          | `@st.cache_data` (sin TTL)  | sesión |
| `load_filter_options`          | `@st.cache_data(ttl=600)`   | 10 min |
| `load_kpis/daily_sales/...`    | `@st.cache_data(ttl=300)`   | 5 min  |
| `_dwh_counts/_schema_counts`   | `@st.cache_data(ttl=600)`   | 10 min |
| `_monthly_sparklines`          | `@st.cache_data(ttl=300)`   | 5 min  |
| `_read_notebook_stats`         | `@st.cache_data(ttl=600)`   | 10 min |

El botón "Recargar" de las sidebars de **Visión General** y **Productos**
ejecuta `st.cache_data.clear() + st.rerun()`.

---

## 4. Health-check de arranque (`dashboard/health_check.py`)

Se ejecuta exactamente **una vez por sesión** (controlado por
`st.session_state["_health_done"]`). Realiza cinco verificaciones:

| Letra | Verificación                                                                | Bloqueante |
|-------|-----------------------------------------------------------------------------|------------|
| (a)   | Existen los 3 parquets (`cltv`, `customer_metrics`, `customer_segments`)    | Sí         |
| (b)   | Existen los 3 joblibs (`pca`, `kmeans`, `scaler`)                           | Sí         |
| (c)   | `len(customer_segments) == len(customer_metrics) == 5 750`                  | Sí (mismatch) / Warn (≠ 5 750) |
| (d)   | `SELECT 1` contra Postgres                                                  | No (pasa a modo OFFLINE) |
| (e)   | `\|SUM(fact_sales.subtotal) − cltv.gross_revenue.sum()\| ≤ 0,02 €`          | No (warning) |

Si (a) o (b) fallan, `app.py` muestra `st.error` y ejecuta `st.stop()`. Si
(d) falla, se activa el banner OFFLINE y las vistas que dependen del DWH
(Overview gráficas D-H, Productos completa) se ocultan.

---

## 5. Navegación y dispatch

Single-page con dispatch interno (no usa `pages/` de Streamlit). El
componente `nav_pills` (en `components/ui.py`) renderiza 6 pills con iconos
Material Symbols Rounded. Cada pill es un `st.button` con `on_click` que
escribe `st.session_state["view"] = slug` y dispara rerun.

```python
NAV_ITEMS = [
    ("01", "Visión General", "overview"),
    ("02", "Clientes",       "clientes"),
    ("03", "Segmentación",   "segmentacion"),
    ("04", "Productos",      "productos"),
    ("05", "Ficha Cliente",  "ficha"),
    ("06", "Metodología",    "metodologia"),
]
```

`app.py` mapea cada slug a la función `render_*` de la vista
correspondiente y llama a `DISPATCH[view](opts, offline)`.

### 5.1 Footer fijo (`footer_sticky`)

48 px fijos al pie:
- Izquierda: ícono matraz + leyenda *"Dataset sintético · no usar en producción"*.
- Centro: pill *"Δ Dataset sintético · TFG UAX 2025/26"*.
- Derecha: counts dinámicos según vista activa: periodo `YYYY-MM → YYYY-MM`,
  nº de clientes, nº de líneas. Se calculan así:
  - **overview**: lee `st.session_state["_overview_counts"]` (publicado al
    final de la vista).
  - **productos**: lee `st.session_state["_productos_kpi"]`.
  - resto: cae a un fallback estático sobre `customer_segments.parquet`.

---

## 6. Decisiones de diseño

| # | Decisión                                                                 | Motivo |
|---|--------------------------------------------------------------------------|--------|
| 1 | Single-page con dispatch interno en lugar de `pages/` de Streamlit       | Control total del top-nav, transiciones sin parpadeo, footer único, y posibilidad de compartir filtros (`opts`) entre vistas. |
| 2 | Capa de I/O única (`data_access.py`)                                     | Cualquier cambio de origen (parquet → API, p. ej.) toca un solo archivo. Ninguna vista hace `read_parquet` ni SQL directamente. |
| 3 | Modo OFFLINE de primera clase                                            | El dashboard arranca sin Postgres; las vistas que dependen del DWH se degradan con `st.info` en vez de fallar. |
| 4 | Plantilla Plotly central + wrapper `apply_chart`                         | Garantiza coherencia visual y obliga a poner título (evita el bug `undefined`). |
| 5 | Cluster colors fijos en TODO el dashboard                                | Reduce carga cognitiva: el lector aprende `teal = VIP, naranja = Devoluciones` una vez. |
| 6 | Health-check separado y bloqueante para parquets/joblibs                 | Si falta un artefacto del modelo, el dashboard no arranca con datos a medias. |
| 7 | Banner ámbar (`alert_warn`) para limitaciones declaradas (zero-cost SKUs, freq=1, return_rate>1) | Honestidad sobre artefactos del dataset sintético: visible, pero no oculta los datos. |
| 8 | KPI cards con sparkline mensual de 12 puntos                             | Da contexto temporal sin gastar otra fila de gráficas. |
| 9 | Comparativas siempre **delta (mediana, no media)** en KPIs y radar       | La distribución de CLTV es severamente asimétrica; usar la media engaña. |
| 10| `frequency = 1` y `return_rate > 1` se documentan, **no se filtran**     | El usuario debe saber del artefacto en lugar de ver una distribución "limpia" inventada. |

---

# 7. Vistas — gráfico a gráfico

Cada vista comparte el mismo *layout*: hero (eyebrow + h1 + sub) → KPIs →
secciones A, B, C… con `section_header(letter, title, kicker)`.

---

## 7.1 Vista 01 · Visión General (`views/overview.py`)

**Hero**: *"Pulso del negocio"* — ventana actual, salud del pipeline,
integridad de parquets y modelos en una sola vista.

### Sidebar — filtros

- **Periodo**: `st.date_input` rango. Default = desde el 1 de enero del año
  más reciente del DWH hasta `max_date`.
- **Categoría**: `st.multiselect` (`opts["categories"]`).
- **Ciudad**: `st.multiselect` (`opts["cities"]`).
- Botón *"Recargar datos"*: limpia caché y rerun.

`prev_filters` se calcula automáticamente como la ventana anterior del
mismo número de días (para los deltas KPI).

### Sección A · Indicadores principales (8 KPIs en 2 filas de 4)

| KPI                | Valor                                  | Delta vs ventana previa | Origen          |
|--------------------|----------------------------------------|-------------------------|-----------------|
| Ingresos netos     | `gross_revenue − returns_value`        | %                       | `dwh.fact_sales`|
| Crecimiento        | `gross_revenue` (delta como valor)     | up/down                 | derived         |
| Tasa devolución    | `returns_value / gross_revenue`        | pp                      | `dwh.fact_returns`|
| AOV                | `gross_revenue / tickets`              | %                       | derived         |
| Líneas de venta    | `count(*)` de `fact_sales`             | %                       | `dwh.fact_sales`|
| Clientes activos   | `count distinct customer_sk`           | %                       | `dim_customer`  |
| Tickets            | `count distinct sale_id`               | %                       | `dwh.fact_sales`|
| Margen bruto       | `total_margin / gross_revenue`         | pp                      | derived         |

Cada card incluye un **sparkline** mensual de 12 puntos con
`_monthly_sparklines` (resample `ME` sobre `daily`).

> *Justificación*: ocho KPIs cubren el embudo (volumen → conversión →
> rentabilidad → retención) en un golpe de vista. El sparkline da contexto
> temporal sin ocupar una segunda fila.

### Sección B · Inventario verificado del DWH

Grid de hasta 8 cards verdes (`inv_card`) con el count actual de:
`dim_customer`, `dim_product`, `dim_store`, `dim_date`, `fact_sales`,
`fact_returns`, `mart_cltv`, `mart_segments` (los dos últimos leídos del
parquet, no del DWH).

> *Justificación*: pone a la vista que "lo que ves" coincide con "lo que
> hay en la base". Es la prueba de vida del DWH.

### Sección C · Estado de la ejecución

- **Izquierda**: `timeline_from_notebooks` lee con `nbformat` los 6
  notebooks de `notebooks/`, cuenta celdas y outputs, y marca con un punto
  ámbar si alguno tiene "warn" en sus outputs.
- **Derecha**: tres expanders con preview (`head(5)`) de cada parquet y
  tres pills con metadatos de los joblibs (`PCA n_components=2`,
  `KMeans n_clusters=3, n_init=10`, `StandardScaler n_features_in_=8`).

> *Justificación*: el dashboard no muere si un parquet no existe — el
> health-check ya bloquea — pero esta sección **demuestra** que los
> artefactos están donde deben estar y muestra metadatos de los modelos.

### Sección D · Evolución de ingresos (línea + media móvil)

Plotly `go.Scatter` x2:
- `daily.revenue`: línea fina azul `#2563EB`, opacity 0.35, fill a cero.
- `daily.rev_ma7`: media móvil 7 días, teal `#0EA5A5`, width 2.

> *Justificación*: la serie diaria es ruidosa; la MA-7 deja ver tendencia
> y estacionalidad semanal. Mostrar ambas evita que el lector se quede
> solo con la suavizada.

### Sección E · Ingresos por categoría (barras horizontales)

`px.bar` horizontal, ordenado desc por revenue, color = `margin_rate` con
escala `[(0, DANGER), (0.5, WARNING), (1, SUCCESS)]`. Texto = ingresos
formateados, tooltip con ingresos.

> *Justificación*: mezclar volumen (longitud) con rentabilidad (color)
> permite ver qué categorías son grandes pero "tóxicas".

### Sección F · Mix por marca (treemap categoría → marca)

`px.treemap` con `path=["category", "brand"]`, color por revenue con
`SEQ_TEAL`.

> *Justificación*: jerarquía visual sin ocupar mucho espacio; los
> rectángulos pequeños son intencionalmente difíciles de leer — el
> objetivo es ver *concentración*, no marcas individuales.

### Sección G · Estacionalidad (heatmap mes × año)

`go.Heatmap` con z = ingresos, x = mes (`01..12`), y = año, escala
`SEQ_TEAL`, texto en celda con valor formateado.

> *Justificación*: la vista clásica que combina detección de tendencia
> año-a-año y patrones intra-anuales en un solo gráfico.

### Sección H · Top 10 tiendas (barras horizontales)

`px.bar` horizontal sobre `load_top_stores().head(10)`, color =
`margin_rate` (misma escala que sección E). Custom tooltip con ciudad,
tickets, clientes, margen.

> *Justificación*: detecta tiendas que son "máquinas de ingresos sin
> margen" o pequeñas pero muy rentables.

> **Nota OFFLINE**: D, E, F, G y H se ocultan en modo OFFLINE; el resto
> sigue funcionando.

---

## 7.2 Vista 02 · Clientes & CLTV (`views/clientes.py`)

**Hero**: *"El valor vive en la cola larga"* — CLTV calculado sobre N
clientes en la ventana 2020-01 → 2026-01, distribución severamente
asimétrica.

### Sidebar — filtros

- **Segmento**: `multiselect` `[0, 1, 2]`, default los 3.
- **Frecuencia de compra**: slider `(1, freq_max)`.

### KPIs (4 cards)

- **Clientes con CLTV** (`n_filt` de `n_total`)
- **CLTV mediana · P50**
- **CLTV media** (etiqueta con `× X mediana`, marcado *up* para hacer
  evidente la asimetría)
- **Concentración Top 20%** = `nlargest(0.2*n)["cltv"].sum() / total`

### Sección A · Hallazgo principal (`finding_banner`)

Banner con número grande (% de clientes con `frequency == 1`) y donut
auxiliar con el mismo porcentaje.

> *Justificación*: un solo número, brutalmente honesto. La interpretación
> queda escrita: la mediana es baja porque la mayoría son one-shot; la
> media está distorsionada por el Cluster 1 que genera ~99,8 % del CLTV.

### Sección B · Distribución del CLTV (3 tabs)

**Tab "Histograma (log)"** — `go.Histogram` con `x = log10(cltv)`, 60 bins.
Líneas verticales para P50, P75, P90, P99 (cada una con su color: teal,
azul, rojo, gris). Excluye `cltv ≤ 0` (artefacto del dataset sintético).

> *Justificación*: con asimetría severa, el log es la única forma de ver
> la distribución *completa*. Las líneas P50/P75/P90/P99 anclan al lector.

**Tab "ECDF"** — `go.Scatter` con curva escalonada (`shape="hv"`),
fill a cero. Eje x logarítmico.

> *Justificación*: responde directamente "¿qué % de clientes tiene CLTV
> ≤ X €?" sin necesidad de bins.

**Tab "Densidad por cluster"** — Tres `go.Violin` horizontales (uno por
cluster), `box_visible=True`, `meanline_visible=True`, sobre log10(CLTV).

> *Justificación*: en una sola vista compara dispersión, mediana y
> outliers entre clusters. Los violines hacen evidente que Cluster 1 es
> dos órdenes de magnitud por encima.

### Sección C · Concentración del CLTV (2 columnas)

**Izq · Curva de Lorenz** — Línea de igualdad (45°) + curva real teal con
fill. Coeficiente de **Gini** calculado en vivo con `np.trapezoid`.

> *Justificación*: el gold-standard para mostrar concentración. El Gini
> traduce la curva a un único número.

**Dcha · CLTV por cluster — mediana vs media** — `go.Bar` horizontal
agrupado: media (opacity 0.4) y mediana (opacity 1.0), por cluster, eje x
logarítmico.

> *Justificación*: visualiza el "skew" por cluster — donde media ≫ mediana,
> la cola es la que manda.

### Sección D · Top 20 clientes por CLTV (data_table)

Tabla HTML estilizada (`data_table`) con barras inline en columna CLTV,
chip de cluster, mono numerals. Buscador (`st.text_input`) que filtra por
nombre o ID. Columnas: `ID, Cliente, Cluster, CLTV, Compras, AOV, Última compra`.

> *Justificación*: poner cara y nombre a los outliers que dominan el Gini
> y la media.

---

## 7.3 Vista 03 · Segmentación (`views/segmentacion.py`)

**Hero**: *"Tres comportamientos, una base"* — KMeans `k=3` sobre 8
features estandarizadas; la varianza de PC1+PC2 se muestra explícita.

### Sidebar — filtros

- **Clusters visibles**: `multiselect` `[0, 1, 2]`.
- Footer con `models/customer_segments.parquet`,
  `StandardScaler → PCA(2) → KMeans(k=3)` y la varianza explicada.

### Sección A · Cluster overview

Grid de 3 `cluster_card` (icono + nombre + share), una por cluster, con:

- Tamaño y % base
- % CLTV
- CLTV mediana, frecuencia mediana, recencia mediana, tasa devolución mediana

> *Justificación*: tres cards autoexplicativas; el eyebrow eyebrow del
> color iguala los gráficos posteriores.

### Sección B · Mapa PCA y composición (3 columnas)

**Col 1 · Scatter PCA** — `go.Scatter` x cluster, x = PC1, y = PC2, marcas
con colores fijos. Hover muestra nombre, CLTV, frecuencia, recencia.

> *Justificación*: enseña la separación geométrica que justifica los 3
> clusters. PC1 ≈ "monetario+frecuencia"; PC2 ≈ "recencia − tasa
> devolución" (anotado en col 3).

**Col 2 · Donut tamaño** — `go.Pie` hole=0.55, anotación central con
`N clientes`. Debajo, 3 chips con label + count + %.

> *Justificación*: reescribe el dato del scatter en porcentajes,
> independiente del filtro.

**Col 3 · Donut varianza explicada** — Tres slices: PC1, PC2, Resto, con
anotación central `XX,X% cubierta`. Debajo caption explicando el
significado de cada PC.

> *Justificación*: hace honesto el "PCA(2)" — el % no cubierto se ve.

### Sección C · Caracterización + heatmap z-score (2 columnas)

**Col izq · Tabla de caracterización** (`data_table`): `Cluster, Tamaño,
% base, % CLTV, CLTV mediana, Frecuencia, Recencia, Tasa dev.`. La
columna `Cluster` se renderiza como chip coloreado.

**Col dcha · Heatmap z-score** — `go.Heatmap` con `z = (profile − mean) / std`
sobre las 8 features, escala `RdBu` divergente centrada en 0.

> *Justificación*: la tabla es para lectura literal; el heatmap es para
> *patrón rápido* — una mancha roja en `cltv, frequency, retention` para
> Cluster 1, etc.

---

## 7.4 Vista 04 · Productos & Devoluciones (`views/productos.py`)

**Hero**: *"Qué vende, qué se devuelve"*. Es la vista más DWH-pesada — en
modo OFFLINE solo se renderiza el banner.

### Sidebar — filtros

- **Periodo** (default: 1-ene del año más reciente → max_date)
- **Categoría** y **Ciudad** (`multiselect`)
- Botón *"Recargar"*

### KPIs (4 cards)

- **Líneas de venta** (`line_items`)
- **Devoluciones** (`returns_value` €)
- **Tasa devolución** (`returns_value / gross_revenue`)
- **AOV** (`gross_revenue / tickets`)

### Aviso de productos sin coste

Si `dwh.dim_product.unit_cost = 0` para ≥ 1 SKUs, se muestra un
`alert_warn` con la lista de SKUs (8 visibles + "+N más"). Razonamiento:
el margen calculado para esas líneas asume coste 0, así que el agregado es
un *techo*, no la cifra real.

> *Justificación*: honestidad. Sin este aviso, el KPI "Margen bruto" sería
> una mentira aceptada por defecto.

### Sección A · Top 15 productos por ingresos

`px.bar` horizontal, color por categoría (paleta `CATEGORY_COLORS` fija),
texto = ingresos formateados, tooltip con categoría, marca, unidades, margen.

> *Justificación*: identifica los caballos de batalla y permite cruzarlos
> mentalmente con la sección B (¿son también los más devueltos?).

### Sección B · Devoluciones — motivo y producto (3 gráficos)

**B1 · Donut por motivo** — `go.Pie` hole=0.5 con `SEQ_TEAL_CORAL`, leyenda
vertical a la derecha. Muestra distribución %.

**B2 · Barras horizontales por motivo** — Mismo dato que B1 pero en €
absolutos, color continuo por valor.

**B3 · Top productos por valor devuelto · color = ratio dev/ventas** —
`px.bar` horizontal sobre `merge(rets_prod, prods)`, color =
`return_ratio = value_devuelto / revenue`. Tooltip con unidades, n_returns,
ratio.

> *Justificación*: B1 + B2 = "qué motivo manda" (la duplicación es
> intencionada: % vs € absolutos para distintas conversaciones). B3 cruza
> volumen devuelto con relevancia comercial — un producto pequeño con
> ratio 80 % es un fuego, aunque pierda en absoluto.

### Sección C · Trazabilidad SQL

Grid 4×1 de cards mono con los `dwh.*` consumidos por la vista:
`fact_sales`, `fact_returns`, `dim_product`, `dim_return_reason`.

> *Justificación*: cumple el requisito de "decir de dónde sale cada cosa"
> sin un PDF aparte.

---

## 7.5 Vista 05 · Ficha de cliente (`views/ficha.py`)

**Hero**: *"Radiografía de un cliente"* — buscador autocompletado sobre
los N clientes del parquet `customer_segments`, comparativa contra cluster
y base global, timeline de compras.

### Sidebar

Solo metadatos (origen del dato). No hay filtros — la selección la hace
el `selectbox` principal.

### Selector y header

- `st.selectbox` ordenado por CLTV desc; el label es
  `"<full_name> · ID <customer_id>"`.
- Card cabecera con avatar (iniciales), chip de cluster, ID, fecha de alta,
  ventana en años + meses, fecha de última compra y resumen
  (`N tickets · CLTV X €`).

### KPIs (4 cards comparados con la mediana del cluster)

| KPI              | Valor cliente              | Delta                          |
|------------------|----------------------------|--------------------------------|
| CLTV             | `selected_row["cltv"]`     | `× ratio cluster` (≥1.05 → up) |
| Frecuencia       | `selected_row["frequency"]`| idem                           |
| Recencia         | `selected_row["recency_days"]` (días) | "muy reciente" / `× ratio` / "≈ cluster" (lower-better) |
| Tasa devolución  | `selected_row["return_rate"]` | pp vs base global (lower-better) |

Si `return_rate > 1`, se muestra `st.warning` declarando el artefacto.

### Sección A · Comparativa contra cluster y base global

**Radar (`metric_comparison_radar`)** — Tres polígonos en
`go.Scatterpolar`:
- Cliente (sólido teal, fillcolor `rgba(14,165,165,0.25)`)
- Cluster (dash teal, fill claro)
- Base global (dot gris, fill 10 %)

6 ejes: `CLTV, AOV, Frecuencia, Retención, Margen, Recencia⁻¹` (recencia
invertida con `_rank(..., invert=True)` para que "mejor" siempre sea hacia
afuera).

> *Justificación*: rankings normalizados a [0, 1] son comparables aunque
> las features estén en escalas distintas; los 3 polígonos en el mismo
> plot enseñan posición *y* dispersión.

**Tabla comparativa** — 7 filas (CLTV, AOV, Frecuencia, Retención,
Margen, Recencia, Tasa dev.), columnas: cliente, cluster, global, vs
cluster (con iconos `▲ × X` / `▼ × X`, código de color `up/down/flat`,
respetando `lower_better` para recencia y devolución).

> *Justificación*: el radar es para "patrón"; la tabla, para el lector que
> quiere número exacto.

### Sección B · Historial de compras

**Timeline horizontal** (`go.Scatter`, modo markers, y=1 constante):
- Una traza por categoría de producto presente en el historial.
- Marcador 14 px coloreado por `CATEGORY_COLORS`.
- Línea punteada gris `#8A97A6` como base.
- Tooltip con producto, categoría, tienda, cantidad, ingresos, fecha.

Caption resumen: top categoría (% del gasto) + tienda más frecuente.

> *Justificación*: cuando un cliente tiene 5–80 compras, el orden y la
> distribución temporal cuentan más que cualquier KPI. Un eje único (y=1)
> deja al lector concentrarse en el ritmo.

> **Modo OFFLINE**: la sección B se sustituye por un `st.info` con
> resumen estático (frecuencia, ingresos brutos del parquet).

---

## 7.6 Vista 06 · Metodología (`views/metodologia.py`)

**Hero**: *"Cómo está construido"* — pipeline ETL, modelo dimensional,
trazabilidad de cada KPI hasta su origen.

### Sección A · Pipeline ETL

Tres `etl-box` con flechas: `public` → `staging` → `dwh`. Cada caja
muestra count de tablas (en vivo de `information_schema`) y, en `dwh`,
el nº de líneas de `fact_sales`.

### Sección B · Modelo dimensional (estrella)

SVG inline (800×380) dibujado a mano: 2 hechos (`fact_sales`,
`fact_returns`) en el centro y 4 dimensiones en las esquinas
(`dim_customer`, `dim_product`, `dim_store`, `dim_date`). Cada caja
muestra count actual.

> *Justificación*: una imagen estática hubiera quedado obsoleta. El SVG
> embebido se rellena con `read_sql("count(*)")` en cada arranque.

### Sección C · Mapa KPI → fórmula → origen

Tabla con 10 filas: para cada KPI (`Ingresos netos, CLTV, Tasa
devolución, AOV, Cluster, Recencia, Margen bruto, Frecuencia, Retención,
PC1/PC2`) se da: fórmula textual, tabla origen, parquet intermediario.

> *Justificación*: ningún KPI sin papeleta. Si alguien pregunta "¿de
> dónde sale el AOV?", la respuesta está aquí, no en una conversación.

### Sección D · Health check & Smoke test (2 cards)

**Card izquierda** — Verificaciones (a)–(e) con dot verde/ámbar:
- (a) 3 parquets existen — bloqueante
- (b) 3 joblibs existen — bloqueante
- (c) `len(segments) == len(metrics)`
- (d) Postgres responde · OK / OFFLINE
- (e) `|gross_DWH − gross_parquet| < 0,02 €`

**Card derecha** — Smoke test (4 checks):
- (a) `read_parquet()` OK
- (b) `joblib.load()` OK
- (c) Pipeline `scaler → pca → kmeans.predict` OK
- (d) `sum(cluster_size) = N`

Pie: comando `conda run -n UAX python dashboard/smoke_test.py`.

### Sección E · Justificación de k = 3 (curva del codo)

`go.Scatter` lines+markers sobre `compute_elbow_curve()` (recompute
KMeans para `k ∈ [2, 8]` con los mismos PCA features). El marcador
correspondiente a `k=3` se pinta azul; los demás, gris. Línea vertical
discontinua marca el codo.

> *Justificación*: defender una elección no documentada es tarjeta roja
> en una entrega académica. Aquí la decisión "k=3" se ve, no se afirma.

### Sección F · PCA(2)

Bar chart con varianza explicada por PC1 y PC2, línea horizontal a 80 %
("objetivo"). 3 `st.metric`: PC1, PC2, total, y caption con el % no
representable en 2D.

> *Justificación*: igual que el codo — la elección de 2 componentes
> queda evaluada contra un objetivo declarado.

### Sección G · 8 features + limitaciones (2 columnas)

**Izq** — Tabla numerada con las 8 features y 1 línea de justificación
de cada una (`net_revenue, margin_rate, frequency, retention_rate, aov,
recency_days, return_rate, cltv`).

**Dcha** — `card` con `<ul>` de **5 limitaciones declaradas**:
1. PCA(2) explica el X % (resto perdido en 2D).
2. N clientes con `return_rate > 1` (artefacto Cluster 2).
3. N clientes con `frequency = 1` (sesgo en mediana).
4. Dataset 100 % sintético.
5. Ventana fija 72 meses (clientes tardíos castigados en retención).

### Sección H · Estadísticos clave del CLTV (expander)

Tabla compacta con: `N clientes, Mediana, Media, P75, P90, P99, Máximo,
clientes con freq=1`. Plegada por defecto.

---

# 8. Resumen — qué cubre el dashboard

| Pregunta de negocio                           | Vista que responde |
|-----------------------------------------------|--------------------|
| ¿Cómo va el negocio ahora vs antes?           | 01 Visión General  |
| ¿Quién genera el valor?                       | 02 Clientes        |
| ¿Cómo agrupar a la base?                      | 03 Segmentación    |
| ¿Qué se vende y qué se devuelve?              | 04 Productos       |
| ¿Cómo es Juan Pérez?                          | 05 Ficha           |
| ¿De dónde sale cada KPI? ¿Cómo está montado?  | 06 Metodología     |

---

# 9. Ideas para evolucionar el dashboard

> Esta sección se ofrece para discusión. **Nada de aquí está implementado;
> lo dejo plano para que se elija qué levantar.**

## 9.1 Layout / UX

1. **Filtros globales persistentes**. Hoy cada vista define sus filtros y
   se pierden al navegar. Mover `periodo`, `categoría`, `ciudad` a un
   sidebar global compartido por overview / productos haría la
   exploración más fluida.
2. **Deep-link por URL**. Persistir `view=overview&from=2025-01&to=2025-12`
   en la query string permite compartir capturas exactas.
3. **Dark-mode toggle**. La paleta ya tiene los tokens (`--ink`, `--bg-*`);
   falta el switch y un *override* del template Plotly.
4. **Modo "presentation"** (un click): oculta sidebar y top-nav, agranda
   tipografía. Útil para el tribunal del TFG.
5. **Comparativa de dos ventanas en paralelo** en Overview: "este Q vs Q
   anterior" como dos columnas de KPI cards en lugar de un delta.
6. **Tooltips de KPI con definición**. Hoy el sparkline da contexto, pero
   un `?` con la fórmula y la fuente cerraría el círculo sin ir a la
   vista 06.
7. **Skeleton loaders** mientras los SQL pesados (Overview D-H)
   resuelven, en vez del spinner por defecto de Streamlit.

## 9.2 Información expuesta — gráficos / análisis nuevos

### Visión General
- **Pareto de clientes / productos / tiendas** (curva acumulada con la
  marca al 80 %).
- **Cohortes mensuales de retención** (heatmap mes-de-alta × mes-relativo).
  Expone la "salud" temporal de la captación, no solo la mediana global.
- **Margen vs ingresos por categoría** (scatter): hoy se mezcla en
  longitud + color; un scatter X=ingresos / Y=margen separa los dos ejes.
- **Mapa de España con puntos por tienda** (lat/lon en `dim_store`):
  ingresos como radio del círculo. Más rico que un Top-10 horizontal.

### Clientes & CLTV
- **CLTV predicho a 12 meses** (BG/NBD + Gamma-Gamma) frente al CLTV
  histórico que ya se calcula. Convertiría la vista de descriptiva en
  predictiva.
- **Distribución de RFM por separado** (3 histogramas pequeños), no solo
  el CLTV agregado: hace explícito qué eje "mata" a un cliente.
- **Curva supervivencia** (Kaplan–Meier) sobre tiempo entre primera y
  última compra: cuándo "muere" un cliente.

### Segmentación
- **Centroides interpretables**: una *radar mini* por cluster con sus
  z-scores, alineada con la card. Hoy hay heatmap; la radar añadiría
  "forma del cluster" en lectura rápida.
- **Estabilidad del cluster** (silhouette score por k) junto a la curva
  del codo — son medidas distintas.
- **t-SNE / UMAP** como tab alternativa al PCA. PCA preserva varianza
  global; UMAP, vecindarios — son útiles juntas.

### Productos & Devoluciones
- **Margen unitario × volumen** (scatter de SKUs): cuadrante "matar /
  potenciar / mantener / vigilar".
- **Devoluciones por motivo a lo largo del tiempo** (área apilada
  mensual): detecta picos por defecto puntual.
- **Affinity / market basket** (top pares de productos por confianza):
  útil para promociones cruzadas; hoy se ignora la línea de venta como
  cesta.
- **Velocidad de venta** (unidades / día disponible) por SKU — necesita
  fechas de alta del producto.

### Ficha de cliente
- **Predicción de próxima compra** (días al siguiente ticket) basada en
  intervalo medio del cliente.
- **Recomendación "next best product"** simple: top categorías del
  cluster que el cliente aún no ha comprado.
- **Comparativa contra mejores del cluster** (no solo mediana): qué le
  separa del p90.
- **Alerta de churn**: si `recency_days > p90 del cluster`, badge rojo.

### Metodología
- **Mostrar el código** del ETL al hover, no solo la fórmula textual
  (con `st.code` desplegable). Cierra la trazabilidad de KPI hasta el
  SQL real.
- **Lineage gráfico interactivo**: SQL files como nodos, parquets como
  artefactos, vistas como consumidores. Hoy el SVG es estático.
- **Versionado**: hash git del último commit que tocó cada KPI. Útil
  cuando dos lectores ven números distintos.

## 9.3 Decisiones a discutir

- ¿Filtrar `frequency = 1` para los KPIs *medios*, o seguir mostrándolo y
  educar? Hoy se hace lo segundo. La ventaja de filtrarlo es que la
  "media de CLTV" deja de ser una trampa; la desventaja es ocultar el
  hallazgo principal del proyecto.
- ¿Dejar las gráficas D-H de Overview en OFFLINE con datos del último
  parquet snapshot, o mantener el `st.info`? La primera opción exige un
  *snapshot diario* del DWH a parquet (otro notebook).
- ¿Permitir descarga CSV/PNG de cada gráfica desde el toolbar de Plotly?
  Streamlit lo permite, hoy se muestra el toolbar en `minimal`.
- ¿Reescribir `data_access.py` con un router por modo (online/offline)
  en lugar de comprobar `if offline:` en cada función? Reduciría
  duplicación si entra una tercera fuente (p. ej. una API).

---

*Última actualización del informe: 2026-05-09.*