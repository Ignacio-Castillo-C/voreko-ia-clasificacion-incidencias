# -*- coding: utf-8 -*-
"""
evaluacion.py
=============
Conversión de salidas del pipeline, métricas, umbrales, criterio de revisión
humana y salida estructurada para VOREKO.

Nota: la "puntuación del modelo" es el valor softmax que devuelve el pipeline
para la etiqueta elegida. Es una medida de confianza relativa entre las
etiquetas candidatas, NO una probabilidad calibrada ni una medida de precisión.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

try:
    from .config import (
        CATEGORIAS,
        CATEGORIAS_CRITICAS,
        UMBRAL_ACCURACY,
        UMBRAL_F1_MACRO,
        UMBRAL_MARGEN_MINIMO,
        UMBRAL_PUNTUACION_MINIMA,
        UMBRAL_RECALL_CRITICO,
    )
except ImportError:  # pragma: no cover
    from config import (
        CATEGORIAS,
        CATEGORIAS_CRITICAS,
        UMBRAL_ACCURACY,
        UMBRAL_F1_MACRO,
        UMBRAL_MARGEN_MINIMO,
        UMBRAL_PUNTUACION_MINIMA,
        UMBRAL_RECALL_CRITICO,
    )


# ---------------------------------------------------------------------------
# 1. Correspondencia entre etiquetas candidatas y categorías
# ---------------------------------------------------------------------------
def invertir_etiquetas(mapa_categoria_a_etiqueta: dict) -> dict:
    """Crea el mapa etiqueta_candidata -> categoría y valida que sea biyectivo."""
    inverso = {v: k for k, v in mapa_categoria_a_etiqueta.items()}
    assert len(inverso) == len(mapa_categoria_a_etiqueta), "Hay etiquetas candidatas repetidas"
    assert set(inverso.values()) == set(CATEGORIAS), "Las etiquetas no cubren exactamente las 5 categorías"
    return inverso


def requiere_revision(categoria: str, puntuacion: float, margen: float) -> tuple[bool, str]:
    """
    Criterio de revisión humana del prototipo:
      1. Puntuación de la etiqueta principal menor al umbral mínimo.
      2. Margen pequeño entre la 1.ª y la 2.ª etiqueta (predicción ambigua).
      3. Toda predicción de 'Riesgos de seguridad' se confirma por una persona.
    """
    motivos = []
    if puntuacion < UMBRAL_PUNTUACION_MINIMA:
        motivos.append("puntuacion_baja")
    if margen < UMBRAL_MARGEN_MINIMO:
        motivos.append("prediccion_ambigua")
    if categoria == "Riesgos de seguridad":
        motivos.append("categoria_seguridad")
    return (len(motivos) > 0, ";".join(motivos))


def salidas_a_dataframe(
    salidas: list[dict],
    df_eval: pd.DataFrame,
    mapa_inverso: dict,
    nombre_modelo: str,
    latencias: list[float],
) -> pd.DataFrame:
    """Convierte las salidas del pipeline en un DataFrame de predicciones."""
    assert len(salidas) == len(df_eval) == len(latencias), "Resultados incompletos: tamaños distintos"
    filas = []
    for salida, (_, reg), lat in zip(salidas, df_eval.iterrows(), latencias):
        assert salida["sequence"] == reg["texto_reporte"], f"Desfase entre texto y salida en {reg['id_reporte']}"
        etiquetas, puntuaciones = salida["labels"], salida["scores"]
        assert set(etiquetas) == set(mapa_inverso), f"Salida inesperada del modelo: {etiquetas}"
        assert abs(sum(puntuaciones) - 1.0) < 1e-3, "Las puntuaciones no suman 1 (multi_label debe ser False)"
        categoria = mapa_inverso[etiquetas[0]]
        margen = float(puntuaciones[0] - puntuaciones[1])
        revision, motivo = requiere_revision(categoria, float(puntuaciones[0]), margen)
        filas.append(
            {
                "modelo": nombre_modelo,
                "id_reporte": reg["id_reporte"],
                "texto_reporte": reg["texto_reporte"],
                "categoria_real": reg["categoria_real"],
                "categoria_predicha": categoria,
                "puntuacion_modelo": float(puntuaciones[0]),
                "segunda_categoria": mapa_inverso[etiquetas[1]],
                "margen_top2": margen,
                "acierto": categoria == reg["categoria_real"],
                "requiere_revision_humana": revision,
                "motivo_revision": motivo,
                "latencia_s": float(lat),
                "tipo_redaccion": reg.get("tipo_redaccion", ""),
                "multiples_incidencias": reg.get("multiples_incidencias", False),
            }
        )
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# 2. Métricas
# ---------------------------------------------------------------------------
def calcular_metricas(y_real: list[str], y_pred: list[str]) -> dict:
    """Accuracy, precision/recall/F1 macro y por categoría, y matriz de confusión."""
    assert len(y_real) == len(y_pred) > 0, "Listas vacías o de distinto tamaño"
    desconocidas = set(y_pred) - set(CATEGORIAS)
    assert not desconocidas, f"Predicciones fuera del catálogo: {desconocidas}"

    p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(
        y_real, y_pred, labels=CATEGORIAS, average="macro", zero_division=0
    )
    p_cls, r_cls, f_cls, soporte = precision_recall_fscore_support(
        y_real, y_pred, labels=CATEGORIAS, average=None, zero_division=0
    )
    por_categoria = pd.DataFrame(
        {"precision": p_cls, "recall": r_cls, "f1": f_cls, "soporte": soporte},
        index=CATEGORIAS,
    )
    matriz = pd.DataFrame(
        confusion_matrix(y_real, y_pred, labels=CATEGORIAS),
        index=[f"real: {c}" for c in CATEGORIAS],
        columns=[f"pred: {c}" for c in CATEGORIAS],
    )
    return {
        "accuracy": float(accuracy_score(y_real, y_pred)),
        "precision_macro": float(p_macro),
        "recall_macro": float(r_macro),
        "f1_macro": float(f_macro),
        "por_categoria": por_categoria,
        "matriz_confusion": matriz,
    }


def resumen_latencia(latencias: list[float]) -> dict:
    arr = np.asarray(latencias, dtype=float)
    return {
        "tiempo_total_s": float(arr.sum()),
        "latencia_media_ms": float(arr.mean() * 1000),
        "latencia_p50_ms": float(np.percentile(arr, 50) * 1000),
        "latencia_p95_ms": float(np.percentile(arr, 95) * 1000),
        "reportes_por_segundo": float(len(arr) / arr.sum()) if arr.sum() > 0 else float("nan"),
    }


def evaluar_umbrales(metricas: dict) -> dict:
    """Compara las métricas con los umbrales de investigación del prototipo."""
    recall_critico = metricas["por_categoria"].loc[CATEGORIAS_CRITICAS, "recall"]
    peor_categoria = recall_critico.idxmin()
    resultado = {
        "cumple_accuracy": metricas["accuracy"] >= UMBRAL_ACCURACY,
        "cumple_f1_macro": metricas["f1_macro"] >= UMBRAL_F1_MACRO,
        "cumple_recall_critico": bool((recall_critico >= UMBRAL_RECALL_CRITICO).all()),
        "recall_critico_minimo": float(recall_critico.min()),
        "categoria_recall_minimo": peor_categoria,
    }
    resultado["cumple_todos"] = all(
        [resultado["cumple_accuracy"], resultado["cumple_f1_macro"], resultado["cumple_recall_critico"]]
    )
    return resultado


def errores_frecuentes(df_pred: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    """Pares (real -> predicha) más frecuentes entre los errores."""
    err = df_pred[~df_pred["acierto"]]
    if err.empty:
        return pd.DataFrame(columns=["modelo", "categoria_real", "categoria_predicha", "casos"])
    return (
        err.groupby(["modelo", "categoria_real", "categoria_predicha"])
        .size()
        .reset_index(name="casos")
        .sort_values(["modelo", "casos"], ascending=[True, False])
        .groupby("modelo")
        .head(top)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# 3. Salida estructurada para VOREKO
# ---------------------------------------------------------------------------
def salida_voreko(texto: str, salida_pipeline: dict, mapa_inverso: dict, version_modelo: str) -> dict:
    """Construye el registro que un servicio de inferencia devolvería a VOREKO."""
    etiquetas, puntuaciones = salida_pipeline["labels"], salida_pipeline["scores"]
    categoria = mapa_inverso[etiquetas[0]]
    margen = float(puntuaciones[0] - puntuaciones[1])
    revision, motivo = requiere_revision(categoria, float(puntuaciones[0]), margen)
    return {
        "texto_reporte": texto,
        "categoria_predicha": categoria,
        "puntuacion_modelo": round(float(puntuaciones[0]), 4),
        "requiere_revision_humana": revision,
        "motivo_revision": motivo or None,
        "version_modelo": version_modelo,
        "fecha_clasificacion_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def a_json(registros: list[dict]) -> str:
    return json.dumps(registros, ensure_ascii=False, indent=2)
