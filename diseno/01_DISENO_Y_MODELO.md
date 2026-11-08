# Diseño funcional y modelo semántico | Inteligencia comercial

## Objetivo

Proporcionar una vista analítica consistente de ventas, rentabilidad, productos e inventario, distinguiendo los datos observados de los escenarios y de las interpretaciones que requieren evidencia adicional.

## Modelo de consumo

| Tabla | Grano | Función |
| --- | --- | --- |
| `FactVentas` | Fila de venta de origen | Venta neta, costo, devolución y cobertura temporal |
| `DimProducto` | Producto | Jerarquía comercial y clasificaciones ABC, XYZ y ADI/CV² |
| `FactInventarioCorte` | Tienda-producto al corte | Existencia, valoración y último registro |
| `FactForecastSemanal` | Semana y clase de serie | Observación agregada y pronóstico de referencia |
| `DimFecha` | Fecha | Dimensión calculada DAX que filtra ventas |
| `DimTienda` | Tienda | Dimensión calculada DAX para ventas e inventario |

Las primeras cuatro tablas se importan desde `output/`. `FactForecastSemanal` permanece desconectada del modelo diario por su granularidad agregada semanal.

## Relaciones

- `DimFecha[Date]` (1) → `FactVentas[fecha]` (*).
- `DimProducto[Product No]` (1) → `FactVentas[Product No]` (*) y `FactInventarioCorte[Product No]` (*).
- `DimTienda[Store]` (1) → `FactVentas[Store]` (*) y `FactInventarioCorte[Store]` (*).
- `FactForecastSemanal`: eje temporal propio, sin relaciones con las dimensiones comerciales.

## Presentación

La paleta GPP utiliza azules profundos y acentos cian en el portal y elementos de alto contraste en Power BI. El portal contiene ocho vistas: panorama, rentabilidad, portafolio, inventario, calidad, pronóstico, simulador y metodología.

| Página Power BI | Pregunta principal | Límite de interpretación |
| --- | --- | --- |
| 01. Resumen ejecutivo | ¿Cuál es el desempeño agregado? | Fuente sin moneda declarada |
| 02. Ventas y rentabilidad | ¿Qué explica la composición comercial? | Sin atribución causal de descuentos |
| 03. Portafolio | ¿Dónde se concentra la actividad? | Clasificaciones globales y descriptivas |
| 04. Inventario | ¿Qué registros están vigentes al corte? | Ausencia de intervalo no equivale a stock cero |
| 05. Calidad | ¿Qué diferencias y faltas de cobertura existen? | No demuestra sobreventa física |
| 06. Pronóstico | ¿Qué referencia ofrece la serie agregada? | Línea base plana, no pronóstico causal |

## Cálculos y controles

- Venta neta: suma firmada de `Sales Amount`.
- Costo neto: suma firmada de `Cogs`.
- Margen bruto: venta neta menos costo neto; porcentaje sobre totales agregados.
- Existencia al corte: registro de inventario con intervalo válido en la fecha de referencia.
- ABC: contribución acumulada de ingresos positivos; XYZ y ADI/CV²: patrones de actividad y variabilidad registrada.
- Forecast: último valor semanal completo proyectado en ocho semanas; validación agrupada de cinco cortes WAPE 37.93 %, prueba final 26.30 %.
- Simulador: sensibilidad aritmética condicionada a supuestos, sin estimación de elasticidad.

**Valores de referencia:** venta neta 10,482,110.25; Cogs 5,847,751.10; margen 4,634,359.15; 125,751 filas de venta; 33,160 filas sin intervalo de inventario; 63,556 pares tienda-producto, de los cuales 19,596 tienen existencias positivas, 40,855 carecen de dato vigente, 2,784 registran cero y 321 un valor negativo.

Para detalles de transformación y supuestos, consultar `docs/ingenieria_caracteristicas.md`, `docs/contrato_de_consumo.md` y `docs/conciliacion_y_controles.md`.
