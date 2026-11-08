# Ingeniería de características y decisiones comerciales

## Enfoque

El análisis parte de dos archivos públicos de un mismo conjunto: ventas y existencias por intervalos. Las transformaciones conservan sus fechas, productos y tiendas. Los indicadores se calculan con reglas reproducibles; cuando se incorpora un escenario de planificación u homologación se identifica por separado.

| Resultado | Fuente y granularidad | Regla | Utilidad |
|---|---|---|---|
| Venta neta | Ventas, tienda-producto-fecha-tipo-devolución | Suma de `Sales Amount`, con signo original | Seguimiento comercial |
| Margen bruto derivado | Ventas, agrupación seleccionada | Suma de `Sales Amount` menos suma de `Cogs` | Contribución comercial |
| Margen porcentual | Agrupación seleccionada | Margen bruto / ventas netas; nulo si denominador cero | Comparación de rentabilidad bruta |
| Unidades devueltas | Ventas | Negativo de `Qty Sold` solo para `Is Return = 1` | Seguimiento de devoluciones |
| ABC de ventas | Producto | Participación acumulada de ingresos positivos; umbrales 80 % y 95 % | Priorización del catálogo |
| Variabilidad XYZ | Producto-semana completa desde primera actividad observada | CV de unidades semanales, al menos 8 semanas activas; X ≤ 0.5, Y ≤ 1.0, Z > 1 | Variabilidad con ventana relevante |
| Intermitencia ADI/CV² | Producto, semanas activas observables | ADI = semanas activas / semanas positivas; CV² sobre semanas con unidades positivas; umbrales 1.32 y 0.49 | Diferenciar patrón intermitente y errático |
| Cobertura temporal | Venta e intervalo, tienda-producto-fecha | Coincidencia de clave y vigencia inclusiva | Calidad de análisis de stock |
| Estado de existencia | Venta asociada a intervalo | Sin dato, negativa, cero, positiva | Distinguir cobertura de disponibilidad |
| Diferencia de costo de stock | Intervalo de inventario | `Cost of Stocks - Qty on hand × Stock Unit Cost Price` | Conciliación de valorización |
| Indicador de presupuesto | Escenario mensual | Venta del mes calendario inmediato anterior × 1.05; se omite grupo sin referencia registrada | Comparación metodológica con objetivos |
| Incidencia de homologación | Catálogo de muestra | Código faltante o asignado a más de un producto | Validación de integración |
| Forecast semanal | Ventas, semana lunes-domingo | Backtesting de cinco métodos sencillos, horizonte de 4 semanas | Planeación exploratoria |

## Reglas de interpretación

**ABC:** cuando la venta neta de un producto es negativa, su contribución al ordenamiento ABC se lleva a cero. La venta neta original sigue disponible y no se modifica. El umbral se asigna atendiendo a la participación acumulada anterior, de modo que el producto que cruza el umbral permanece en el grupo precedente.

**Variabilidad:** se utilizan semanas completas desde la primera semana con actividad registrada de cada producto. Los productos con menos de ocho semanas observables quedan en `SIN_BASE`. La clasificación ABC–XYZ se complementa con ADI/CV², que distingue frecuencia de semanas con venta y variabilidad de cantidades positivas. Estas medidas describen la actividad registrada en la muestra.

**Inventario:** `Start Date` y `End Date` definen vigencia; la fecha `9999-12-31` representa un intervalo abierto. Para la correspondencia con ventas, el fin efectivo se limita a la última fecha observada. No se suman existencias de intervalos de fechas distintas como un stock actual, ni se infieren movimientos de almacén inexistentes.

**Meta ilustrativa:** se aplica 1.05 a la venta registrada del mes calendario inmediato anterior. Se excluyen los meses incompletos y los grupos sin referencia del mes previo. La meta es una sensibilidad ilustrativa sobre los registros de venta.

**Homologación:** se generan 12 faltantes y 8 asignaciones de código incorrectas que forman 16 registros ambiguos. La clasificación y el impacto comercial permiten comprobar que el proceso los detecta; se etiquetan como escenario demostrativo.

**Forecast:** cinco cortes temporales sirven para elegir entre líneas base y se conserva una prueba final independiente de cuatro semanas. La proyección empieza en la primera semana completamente futura. El WAPE agrupado de los cinco cortes es 37.93 % y la prueba final de cuatro semanas tiene WAPE 26.30 %. La dispersión por corte se presenta en el notebook. La semana de cierre 2026-04-26 es parcial y se excluye; el pronóstico inicia 2026-05-03. No se generan bandas de incertidumbre sin validación suficiente.
