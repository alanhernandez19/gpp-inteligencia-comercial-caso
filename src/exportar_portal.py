from pathlib import Path
import pandas as pd, numpy as np, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'; DEST=ROOT/'web'/'data'; DEST.mkdir(parents=True,exist_ok=True)
v=pd.read_csv(OUT/'FactVentas.csv',encoding='utf-8-sig'); p=pd.read_csv(OUT/'DimProducto.csv',encoding='utf-8-sig'); i=pd.read_csv(OUT/'FactInventarioCorte.csv',encoding='utf-8-sig'); f=pd.read_csv(OUT/'FactForecastSemanal.csv',encoding='utf-8-sig')
v=v.merge(p[['Product No','Product Division','Product Category','Supplier','abc_ventas','perfil_intermitencia']],on='Product No',how='left',validate='many_to_one');i=i.merge(p[['Product No','Product Division','abc_ventas','perfil_intermitencia']],on='Product No',how='left',validate='many_to_one');v['mes']=v.fecha.str[:7]
# Los importes de devolución ya conservan su signo; la venta bruta excluye esas filas.
v['bruta']=np.where(v['Is Return']==0,v['Sales Amount'],0);v['dev']=np.where(v['Is Return']==1,-v['Sales Amount'],0);v['bajo']=np.where((v['Is Return']==0)&(v.Cogs>v['Sales Amount']),v['Sales Amount'],0);v['n_bajo']=((v['Is Return']==0)&(v.Cogs>v['Sales Amount'])).astype(int);v['sin_dato']=(v.estado_cobertura=='SIN_DATO').astype(int);v['importe_sin_dato']=np.where(v.sin_dato==1,v['Sales Amount'],0);v['no_positivo']=v.estado_cobertura.isin(['STOCK_CERO','STOCK_NEGATIVO']).astype(int)
MET=['Sales Amount','Cogs','Qty Sold','bruta','dev','bajo','n_bajo','sin_dato','importe_sin_dato','no_positivo'];keys=['mes','Store','Product Division','Sales Type'];
# Agregación de ventas para consultas en el portal estático.
r=v.groupby(keys,dropna=False,observed=True).agg(**{k:(k,'sum') for k in MET},lineas=('fecha','size')).reset_index()
def number(x):
 if pd.isna(x):return None
 return round(float(x),4)
def matrix(d,dimensions,metrics):return [[str(row[k]) if pd.notna(row[k]) else '' for k in dimensions]+[number(row[k]) for k in metrics] for _,row in d.iterrows()]
# Detalle mensual por tienda y producto para la exploración filtrada.
pv=v.groupby(['mes','Store','Product No'],observed=True).agg(venta=('Sales Amount','sum'),cogs=('Cogs','sum'),unidades=('Qty Sold','sum'),lineas=('fecha','size'),sin_dato=('sin_dato','sum')).reset_index()
# Indicadores de calidad por mes, tienda, división y causa.
qc=v.groupby(['mes','Store','Product Division','causa_sin_dato'],observed=True).agg(lineas=('fecha','size'),venta=('Sales Amount','sum')).reset_index()
# La cobertura de inventario al corte es distinta de la cobertura temporal de ventas.
# Se conserva el detalle tienda-producto para aplicar filtros sobre estados y antigüedad.
inventory=i[['Store','Product No','estado_corte','dias_desde_ultimo_registro','qty_ultimo_registro','Qty on hand','Cost of Stocks']].copy()
for c in ['dias_desde_ultimo_registro','qty_ultimo_registro','Qty on hand','Cost of Stocks']: inventory[c]=inventory[c].round(2)
# Catálogo de productos con sus atributos de origen y clasificaciones derivadas.
catalog=p[['Product No','Product Description','Product Division','Product Category','Supplier','abc_ventas','perfil_intermitencia','adi','cv2']]
forecast=f[['semana_fin','tipo','valor','modelo']].fillna('')
source_sha={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['FactVentas.csv','DimProducto.csv','FactInventarioCorte.csv','FactForecastSemanal.csv']}
obj={'meta':{'title':'Inteligencia comercial · Retail','source':'Retail Transactions and Stocks Data · Jimmy Smith · Mendeley Data v1 · CC BY 4.0','doi':'https://doi.org/10.17632/27x8mjm8k4.1','currency':'No especificada','cutoff':'2026-04-24','forecast_wape_folds':37.93,'forecast_wape_holdout':26.30,'source_sha256':source_sha,'schema_version':1},'stores':sorted(v.Store.unique().tolist()),'divisions':sorted(p['Product Division'].unique().tolist()),'months':sorted(v.mes.unique().tolist()),'sales':matrix(r,keys,MET+['lineas']),'storeProduct':matrix(pv,['mes','Store','Product No'],['venta','cogs','unidades','lineas','sin_dato']),'catalog':matrix(catalog,['Product No','Product Description','Product Division','Product Category','Supplier','abc_ventas','perfil_intermitencia'],['adi','cv2']),'qualityCause':matrix(qc,['mes','Store','Product Division','causa_sin_dato'],['lineas','venta']),'inventory':matrix(inventory,['Store','Product No','estado_corte'],['dias_desde_ultimo_registro','qty_ultimo_registro','Qty on hand','Cost of Stocks']),'forecast':matrix(forecast,['semana_fin','tipo','modelo'],['valor'])}
total=v['Sales Amount'].sum(); assert round(total,2)==10482110.25
assert len(v)==125751 and len(p)==2326 and len(i)==63556
assert (qc.loc[qc.causa_sin_dato!='CON_INTERVALO','lineas'].sum())==33160
path=DEST/'retail_dashboard.json';path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
print('rows',len(r),len(pv),len(qc),len(inventory),'bytes',path.stat().st_size,'totals',total,v.Cogs.sum(),v.bruta.sum(),v.dev.sum())
