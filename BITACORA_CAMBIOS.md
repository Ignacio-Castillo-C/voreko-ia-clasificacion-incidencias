# Bitácora de cambios y correcciones — VOREKO IA

Proyecto: `voreko-ia-clasificacion-incidencias`
Responsable: José Ignacio Castillo Camacho

Tipos de cambio: **ERR** = error real detectado al ejecutar o revisar · **PREV** = mejora preventiva · **CONF** = cambio de configuración.

<!-- TABLA_RESUMEN_INICIO -->
| Versión | Fecha | Archivo / celda | Tipo | Problema identificado | Cambio realizado | Comprobación | Resultado | Estado |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 2026-10-09 | Todo el proyecto | — | Primera versión: dataset, módulos `src/`, pruebas y notebook | — | `pytest` (15 pruebas) | 15/15 OK | Base |
| 1.0.1 | 2026-10-09 | `src/generar_dataset.py` | CONF | El CSV se escribía como UTF-8 con BOM; la columna `id_reporte` podía leerse como `﻿id_reporte` si se abría con `encoding="utf-8"` | Se cambió a UTF-8 sin BOM | Regeneración del CSV y `test_generador_reproducible` | OK | Cerrado |
| 1.1 | 2026-10-09 | Notebook, celda 2 (`%pip`) | PREV | La instrucción `%pip` usaba continuación de línea con `\`; la verificación de sintaxis la marcó y su comportamiento depende de la versión de IPython | Instalación escrita en una sola línea | Análisis `ast` de las 26 celdas de código | 0 errores | Cerrado |
| 1.2 | 2026-10-09 | Notebook, celdas 5 y 10 (gráficas) | ERR | Al renderizar: el texto "umbral 0.8" se encimaba con las etiquetas del eje X; la leyenda tapaba las barras de la gráfica de distribución; el formato `{:.0f} M` mostraba "0 M" para modelos pequeños | Etiqueta del umbral movida a la parte superior; leyenda debajo de la gráfica; formato `{:,.1f} M` | Re-ejecución completa del notebook con el arnés offline e inspección visual de las 4 figuras | Sin traslapes | Cerrado |
| 1.3 | 2026-10-09 | `tests/test_notebook.py`, `tests/revision_notebook_offline.py` | PREV | No existía una prueba que garantizara que el código incrustado en el notebook fuera idéntico al de `src/` | Nuevas pruebas de sintaxis, consistencia notebook–`src/`, etapas obligatorias, ausencia de tokens y de salidas previas; arnés de ejecución offline | `pytest` (20 pruebas) y arnés offline | 20/20 OK; notebook ejecutado de punta a punta con 18/18 comprobaciones internas | Cerrado |
| 1.4 | 2026-10-09 | `docs/Analisis_comparativo_VOREKO_IA.docx`, `docs/construir_documento_formato.py` | CONF | El documento comparativo debía entregarse en el formato institucional FORMATO_TAREA_SEPT2026 | El documento se genera sobre el formato: portada (Actividad 4, título y fecha 09/10/2026) y contenido distribuido en sus bandas Introducción, Desarrollo del Ejercicio, Conclusiones y Referencias; se conservan estilos, márgenes y colores. Se retiró el generador anterior (`construir_documento.js`) | Validación XSD del .docx y revisión visual de las 13 páginas renderizadas | Validación aprobada; sin traslapes. La "Fecha" se muestra al inicio de la página 2, igual que en el formato original | Cerrado |
| 1.5 | 2026-10-12 | Ejecución completa en Google Colab | — | Ejecución real del notebook (pendiente desde v1.0) | Ninguno: se ejecutó el código de la v1.4 sin cambios | Tesla T4 (14,913 MB), Python 3.13.15, torch 2.11.0+cu130, transformers 5.18.0; métricas recalculadas desde predicciones_evaluacion.csv | 18/18 comprobaciones OK; métricas coinciden con las tablas del notebook | Cerrado |
| 1.5.1 | 2026-10-12 | Notebook, celdas 8 y 13 (`version_modelo`) | ERR | La salida JSON registró `@desconocida` como revisión del modelo | Causa confirmada: en Transformers 5 `config._commit_hash` llega vacío. Se toma el *commit* desde la API del Hub (`info_hub[...]['sha']`, celda 4), con respaldo a la revisión del modelo | Arnés offline (kernel limpio) | Ejecución completa sin errores · ⏳ falta confirmarlo en Colab | Corregido en código; pendiente de re-ejecución |
| 1.5.2 | 2026-10-12 | Notebook, celda 10 (gráfica eficiencia vs. precisión) | ERR | Las etiquetas de XLM-RoBERTa-large y mDeBERTa-v3-base se enciman porque sus puntos quedaron cercanos | Desplazamiento de etiquetas según el orden de F1. La figura del reporte se regeneró con los mismos datos de `metricas_comparativas.csv` (`docs/figuras/eficiencia_vs_precision_corregida.png`); `results/figuras/` conserva la original de Colab | Revisión visual | Sin traslapes | Corregido en código; pendiente de re-ejecución |
| 1.5.3 | 2026-10-12 | `docs/Analisis_comparativo_VOREKO_IA.docx` | CONF | Las tablas y secciones del reporte estaban marcadas como *Pendiente* | Se llenaron 36 celdas y se agregaron el análisis de resultados, la recomendación, la prueba funcional y las conclusiones, editando la versión del autor (`docs/actualizar_documento_resultados.py`), con valores leídos de `results/` | Validación XSD; revisión visual de 16 páginas; sin texto *Pendiente* restante | OK | Cerrado |
<!-- TABLA_RESUMEN_FIN -->

---

## Detalle de las comprobaciones ejecutadas en esta versión

Entorno de revisión: contenedor Linux sin GPU y **sin acceso a huggingface.co** (bloqueado por la red del entorno). Python 3.13.16, torch 2.14.1, transformers 5.19.0, datasets 5.1.0, huggingface_hub 2.2.0, scikit-learn 1.9.1, pandas 3.0.6.

| # | Comprobación (sección 6 del plan) | Cómo se verificó | Estado |
|---|---|---|---|
| 1 | Sintaxis de todas las celdas | `ast` sobre las 26 celdas de código (`test_sintaxis_de_todas_las_celdas`) | ✅ Verificado |
| 2 | Importaciones y compatibilidad | Ejecución completa del notebook con transformers 5.19 (offline); `dtype=float32` forzado y validado con `assert` | ✅ Verificado (versión local) · ⏳ Colab |
| 3 | Disponibilidad de los modelos | API pública del Hub consultada vía web el 2026-10-09: los tres existen, son públicos, MIT, `zero-shot-classification`, con español | ✅ Verificado manualmente · ⏳ descarga real en Colab |
| 4 | Correspondencia etiquetas–predicciones | `invertir_etiquetas` (biyección) y `salidas_a_dataframe` (texto, etiquetas y suma de puntuaciones) con pruebas negativas | ✅ Verificado |
| 5 | Lectura correcta del dataset | `cargar_dataset` + `validar_dataset` + igualdad exacta con el generador | ✅ Verificado |
| 6 | Cantidades y valores faltantes | `validar_dataset` (150 registros, 30 por clase, sin nulos, sin duplicados) | ✅ Verificado |
| 7 | Uso de GPU cuando está disponible | Lógica `device=0` + `assert` sobre `clasificador.device`; rama CPU ejecutada | ✅ Rama CPU · ⏳ Rama GPU en Colab |
| 8 | Cálculo de métricas | Caso conocido calculado a mano (`test_metricas_caso_conocido`) y accuracy recalculada en el notebook | ✅ Verificado |
| 9 | Medición de tiempos | Latencias > 0 y suma = tiempo total; calentamiento y `torch.cuda.synchronize()` en código | ✅ Lógica · ⏳ Tiempos reales en GPU |
| 10 | Variables sin definir | Ejecución de todas las celdas en orden con kernel limpio | ✅ Verificado |
| 11 | Consistencia de tablas y gráficas | Comprobaciones 9, 11 y 14 del notebook + revisión visual | ✅ Verificado |
| 12 | Exportación de resultados | Comprobación 17 del notebook (13 archivos) | ✅ Verificado |
| 13 | Reproducibilidad desde sesión limpia | Arnés offline: kernel nuevo, carpeta temporal vacía, dataset regenerado desde el script | ✅ Verificado (offline) · ⏳ Colab |

## Ejecución en Google Colab (2026-10-12)

Las cuatro pruebas que estaban pendientes se completaron: descarga real de los tres modelos (incluido el tokenizador de XLM-RoBERTa), ejecución en GPU Tesla T4, selección de la variante de etiquetas con la partición de exploración (A, nombres cortos; diferencia de 0.0004 en F1 promedio) y recomendación final (XLM-RoBERTa-large como candidato condicionado; ningún modelo cumplió los umbrales). Evidencia: `notebooks/VOREKO_IA_comparacion_modelos_ejecutado_2026-10-12.ipynb` y `results/`.

## Pruebas pendientes

1. Volver a ejecutar en Colab el notebook v1.5 para confirmar las correcciones 1.5.1 y 1.5.2 (sólo cambian la etiqueta `version_modelo` y la posición de las etiquetas de una gráfica; las métricas no deberían cambiar).
