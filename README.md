# GPP Group | Inteligencia comercial

Proyecto de Business Intelligence sobre datos públicos de ventas e inventario. Integra procesamiento reproducible con Python, un modelo semántico de Power BI y un portal web interactivo para investigar rentabilidad, portafolio, continuidad de registros y calidad de información.

## Objetivo analítico

Consolidar datos comerciales con granularidades distintas y transformar las diferencias entre fuentes en indicadores verificables. El análisis separa registros observados, cálculos derivados, escenarios e hipótesis; las inconsistencias no se presentan como causas operativas demostradas.

## Arquitectura y archivos

| Elemento | Ruta | Alcance |
| --- | --- | --- |
| Portal | `web/index.html`, `web/dashboard.html` | Portada y ocho vistas de exploración |
| Sitio estático | `site/` | Recursos web con rutas relativas |
| Power BI | `powerbi/AH_Inteligencia_Comercial.pbip` | Modelo editable y seis páginas de informe |
| PDF del informe | `reports/GPP_Inteligencia_Comercial_PowerBI_Desktop.pdf` | Exportación desde Power BI Desktop |
| Procesamiento | `src/` | ETL, ingeniería de indicadores y validaciones |
| Análisis | `notebooks/` | Exploración, transformación y conciliación |
| Insumos y resultados | `input/`, `output/`, `data/` | Fuentes y tablas preparadas para consumo |
| Pruebas | `tests/` | Pruebas automatizadas de cálculos y recursos web |
| Documentación | `docs/`, `diseno/` | Contratos, reglas, resultados y modelo |
| SQL | `sql/` | Conciliación de importes |

El nombre `AH_Inteligencia_Comercial.pbip` es un identificador técnico del proyecto Power BI y se conserva junto a sus carpetas asociadas.

## Reproducción

1. Instalar las bibliotecas de `requirements.txt`.
2. Ejecutar `python src/pipeline.py` desde la raíz para regenerar `output/`.
3. Ejecutar `python src/exportar_portal.py` para generar las estructuras de datos web.
4. Ejecutar `python -m unittest discover -s tests -v` y `python src/validaciones.py`.
5. Abrir `powerbi/AH_Inteligencia_Comercial.pbip` en Power BI Desktop y configurar `pCarpetaOutput` con la ruta absoluta de la carpeta `output`.

El portal incorpora `data.js` para abrirse desde un navegador sin depender de una API remota. El archivo `web/data/retail_dashboard.json` permite validar el contenido estructurado generado.

## Criterios de interpretación

- La venta neta y el costo neto conservan el signo original de devoluciones; el margen porcentual se calcula sobre importes agregados.
- `SIN_DATO` significa ausencia de intervalo de inventario vigente para tienda-producto-fecha y no demuestra una falta física de existencias.
- ABC, XYZ y ADI/CV² describen patrones registrados en la muestra, no la demanda potencial.
- El pronóstico global de ocho semanas es una línea base de último valor, sin estacionalidad estimada ni bandas de incertidumbre.
- Los parámetros del simulador son supuestos de sensibilidad aritmética, no estimaciones causales.

## Procedencia y atribución

La información procede de una fuente pública y no contiene información interna de GPP Group. La identidad visual empleada en el caso es ilustrativa y no supone una relación contractual ni aval corporativo.

Fuente: Jimmy Smith, *Retail Transactions and Stocks Data*, Mendeley Data v1, 27 de abril de 2026. DOI: https://doi.org/10.17632/27x8mjm8k4.1. Licencia CC BY 4.0: https://creativecommons.org/licenses/by/4.0/. La fuente no especifica moneda.
