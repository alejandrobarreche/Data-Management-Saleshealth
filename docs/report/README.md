# Informe técnico — `docs/report/`

Fuentes LaTeX del informe técnico del proyecto **SalesHealth** (Gestión
de Datos, UAX, curso 2025/26).

## Estructura

```
docs/report/
├── main.tex                 # archivo maestro
├── projectreport.sty        # paquete de estilo (sin biblatex)
├── chapter1_introduccion.tex
├── chapter2_modelo_datos.tex
├── chapter3_etl.tex
├── chapter4_cltv_metricas.tex
├── chapter5_segmentacion.tex
├── chapter6_dashboard.tex
├── chapter7_conclusiones.tex
├── appendix.tex
├── Images/                  # diagramas y capturas (PNG)
└── README.md                # este archivo
```

El informe **no usa bibliografía**: no hay `references.bib`, no se
invoca `biber`/`biblatex` y no aparecen `\cite`/`\printbibliography`. Se
sostiene sobre el código del propio repositorio.

## Compilación

Compilación recomendada (dos pasadas para resolver índices, figuras y
referencias internas):

```bash
cd docs/report
latexmk -pdf -interaction=nonstopmode main.tex
```

o, equivalente sin `latexmk`:

```bash
cd docs/report
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex   # opcional, asegura ToC + lof + lot + lol
```

No es necesario `biber`. El PDF resultante (`main.pdf`) consta de unas
50 páginas a una columna y queda **fuera de control de versiones**: el
`.gitignore` del proyecto evita que se suba.

## Paquetes LaTeX requeridos

Todos los paquetes están cargados desde `projectreport.sty` o
`main.tex`. En una distribución TeX Live razonablemente completa
(equivalente a `texlive-full`), no se requiere instalación adicional.
Si la instalación es mínima, deben estar disponibles al menos:

- `geometry`, `inputenc`, `fontenc`, `lmodern`, `microtype`, `setspace`
- `babel` con soporte para `spanish` (paquete Debian/Ubuntu:
  `texlive-lang-spanish`). El estilo recae en `english` con etiquetas
  traducidas a mano si `spanish.ldf` no existe, así que el documento
  compila incluso sin Spanish babel.
- `fancyhdr`, `graphicx`, `xcolor`
- `amsmath`, `amssymb`, `amsthm`, `mathtools`
- `booktabs`, `array`, `tabularx`, `longtable`
- `caption`, `enumitem`, `float`, `hyperref`
- `listings` (configurado con un estilo propio en el `.sty`)

Distribuciones probadas:

- TeX Live 2022/Debian con `pdflatex` (verificado en este repositorio).
- TeX Live 2023/2024 macOS (MacTeX): debería funcionar sin cambios.

## Imágenes generadas

Las imágenes de `Images/` se generan a partir del propio repositorio:

| Imagen                                  | Origen                                                                 |
|-----------------------------------------|------------------------------------------------------------------------|
| `er_diagram.png`                        | `docs/er_diagram.md` (mermaid) → Graphviz/`dot`                        |
| `dim_diagram.png`                       | `docs/dimensional_diagram.md` (mermaid) → Graphviz/`dot`               |
| `cltv_distribution.png`                 | `data/processed/cltv.parquet` → matplotlib                             |
| `elbow.png`                             | `models/customer_segments.parquet` → matplotlib                        |
| `pca_clusters.png`                      | `models/customer_segments.parquet` → matplotlib                        |
| `dashboard_*.png` (6 archivos)          | Capturas de las 6 vistas del dashboard generado por `dashboard/html/`. |

Si alguna imagen se borra o se desea regenerar, los notebooks 03--05 y
los scripts del directorio `figures/` (en la raíz del repo) reproducen
el contenido sin recurrir a fuentes externas.

## Limpieza

Para borrar los productos intermedios de LaTeX sin tocar las fuentes:

```bash
latexmk -C
# o, a mano
rm -f *.aux *.toc *.lof *.lot *.lol *.out *.log *.pdf
```
