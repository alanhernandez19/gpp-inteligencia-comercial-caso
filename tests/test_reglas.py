"""Casos pequeños para verificar reglas sin depender de los totales de Retail."""
import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline import interval_quality, coverage
from fuentes_manuales import validar_ajustes


class ReglasDeInventario(unittest.TestCase):
    def setUp(self):
        self.ventas = pd.DataFrame({
            'Store': ['T1', 'T1', 'T1'],
            'Product No': ['P1', 'P1', 'P2'],
            'Transaction Date': pd.to_datetime(['2025-01-02', '2025-01-06', '2025-01-03']),
        })
        self.inventario = pd.DataFrame({
            'Store': ['T1', 'T1'], 'Product No': ['P1', 'P1'],
            'Start Date': pd.to_datetime(['2025-01-01', '2025-01-05']),
            'End Date': ['2025-01-03', '9999-12-31'],
            'Qty on hand': [4, 0], 'Cost of Stocks': [8, 0],
            'Stock Unit Cost Price': [2, 2], 'Stocks Selling Amount': [12, 0],
            'Stock Unit Selling Price': [3, 3],
        })

    def test_hueco_y_fin_abierto(self):
        resumen, _, stock, huecos, solapes = interval_quality(self.inventario, self.ventas)
        self.assertEqual((huecos, solapes), (1, 0))
        self.assertEqual(int(resumen.set_index('control').loc['intervalos_abiertos', 'value']), 1)
        _, ausentes = coverage(self.ventas, stock)
        self.assertEqual(len(ausentes), 1)
        self.assertEqual(ausentes.iloc[0]['Product No'], 'P2')

    def test_solape(self):
        datos = self.inventario.copy()
        datos.loc[0, 'End Date'] = '2025-01-06'
        _, _, _, _, solapes = interval_quality(datos, self.ventas)
        self.assertEqual(solapes, 1)

    def test_inicio_despues_de_fin(self):
        datos = self.inventario.copy()
        datos.loc[0, 'End Date'] = '2024-12-31'
        resumen, _, _, _, _ = interval_quality(datos, self.ventas)
        self.assertEqual(int(resumen.set_index('control').loc['intervalos_inicio_mayor_fin', 'value']), 1)


