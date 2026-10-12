# Matriz de cumplimiento de la rúbrica — Actividad 4

Fecha de corte: 2026-10-12 · Versión del proyecto: 1.5 (notebook ejecutado en Colab con GPU Tesla T4)
Objetivo: nivel **Altamente competente** (100 %–86 %) en los cuatro criterios.

> No se afirma haber obtenido el 100 %: la calificación depende de la evaluación docente. Tampoco hay que confundir los umbrales del prototipo, que **no se alcanzaron**, con la rúbrica: esta evalúa la selección, la implementación, la comparación y la justificación, no que el modelo llegue al 80 %.

**Estados:** ✅ Cumplido · 🟡 Parcialmente cumplido · ⏳ Pendiente

---

## 1. Selección y análisis de modelos preentrenados (25 %)

| Exigencia (nivel Altamente competente) | Evidencia generada | Archivo y sección | Validación realizada | Estado | Acción necesaria |
|---|---|---|---|---|---|
| Identifica claramente el ecosistema Hugging Face | Tabla Models / Datasets / Spaces con uso actual y función en VOREKO; uso de `load_dataset` y `HfApi` | Word, Desarrollo §3; notebook §4–§5 | Revisión contra Tema 9 | ✅ | — |
| Define criterios técnicos y prácticos sólidos | Siete criterios definidos antes de ver resultados | Word, Desarrollo §4 | Contraste con el Checkpoint del Tema 9 | ✅ | — |
| Evalúa al menos tres modelos de forma justificada y contextualizada | Tres arquitecturas de tamaño distinto; fichas, ventajas y limitaciones | Word, Desarrollo §5; `results/modelos_hub.json` | Descarga real en Colab: públicos, MIT, zero-shot, español; *commit* registrado | ✅ | — |

## 2. Implementación y prototipado en Google Colab (25 %)

| Exigencia | Evidencia | Archivo y sección | Validación | Estado | Acción necesaria |
|---|---|---|---|---|---|
| Implementa correctamente los modelos en Colab con GPU | Ejecución completa en Tesla T4; los tres modelos en `cuda:0` y float32 | Notebook ejecutado (2026-10-12); `results/entorno_ejecucion.json` | Comprobaciones 3, 12 y 13 del notebook | ✅ | — |
| Estructura el código por celdas | 16 secciones con Markdown, código comentado y conclusiones parciales | Notebook | `test_etapas_obligatorias_presentes` | ✅ | — |
| Garantiza ejecución reproducible | Semilla, dataset regenerable, versiones y *commit* registrados, módulos idénticos a `src/` | Notebook §3, §5; `tests/` | 18/18 comprobaciones en Colab; 20 pruebas pytest; métricas recalculadas desde las predicciones | ✅ | Opcional: re-ejecutar la v1.5 para confirmar las correcciones 1.5.1 y 1.5.2 |

## 3. Evaluación y comparación del desempeño (25 %)

| Exigencia | Evidencia | Archivo y sección | Validación | Estado | Acción necesaria |
|---|---|---|---|---|---|
| Aplica correctamente accuracy, precision, recall y F1-score | Macro y por categoría, matrices de confusión, métricas complementarias | `results/metricas_*.csv`; Word, Desarrollo §8 | `test_metricas_caso_conocido`; accuracy recalculada en el notebook y fuera de él | ✅ | — |
| Compara resultados | Tabla consolidada, recall por categoría, errores frecuentes, análisis por tipo de redacción | Word, Desarrollo §8; Figura 2 | Comprobaciones 9, 11 y 14 | ✅ | — |
| Analiza el balance entre eficiencia y precisión | Latencia media/p95, memoria, parámetros; hallazgo de que mDeBERTa es más lento que XLM-R | Word, Desarrollo §9; Figura 3 | — | ✅ | — |

## 4. Documentación técnica y justificación final (25 %)

| Exigencia | Evidencia | Archivo y sección | Validación | Estado | Acción necesaria |
|---|---|---|---|---|---|
| Documenta de forma clara y estructurada el prototipo | Word en formato institucional con resultados reales; README; diccionario de datos; bitácora v1.5 | `docs/Analisis_comparativo_VOREKO_IA.docx`; `README.md`; `BITACORA_CAMBIOS.md` | Validación XSD y revisión visual de 16 páginas; sin texto *Pendiente* | ✅ | — |
| Tabla comparativa (tarea, tamaño, licencia, precisión, latencia, recursos) | Tabla completa con valores medidos | Word, Desarrollo §8 | Valores leídos de `results/` por script | ✅ | — |
| Decisiones de ajuste mínimo, umbrales y riesgos | Variante elegida con exploración (y su limitación), umbrales, revisión humana y riesgo residual en seguridad | Word, Desarrollo §10–§11 | — | ✅ | — |
| Organiza adecuadamente el repositorio | Estructura completa con `results/` poblada y notebook ejecutado | Raíz del repositorio | Revisión de estructura contra el Tema 10 | 🟡 | **Publicar en GitHub** (`docs/PUBLICAR_EN_GITHUB.md`) y verificar la URL |
| Justifica la selección del modelo con base en métricas y objetivos reales | Recomendación por regla definida de antemano, condicionada y con alternativa y siguientes pasos | Word, Desarrollo §12 | `results/recomendacion.json` | ✅ | — |

---

## Resumen

| Criterio | Peso | Estado | Lo que falta |
|---|---|---|---|
| 1. Selección y análisis de modelos | 25 % | ✅ Cumplido | — |
| 2. Implementación en Colab | 25 % | ✅ Cumplido | — |
| 3. Evaluación y comparación | 25 % | ✅ Cumplido | — |
| 4. Documentación y justificación | 25 % | 🟡 Parcial | Publicar el repositorio en GitHub y verificar la URL |
