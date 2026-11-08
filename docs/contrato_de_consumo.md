# Contrato de consumo — Inteligencia Comercial

`output/` reúne cuatro tablas de consumo generadas desde las fuentes Retail. Los análisis y controles complementarios se calculan con los módulos Python y notebooks.

| Archivo | Grano | Uso analítico | Regla |
| --- | --- | --- | --- |
| `FactVentas.csv` | Fila agregada de venta de la fuente | Modelo de consumo | Fecha, tienda, producto, signo de devolución, venta, Cogs y estado/causa de cobertura. No equivale a ticket. |
| `DimProducto.csv` | Producto | Modelo de consumo | Jerarquía, proveedor, ABC, XYZ y ADI/CV² de la muestra completa. Clasificación estática. |
| `FactInventarioCorte.csv` | Tienda-producto a cierre comercial | Modelo de consumo | Un único corte; cantidad y costo son nulos sin intervalo vigente. El último registro histórico y días transcurridos se informan por separado. |
| `FactForecastSemanal.csv` | Semana-tipo de serie | Modelo de consumo | Serie semanal completa observada y ocho semanas de línea base. Sin bandas de incertidumbre. |

`DimFecha` y `DimTienda` se calculan en Power BI mediante `CALENDAR` y `DISTINCT`. `FactForecastSemanal` se presenta sin relaciones de tienda o producto; su granularidad es agregada semanal. La serie semanal es agregada y se analiza por su fecha propia.

## Medidas y límites

- **Venta bruta:** importe donde `Is Return = 0`; **devoluciones:** importe negativo donde `Is Return = 1`; **venta neta:** suma firmada de `Sales Amount`.
- **Costo neto:** suma firmada de `Cogs`; **margen bruto:** venta neta menos costo neto; **margen %:** margen agregado dividido entre venta neta agregada, nunca promedio de porcentajes.
- **Cobertura temporal:** `SIN_DATO` significa sin intervalo vigente en tienda-producto-fecha; `STOCK_CERO` y `STOCK_NEGATIVO` describen un registro, no un quiebre operativo demostrado. La causa se consulta en `FactVentas[causa_sin_dato]`.
- **Existencia:** `FactInventarioCorte` ofrece cantidad y costo para pares con intervalo vigente; para pares sin vigencia, el último registro conocido se conserva como antecedente, no como existencia actual. No se dispone de movimientos de entradas/salidas.
- **ABC/XYZ:** clasificación descriptiva global sobre la muestra; no cambia dinámicamente por tienda o periodo.
- **Forecast:** línea base exploratoria, sin resultados por tienda ni producto; WAPE agrupado en cinco cortes = 37.93 %; prueba final independiente = 26.30 %; rango por corte = 13.7–53.2 %. La última semana parcial termina 2026-04-26 y se excluye de la serie completa; la primera semana proyectada termina 2026-05-03.
- **Escenarios manuales y presupuesto:** se analizan como ejemplos independientes de las ventas observadas.

El alcance del modelo comprende ventas agregadas, productos, tiendas e intervalos de inventario; la fuente carece de identificadores de cliente y ticket, movimientos de compra y canales diferenciados.

## Relaciones de Power BI

- `DimFecha[Date]` 1:* `FactVentas[fecha]`.
- `DimTienda[Store]` 1:* `FactVentas[Store]` y `FactInventarioCorte[Store]`.
- `DimProducto[Product No]` 1:* `FactVentas[Product No]` y `FactInventarioCorte[Product No]`.
- `FactForecastSemanal` desconectada, con eje temporal propio.

El patrón de medidas es aditivo para importes y de conteo por par tienda-producto para estados de inventario.
