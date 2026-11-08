"""Conciliación de las salidas publicadas en el portal con sus fuentes de consumo."""
from pathlib import Path
import hashlib
import json
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class PortalDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = json.loads((ROOT / 'web/data/retail_dashboard.json').read_text(encoding='utf-8'))
        cls.sales = pd.read_csv(ROOT / 'output/FactVentas.csv', encoding='utf-8-sig')
        cls.stock = pd.read_csv(ROOT / 'output/FactInventarioCorte.csv', encoding='utf-8-sig')

    def test_cifras_globales_de_origen(self):
        r = self.web['sales']
        self.assertAlmostEqual(sum(x[4] for x in r), self.sales['Sales Amount'].sum(), places=2)
        self.assertAlmostEqual(sum(x[5] for x in r), self.sales['Cogs'].sum(), places=2)
        self.assertEqual(sum(x[14] for x in r), len(self.sales))
        self.assertEqual(sum(x[11] for x in r), (self.sales['estado_cobertura']=='SIN_DATO').sum())

    def test_inventario_y_catalogo(self):
        self.assertEqual(len(self.web['inventory']), len(self.stock))
        self.assertEqual(len(self.web['catalog']), 2326)
        self.assertEqual(sum(x[2]=='SIN_DATO' for x in self.web['inventory']), 40855)

    def test_pronostico_y_integridad_de_fuentes(self):
        self.assertEqual(sum(x[1]=='PRONOSTICO' for x in self.web['forecast']), 8)
        self.assertAlmostEqual(sum(x[3] for x in self.web['forecast'] if x[1]=='PRONOSTICO'), 984829.44, places=2)
        for name, fingerprint in self.web['meta']['source_sha256'].items():
            value = hashlib.sha256((ROOT/'output'/name).read_bytes()).hexdigest()
            self.assertEqual(value, fingerprint)


if __name__ == '__main__':
    unittest.main()
