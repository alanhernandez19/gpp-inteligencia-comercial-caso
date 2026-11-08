"""Validación de un archivo manual de escenario."""
from pathlib import Path
import pandas as pd

COLUMNAS = ['documento', 'fecha_recepcion', 'mes', 'Store', 'Product No',
            'importe_ajuste', 'estado', 'version', 'nota']
ESTADOS = {'APROBADO', 'PENDIENTE', 'RECHAZADO'}


def validar_ajustes(ruta: Path, productos: set, tiendas: set) -> pd.DataFrame:
    datos = pd.read_csv(ruta, dtype=str, keep_default_na=False)
    faltantes = set(COLUMNAS) - set(datos.columns)
    if faltantes:
        raise ValueError(f'Faltan columnas del archivo manual: {sorted(faltantes)}')
    datos = datos[COLUMNAS].copy()
    fecha = pd.to_datetime(datos['fecha_recepcion'], errors='coerce')
    importe = pd.to_numeric(datos['importe_ajuste'], errors='coerce')
    mes = pd.to_datetime(datos['mes'] + '-01', errors='coerce')
    duplicado = datos.duplicated(['documento', 'version'], keep=False)
    condiciones = {
        'DOCUMENTO_DUPLICADO': duplicado,
        'FECHA_INVALIDA': fecha.isna(),
        'MES_INVALIDO': mes.isna(),
        'IMPORTE_INVALIDO': importe.isna(),
        'PRODUCTO_DESCONOCIDO': ~datos['Product No'].isin(productos),
        'TIENDA_DESCONOCIDA': ~datos['Store'].isin(tiendas),
        'ESTADO_INVALIDO': ~datos['estado'].isin(ESTADOS),
        'VERSION_INVALIDA': ~datos['version'].str.fullmatch(r'[1-9][0-9]*'),
    }
    datos['incidencias'] = [
        '|'.join(nombre for nombre, mascara in condiciones.items() if bool(mascara.iloc[i]))
        for i in range(len(datos))
    ]
    datos['resultado_validacion'] = datos['incidencias'].map(lambda x: 'RECHAZADO' if x else 'VALIDO')
    datos['importe_ajuste_validado'] = importe
    datos['naturaleza'] = 'ESCENARIO_DEMOSTRATIVO'
    return datos


def procesar_ajustes(raiz: Path, ventas: pd.DataFrame) -> dict:
    ruta = raiz / 'input' / 'manual' / 'Ajustes_Comerciales_escenario.csv'
    if not ruta.is_file():
        raise FileNotFoundError(f'Falta archivo manual requerido: {ruta}')
    datos = validar_ajustes(ruta, set(ventas['Product No']), set(ventas['Store']))
    validos = datos.loc[datos['resultado_validacion'].eq('VALIDO')].copy()
    return {
        'archivo_manual_filas': len(datos),
        'archivo_manual_rechazadas': int(datos['resultado_validacion'].eq('RECHAZADO').sum()),
        'archivo_manual_validas': len(validos),
        'archivo_manual_aprobadas': int(validos['estado'].eq('APROBADO').sum()),
    }
