"""Controles sobre las cuatro tablas de consumo y conciliación con el origen."""
from pathlib import Path
import argparse
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output'
ARCHIVOS = {'FactVentas.csv', 'DimProducto.csv', 'FactInventarioCorte.csv', 'FactForecastSemanal.csv'}


def comprobar(source_dir: Path | None = None):
    """Concilia hechos y dimensiones de consumo con sus fuentes."""
    encontrados = {x.name for x in OUT.iterdir() if x.is_file() and x.suffix.lower() == '.csv'}
    if encontrados != ARCHIVOS:
        raise AssertionError(f'Salidas de consumo inesperadas: faltan={ARCHIVOS-encontrados}; sobran={encontrados-ARCHIVOS}')
    ventas = pd.read_csv(OUT / 'FactVentas.csv')
    productos = pd.read_csv(OUT / 'DimProducto.csv')
    corte = pd.read_csv(OUT / 'FactInventarioCorte.csv')
    forecast = pd.read_csv(OUT / 'FactForecastSemanal.csv')
    checks = {
        'solo_cuatro_csv_de_consumo': encontrados == ARCHIVOS,
        'ventas_no_vacias': len(ventas) > 0,
        'productos_no_vacios': len(productos) > 0,
        'inventario_corte_no_vacio': len(corte) > 0,
        'forecast_no_vacio': len(forecast) > 0,
        'producto_unico': productos['Product No'].is_unique,
        'corte_unico_por_tienda_producto': not corte.duplicated(['Store','Product No']).any(),
        'fecha_ventas_no_nula': ventas['fecha'].notna().all(),
        'venta_sin_productos_huerfanos': ventas['Product No'].isin(productos['Product No']).all(),
        'tienda_dax_construible': ventas['Store'].notna().all(),
        'stock_sin_productos_huerfanos': corte['Product No'].isin(productos['Product No']).all(),
        'stock_sin_tiendas_huerfanas': corte['Store'].isin(ventas['Store']).all(),
        'fechas_dax_construibles': pd.to_datetime(ventas['fecha'],errors='coerce').notna().all(),
        'cobertura_por_fila': ventas[['estado_cobertura','causa_sin_dato']].notna().all().all(),
        'cobertura_estados_validos': ventas['estado_cobertura'].isin(['SIN_DATO','STOCK_CERO','STOCK_NEGATIVO','STOCK_POSITIVO']).all(),
        'sin_dato_identificado': (ventas['estado_cobertura'].eq('SIN_DATO') == ventas['causa_sin_dato'].ne('CON_INTERVALO')).all(),
        'corte_sin_dato_no_es_cero': corte.loc[corte['estado_corte'].eq('SIN_DATO'),'Qty on hand'].isna().all(),
         'corte_fecha_unica': corte['fecha_corte'].nunique() == 1,
        'corte_estados_completos': int(corte['estado_corte'].value_counts().sum()) == len(corte),
        'ultimo_registro_solo_nulo_sin_historial': int(corte['fecha_ultimo_registro'].isna().sum()) == 2588,
        'ultimo_registro_sin_fecha_dias_nulos': (corte['fecha_ultimo_registro'].isna() == corte['dias_desde_ultimo_registro'].isna()).all(),
        'corte_sin_dato_con_historial': int((corte['estado_corte'].eq('SIN_DATO') & corte['fecha_ultimo_registro'].notna()).sum()) == 38267,
        'corte_ultimos_dias_no_negativos': corte['dias_desde_ultimo_registro'].dropna().ge(0).all(),
        'forecast_consumo_unico': not forecast.duplicated(['semana_fin','tipo']).any(),
        'forecast_consumo_8_semanas': int(forecast['tipo'].eq('PRONOSTICO').sum()) == 8,
        'forecast_tipos_validos': forecast['tipo'].isin(['OBSERVADO','PRONOSTICO']).all(),
        'forecast_sin_bandas_no_calibradas': not {'limite_inferior','limite_superior'}.intersection(forecast.columns),
        'forecast_pronostico_valido': forecast.loc[forecast['tipo'].eq('PRONOSTICO'),'valor'].notna().all(),
        'venta_con_clave_unica': not ventas.duplicated(['fecha','Store','Product No','Sales Type','Is Return']).any(),
        'abc_categorias_validas': productos['abc_ventas'].isin(['A','B','C']).all(),
        'xyz_categorias_validas': productos['xyz_demanda'].isin(['X','Y','Z','SIN_BASE']).all(),
        'abc_total_productos': len(productos) == productos['Product No'].nunique(),
        'sin_stock_no_imputado': corte.loc[corte['estado_corte'].eq('SIN_DATO'),'Cost of Stocks'].isna().all(),
        'ventas_base_conciliadas': abs(ventas['Sales Amount'].sum()-10482110.25) < .01,
        'cogs_base_conciliados': abs(ventas['Cogs'].sum()-5847751.10) < .02,
        'filas_base_conciliadas': len(ventas) == 125751,
        'filas_sin_cobertura_conciliadas': int(ventas['estado_cobertura'].eq('SIN_DATO').sum()) == 33160,
        'importe_sin_cobertura_conciliado': abs(ventas.loc[ventas['estado_cobertura'].eq('SIN_DATO'),'Sales Amount'].sum()-3190352.07) < .02,
        'retornos_venta_firmada': ventas.loc[ventas['Is Return'].eq(1),'Sales Amount'].le(0).all(),
        'retornos_cogs_firmados': ventas.loc[ventas['Is Return'].eq(1),'Cogs'].le(0).all(),
    }
    if source_dir is None:
        source_dir = ROOT/'input'
    archivo = source_dir/'retail_sales_ml_apl.csv'
    if not archivo.is_file():
        raise FileNotFoundError(f'La conciliación requiere el CSV de origen: {archivo}')
    origen = pd.read_csv(archivo, usecols=['Transaction Date','Sales Amount','Cogs','Qty Sold'])
    diario = origen.groupby('Transaction Date')[['Sales Amount','Cogs','Qty Sold']].sum().sort_index()
    derivado = ventas.groupby('fecha')[['Sales Amount','Cogs','Qty Sold']].sum().sort_index()
    checks['origen_dias_coinciden'] = diario.index.tolist() == derivado.index.tolist()
    if checks['origen_dias_coinciden']:
        diferencias = (diario.reset_index(drop=True)-derivado.reset_index(drop=True)).abs().max()
        checks['origen_ventas_por_dia'] = diferencias['Sales Amount'] < .01
        checks['origen_cogs_por_dia'] = diferencias['Cogs'] < .01
        checks['origen_unidades_por_dia'] = diferencias['Qty Sold'] < .001
    checks['origen_filas_ventas'] = len(origen) == len(ventas)
    checks['origen_venta_total'] = abs(origen['Sales Amount'].sum()-ventas['Sales Amount'].sum()) < .01
    checks['origen_costos_totales'] = abs(origen['Cogs'].sum()-ventas['Cogs'].sum()) < .01
    checks['origen_unidades_totales'] = abs(origen['Qty Sold'].sum()-ventas['Qty Sold'].sum()) < .001
    errores = [nombre for nombre,correcto in checks.items() if not bool(correcto)]
    if errores:
        raise AssertionError('Controles incumplidos: ' + ', '.join(errores))
    return {'controles':len(checks),'estado':'OK'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-dir', type=Path, default=None)
    args=parser.parse_args()
    print(comprobar(args.source_dir))
