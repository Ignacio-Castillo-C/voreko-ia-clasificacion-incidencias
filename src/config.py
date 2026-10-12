# -*- coding: utf-8 -*-
"""
config.py
=========
Configuración única del experimento VOREKO IA. Todos los módulos, pruebas y el
notebook toman de aquí los modelos, etiquetas, plantillas y umbrales para
garantizar condiciones idénticas de evaluación.
"""

from __future__ import annotations

SEMILLA = 2026

# ---------------------------------------------------------------------------
# Modelos evaluados (verificados en Hugging Face el 2026-10-09)
# ---------------------------------------------------------------------------
# Los valores de parámetros y tamaño provienen de la API pública del Hub
# (campo safetensors.total y tamaño de model.safetensors). Son datos
# publicados, NO mediciones propias.
MODELOS = {
    "MiniLMv2-L6": {
        "id": "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli",
        "arquitectura": "Multilingual MiniLMv2 (6 capas, destilado de XLM-RoBERTa-large)",
        "parametros_publicados": 106_995_589,
        "tamano_safetensors_mb": 428.0,
        "licencia": "MIT",
        "xnli_es_publicado": 0.748,   # ficha del modelo (XNLI test, español)
    },
    "mDeBERTa-v3-base": {
        "id": "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
        "arquitectura": "mDeBERTa-v3-base (12 capas)",
        "parametros_publicados": 278_812_163,
        "tamano_safetensors_mb": 557.7,
        "licencia": "MIT",
        "xnli_es_publicado": 0.845,
    },
    "XLM-RoBERTa-large": {
        "id": "joeddav/xlm-roberta-large-xnli",
        "arquitectura": "XLM-RoBERTa-large (24 capas)",
        "parametros_publicados": 560_943_621,
        "tamano_safetensors_mb": 2243.8,
        "licencia": "MIT",
        "xnli_es_publicado": None,    # la ficha no publica exactitud
    },
}

# ---------------------------------------------------------------------------
# Categorías y su redacción como etiquetas candidatas
# ---------------------------------------------------------------------------
CATEGORIAS = [
    "Sobrecosto",
    "Retraso de ejecución",
    "Problemas de calidad",
    "Riesgos de seguridad",
    "Sin incidencia identificada",
]

# Categorías críticas: las que representan una incidencia que debe revisarse.
# Un falso negativo en ellas implica que un problema real pasa inadvertido.
CATEGORIAS_CRITICAS = [
    "Sobrecosto",
    "Retraso de ejecución",
    "Problemas de calidad",
    "Riesgos de seguridad",
]

# Dos variantes de redacción de etiquetas (ajuste mínimo). La variante final
# se elige SOLO con la partición de exploración; la evaluación final usa una
# única variante idéntica para los tres modelos.
VARIANTES_ETIQUETAS = {
    "A_nombres_cortos": {
        "plantilla": "Este reporte de obra trata sobre {}.",
        "etiquetas": {
            "Sobrecosto": "sobrecosto",
            "Retraso de ejecución": "retraso de ejecución",
            "Problemas de calidad": "problemas de calidad",
            "Riesgos de seguridad": "riesgos de seguridad",
            "Sin incidencia identificada": "sin incidencia",
        },
    },
    "B_descriptivas": {
        "plantilla": "En este reporte de obra se describe {}.",
        "etiquetas": {
            "Sobrecosto": "un gasto mayor al presupuestado o un aumento de precios",
            "Retraso de ejecución": "un retraso o atraso en los trabajos o entregas",
            "Problemas de calidad": "un defecto o mala calidad en los trabajos terminados",
            "Riesgos de seguridad": "un peligro o riesgo de accidente para las personas",
            "Sin incidencia identificada": "un avance normal o un trabajo terminado sin problemas",
        },
    },
}

VARIANTE_POR_DEFECTO = "B_descriptivas"

# ---------------------------------------------------------------------------
# Umbrales de investigación definidos para el prototipo
# (objetivos propios; NO provienen de la rúbrica ni están garantizados)
# ---------------------------------------------------------------------------
UMBRAL_ACCURACY = 0.80
UMBRAL_F1_MACRO = 0.80
UMBRAL_RECALL_CRITICO = 0.80

# Revisión humana: se marca un registro cuando la puntuación del modelo es
# baja o cuando la diferencia entre las dos primeras etiquetas es pequeña.
UMBRAL_PUNTUACION_MINIMA = 0.50
UMBRAL_MARGEN_MINIMO = 0.15

# Medición de latencia
N_CALENTAMIENTO = 3
