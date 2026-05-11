# Proyecto Final — Gestión de Datos

Construcción de un entorno analítico (Data Warehouse) y cálculo de métricas de cliente (CLTV) sobre un dataset de **50 productos** del sector **salud / bienestar**.

## Objetivos

1. Diseñar un **modelo Entidad–Relación** y un **modelo dimensional** (esquema estrella).
2. Implementar un **ETL** desde datos crudos (`public`) hasta el DWH (`dwh`) pasando por un área de `staging`.
3. Calcular el **CLTV** por cliente:
   `CLTV = Ingresos_t × Margen_t × Frecuencia_t × R_t`
   y dos métricas adicionales (p. ej. **Recencia**, **Tasa de retención** o **AOV**).
4. Aplicar **PCA + KMeans** sobre las métricas de cliente para segmentar.
5. Documentar todo en un informe técnico (máx. 5 hojas / 10 caras).

## Arquitectura

- **Lenguaje**: Python 3.11+
- **Base de datos**: PostgreSQL (en Docker, `localhost:5433`, BD `saleshealth`)
- **Tres esquemas en la misma BD**:
  - `public` → datos crudos (raw)
  - `staging` → datos limpios y normalizados
  - `dwh` → modelo estrella (`dim_*`, `fact_*`)
- **Orquestación ETL**: notebooks Jupyter (sin Airflow ni Prefect)
- **Dashboards**: Streamlit
- **Configuración**: `python-dotenv`

## Requisitos previos

- Python 3.11 o superior
- Docker con un contenedor de PostgreSQL escuchando en `localhost:5433`, con la base `saleshealth` creada y las tablas crudas en el esquema `public`.

## Setup

```bash
# 1. Clonar / situarse en la carpeta del proyecto
cd Proyecto-Final

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
#  → editar .env y rellenar DB_USER y DB_PASSWORD
```

## Ejecución de los notebooks

Los notebooks están numerados y deben ejecutarse en orden:

| # | Notebook | Propósito |
|---|----------|-----------|
| 00 | `00_exploration.ipynb` | Exploración del dataset crudo en `public` |
| 01 | `01_etl_staging.ipynb` | Limpieza y carga `public → staging` |
| 02 | `02_etl_dwh.ipynb` | Carga `staging → dwh` (dimensiones y hechos) |
| 03 | `03_cltv_calculation.ipynb` | Cálculo del CLTV por cliente |
| 04 | `04_customer_metrics.ipynb` | Recencia, retención, AOV, etc. |
| 05 | `05_pca_clustering.ipynb` | PCA + KMeans para segmentar clientes |

Para abrirlos:

```bash
jupyter notebook
```

## Lanzar el dashboard

```bash
streamlit run dashboard/app.py
```

## Estructura del proyecto

```
Proyecto-Final/
├── .claude/agents/          # Subagentes de Claude Code (data-engineer, modeler, analyst, ml)
├── config/                  # Carga de configuración desde .env
├── sql/                     # DDL y SQL de transformación
│   ├── 02_dwh_schema/       # CREATE SCHEMA + dim_* + fact_*
│   └── 03_transformations/  # Transformaciones del DWH
├── notebooks/               # 6 notebooks numerados (orquestan el pipeline)
├── src/                     # Código reutilizable
│   ├── db/                  # Conexión y queries
│   ├── etl/                 # Extract / Transform / Load
│   ├── analytics/           # CLTV, métricas, segmentación
│   └── utils/               # Logger y utilidades
├── dashboard/               # App Streamlit
├── data/                    # Datos locales (raw / processed) — ignorados por git
├── docs/                    # Diagramas ER, dimensional e informe técnico
└── tests/                   # Tests con pytest
```