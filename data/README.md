# data/ — Diccionario de datos

## `reportes_obra_sinteticos.csv`

**Origen:** dataset **sintético elaborado con fines académicos** para la Actividad 4. No contiene reportes reales de usuarios de VOREKO. Los textos se redactaron con apoyo de IA generativa y fueron revisados por el autor, a partir de situaciones habituales en obras residenciales pequeñas y medianas en México.

**Generación reproducible:** `python src/generar_dataset.py` (semilla 2026). El script contiene los 150 textos con su etiqueta y asigna de forma determinista la fecha simulada, el tipo de obra, el orden de los registros y la partición. La prueba `tests/test_dataset.py::test_generador_reproducible` comprueba que el CSV publicado es idéntico a una nueva generación.

**Formato:** CSV, UTF-8 sin BOM, separador coma, 150 filas + encabezado.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_reporte` | texto | Identificador único `VRK-<SOB|RET|CAL|SEG|SIN>-NNN` |
| `texto_reporte` | texto | Observación en español (9 a 23 palabras) |
| `categoria_real` | texto | Una de: Sobrecosto, Retraso de ejecución, Problemas de calidad, Riesgos de seguridad, Sin incidencia identificada |
| `origen` | texto | Siempre `sintetico_academico` |
| `fecha_simulada` | fecha | Fecha ficticia entre 2026-01-05 y 2026-09-30 |
| `descripcion_contexto` | texto | Tipo de obra y etapa simuladas |
| `tipo_redaccion` | texto | `directo` (78), `negacion` (32), `coloquial` (20), `ambiguo` (12), `contraste` (8) |
| `multiples_incidencias` | booleano | `True` en 11 reportes con más de una incidencia |
| `particion` | texto | `exploracion` (6 por clase, 30) o `evaluacion` (24 por clase, 120) |

## Regla de etiquetado

1. Se asigna la incidencia que el texto expresa como problema principal.
2. Si hay dos incidencias con peso similar: Riesgos de seguridad > Problemas de calidad > Retraso de ejecución > Sobrecosto, y `multiples_incidencias = True`.
3. *Sin incidencia identificada* sólo cuando se describe avance normal o resultado satisfactorio, aunque aparezcan palabras de otras categorías.

La etiqueta representa el significado del texto y se asignó antes de ejecutar cualquier modelo.

## Validaciones automáticas

150 registros · 30 por clase · sin valores faltantes · sin textos vacíos · sin `id_reporte` ni textos duplicados · categorías y particiones válidas · fechas con formato válido · particiones sin traslape · menos de 5 % de textos que contienen literalmente el nombre de su categoría.

## Límites de validez

Los textos sintéticos están mejor redactados que las notas reales, la distribución equilibrada no refleja la frecuencia real y no hay medición de acuerdo entre anotadores. Se recomienda validar con observaciones reales anonimizadas y revisadas por especialistas antes de cualquier uso en producción.
