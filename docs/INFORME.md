# Proyecto Final — Gestión de Datos
**Construcción de un DWH y cálculo de CLTV en el sector salud / bienestar**
*Alejandro Barreche · UAX · curso 2025/26*

## 1. Objetivo y alcance
A partir de un dataset relacional con **50 productos** del sector salud / bienestar
(20 000 ventas, 42 555 líneas, 5 750 clientes, 2 330 devoluciones), se construye
un **Data Warehouse en estrella**, se calcula el **CLTV** por cliente y se segmenta
la base usando **PCA + KMeans**.

## 2. Arquitectura
- **Fuente:** PostgreSQL 16 en Docker (`localhost:5433`, BD `saleshealth`).
- **Tres esquemas en la misma BD:**
  - `public` → datos crudos (17 tablas).
  - `staging` → copias limpias y tipadas (trim, lower(email), recomputado de
    8 `subtotal` inconsistentes, etc.).
  - `dwh` → 6 dimensiones + 2 hechos (estrella).
- **Orquestación:** notebooks Jupyter numerados.
- **SQL:** scripts versionados en `sql/02_dwh_schema`,
  `sql/03_transformations`
- **Stack Python:** pandas 3.0, sqlalchemy 2.0, scikit-learn 1.8, streamlit 1.56.
- **Entorno:** conda `UAX`.

## 3. Modelo Entidad–Relación (`public`)
Resumen de las 17 tablas crudas:

| Bloque | Tablas |
|---|---|
| Producto | `product`, `central_product`, `category`, `brand`, `product_offer`, `offer` |
| Almacén | `warehouse`, `warehouse_location`, `central_inventory`, `inventory` |
| Tienda + geografía | `store`, `city_zone` (`postal_code`) |
| Cliente y ventas | `customer`, `sale`, `sale_item` |
| Devoluciones | `return_item`, `return_reason` |

Relaciones clave: `sale 1—N sale_item`, `sale N—1 customer`, `sale N—1 store`,
`sale_item N—1 product`, `sale_item 1—N return_item`, `store N—1 city_zone (postal_code)`.

Diagrama: ver `docs/er_diagram.md`.

## 4. Modelo dimensional (`dwh`)

### Dimensiones
| Tabla | Grano / NK | Atributos destacados |
|---|---|---|
| `dim_date` | `date_id` (yyyymmdd) | `year, quarter, month, day_of_week, is_weekend` |
| `dim_customer` | `customer_id` | nombre completo, email, teléfono, `signup_date` |
| `dim_product` | `product_id` | `name, category, brand, sku, unit_cost, unit_price` |
| `dim_store` | `store_id` | enriquecida con `city_zone`: `district, area_type, zone_orientation` |
| `dim_offer` | `offer_id` | `discount_percent, start_date, end_date` |
| `dim_return_reason` | `reason_id` | `reason, active` |

### Hechos
- **`fact_sales`** (grano = línea de venta, 42 555 filas)
  Métricas: `quantity, unit_price, unit_cost, subtotal, cost, margin`.
- **`fact_returns`** (grano = línea devuelta, 2 330 filas)
  Métricas: `quantity, returned_value`.

Diagrama: ver `docs/dimensional_diagram.md`.

### Decisiones de diseño
1. **Surrogate keys (`*_sk`)** para todas las dimensiones, con la business key
   marcada `unique` para idempotencia en futuras cargas.
2. `dim_product` se construye combinando `product` (50) y `central_product` (49)
   con `LEFT JOIN`: cuando hay ficha en `central_product` se usa ésta (FKs a
   `brand`/`category`, `unit_cost`); en otro caso, se cae a los textos planos
   de `product`. Sin esta unión no habría coste y, por tanto, no podría
   calcularse el margen.
3. `fact_returns` mantiene las FKs `customer_sk, product_sk, store_sk`
   *denormalizadas* desde `fact_sales` para permitir analítica de devoluciones
   sin volver a recorrer la fact de ventas.
4. `subtotal` en raw difería de `quantity * unit_price` en 8 filas; el staging
   lo recomputa para que `subtotal = quantity * unit_price` en el 100 % de las
   líneas.

