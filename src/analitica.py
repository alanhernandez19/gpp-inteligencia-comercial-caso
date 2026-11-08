"""Indicadores comerciales, calidad de inventario y evaluación de demanda."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def exportar(tabla: pd.DataFrame, salida: Path, nombre: str) -> None:
    tabla.to_csv(salida / nombre, index=False, encoding='utf-8-sig')


def calendario_ventas(ventas: pd.DataFrame) -> pd.DataFrame:
    tabla = ventas.copy()
    tabla['fecha'] = tabla['Transaction Date']
    tabla['mes'] = tabla['fecha'].dt.to_period('M').astype(str)
    tabla['semana_fin'] = tabla['fecha'].dt.to_period('W-SUN').dt.end_time.dt.normalize()
    tabla['margen_bruto'] = tabla['Sales Amount'] - tabla['Cogs']
    tabla['unidades_brutas'] = tabla['Qty Sold'].where(tabla['Is Return'].eq(0), 0)
    tabla['unidades_devueltas'] = -tabla['Qty Sold'].where(tabla['Is Return'].eq(1), 0)
    return tabla


def resumen_comercial(tabla: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    medidas = {'Sales Amount': 'sum', 'Cogs': 'sum', 'margen_bruto': 'sum',
               'Qty Sold': 'sum', 'unidades_brutas': 'sum', 'unidades_devueltas': 'sum',
               'Number of Transactions': 'sum'}
    resultado = tabla.groupby(columnas, dropna=False, observed=True).agg(medidas).reset_index()
    resultado = resultado.rename(columns={
        'Sales Amount': 'ventas_netas', 'Cogs': 'costo_ventas',
        'Qty Sold': 'unidades_netas', 'Number of Transactions': 'transacciones_reportadas'
    })
    resultado['margen_pct'] = (100 * resultado['margen_bruto'] /
                               resultado['ventas_netas'].replace(0, np.nan))
    return resultado


def clasificacion_abc(ventas: pd.DataFrame) -> pd.DataFrame:
    productos = resumen_comercial(ventas, ['Product No', 'Product Division', 'Product Category', 'Supplier'])
    productos['contribucion_positiva'] = productos['ventas_netas'].clip(lower=0)
    productos = productos.sort_values(['contribucion_positiva', 'Product No'], ascending=[False, True])
    total = productos['contribucion_positiva'].sum()
    productos['participacion_acumulada'] = productos['contribucion_positiva'].cumsum() / total if total else np.nan
    acumulada_anterior = productos['participacion_acumulada'].shift(fill_value=0)
    productos['abc_ventas'] = np.select([acumulada_anterior < .80, acumulada_anterior < .95], ['A', 'B'], default='C')
    return productos


def clasificacion_xyz(ventas: pd.DataFrame, productos: pd.DataFrame) -> pd.DataFrame:
    """Variabilidad e intermitencia desde la primera semana completa con actividad."""
    semanas = pd.date_range(ventas['semana_fin'].min(), ventas['semana_fin'].max(), freq='W-SUN')
    semanas = semanas[(semanas - pd.Timedelta(days=6) >= ventas['fecha'].min()) &
                      (semanas <= ventas['fecha'].max())]
    unidades = ventas.groupby(['Product No', 'semana_fin'])['Qty Sold'].sum().unstack(fill_value=0)
    unidades = unidades.reindex(columns=semanas, fill_value=0)
    registros = []
    for producto, serie in unidades.iterrows():
        actividad = serie[serie.ne(0)]
        if actividad.empty:
            registros.append((producto, 0, 0, np.nan, np.nan, np.nan, 'SIN_BASE', 'SIN_BASE'))
            continue
        activa = serie.loc[actividad.index[0]:]
        media = activa.mean()
        cv = activa.std(ddof=0) / media if media > 0 else np.nan
        positivos = activa[activa.gt(0)]
        adi = len(activa) / len(positivos) if len(positivos) else np.nan
        cv2 = (positivos.std(ddof=0) / positivos.mean()) ** 2 if len(positivos) and positivos.mean() else np.nan
        if len(activa) < 8 or np.isnan(cv):
            xyz = 'SIN_BASE'
        else:
            xyz = 'X' if cv <= .5 else 'Y' if cv <= 1 else 'Z'
        if np.isnan(adi) or np.isnan(cv2):
            perfil = 'SIN_BASE'
        elif adi < 1.32:
            perfil = 'SUAVE' if cv2 < .49 else 'ERRATICA'
        else:
            perfil = 'INTERMITENTE' if cv2 < .49 else 'IRREGULAR'
        registros.append((producto, len(activa), len(positivos), cv, adi, cv2, xyz, perfil))
    detalle = pd.DataFrame(registros, columns=['Product No', 'semanas_activas_observables',
                            'semanas_con_venta_neta_positiva', 'cv_semanal', 'adi', 'cv2',
                            'xyz_demanda', 'perfil_intermitencia'])
    salida = productos.merge(detalle, on='Product No', how='left')
    salida['abc_xyz'] = salida['abc_ventas'] + salida['xyz_demanda']
    return salida


def cobertura_temporal(ventas: pd.DataFrame, inventario: pd.DataFrame):
    """Empareja intervalos y distingue causas de ausencia de vigencia."""
    izquierda = ventas[['Store', 'Product No', 'fecha', 'Sales Amount', 'Cogs', 'Qty Sold',
                         'Is Return', 'Product Division']].reset_index(names='id_venta')
    derecha = inventario[['Store', 'Product No', 'Start Date', 'End Date', 'Qty on hand',
                           'Cost of Stocks', 'Stock Unit Cost Price']].copy()
    abierta = derecha['End Date'].eq('9999-12-31')
    derecha['fin_efectivo'] = pd.to_datetime(derecha['End Date'].mask(
        abierta, ventas['fecha'].max().strftime('%Y-%m-%d')))
    primera = derecha.groupby(['Store','Product No'])['Start Date'].min().rename('primer_inicio')
    ultima = derecha.groupby(['Store','Product No'])['fin_efectivo'].max().rename('ultimo_fin')
    derecha = derecha.reset_index(names='id_inventario')
    cruces = pd.merge_asof(izquierda.sort_values('fecha'), derecha.sort_values('Start Date'),
        left_on='fecha', right_on='Start Date', by=['Store','Product No'], direction='backward')
    vigente = cruces['id_inventario'].notna() & cruces['fecha'].le(cruces['fin_efectivo'])
    cruces['estado_cobertura'] = np.select([
        ~vigente, cruces['Qty on hand'].lt(0), cruces['Qty on hand'].eq(0), cruces['Qty on hand'].gt(0)
    ], ['SIN_DATO', 'STOCK_NEGATIVO', 'STOCK_CERO', 'STOCK_POSITIVO'], default='SIN_DATO')
    limites = pd.concat([primera, ultima], axis=1).reset_index()
    cruces = cruces.merge(limites, on=['Store','Product No'], how='left')
    cruces['causa_sin_dato'] = np.select([
        cruces['primer_inicio'].isna(),
        cruces['fecha'].lt(cruces['primer_inicio']),
        cruces['fecha'].gt(cruces['ultimo_fin']),
        ~vigente
    ], ['PAR_SIN_INVENTARIO', 'ANTES_PRIMER_INTERVALO', 'DESPUES_ULTIMO_INTERVALO',
        'ENTRE_INTERVALOS'], default='CON_INTERVALO')
    return cruces


def calidad_inventario(inventario: pd.DataFrame) -> pd.DataFrame:
    salida = inventario[['Store', 'Product No', 'Start Date', 'End Date', 'Qty on hand',
                         'Cost of Stocks', 'Stock Unit Cost Price', 'Supplier']].copy()
    salida['valor_calculado'] = salida['Qty on hand'] * salida['Stock Unit Cost Price']
    salida['diferencia_valorizacion'] = salida['Cost of Stocks'] - salida['valor_calculado']
    salida['valorizacion_fuera_tolerancia'] = salida['diferencia_valorizacion'].abs() > .10
    salida['existencia_negativa'] = salida['Qty on hand'] < 0
    salida['existencia_cero_valorizada'] = (salida['Qty on hand'] == 0) & (salida['Cost of Stocks'] != 0)
    return salida


def agregar_cobertura(cruces: pd.DataFrame, columnas: list[str]) -> pd.DataFrame:
    datos = cruces.copy()
    datos['sin_dato'] = datos['estado_cobertura'].eq('SIN_DATO')
    datos['venta_sin_dato'] = datos['Sales Amount'].where(datos['sin_dato'], 0)
    datos['venta_con_dato'] = datos['Sales Amount'].where(~datos['sin_dato'], 0)
    resultado = datos.groupby(columnas).agg(
        filas_ventas=('id_venta', 'size'), ventas_netas=('Sales Amount', 'sum'),
        filas_sin_dato=('sin_dato', 'sum'), ventas_sin_dato=('venta_sin_dato', 'sum'),
        ventas_con_dato=('venta_con_dato', 'sum')
    ).reset_index()
    resultado['filas_sin_dato_pct'] = 100 * resultado['filas_sin_dato'] / resultado['filas_ventas']
    resultado['ventas_sin_dato_pct'] = 100 * resultado['ventas_sin_dato'] / resultado['ventas_netas'].replace(0, np.nan)
    return resultado


def candidatos_demanda(entrenamiento: pd.Series, horizonte: int) -> dict[str, np.ndarray]:
    ultimo = float(entrenamiento.iloc[-1])
    media4 = float(entrenamiento.iloc[-4:].mean())
    media8 = float(entrenamiento.iloc[-8:].mean())
    secuencia4 = entrenamiento.iloc[-4:].to_numpy(dtype=float)
    return {
        'ultimo_valor': np.repeat(ultimo, horizonte),
        'media_4': np.repeat(media4, horizonte),
        'media_8': np.repeat(media8, horizonte),
        'media_total': np.repeat(float(entrenamiento.mean()), horizonte),
        'patron_4': np.resize(secuencia4, horizonte),
    }


def backtesting(ventas: pd.DataFrame):
    semanal = ventas.groupby('semana_fin')['Sales Amount'].sum().sort_index()
    fechas = semanal.index
    primera, ultima = ventas['fecha'].min(), ventas['fecha'].max()
    semanal = semanal[(fechas - pd.Timedelta(days=6) >= primera) & (fechas <= ultima)]
    horizonte = 4
    # Reservar el último bloque para comprobar el modelo que ganó en cortes previos.
    entrenamiento = semanal.iloc[:-horizonte]
    cortes = range(20, len(entrenamiento) - horizonte + 1, 4)
    pruebas = []
    for fin in cortes:
        train = entrenamiento.iloc[:fin]
        test = entrenamiento.iloc[fin:fin + horizonte]
        for nombre, pred in candidatos_demanda(train, horizonte).items():
            for fecha, real, estimado in zip(test.index, test.values, pred):
                pruebas.append({'origen': train.index[-1], 'semana_fin': fecha,
                                'modelo': nombre, 'real': real, 'pronostico': estimado})
    detalle = pd.DataFrame(pruebas)
    if detalle.empty:
        raise ValueError('No hay semanas suficientes para validar varios cortes.')
    detalle['error'] = detalle['real'] - detalle['pronostico']
    detalle['error_absoluto'] = detalle['error'].abs()
    resumen = detalle.groupby('modelo').agg(
        mae=('error_absoluto', 'mean'), error_abs_total=('error_absoluto', 'sum'),
        real_abs_total=('real', lambda x: x.abs().sum()), sesgo=('error', 'mean'),
        cortes=('origen', 'nunique')
    ).reset_index()
    resumen['wape_pct'] = 100 * resumen['error_abs_total'] / resumen['real_abs_total']
    resumen = resumen.sort_values(['wape_pct', 'modelo'])
    por_corte = detalle.groupby(['modelo', 'origen']).agg(
        error_absoluto=('error_absoluto', 'sum'), observado=('real', 'sum'),
        sesgo_semanal=('error', 'mean')).reset_index()
    por_corte['wape_pct'] = 100 * por_corte['error_absoluto'] / por_corte['observado'].abs()
    ganador = resumen.iloc[0]['modelo']
    pred_prueba = candidatos_demanda(entrenamiento, horizonte)[ganador]
    prueba = pd.DataFrame({'semana_fin': semanal.iloc[-4:].index,
                           'real': semanal.iloc[-4:].values, 'pronostico': pred_prueba,
                           'modelo': ganador})
    prueba['error'] = prueba['real'] - prueba['pronostico']
    prueba['error_absoluto'] = prueba['error'].abs()
    # El siguiente domingo tras el corte del archivo es parcial: se excluye de la proyección.
    primer_futuro = ultima.to_period('W-SUN').end_time.normalize() + pd.Timedelta(days=7)
    futuro = pd.date_range(primer_futuro, periods=8, freq='W-SUN')
    proyeccion = pd.DataFrame({'semana_fin': futuro,
        'pronostico': candidatos_demanda(semanal, 8)[ganador],
        'modelo': ganador, 'tipo': 'LINEA_BASE_EXPLORATORIA'})
    # No se extrapola una banda desde 4 semanas validadas hacia 8 futuras.
    # La variabilidad del error se presenta por corte en el notebook exploratorio.
    historico = semanal.rename('ventas_observadas').reset_index().rename(columns={'semana_fin': 'semana_fin'})
    return historico, detalle, resumen, por_corte, prueba, proyeccion


def presupuesto_muestra(ventas: pd.DataFrame) -> pd.DataFrame:
    """Objetivo ilustrativo: usa únicamente el mes calendario inmediatamente anterior."""
    inicio, fin = ventas['fecha'].min(), ventas['fecha'].max()
    datos = ventas.copy()
    if inicio.day != 1:
        datos = datos.loc[datos['fecha'].dt.to_period('M') > inicio.to_period('M')]
    if fin.day != fin.days_in_month:
        datos = datos.loc[datos['fecha'].dt.to_period('M') < fin.to_period('M')]
    tabla = resumen_comercial(datos, ['mes', 'Store', 'Product Division'])
    tabla['mes_previo'] = (pd.PeriodIndex(tabla['mes'], freq='M') - 1).astype(str)
    referencia = tabla[['mes', 'Store', 'Product Division', 'ventas_netas']].rename(
        columns={'mes': 'mes_previo', 'ventas_netas': 'referencia_mes_previo'})
    tabla = tabla.merge(referencia, on=['mes_previo','Store','Product Division'], how='left')
    tabla = tabla.dropna(subset=['referencia_mes_previo']).copy()
    tabla['meta_escenario'] = (tabla['referencia_mes_previo'].clip(lower=0) * 1.05).round(2)
    tabla['ratio_escenario_pct'] = 100 * tabla['ventas_netas'] / tabla['meta_escenario'].replace(0, np.nan)
    tabla['naturaleza'] = 'ESCENARIO_DEMOSTRATIVO'
    return tabla[['mes', 'Store', 'Product Division', 'referencia_mes_previo',
                  'meta_escenario', 'ventas_netas', 'ratio_escenario_pct', 'naturaleza']]


def homologacion_muestra(productos: pd.DataFrame, ventas: pd.DataFrame) -> pd.DataFrame:
    """Catálogo de prueba con correspondencias completas, faltantes y ambiguas."""
    claves = productos[['Product No', 'Product Division']].sort_values('Product No').reset_index(drop=True)
    claves['codigo_sistema_comercial'] = ['COM-' + str(i).zfill(5) for i in range(1, len(claves) + 1)]
    claves['codigo_sistema_inventario'] = claves['Product No']
    claves['naturaleza'] = 'ESCENARIO_DEMOSTRATIVO'
    # Incidencias controladas: se conserva la referencia correcta en la columna original.
    claves.loc[:11, 'codigo_sistema_inventario'] = pd.NA
    claves.loc[12:19, 'codigo_sistema_inventario'] = claves.loc[20:27, 'Product No'].to_numpy()
    duplicada = claves['codigo_sistema_inventario'].duplicated(keep=False) & claves['codigo_sistema_inventario'].notna()
    claves['estado_homologacion'] = np.select([
        claves['codigo_sistema_inventario'].isna(), duplicada,
        claves['codigo_sistema_inventario'].fillna('').ne(claves['Product No'])
    ], ['SIN_CORRESPONDENCIA', 'CODIGO_AMBIGUO', 'CODIGO_INCONSISTENTE'], default='CORRECTO')
    impacto = ventas.groupby('Product No')['Sales Amount'].sum().rename('ventas_netas_asociadas')
    claves = claves.join(impacto, on='Product No')
    return claves


def inventario_a_corte(ventas: pd.DataFrame, inventario: pd.DataFrame) -> pd.DataFrame:
    """Existencia vigente y último registro conocido por tienda-producto."""
    corte = ventas['fecha'].max()
    claves = ['Store', 'Product No']
    pares = pd.concat([ventas[claves], inventario[claves]]).drop_duplicates().reset_index(drop=True)
    historial = inventario.copy()
    abiertas = historial['End Date'].eq('9999-12-31')
    historial['fin_efectivo'] = pd.to_datetime(historial['End Date'].mask(
        abiertas, corte.strftime('%Y-%m-%d')))
    historial = historial.loc[historial['Start Date'].le(corte)].copy()
    vigente = historial.loc[historial['fin_efectivo'].ge(corte)]
    if vigente.duplicated(claves).any():
        raise ValueError('Más de un intervalo vigente por tienda-producto al corte.')
    columnas = claves + ['Qty on hand', 'Cost of Stocks']
    salida = pares.merge(vigente[columnas], on=claves, how='left', validate='one_to_one')
    cantidad = salida['Qty on hand']
    salida['estado_corte'] = np.select([
        cantidad.isna(), cantidad.lt(0), cantidad.eq(0)
    ], ['SIN_DATO', 'STOCK_NEGATIVO', 'STOCK_CERO'], default='STOCK_POSITIVO')
    # El último fin registrado permite distinguir un par sin historial de un registro vencido.
    ultimo = (historial.sort_values(claves + ['fin_efectivo', 'Start Date'])
                    .drop_duplicates(claves, keep='last'))
    ultimo = ultimo[claves + ['fin_efectivo', 'Qty on hand']].rename(columns={
        'fin_efectivo': 'fecha_ultimo_registro',
        'Qty on hand': 'qty_ultimo_registro'})
    salida = salida.merge(ultimo, on=claves, how='left', validate='one_to_one')
    salida['dias_desde_ultimo_registro'] = (
        corte - salida['fecha_ultimo_registro']).dt.days.astype('Int64')
    salida['fecha_corte'] = corte
    return salida


def serie_forecast(historico: pd.DataFrame, proyeccion: pd.DataFrame) -> pd.DataFrame:
    """Serie observada y línea base exploratoria sin bandas no calibradas."""
    real = historico[['semana_fin', 'ventas_observadas']].rename(columns={'ventas_observadas': 'valor'})
    real['tipo'] = 'OBSERVADO'
    real['modelo'] = ''
    futuro = proyeccion[['semana_fin', 'pronostico', 'modelo']].rename(
        columns={'pronostico': 'valor'})
    futuro['tipo'] = 'PRONOSTICO'
    return pd.concat([real, futuro], ignore_index=True)[['semana_fin','tipo','valor','modelo']]


def modelo_consumo(ventas: pd.DataFrame, inventario: pd.DataFrame,
                   productos_perfil: pd.DataFrame, cruces: pd.DataFrame,
                   salida: Path) -> None:
    """Hechos y maestro para un modelo mínimo; fecha y tienda se crean en DAX."""
    atributos = ['Product No', 'Product Description', 'Product Division',
                 'Product Category', 'Product Subcategory', 'Product Segment', 'Supplier']
    productos = ventas[atributos].drop_duplicates('Product No').sort_values('Product No')
    perfil = productos_perfil[['Product No', 'abc_ventas', 'xyz_demanda',
                              'perfil_intermitencia', 'adi', 'cv2', 'cv_semanal']]
    productos = productos.merge(perfil, on='Product No', validate='one_to_one')
    hechos = ventas[['fecha', 'Store', 'Product No', 'Sales Type', 'Is Return',
                     'Qty Sold', 'Sales Amount', 'Cogs', 'Number of Transactions']].copy()
    estado = cruces.set_index('id_venta')[['estado_cobertura', 'causa_sin_dato']]
    hechos = hechos.join(estado, how='left')
    if hechos[['estado_cobertura', 'causa_sin_dato']].isna().any().any():
        raise ValueError('Falta clasificación de cobertura para filas de venta.')
    exportar(productos, salida, 'DimProducto.csv')
    exportar(hechos, salida, 'FactVentas.csv')
    exportar(inventario_a_corte(ventas, inventario), salida, 'FactInventarioCorte.csv')

def ejecutar(ventas_originales: pd.DataFrame, inventario: pd.DataFrame, salida: Path) -> dict:
    """Calcula indicadores de análisis y exporta cuatro tablas de consumo."""
    ventas = calendario_ventas(ventas_originales)
    productos = clasificacion_xyz(ventas, clasificacion_abc(ventas))
    cruces = cobertura_temporal(ventas, inventario)
    modelo_consumo(ventas, inventario, productos, cruces, salida)
    historico, detalle, resumen, por_corte, prueba, proyeccion = backtesting(ventas)
    exportar(serie_forecast(historico, proyeccion), salida, 'FactForecastSemanal.csv')
    inventario_calidad = calidad_inventario(inventario)
    presupuesto = presupuesto_muestra(ventas)
    homologacion = homologacion_muestra(productos, ventas)
    return {
        'filas_productos': int(len(productos)),
        'filas_ventas_con_cobertura': int(cruces['estado_cobertura'].ne('SIN_DATO').sum()),
        'ventas_netas_sin_cobertura': round(float(cruces.loc[cruces['estado_cobertura'].eq('SIN_DATO'), 'Sales Amount'].sum()), 2),
        'filas_valorizacion_fuera_tolerancia': int(inventario_calidad['valorizacion_fuera_tolerancia'].sum()),
        'forecast_modelo_elegido': resumen.iloc[0]['modelo'],
        'forecast_cortes': int(resumen.iloc[0]['cortes']),
        'forecast_wape_prueba_final_pct': round(float(100 * prueba['error_absoluto'].sum() / prueba['real'].abs().sum()), 2),
        'presupuesto_filas_escenario': int(len(presupuesto)),
        'homologacion_incidencias_escenario': int(homologacion['estado_homologacion'].ne('CORRECTO').sum()),
    }
