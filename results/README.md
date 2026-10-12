# results/

Resultados de la ejecución en Google Colab (GPU Tesla T4, 12 de octubre de 2026), tal como los generó el notebook. No se modificaron. La figura de eficiencia vs. precisión con las etiquetas corregidas está en `docs/figuras/eficiencia_vs_precision_corregida.png` (mismos datos).

| Archivo | Contenido |
|---|---|
| `entorno_ejecucion.json` | Python, torch, transformers, GPU, memoria total, variante elegida, revisión de cada modelo |
| `modelos_hub.json` | Licencia, tarea, parámetros y *commit* de cada modelo según la API del Hub |
| `exploracion_variantes.csv` | Accuracy y F1 macro de las dos variantes de etiquetas (partición de exploración) |
| `predicciones_evaluacion.csv` | 360 predicciones (120 × 3 modelos) con puntuación, margen, latencia y revisión humana |
| `metricas_comparativas.csv` | Tabla consolidada: métricas, latencia, memoria y parámetros |
| `metricas_por_categoria.csv` | Precision, recall, F1 y soporte por modelo y categoría |
| `errores_frecuentes.csv` | Pares de confusión más frecuentes |
| `evaluacion_umbrales.csv` | Cumplimiento de umbrales y porcentaje de revisión humana |
| `recomendacion.json` | Modelo recomendado y motivo |
| `ejemplo_respuesta_voreko.json` | Salida estructurada para la prueba funcional |
| `revision_tecnica.csv` | Resultado de las 18 comprobaciones automáticas |
| `figuras/*.png` | Distribución de clases, matrices de confusión, comparación y eficiencia vs. precisión |

No coloques aquí resultados de la prueba offline con modelos diminutos (`tests/revision_notebook_offline.py`): sus métricas no tienen significado.
