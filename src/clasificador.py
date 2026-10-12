# -*- coding: utf-8 -*-
"""
clasificador.py
===============
Carga de modelos NLI de Hugging Face y clasificación zero-shot con medición
de latencia y memoria GPU.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass, field

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


@dataclass
class ModeloCargado:
    """Agrupa el pipeline y los metadatos de carga de un modelo."""

    nombre: str
    model_id: str
    clasificador: object
    dispositivo: str
    dtype: str
    parametros_contados: int
    segundos_carga: float
    revision: str | None = None
    notas: list[str] = field(default_factory=list)


def detectar_dispositivo() -> tuple[int, str]:
    """Devuelve (device_id para pipeline, descripción). -1 significa CPU."""
    if torch.cuda.is_available():
        return 0, f"cuda:0 ({torch.cuda.get_device_name(0)})"
    return -1, "cpu"


def sincronizar() -> None:
    """Espera a que terminen las operaciones en GPU antes de leer el reloj."""
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def cargar_modelo(nombre: str, model_id: str, token: str | bool | None = None) -> ModeloCargado:
    """
    Carga tokenizador y modelo en float32 y construye el pipeline zero-shot.

    Se fuerza float32 porque:
      * mDeBERTa-v3 no admite FP16 según su ficha técnica, y
      * desde Transformers v5 el valor por defecto de `dtype` es "auto", lo que
        cargaría mDeBERTa en float16 (sus pesos están publicados en F16).
    Así los tres modelos se comparan con la misma precisión numérica.
    """
    device_id, descripcion = detectar_dispositivo()
    inicio = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
    modelo = AutoModelForSequenceClassification.from_pretrained(model_id, dtype=torch.float32, token=token)
    modelo.eval()

    # Validaciones mínimas de compatibilidad con la tarea zero-shot
    etiquetas_nli = {k.lower(): v for k, v in modelo.config.label2id.items()}
    assert any(k.startswith("entail") for k in etiquetas_nli), (
        f"{model_id} no define la etiqueta 'entailment' en label2id: {modelo.config.label2id}"
    )
    assert next(modelo.parameters()).dtype == torch.float32, "El modelo no quedó en float32"

    clasificador = pipeline(
        "zero-shot-classification",
        model=modelo,
        tokenizer=tokenizer,
        device=device_id,
    )
    sincronizar()
    segundos = time.perf_counter() - inicio
    return ModeloCargado(
        nombre=nombre,
        model_id=model_id,
        clasificador=clasificador,
        dispositivo=descripcion,
        dtype=str(next(modelo.parameters()).dtype),
        parametros_contados=sum(p.numel() for p in modelo.parameters()),
        segundos_carga=round(segundos, 2),
        revision=getattr(modelo.config, "_commit_hash", None),
    )


def clasificar_textos(
    cargado: ModeloCargado,
    textos: list[str],
    etiquetas_candidatas: list[str],
    plantilla: str,
    n_calentamiento: int = 3,
) -> dict:
    """
    Clasifica cada texto de forma individual (un reporte por llamada, como en
    VOREKO) y registra la latencia de cada uno.

    Devuelve un diccionario con las salidas crudas, latencias y memoria pico.
    """
    assert len(textos) > 0, "No hay textos para clasificar"
    assert all(isinstance(t, str) and t.strip() for t in textos), "Hay textos vacíos o no válidos"

    clf = cargado.clasificador
    usa_gpu = torch.cuda.is_available()

    # Calentamiento: carga de kernels CUDA y cachés; no se mide
    with torch.inference_mode():
        for t in textos[: max(1, n_calentamiento)]:
            clf(t, candidate_labels=etiquetas_candidatas, hypothesis_template=plantilla, multi_label=False)
    sincronizar()

    if usa_gpu:
        torch.cuda.reset_peak_memory_stats()

    salidas, latencias = [], []
    with torch.inference_mode():
        for t in textos:
            sincronizar()
            t0 = time.perf_counter()
            salida = clf(t, candidate_labels=etiquetas_candidatas, hypothesis_template=plantilla, multi_label=False)
            sincronizar()
            latencias.append(time.perf_counter() - t0)
            salidas.append(salida)

    memoria_pico_mb = torch.cuda.max_memory_allocated() / 1024**2 if usa_gpu else None
    return {
        "salidas": salidas,
        "latencias_s": latencias,
        "tiempo_total_s": float(sum(latencias)),
        "memoria_pico_gpu_mb": memoria_pico_mb,
    }


def liberar_modelo(cargado: ModeloCargado | None) -> None:
    """Libera la memoria GPU ocupada por un modelo antes de cargar el siguiente."""
    if cargado is not None:
        try:
            del cargado.clasificador.model
        except AttributeError:
            pass
        cargado.clasificador = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
