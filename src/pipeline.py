"""Integración comercial: ventas e inventarios minoristas."""
from __future__ import annotations
import argparse, sqlite3
from pathlib import Path
import pandas as pd
from analitica import ejecutar as ampliar_analisis, cobertura_temporal
from fuentes_manuales import procesar_ajustes

ROOT=Path(__file__).resolve().parents[1]
SALES_FILE='retail_sales_ml_apl.csv'
STOCK_FILE='retail_inventory_ml_apl.csv'


def locate(name:str,source:Path|None):
    paths=([source/name] if source else [])+[ROOT/'input'/name]
    for p in paths:
        if p.is_file():return p
    raise FileNotFoundError(f'No se encuentra {name}. Colocar ambos CSV en input/ o indicar --source-dir.')


def load(source:Path|None=None):
    sp,ip=locate(SALES_FILE,source),locate(STOCK_FILE,source)
    sales=pd.read_csv(sp,parse_dates=['Transaction Date'],low_memory=False)
    stock=pd.read_csv(ip,low_memory=False,dtype={'End Date':'string'},parse_dates=['Start Date'])
    assert len(sales)>0 and len(stock)>0
    return sales, stock


def analyse_sales(sales):
    key=['Transaction Date','Store','Product No','Sales Type','Is Return']
    summary=[]
    def add(name,value,unit='registros'):
        summary.append({'control':name,'value':value,'unit':unit})
    add('filas_ventas',int(len(sales)))
    add('duplicados_clave_ventas',int(sales.duplicated(key).sum()))
    add('devoluciones_filas',int((sales['Is Return']==1).sum()))
    add('devoluciones_cantidad_no_negativa',int(((sales['Is Return']==1)&(sales['Qty Sold']>=0)).sum()))
    add('devoluciones_venta_no_negativa',int(((sales['Is Return']==1)&(sales['Sales Amount']>=0)).sum()))
    add('devoluciones_cogs_no_negativo',int(((sales['Is Return']==1)&(sales['Cogs']>=0)).sum()))
    add('razon_devolucion_filas_no_nulas',int(sales['Reason of Return'].notna().sum()))
    add('ventas_brutas',round(float(sales.loc[sales['Is Return']==0,'Sales Amount'].sum()),2),'importe')
    add('importe_devoluciones',round(float(sales.loc[sales['Is Return']==1,'Sales Amount'].sum()),2),'importe')
    add('ventas_netas',round(float(sales['Sales Amount'].sum()),2),'importe')
    add('cogs_neto',round(float(sales['Cogs'].sum()),4),'importe')
    margin=float((sales['Sales Amount']-sales['Cogs']).sum())
    add('margen_bruto_derivado',round(margin,4),'importe')
    add('margen_bruto_porcentaje',round(margin/sales['Sales Amount'].sum()*100,4),'porcentaje')
    add('fechas_con_ventas',int(sales['Transaction Date'].nunique()),'fechas')
    add('fecha_inicio_ventas',str(sales['Transaction Date'].min().date()),'fecha')
    add('fecha_fin_ventas',str(sales['Transaction Date'].max().date()),'fecha')
    return pd.DataFrame(summary)


def interval_quality(stock,sales):
    maxdate=sales['Transaction Date'].max()
    st=stock[['Store','Product No','Start Date','End Date','Qty on hand','Cost of Stocks','Stock Unit Cost Price','Stocks Selling Amount','Stock Unit Selling Price']].copy()
    st['is_open_interval']=st['End Date'].eq('9999-12-31')
    st['end_effective']=pd.to_datetime(st['End Date'].mask(st['is_open_interval'],maxdate.strftime('%Y-%m-%d')),errors='coerce')
    st['end_for_sequence']=pd.to_datetime(st['End Date'].mask(st['is_open_interval'],'2262-01-01'),errors='coerce')
    # Preservar el valor original de fin abierto, sin convertir 9999 a datetime de pandas.
    s=st.sort_values(['Store','Product No','Start Date','end_for_sequence'],kind='mergesort')
    groups=s.groupby(['Store','Product No'],sort=False)
    previous_end=groups['end_for_sequence'].shift()
    delta=(s['Start Date']-previous_end).dt.days
    gaps=(delta>1)
    overlaps=(delta<=0)
    invalid=st['Start Date']>st['end_for_sequence']
    discrepancy=st['Cost of Stocks']-st['Qty on hand']*st['Stock Unit Cost Price']
    summary=[
      ('filas_inventario',len(st),'registros'),('intervalos_abiertos',st['is_open_interval'].sum(),'registros'),
      ('fechas_fin_invalidas',st['end_for_sequence'].isna().sum(),'registros'),('intervalos_inicio_mayor_fin',invalid.sum(),'registros'),
      ('huecos_entre_intervalos',gaps.sum(),'separaciones'),('solapes_entre_intervalos',overlaps.sum(),'separaciones'),
      ('existencias_negativas',st['Qty on hand'].lt(0).sum(),'registros'),
      ('existencias_cero',st['Qty on hand'].eq(0).sum(),'registros'),
      ('valorizacion_diferencia_abs_gt_010',discrepancy.abs().gt(0.1).sum(),'registros'),
      ('valorizacion_diferencia_abs_suma_gt_010',round(float(discrepancy[discrepancy.abs()>0.1].abs().sum()),4),'importe'),
      ('valorizacion_diferencia_neta_gt_010',round(float(discrepancy[discrepancy.abs()>0.1].sum()),4),'importe'),
      ('existencia_cero_con_costo_stock_distinto_cero',((st['Qty on hand']==0)&(st['Cost of Stocks']!=0)).sum(),'registros')]
    summary=pd.DataFrame(summary,columns=['control','value','unit'])
    exceptions=st.loc[(discrepancy.abs()>0.1)|invalid|st['Qty on hand'].lt(0),['Store','Product No','Start Date','End Date','Qty on hand','Cost of Stocks','Stock Unit Cost Price']].copy()
    exceptions['difference']=discrepancy.loc[exceptions.index]
    exceptions['valorization_gt_010']=exceptions['difference'].abs()>0.1
    exceptions['negative_quantity']=exceptions['Qty on hand']<0
    return summary,exceptions,st,gaps.sum(),overlaps.sum()