class ArchivoManual(unittest.TestCase):
    def test_duplicado_y_referencia_invalida(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'ajustes.csv'
            archivo.write_text(
                'documento,fecha_recepcion,mes,Store,Product No,importe_ajuste,estado,version,nota\n'
                'A1,2025-01-01,2025-01,T1,P1,10,APROBADO,1,Correcto\n'
                'A2,2025-01-01,2025-01,T1,P1,20,APROBADO,1,Duplicado\n'
                'A2,2025-01-01,2025-01,T1,P1,20,APROBADO,1,Duplicado\n'
                'A3,2025-01-01,2025-01,T9,P1,10,APROBADO,1,Tienda ausente\n', encoding='utf-8'
            )
            resultado = validar_ajustes(archivo, {'P1'}, {'T1'})
            self.assertEqual(resultado['resultado_validacion'].tolist(),
                             ['VALIDO', 'RECHAZADO', 'RECHAZADO', 'RECHAZADO'])
            self.assertTrue(resultado.loc[1, 'incidencias'].startswith('DOCUMENTO_DUPLICADO'))


class ReglasAnaliticas(unittest.TestCase):
    def test_producto_con_inicio_tardio(self):
        from analitica import clasificacion_xyz
        semanas = pd.date_range('2025-01-05', periods=20, freq='W-SUN')
        ventas = pd.DataFrame({
            'Product No': ['P1']*20 + ['P2']*4,
            'semana_fin': list(semanas) + list(semanas[16:]),
            'fecha': list(semanas) + list(semanas[16:]),
            'Qty Sold': [5]*20 + [5]*4})
        productos = pd.DataFrame({'Product No':['P1','P2'], 'abc_ventas':['A','B']})
        resultado = clasificacion_xyz(ventas, productos).set_index('Product No')
        self.assertEqual(int(resultado.loc['P2','semanas_activas_observables']),4)
        self.assertEqual(resultado.loc['P2','xyz_demanda'],'SIN_BASE')

    def test_mes_sin_referencia_inmediata(self):
        from analitica import presupuesto_muestra
        datos = pd.DataFrame({
          'fecha':pd.to_datetime(['2025-01-01','2025-03-10','2025-04-10','2025-05-31']),
          'mes':['2025-01','2025-03','2025-04','2025-05'],
          'Store':['T1']*4, 'Product Division':['D1']*4,
          'Sales Amount':[100,120,130,140], 'Cogs':[50]*4,
          'margen_bruto':[50,70,80,90], 'Qty Sold':[1]*4,
          'unidades_brutas':[1]*4, 'unidades_devueltas':[0]*4,
          'Number of Transactions':[1]*4})
        salida = presupuesto_muestra(datos)
        self.assertNotIn('2025-03',salida['mes'].tolist())
        self.assertIn('2025-04',salida['mes'].tolist())

    def test_forecast_excluye_semana_parcial(self):
        from analitica import calendario_ventas, backtesting
        fechas = pd.date_range('2025-06-01','2026-04-24',freq='D')
        ventas = pd.DataFrame({'Transaction Date':fechas,'Sales Amount':[100]*len(fechas),
                               'Cogs':[50]*len(fechas),'Qty Sold':[1]*len(fechas),
                               'Is Return':[0]*len(fechas)})
        _,_,_,_,_,futuro = backtesting(calendario_ventas(ventas))
        self.assertEqual(futuro['semana_fin'].iloc[0],pd.Timestamp('2026-05-03'))
        self.assertEqual(len(futuro),8)

    def test_abc_venta_negativa(self):
        from analitica import clasificacion_abc
        ventas = pd.DataFrame({'Product No':['P1','P2'], 'Product Division':['D1']*2,
          'Product Category':['C1']*2,'Supplier':['S1']*2,'Sales Amount':[100,-20],
          'Cogs':[40,0],'margen_bruto':[60,-20],'Qty Sold':[2,-1],
          'unidades_brutas':[2,0],'unidades_devueltas':[0,1],
          'Number of Transactions':[1,1]})
        resultado = clasificacion_abc(ventas).set_index('Product No')
        self.assertEqual(resultado.loc['P2','contribucion_positiva'],0)


if __name__ == '__main__':
    unittest.main()

class ContratosDeConsumo(unittest.TestCase):
    def test_corte_separa_historial_de_vigencia(self):
        from analitica import inventario_a_corte
        ventas = pd.DataFrame({
            'Store':['T1','T1','T1'], 'Product No':['P1','P2','P3'],
            'fecha':pd.to_datetime(['2025-01-10']*3)})
        stock = pd.DataFrame({
            'Store':['T1','T1'], 'Product No':['P1','P2'],
            'Start Date':pd.to_datetime(['2025-01-01']*2),
            'End Date':['2025-01-05','9999-12-31'],
            'Qty on hand':[7,3], 'Cost of Stocks':[70,30]})
        r=inventario_a_corte(ventas,stock).set_index('Product No')
        self.assertEqual(r.loc['P1','estado_corte'],'SIN_DATO')
        self.assertTrue(pd.isna(r.loc['P1','Qty on hand']))
        self.assertEqual(r.loc['P1','qty_ultimo_registro'],7)
        self.assertEqual(r.loc['P1','dias_desde_ultimo_registro'],5)
        self.assertEqual(r.loc['P2','estado_corte'],'STOCK_POSITIVO')
        self.assertEqual(r.loc['P2','dias_desde_ultimo_registro'],0)
        self.assertTrue(pd.isna(r.loc['P3','fecha_ultimo_registro']))

    def test_forecast_no_exporta_banda_no_calibrada(self):
        from analitica import serie_forecast
        historico=pd.DataFrame({'semana_fin':pd.to_datetime(['2025-01-05']),
                                'ventas_observadas':[100]})
        proy=pd.DataFrame({'semana_fin':pd.to_datetime(['2025-01-12']),
                           'pronostico':[90],'modelo':['ultimo_valor']})
        r=serie_forecast(historico,proy)
        self.assertEqual(r.columns.tolist(),['semana_fin','tipo','valor','modelo'])
        self.assertEqual(r['tipo'].tolist(),['OBSERVADO','PRONOSTICO'])