## 5. ETL
Pipeline reproducible end-to-end (`src.etl.transform.apply_transformations`):

```
public  ─►  staging  ─►  dwh
```

Cada notebook orquesta una etapa:

| # | Notebook | Salida |
|---|---|---|
| 00 | `00_exploration.ipynb` | perfilado de `public` |
| 01 | `01_etl_staging.ipynb` | tablas `staging.*` |
| 02 | `02_etl_dwh.ipynb` | esquema `dwh` cargado |
| 03 | `03_cltv_calculation.ipynb` | `data/processed/cltv.parquet` |
| 04 | `04_customer_metrics.ipynb` | `data/processed/customer_metrics.parquet` |
| 05 | `05_pca_clustering.ipynb` | `models/{pca,kmeans,scaler}.joblib` y `customer_segments.parquet` |

## 6. Cálculo de CLTV
Fórmula del enunciado:
$$CLTV = Ingresos_t \times Margen_t \times Frecuencia_t \times R_t$$

Operacionalización (sobre la ventana 2020-01 → 2026-01, **72 meses**):

| Componente | Definición |
|---|---|
| `Ingresos_t` | `Σ subtotal − Σ returned_value` por cliente (ventas netas). |
| `Margen_t` | `(Ingresos_t − Σ unit_cost·qty) / Ingresos_t` (proporción). |
| `Frecuencia_t` | `count(distinct sale_id)` por cliente. |
| `R_t` | `meses_activos / meses_de_la_ventana` — proxy de retención. |

**Resultados agregados (5 750 clientes):**

| | mediana | media | máx |
|---|---:|---:|---:|
| Ingresos brutos | 149,9 € | 1 683 € | 24 922 € |
| Margen | 0,40 | 0,36 | 1,00 |
| Frecuencia | 1 | 3,5 | 34 |
| Retención (meses_act / 72) | 0,014 | 0,044 | 0,40 |
| **CLTV** | **0,72 €** | **3 165 €** | **109 735 €** |

La mediana queda muy por debajo de la media porque la mayoría de clientes
tienen una sola compra (frecuencia=1, retención≈1/72), mientras que un
pequeño grupo recurrente concentra el valor.

## 7. Métricas adicionales por cliente
Además del CLTV se calculan tres métricas:

- **Recencia** (días desde la última compra a la fecha de corte):
  mediana 421 días, P75 1 300 días.
- **AOV** (ticket medio = ingresos netos / frecuencia): media 210 €, P75 300 €.
- **Tasa de devolución** (`returned_value / gross_revenue`): media 6,9 %.

## 8. Segmentación: PCA + KMeans
Se construye un panel por cliente con 8 features:
`net_revenue, margin_rate, frequency, retention_rate, aov, recency_days,
return_rate, cltv`. Tras estandarizar (`StandardScaler`) se proyecta a 2
componentes principales y se aplica KMeans con `k = 3` (elegido por curva del codo).

**Varianza explicada PC1+PC2 ≈ 80 %** (suficiente para visualización; si se
quisiera mayor fidelidad analítica se subiría a 3-4 componentes manteniendo
el K-Means en el espacio reducido).


## 9. Calidad y tests
- `pytest` (9 tests) cubre integridad referencial, unicidad de business keys,
  conservación de ingresos staging → dwh, y consistencia de la fórmula de CLTV.
- Logs de la ETL vía `src.utils.get_logger`.

## 10. Reproducibilidad
```bash
conda activate UAX
pip install -r requirements.txt
# Ejecutar todos los notebooks en orden
jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb
# Dashboard
streamlit run dashboard/app.py
```

## 11. Limitaciones
- El dataset es sintético: hay clientes con `return_rate > 1` (devoluciones que
  superan ventas) — se preservan tal cual para no falsear el dato fuente.
- 1 producto (`product_id` ausente en `central_product`) carece de coste; su
  margen se calcula como `0` cuando aplica.
- La ventana de retención usa meses naturales; en producción podría ser
  útil una versión continua.
