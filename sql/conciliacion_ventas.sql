-- Conciliación de importes, costos y margen por tipo de venta en fact_ventas.
SELECT tipo_venta,
       COUNT(*) AS filas,
       ROUND(SUM(importe_venta), 2) AS ventas_netas,
       ROUND(SUM(cogs), 2) AS costo_ventas,
       ROUND(SUM(importe_venta - cogs), 2) AS margen_bruto,
       ROUND(100.0 * SUM(importe_venta-cogs) / NULLIF(SUM(importe_venta), 0), 2) AS margen_pct
FROM fact_ventas
GROUP BY tipo_venta
ORDER BY ventas_netas DESC;
