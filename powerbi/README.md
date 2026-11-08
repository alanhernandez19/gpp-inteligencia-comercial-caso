# Power BI | Inteligencia comercial

`AH_Inteligencia_Comercial.pbip` contiene el modelo semántico y seis páginas de análisis comercial con identidad visual GPP. El nombre de los archivos PBIP se mantiene para preservar las referencias entre proyecto, informe y modelo.

## Apertura y actualización

1. Ejecutar `python src/pipeline.py` desde la raíz para regenerar las cuatro tablas en `output/`.
2. Abrir `powerbi/AH_Inteligencia_Comercial.pbip` en Power BI Desktop.
3. En Power Query, establecer `pCarpetaOutput` en la ruta absoluta de `output`, sin separador final.
4. Aplicar cambios, actualizar y comprobar indicadores, relaciones y segmentadores.

Una exportación de seis páginas realizada desde Power BI Desktop se conserva en `reports/GPP_Inteligencia_Comercial_PowerBI_Desktop.pdf`.

## Modelo

- Importadas: `FactVentas`, `DimProducto`, `FactInventarioCorte`, `FactForecastSemanal`.
- Calculadas en DAX: `DimFecha`, `DimTienda`.
- Medidas agrupadas en cinco tablas temáticas.
- `FactForecastSemanal` mantiene su eje semanal global, sin relaciones con tienda ni producto.
- Las existencias al corte representan intervalos vigentes, no una reconstrucción de todos los movimientos de inventario.

## Vistas del informe

1. Resumen ejecutivo: ventas netas, margen, devoluciones y evolución.
2. Ventas y rentabilidad: costos, modalidades de venta y márgenes.
3. Portafolio: clasificación ABC, perfiles ADI/CV² y productos.
4. Inventario: vigencia y estados de existencias al corte.
5. Calidad y conciliación: causas de ausencia de intervalos y proporciones de cobertura.
6. Pronóstico: serie semanal observada y línea base proyectada de ocho semanas.

## Reglas y límites

El margen se calcula sobre agregados y no mediante el promedio simple de porcentajes. `SIN_DATO` indica que no se observa un intervalo válido, pero no representa un inventario físico cero. La proyección semanal es global y no debe interpretarse como pronóstico por tienda o producto.

Consultar `docs/contrato_de_consumo.md` y `docs/conciliacion_y_controles.md` para las definiciones y valores de control.
