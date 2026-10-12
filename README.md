# VOREKO IA — Clasificación de incidencias en reportes de obra

**Evaluación comparativa de modelos preentrenados de Hugging Face para clasificar observaciones de construcción escritas en español.**

Actividad 4 · Módulo 2 · Semana 5 — *Gestión de Proyectos de Inteligencia Artificial*, Maestría en Inteligencia Artificial, Universidad Tecmilenio.
Autor: José Ignacio Castillo Camacho.

> **Estado del proyecto (v1.5, 2026-10-12):** notebook ejecutado en Google Colab con GPU Tesla T4; resultados en `results/` y en [Resultados y conclusiones](#resultados-y-conclusiones).

---

## Objetivo

Identificar el modelo preentrenado más adecuado para asignar a cada observación de obra **una categoría principal**:

| Categoría | Ejemplo |
|---|---|
| Sobrecosto | "Se compraron 40 bultos de cemento a $265 cuando en el presupuesto venían a $228." |
| Retraso de ejecución | "No llegó la bomba para el colado y la cuadrilla estuvo parada medio día." |
| Problemas de calidad | "Las losetas del pasillo suenan huecas al pisarlas." |
| Riesgos de seguridad | "La excavación de la cisterna no tiene ademe y la orilla ya se está desmoronando." |
| Sin incidencia identificada | "La prueba hidrostática salió bien, no se detectaron fugas." |

El modelo identifica **posibles** incidencias a partir del lenguaje. No comprueba costos, atrasos ni incumplimientos contractuales: su función es ayudar a priorizar qué revisar.

## Contexto de VOREKO

VOREKO es una aplicación (FlutterFlow + Supabase) para administrar obras residenciales pequeñas y medianas: proyectos, presupuestos, gastos, fotografías, avances e indicadores. Las observaciones de texto libre no se clasifican hoy; este prototipo evalúa si un modelo puede sugerir la categoría para alimentar el panel de seguimiento.

## Modelos utilizados

Rama de IA: **procesamiento de lenguaje natural**, clasificación *zero-shot* mediante inferencia de lenguaje natural (NLI).

| Modelo | Arquitectura | Parámetros* | Licencia | XNLI español* |
|---|---|---|---|---|
| [`MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli`](https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli) | MiniLMv2, 6 capas | 107 M | MIT | 0.748 |
| [`MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli) | mDeBERTa-v3-base, 12 capas | 279 M | MIT | 0.845 |
| [`joeddav/xlm-roberta-large-xnli`](https://huggingface.co/joeddav/xlm-roberta-large-xnli) | XLM-RoBERTa-large, 24 capas | 561 M | MIT | no publicada |

\* Datos publicados en las fichas de Hugging Face (consultadas el 2026-10-09), **no mediciones propias**.

## Dataset

`data/reportes_obra_sinteticos.csv` — **dataset sintético elaborado con fines académicos**; no contiene reportes reales de VOREKO.

- 150 reportes en español (30 por categoría), redactados con apoyo de IA generativa y revisados por el autor.
- Redacción variada: directa (78), negaciones (32), coloquial (20), ambigua (12) y contraste (8); 11 reportes con más de una incidencia.
- Partición estratificada con semilla 2026: **exploración** (30) para el ajuste mínimo de etiquetas y **evaluación** (120) para las métricas finales.
- Se regenera de forma idéntica con `python src/generar_dataset.py`. Detalle de campos y regla de etiquetado en [`data/README.md`](data/README.md).

**Límite de validez:** los resultados permiten comparar los modelos entre sí; no estiman el desempeño con usuarios reales. Antes de producción se requiere validar con observaciones reales, anonimizadas y etiquetadas por especialistas.

## Estructura del repositorio

```
voreko-ia-clasificacion-incidencias/
├── README.md
├── requirements.txt
├── .gitignore
├── BITACORA_CAMBIOS.md           # cambios, comprobaciones y pruebas pendientes
├── notebooks/
│   ├── VOREKO_IA_comparacion_modelos.ipynb                    # versión 1.5 (fuente, sin salidas)
│   └── VOREKO_IA_comparacion_modelos_ejecutado_2026-10-12.ipynb   # evidencia: ejecución en Colab T4
├── data/
│   ├── reportes_obra_sinteticos.csv
│   └── README.md                 # diccionario de datos
├── src/
│   ├── config.py                 # modelos, etiquetas, umbrales (fuente única)
│   ├── generar_dataset.py        # genera el CSV de forma reproducible
│   ├── datos.py                  # carga y validación
│   ├── clasificador.py           # carga de modelos, inferencia, latencia y memoria
│   ├── evaluacion.py             # métricas, umbrales, revisión humana, salida JSON
│   ├── ejecutar_experimento.py   # experimento completo desde terminal
│   └── construir_notebook.py     # genera el .ipynb a partir de src/
├── tests/                        # 20 pruebas pytest + arnés offline del notebook
├── results/                      # resultados de la ejecución en Colab (Tesla T4)
└── docs/
    ├── Analisis_comparativo_VOREKO_IA.docx
    ├── MATRIZ_CUMPLIMIENTO_RUBRICA.md
    ├── PUBLICAR_EN_GITHUB.md
    ├── FORMATO_TAREA_SEPT2026.docx  # formato institucional
    ├── construir_documento_formato.py
    ├── actualizar_documento_resultados.py   # llena el Word con los valores de results/
    └── figuras/
```

## Requisitos del entorno

- Google Colab con **GPU T4** (o cualquier GPU NVIDIA con al menos 4 GB libres; el modelo más grande ocupa ≈ 2.1 GB en float32).
- Python ≥ 3.10, `transformers >= 4.56` (ver [`requirements.txt`](requirements.txt)).
- Cuenta de Hugging Face y token de tipo *Read* (opcional: los modelos son públicos).

## Activación de GPU en Colab

1. *Entorno de ejecución → Cambiar tipo de entorno de ejecución*.
2. *Acelerador por hardware: **GPU T4*** → *Guardar*.
3. La celda 3 del notebook ejecuta `nvidia-smi` y muestra la GPU. Si no hay GPU, el notebook lo indica explícitamente y etiqueta todos los tiempos como CPU.

## Instalación

**En Colab:** no hace falta instalar nada manualmente; la celda 2 instala las dependencias (sin reinstalar `torch`). Si Colab pide reiniciar la sesión, reiniciar y continuar desde la celda 3.

**En equipo local con GPU:**

```bash
git clone https://github.com/<usuario>/voreko-ia-clasificacion-incidencias.git
cd voreko-ia-clasificacion-incidencias
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Token de Hugging Face (seguro):** en Colab, panel 🔑 *Secrets* → `HF_TOKEN` con acceso al notebook. Localmente, `huggingface-cli login` o la variable de entorno `HF_TOKEN`. Nunca escribir el token en el código.

## Ejecución del notebook

1. Abrir `notebooks/VOREKO_IA_comparacion_modelos.ipynb` en Colab (*Archivo → Subir notebook*, o desde GitHub).
2. Opcional: subir `data/reportes_obra_sinteticos.csv`. Si no se sube, el notebook lo regenera idéntico desde el script incrustado.
3. Activar GPU y ejecutar *Entorno de ejecución → Ejecutar todas*.
4. Al final se descarga `resultados_voreko_ia.zip`. Guardar también el notebook con salidas (*Archivo → Descargar → .ipynb*).

## Reproducción de las métricas

```bash
# Experimento completo desde terminal (Colab o equipo con GPU)
python -m src.ejecutar_experimento
# Pruebas automatizadas (no requieren GPU ni Internet)
pytest -q
# Ejecución completa del notebook sin Internet con modelos diminutos (sólo valida el código)
python tests/revision_notebook_offline.py
```

Condiciones idénticas para los tres modelos: mismos 120 textos y orden, misma plantilla y etiquetas, `multi_label=False`, `float32`, un reporte por llamada, 3 llamadas de calentamiento, `torch.inference_mode()` y `torch.cuda.synchronize()` en cada medición. Las versiones exactas y la revisión (*commit*) de cada modelo quedan en `results/entorno_ejecucion.json`.

## Resultados y conclusiones

Ejecución: Google Colab, GPU **Tesla T4**, 12 de octubre de 2026 — 120 reportes de evaluación, variante de etiquetas A (nombres cortos), 18/18 comprobaciones automáticas correctas. Archivos en [`results/`](results/) y notebook con salidas en `notebooks/VOREKO_IA_comparacion_modelos_ejecutado_2026-10-12.ipynb`.

| Modelo | Accuracy | F1 macro | Recall mín. crítico | Latencia media (ms) | Memoria GPU máx. (MB) | Cumple umbrales |
|---|---|---|---|---|---|---|
| MiniLMv2-L6 | 0.225 | 0.197 | 0.042 (Problemas de calidad) | 29.6 | 419 | No |
| mDeBERTa-v3-base | 0.517 | 0.498 | 0.167 (Problemas de calidad) | 143.2 | 1,086 | No |
| XLM-RoBERTa-large | 0.575 | 0.543 | 0.167 (Riesgos de seguridad) | 133.2 | 2,149 | No |

**Umbrales de investigación del prototipo** (objetivos propios, no de la rúbrica): accuracy ≥ 0.80, F1 macro ≥ 0.80 y recall ≥ 0.80 en cada categoría crítica. **Ningún modelo los cumplió.**

**Recomendación:** `joeddav/xlm-roberta-large-xnli` como **candidato condicionado** (regla 2: mayor F1 macro cuando ningún modelo cumple). No es apto para clasificar sin supervisión.

**Hallazgos principales**

- MiniLMv2-L6 quedó prácticamente al nivel del azar (0.225; con cinco clases el azar es 0.20): es rápido, pero no sirve para este caso.
- Los tres modelos dejan pasar la mayoría de los **riesgos de seguridad** (recall 0.125–0.208), y el criterio de revisión no los detecta, porque sólo se activa cuando el modelo predice seguridad. Se propone una regla adicional por términos de seguridad (no probada todavía).
- mDeBERTa-v3-base fue más lento en promedio (143 ms) que XLM-RoBERTa-large (133 ms), a pesar de tener la mitad de parámetros; la memoria sí escaló con el tamaño (0.4 / 1.1 / 2.1 GB).
- La elección de la redacción de etiquetas fue un empate en la exploración (diferencia de 0.0004), y cada modelo prefirió una variante distinta. En la siguiente iteración conviene elegirla por modelo.
- Siguiente etapa: observaciones reales anonimizadas y etiquetadas por especialistas, y ajuste fino.

## Limitaciones

- Dataset sintético: métricas probablemente optimistas frente a notas reales.
- Una sola categoría por reporte; los comentarios con varias incidencias requieren clasificación multietiqueta.
- La redacción de las etiquetas influye en el resultado.
- La puntuación del modelo no es una probabilidad calibrada ni una medida de precisión.
- Colab es un entorno de experimentación, no un backend de producción.

## Próximas etapas de integración

Propuesta conceptual (no implementada): FlutterFlow registra la observación → Supabase la guarda → una Edge Function invoca un servicio externo de inferencia → la categoría, la puntuación y la versión del modelo regresan a Supabase → el panel de seguimiento muestra las incidencias → los casos ambiguos y de seguridad pasan a revisión humana, y las correcciones forman el dataset real para un ajuste fino posterior. Diagrama en `docs/figuras/arquitectura_voreko_ia.png`.

## Licencia y uso

Código con fines académicos. Los modelos utilizados tienen licencia MIT según sus fichas en Hugging Face.