def coverage(sales, stock):
    preparado = sales.rename(columns={'Transaction Date': 'fecha'}).copy()
    for columna in ['Sales Amount', 'Cogs', 'Qty Sold', 'Is Return']:
        if columna not in preparado:
            preparado[columna] = 0
    if 'Product Division' not in preparado:
        preparado['Product Division'] = 'SIN_CLASIFICAR'
    cruces = cobertura_temporal(preparado, stock)
    valido = cruces['estado_cobertura'].ne('SIN_DATO')
    summary = pd.DataFrame([
        {'control': 'filas_venta_con_intervalo_vigente', 'value': int(valido.sum()), 'unit': 'registros'},
        {'control': 'filas_venta_sin_intervalo_vigente', 'value': int((~valido).sum()), 'unit': 'registros'},
        {'control': 'porcentaje_ventas_con_cobertura', 'value': round(float(valido.mean()*100),4), 'unit': 'porcentaje'}])
    missing = cruces.loc[~valido, ['id_venta','Store','Product No','fecha','causa_sin_dato']].rename(
        columns={'id_venta':'sales_row','fecha':'Transaction Date'})
    return summary, missing


def main(source:Path|None=None, sqlite:bool=False):
    OUT=ROOT/'output';OUT.mkdir(exist_ok=True,parents=True)
    # Eliminar únicamente salidas antiguas administradas por el ETL.
    for anterior in OUT.iterdir():
        if anterior.is_file() and anterior.suffix.lower() == '.csv':
            anterior.unlink()
    sales,stock=load(source)
    sumsales=analyse_sales(sales)
    sumstock,_,stock_for_interval,_,overlaps=interval_quality(stock,sales)
    if overlaps:
        raise RuntimeError(f'Se detectaron {overlaps} solapes; el emparejamiento temporal exige revisar primero su resolución.')
    ampliacion = ampliar_analisis(sales,stock,OUT)
    estados = pd.read_csv(OUT/'FactVentas.csv', usecols=['estado_cobertura'])['estado_cobertura']
    cubiertas = estados.ne('SIN_DATO')
    sumcoverage = pd.DataFrame([
        {'control':'filas_venta_con_intervalo_vigente','value':int(cubiertas.sum()),'unit':'registros'},
        {'control':'filas_venta_sin_intervalo_vigente','value':int((~cubiertas).sum()),'unit':'registros'},
        {'control':'porcentaje_ventas_con_cobertura','value':round(float(cubiertas.mean()*100),4),'unit':'porcentaje'}])
    summary = pd.concat([sumsales,sumstock,sumcoverage],ignore_index=True)
    ampliacion.update(procesar_ajustes(ROOT, sales))
    if sqlite:
        db = ROOT / 'sql' / 'retail_analytics.sqlite'
        db.parent.mkdir(exist_ok=True)
        if db.exists():
            db.unlink()
        with sqlite3.connect(db) as con:
            tabla = sales.rename(columns={
                'Transaction Date': 'fecha', 'Sales Type': 'tipo_venta',
                'Is Return': 'es_devolucion', 'Product No': 'producto',
                'Store': 'tienda', 'Qty Sold': 'unidades',
                'Sales Amount': 'importe_venta', 'Cogs': 'cogs'
            }).copy()
            tabla['fecha'] = tabla['fecha'].dt.strftime('%Y-%m-%d')
            tabla.to_sql('fact_ventas', con, index=False, chunksize=10000)
            stock_sql = stock.copy()
            stock_sql['Start Date'] = stock_sql['Start Date'].dt.strftime('%Y-%m-%d')
            stock_sql.to_sql('fact_inventario_intervalos', con, index=False, chunksize=10000)
            summary.to_sql('qa_resumen', con, index=False)
            con.execute('CREATE INDEX ix_ventas ON fact_ventas(tienda,producto,fecha)')
            con.execute('CREATE INDEX ix_stock ON fact_inventario_intervalos(Store,"Product No","Start Date")')
            ventas_sql = con.execute('SELECT ROUND(SUM(importe_venta),2), ROUND(SUM(cogs),4), COUNT(*) FROM fact_ventas').fetchone()
            assert abs(ventas_sql[0] - round(float(sales['Sales Amount'].sum()),2)) < .011
            assert abs(ventas_sql[1] - round(float(sales['Cogs'].sum()),4)) < .001
            assert ventas_sql[2] == len(sales)
        print('\nConciliación SQL:', db)
    print(summary.to_string(index=False))
    print('\nAnálisis ampliado:', ampliacion)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-dir',type=Path,default=None,help='Carpeta de los dos CSV originales')
    parser.add_argument('--sqlite', action='store_true', help='Crear base SQLite para consultas de conciliación SQL')
    args=parser.parse_args()
    main(args.source_dir, sqlite=args.sqlite)
