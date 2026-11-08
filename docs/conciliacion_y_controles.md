# Calidad de información y conciliación

## Controles observados

- Las ventas agregadas conservan el signo de las devoluciones. `Sales Amount` y `Cogs` se suman directamente sin restar nuevamente las líneas devueltas.
- Las claves de análisis de ventas conservan tienda, producto, fecha, tipo de venta e indicador de devolución.
- Para vincular ventas con existencias se utiliza tienda-producto-fecha dentro de un intervalo de vigencia. Los periodos sin cobertura se clasifican como `SIN_DATO`.
- Las discrepancias de valorización se calculan por intervalo antes de sumar importes. Diferencia neta y suma absoluta son indicadores diferentes.
- El catálogo de homologación de muestra conserva las claves originales y detecta correspondencias incompletas y códigos ambiguos.

## Resultados de referencia

| Control | Resultado |
|---|---:|
| Filas de ventas | 125,751 |
| Filas de inventario | 284,755 |
| Filas de ventas sin cobertura temporal de stock | 33,160 |
| Venta neta asociada a filas sin cobertura | 3,190,352.07 |
| Intervalos con existencia negativa | 1,380 |
| Diferencias de valorización absolutas superiores a 0.10 | 6,358 |
| Suma absoluta de esas diferencias | 22,722.79 |
| Diferencia neta de esos registros | -580.15 |

Estas cifras describen los archivos estudiados y se reproducen con `src/pipeline.py`. Las diferencias se describen como observaciones del registro; sus causas no están identificadas en la fuente.

## Niveles de evidencia

- **Observado:** campo, registro, cálculo o cruce reproducible desde los CSV públicos.
- **Calculado:** indicador derivado bajo una regla explícita.
- **Escenario:** archivo o parámetro de muestra; sirve para comprobar un proceso.
- **Hipótesis:** posible causa o explicación que los datos no demuestran.

## Comprobación automática

`python src/validaciones.py` contrasta las cuatro tablas de consumo, conciliación diaria contra ventas originales, totales, cobertura, clasificaciones y horizonte del forecast. Los ejercicios de homologación y presupuesto se inspeccionan en los notebooks.

## Escenario de ingesta manual

El archivo `input/manual/Ajustes_Comerciales_escenario.csv` se valida por estructura, fechas, importe, catálogo y estado. Los duplicados de la pareja documento-versión se rechazan en todas sus apariciones (`keep=False`); una versión posterior es otro registro y no sustituye automáticamente una anterior. Solo los registros estructuralmente válidos con estado `APROBADO` pueden utilizarse en un ejercicio explícito. Las incidencias permanecen disponibles en el notebook 03.

## Conciliación SQL

La consulta [`sql/conciliacion_ventas.sql`](../sql/conciliacion_ventas.sql) agrupa importes, costos y margen por tipo de venta. La base SQLite se genera con `python src/pipeline.py --sqlite` a partir de las mismas fuentes y permite ejecutar la consulta con un cliente SQLite. La conciliación valida las sumas de venta, Cogs y filas contra el origen. El archivo `.sqlite` es generado y no se incorpora a `output/`.
