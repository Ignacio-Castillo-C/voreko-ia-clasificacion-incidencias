# -*- coding: utf-8 -*-
"""
datos.py
========
Carga y validación del dataset sintético de reportes de obra.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:  # permite usar el módulo como paquete (src.datos) o suelto (datos)
    from .config import CATEGORIAS
except ImportError:  # pragma: no cover
    from config import CATEGORIAS

COLUMNAS_OBLIGATORIAS = [
    "id_reporte",
    "texto_reporte",
    "categoria_real",
    "origen",
    "fecha_simulada",
    "descripcion_contexto",
]
COLUMNAS_ADICIONALES = ["tipo_redaccion", "multiples_incidencias", "particion"]
PARTICIONES_VALIDAS = {"exploracion", "evaluacion"}


def cargar_dataset(ruta: str | Path) -> pd.DataFrame:
    """Lee el CSV en UTF-8 y normaliza tipos básicos."""
    df = pd.read_csv(ruta, encoding="utf-8")
    if "multiples_incidencias" in df.columns:
        df["multiples_incidencias"] = (
            df["multiples_incidencias"].astype(str).str.strip().str.lower().map({"true": True, "false": False})
        )
    return df


def validar_dataset(df: pd.DataFrame, n_por_clase: int | None = 30) -> dict:
    """
    Ejecuta las verificaciones de integridad y devuelve un resumen.
    Lanza AssertionError con un mensaje claro si alguna verificación falla.
    """
    faltantes_col = [c for c in COLUMNAS_OBLIGATORIAS + COLUMNAS_ADICIONALES if c not in df.columns]
    assert not faltantes_col, f"Faltan columnas: {faltantes_col}"

    nulos = df[COLUMNAS_OBLIGATORIAS + COLUMNAS_ADICIONALES].isna().sum()
    assert nulos.sum() == 0, f"Hay valores faltantes:\n{nulos[nulos > 0]}"

    textos = df["texto_reporte"].astype(str).str.strip()
    assert (textos.str.len() > 0).all(), "Existen textos vacíos"

    assert df["id_reporte"].is_unique, "Hay id_reporte duplicados"
    duplicados_texto = textos.str.lower().duplicated().sum()
    assert duplicados_texto == 0, f"Hay {duplicados_texto} textos duplicados"

    clases_invalidas = set(df["categoria_real"]) - set(CATEGORIAS)
    assert not clases_invalidas, f"Categorías no válidas: {clases_invalidas}"

    particiones_invalidas = set(df["particion"]) - PARTICIONES_VALIDAS
    assert not particiones_invalidas, f"Particiones no válidas: {particiones_invalidas}"

    assert (df["origen"] == "sintetico_academico").all(), "Todos los registros deben estar marcados como sintéticos"

    fechas = pd.to_datetime(df["fecha_simulada"], format="%Y-%m-%d", errors="coerce")
    assert fechas.notna().all(), "Hay fechas con formato inválido"

    distribucion = df["categoria_real"].value_counts().reindex(CATEGORIAS)
    if n_por_clase is not None:
        assert (distribucion == n_por_clase).all(), f"Distribución no equilibrada:\n{distribucion}"

    # Ninguna observación de exploración puede aparecer en evaluación
    ids_exp = set(df.loc[df["particion"] == "exploracion", "id_reporte"])
    ids_eval = set(df.loc[df["particion"] == "evaluacion", "id_reporte"])
    assert ids_exp.isdisjoint(ids_eval), "Las particiones se traslapan"

    return {
        "registros": int(len(df)),
        "distribucion": distribucion.to_dict(),
        "por_particion": df.groupby(["particion", "categoria_real"]).size().unstack(fill_value=0),
        "multiples_incidencias": int(df["multiples_incidencias"].sum()),
        "tipos_redaccion": df["tipo_redaccion"].value_counts().to_dict(),
    }


def separar_particiones(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (exploracion, evaluacion) en un orden estable por id_reporte."""
    exp = df[df["particion"] == "exploracion"].sort_values("id_reporte").reset_index(drop=True)
    ev = df[df["particion"] == "evaluacion"].sort_values("id_reporte").reset_index(drop=True)
    return exp, ev
