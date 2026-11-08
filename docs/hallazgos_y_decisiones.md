# Hallazgos comerciales y alcance

**Base comercial.** Se observan 10,482,110.25 de ventas netas y 5,847,751.10 de Cogs; el margen bruto agregado derivado es 44.21 %. Los importes no tienen moneda declarada. Las devoluciones ya están firmadas y no se descuentan dos veces.

**Portafolio.** La clasificación ABC y los indicadores de variabilidad semanal e intermitencia permiten explorar concentración y comportamiento de ventas registradas, no demanda potencial. Los cálculos se inspeccionan en el notebook 01 y el perfil empleado en visualizaciones está incluido en `DimProducto`.

**Cobertura del inventario.** 33,160 filas comerciales carecen de intervalo vigente tienda-producto-fecha, por un importe neto de 3,190,352.07. Sus causas se clasifican dentro de `FactVentas`. La existencia igual o inferior a cero indica lo observado en el registro, no demuestra quiebre ni sobreventa.

**Valorización.** Se registran 6,358 diferencias superiores a 0.10 de tolerancia. La exploración de residuos y excepciones se realiza en el notebook 03; no se atribuyen causas sin información de movimientos o políticas contables.

**Planeación.** El forecast semanal 4+8 constituye una línea base experimental con precisión variable según el corte. El presupuesto de crecimiento supuesto del 5 % es un ejercicio de escenario dentro del notebook 01, no un objetivo empresarial observado.

**Continuidad del inventario.** Al corte 2026-04-24, 40,855 de 63,556 pares tienda-producto no disponen de intervalo vigente. De ellos, 38,267 tienen un intervalo histórico anterior; la mediana de días desde el último registro es 108 y el 84.3 % tenía existencia positiva en ese último registro. Son condiciones de registro, sin causa operacional atribuida.

**Tipo de venta y devoluciones.** Se registran devoluciones por 733,571.01, equivalentes a 6.54 % de 11,215,681.26 de venta bruta. Se observan márgenes brutos negativos en Markdown Tier 2 y Clearance y 7,045 filas no devueltas con Cogs superior al importe de venta. El significado contable exacto de Cogs no se detalla en la fuente.

**Cobertura con intervalo.** En 11,459 filas el intervalo vigente registra existencia cero o negativa. El dato corresponde a un estado almacenado, no a una demostración de venta sin stock físico.
