# -*- coding: utf-8 -*-
"""
ejecutar_experimento.py
=======================
Ejecuta el experimento completo fuera del notebook (por ejemplo, en una
terminal de Colab o en un equipo con GPU) y guarda los resultados en results/.

    python -m src.ejecutar_experimento                 # flujo completo
    python -m src.ejecutar_experimento --modelos MiniLMv2-L6   # sólo un modelo

Etapas:
  1. Carga y valida el dataset.
  2. Ajuste mínimo: elige la variante de etiquetas con la partición de
     EXPLORACIÓN (promedio de F1 macro de los modelos evaluados).
  3. Evaluación final con la partición de EVALUACIÓN y la variante elegida,
     idéntica para todos los modelos.
  4. Guarda predicciones, métricas, entorno y resumen en results/.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import pandas as pd
import torch
import transformers

from .clasificador import cargar_modelo, clasificar_textos, liberar_modelo
from .config import MODELOS, N_CALENTAMIENTO, VARIANTES_ETIQUETAS
from .datos import cargar_dataset, separar_particiones, validar_dataset
from .evaluacion import (
    calcular_metricas,
    evaluar_umbrales,
    invertir_etiquetas,
    resumen_latencia,
    salidas_a_dataframe,
)

RAIZ = Path(__file__).resolve().parents[1]


def info_entorno() -> dict:
    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    return {
        "python": sys.version.split()[0],
        "plataforma": platform.platform(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_disponible": torch.cuda.is_available(),
        "gpu": gpu,
        "memoria_gpu_total_mb": (
            torch.cuda.get_device_properties(0).total_memory / 1024**2 if gpu else None
        ),
    }


def evaluar_variante(nombre_variante: str, df: pd.DataFrame, modelos: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    variante = VARIANTES_ETIQUETAS[nombre_variante]
    mapa = variante["etiquetas"]
    inverso = invertir_etiquetas(mapa)
    candidatas = list(mapa.values())
    textos = df["texto_reporte"].tolist()

    predicciones, filas = [], []
    for nombre in modelos:
        cargado = None
        try:
            cargado = cargar_modelo(nombre, MODELOS[nombre]["id"])
            r = clasificar_textos(cargado, textos, candidatas, variante["plantilla"], N_CALENTAMIENTO)
            df_pred = salidas_a_dataframe(r["salidas"], df, inverso, nombre, r["latencias_s"])
            m = calcular_metricas(df_pred["categoria_real"].tolist(), df_pred["categoria_predicha"].tolist())
            fila = {
                "modelo": nombre,
                "variante": nombre_variante,
                "dispositivo": cargado.dispositivo,
                "dtype": cargado.dtype,
                "parametros_contados": cargado.parametros_contados,
                "segundos_carga": cargado.segundos_carga,
                "accuracy": m["accuracy"],
                "precision_macro": m["precision_macro"],
                "recall_macro": m["recall_macro"],
                "f1_macro": m["f1_macro"],
                "memoria_pico_gpu_mb": r["memoria_pico_gpu_mb"],
                **resumen_latencia(r["latencias_s"]),
                **{f"recall_{c}": v for c, v in m["por_categoria"]["recall"].items()},
                **evaluar_umbrales(m),
            }
            filas.append(fila)
            predicciones.append(df_pred)
        except Exception as exc:  # se registra y se vuelve a lanzar: nunca se oculta
            print(f"[ERROR] {nombre}: {type(exc).__name__}: {exc}")
            raise
        finally:
            liberar_modelo(cargado)
    return pd.concat(predicciones, ignore_index=True), filas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datos", type=Path, default=RAIZ / "data" / "reportes_obra_sinteticos.csv")
    parser.add_argument("--salida", type=Path, default=RAIZ / "results")
    parser.add_argument("--modelos", nargs="+", default=list(MODELOS))
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    entorno = info_entorno()
    print(json.dumps(entorno, indent=2, ensure_ascii=False))
    if not entorno["cuda_disponible"]:
        print("AVISO: no hay GPU. Los tiempos corresponden a CPU y no deben reportarse como GPU.")

    df = cargar_dataset(args.datos)
    validar_dataset(df)
    df_exp, df_eval = separar_particiones(df)

    # Ajuste mínimo con la partición de exploración
    filas_exp = []
    for nombre_variante in VARIANTES_ETIQUETAS:
        _, filas = evaluar_variante(nombre_variante, df_exp, args.modelos)
        filas_exp.extend(filas)
    tabla_exp = pd.DataFrame(filas_exp)
    tabla_exp.to_csv(args.salida / "exploracion_variantes.csv", index=False, encoding="utf-8")
    variante_elegida = tabla_exp.groupby("variante")["f1_macro"].mean().idxmax()
    print(f"Variante elegida con exploración: {variante_elegida}")

    # Evaluación final
    df_pred, filas_eval = evaluar_variante(variante_elegida, df_eval, args.modelos)
    df_pred.to_csv(args.salida / "predicciones_evaluacion.csv", index=False, encoding="utf-8")
    pd.DataFrame(filas_eval).to_csv(args.salida / "metricas_comparativas.csv", index=False, encoding="utf-8")
    with (args.salida / "entorno_ejecucion.json").open("w", encoding="utf-8") as f:
        json.dump({**entorno, "variante_elegida": variante_elegida}, f, ensure_ascii=False, indent=2)
    print("Resultados guardados en", args.salida)


if __name__ == "__main__":
    main()
