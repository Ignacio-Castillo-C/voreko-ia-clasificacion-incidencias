# -*- coding: utf-8 -*-
"""Pruebas del dataset sintético y de su generador."""

from pathlib import Path

import pandas as pd
import pytest

from src.config import CATEGORIAS
from src.datos import cargar_dataset, separar_particiones, validar_dataset
from src.generar_dataset import construir_registros

RUTA = Path(__file__).resolve().parents[1] / "data" / "reportes_obra_sinteticos.csv"


@pytest.fixture(scope="module")
def df():
    return cargar_dataset(RUTA)


def test_validacion_completa(df):
    resumen = validar_dataset(df, n_por_clase=30)
    assert resumen["registros"] == 150


def test_particion_estratificada(df):
    exp, ev = separar_particiones(df)
    assert len(exp) == 30 and len(ev) == 120
    assert (exp["categoria_real"].value_counts() == 6).all()
    assert (ev["categoria_real"].value_counts() == 24).all()


def test_generador_reproducible(df):
    """El CSV publicado debe coincidir exactamente con una nueva generación."""
    regenerado = pd.DataFrame(construir_registros())
    regenerado["multiples_incidencias"] = regenerado["multiples_incidencias"].astype(bool)
    pd.testing.assert_frame_equal(
        df.reset_index(drop=True), regenerado[df.columns].reset_index(drop=True), check_dtype=False
    )


def test_textos_no_usan_literalmente_su_categoria(df):
    """Control de dificultad: pocos textos repiten el nombre exacto de su clase."""
    literales = sum(
        c.lower() in t.lower() for t, c in zip(df["texto_reporte"], df["categoria_real"])
    )
    assert literales / len(df) < 0.05


def test_diversidad_redaccion(df):
    tipos = df["tipo_redaccion"].value_counts()
    assert {"directo", "coloquial", "negacion", "ambiguo", "contraste"} <= set(tipos.index)
    assert df["multiples_incidencias"].sum() >= 10


def test_validacion_detecta_errores(df):
    malo = df.copy()
    malo.loc[0, "categoria_real"] = "Otra"
    with pytest.raises(AssertionError):
        validar_dataset(malo)
    vacio = df.copy()
    vacio.loc[1, "texto_reporte"] = "   "
    with pytest.raises(AssertionError):
        validar_dataset(vacio)
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    with pytest.raises(AssertionError):
        validar_dataset(dup, n_por_clase=None)
    assert set(df["categoria_real"]) == set(CATEGORIAS)
