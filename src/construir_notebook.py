# -*- coding: utf-8 -*-
"""
construir_notebook.py
=====================
Genera notebooks/VOREKO_IA_comparacion_modelos.ipynb a partir de este script y
de los módulos de src/. Los módulos se incrustan con %%writefile para que el
notebook sea autosuficiente en Google Colab y, al mismo tiempo, idéntico al
código probado del repositorio (una sola fuente de verdad).

    python src/construir_notebook.py
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src"
SALIDA = RAIZ / "notebooks" / "VOREKO_IA_comparacion_modelos.ipynb"
BITACORA = RAIZ / "BITACORA_CAMBIOS.md"

celdas: list = []


def md(texto: str) -> None:
    celdas.append(nbf.v4.new_markdown_cell(texto.strip("\n")))


def py(codigo: str) -> None:
    celdas.append(nbf.v4.new_code_cell(codigo.strip("\n")))


def modulo(nombre: str) -> None:
    contenido = (SRC / nombre).read_text(encoding="utf-8")
    py(f"%%writefile src/{nombre}\n{contenido}")


def tabla_bitacora() -> str:
    """Copia la tabla resumen de la bitácora para que notebook y archivo coincidan."""
    texto = BITACORA.read_text(encoding="utf-8")
    inicio = texto.index("<!-- TABLA_RESUMEN_INICIO -->")
    fin = texto.index("<!-- TABLA_RESUMEN_FIN -->")
    return texto[inicio:fin].replace("<!-- TABLA_RESUMEN_INICIO -->", "").strip()


# =============================================================================
# Portada
# =============================================================================
md(r"""
# VOREKO IA — Evaluación comparativa de modelos preentrenados para la clasificación de incidencias en proyectos de construcción

**Maestría en Inteligencia Artificial — Universidad Tecmilenio**
Gestión de Proyectos de Inteligencia Artificial · Módulo 2 · Semana 5 · Actividad 4
**Autor:** José Ignacio Castillo Camacho

> **Regla de integridad.** Todas las métricas, tiempos y gráficas de este cuaderno se generan al ejecutarlo. Ningún resultado está escrito a mano. Si una celda falla, el error se muestra y las pruebas finales no se marcan como superadas.

**Antes de ejecutar:** *Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU T4 → Guardar*, y después *Entorno de ejecución → Ejecutar todas*.
""")

# =============================================================================
# Celda 1. Introducción
# =============================================================================
md(r"""
## 1. Introducción

**VOREKO** es una aplicación en desarrollo para administrar y dar seguimiento a obras residenciales pequeñas y medianas (proyectos, presupuestos, gastos, fotografías y avances). Los residentes y clientes escriben observaciones libres como *"no llegó la bomba y la cuadrilla estuvo parada medio día"*. Cuando una obra acumula decenas de notas por semana, es fácil que una incidencia importante pase inadvertida.

**Objetivo del experimento.** Comparar tres modelos preentrenados de Hugging Face que realizan **clasificación *zero-shot*** (sin entrenamiento adicional) para asignar a cada observación una **categoría principal**:

| Categoría | Ejemplo de situación |
|---|---|
| Sobrecosto | Aumento de precio de materiales, compras por encima del presupuesto |
| Retraso de ejecución | Concreto que no llega, ausencia de trabajadores, permisos pendientes |
| Problemas de calidad | Acabados deficientes, instalaciones defectuosas |
| Riesgos de seguridad | Falta de equipo de protección, excavaciones sin ademe |
| Sin incidencia identificada | Actividades terminadas satisfactoriamente |

**Rama de IA:** procesamiento de lenguaje natural (NLP) — clasificación de texto mediante inferencia de lenguaje natural (NLI).

**Alcance.** El modelo identifica *posibles* incidencias a partir del lenguaje. **No** comprueba costos, atrasos ni incumplimientos contractuales; su función es ayudar a priorizar qué notas revisa primero una persona.

**Limitación conocida.** Un comentario puede contener varias incidencias. En este prototipo se asigna una sola categoría (`multi_label=False`); la clasificación multietiqueta queda como trabajo futuro.
""")

# =============================================================================
# Celda 2. Dependencias
# =============================================================================
md(r"""
## 2. Instalación de dependencias

Colab ya trae `torch`, `pandas`, `numpy` y `matplotlib` compilados para su GPU, por lo que **no se reinstala `torch`** (reinstalarlo puede romper la compatibilidad con CUDA). Sólo se instalan o actualizan las bibliotecas de Hugging Face y sus dependencias de tokenización.

`transformers>=4.56` es necesario porque el código usa el argumento `dtype` para fijar `float32`.

> Si Colab muestra el aviso **"Reiniciar sesión"** después de esta celda, reinicia (*Entorno de ejecución → Reiniciar sesión*) y continúa desde la celda 3. No es necesario volver a instalar.
""")
py(r"""
%pip install -q "transformers>=4.56,<6" "datasets>=3.0" "huggingface_hub>=0.34" "accelerate>=1.0" "sentencepiece>=0.2" "protobuf>=4.25" "scikit-learn>=1.4"

# Comprobación de versiones instaladas (sin importar los paquetes todavía)
from importlib.metadata import version, PackageNotFoundError

paquetes = ["torch", "transformers", "datasets", "huggingface_hub", "accelerate", "tokenizers",
            "sentencepiece", "protobuf", "scikit-learn", "pandas", "numpy", "matplotlib"]
for p in paquetes:
    try:
        print(f"{p:<16} {version(p)}")
    except PackageNotFoundError:
        print(f"{p:<16} NO INSTALADO")
""")

# =============================================================================
# Celda 3. GPU y entorno
# =============================================================================
md(r"""
## 3. GPU y entorno de ejecución

Se verifica la GPU con `nvidia-smi` y con PyTorch, y se registran las versiones del entorno en `results/entorno_ejecucion.json`. Si **no** hay GPU el cuaderno sigue funcionando en CPU, pero lo indica de forma explícita y todos los tiempos quedan etiquetados como CPU.
""")
py(r"""
!nvidia-smi || echo "nvidia-smi no disponible: no hay GPU asignada a esta sesión"
""")
py(r"""
import os, sys, json, platform, random, time, gc, shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import transformers
from importlib.metadata import version

# Carpetas de trabajo (en Colab se crean dentro de /content)
for carpeta in ["src", "data", "results", "results/figuras"]:
    Path(carpeta).mkdir(parents=True, exist_ok=True)
Path("src/__init__.py").touch()

# Semilla global (la inferencia es determinista; se fija por buena práctica)
SEMILLA = 2026
random.seed(SEMILLA); np.random.seed(SEMILLA); torch.manual_seed(SEMILLA)

GPU_DISPONIBLE = torch.cuda.is_available()
entorno = {
    "fecha_ejecucion_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "python": sys.version.split()[0],
    "plataforma": platform.platform(),
    "torch": torch.__version__,
    "cuda_torch": torch.version.cuda,
    "transformers": transformers.__version__,
    "datasets": version("datasets"),
    "huggingface_hub": version("huggingface_hub"),
    "scikit_learn": version("scikit-learn"),
    "cuda_disponible": GPU_DISPONIBLE,
    "gpu": torch.cuda.get_device_name(0) if GPU_DISPONIBLE else None,
    "memoria_gpu_total_mb": round(torch.cuda.get_device_properties(0).total_memory / 1024**2) if GPU_DISPONIBLE else None,
    "cpu_nucleos": os.cpu_count(),
}
print(json.dumps(entorno, indent=2, ensure_ascii=False))

# Comprobación de versión mínima de transformers (si falla: reiniciar sesión tras la celda 2)
mayor, menor = (int(x) for x in transformers.__version__.split(".")[:2])
assert (mayor, menor) >= (4, 56), (
    f"transformers {transformers.__version__} está cargado en memoria. Reinicia la sesión y ejecuta desde la celda 3."
)

if GPU_DISPONIBLE:
    print(f"\n✅ GPU detectada: {entorno['gpu']} — las mediciones de latencia corresponden a GPU.")
else:
    print("\n⚠️ NO HAY GPU. El experimento se ejecutará en CPU. "
          "Los tiempos NO deben presentarse como mediciones en GPU.")
""")

# =============================================================================
# Celda 4. Autenticación
# =============================================================================
md(r"""
## 4. Autenticación en Hugging Face Hub

Los tres modelos son **públicos**, por lo que la descarga funciona sin token. Aun así, se autentica de forma segura para evitar límites de descarga anónima y seguir la práctica del curso:

1. **Colab Secrets (recomendado):** en el panel lateral 🔑 crea el secreto `HF_TOKEN` con un token de tipo *Read* y habilita el acceso al cuaderno.
2. **Inicio de sesión interactivo:** cambia `USAR_LOGIN_INTERACTIVO = True` para que `login()` solicite el token en un campo oculto.

El token **nunca** se escribe en el código, no se imprime y no se guarda en los archivos de resultados.

Después se consulta la API del Hub para comprobar que cada modelo existe, no está restringido (*gated*), y para registrar su licencia, tarea, número de parámetros y la revisión (*commit*) exacta que se descargará.
""")
py(r"""
from huggingface_hub import HfApi, login

USAR_LOGIN_INTERACTIVO = False   # cambiar a True si no se usa Colab Secrets
HF_TOKEN = None

try:
    from google.colab import userdata
    HF_TOKEN = userdata.get("HF_TOKEN")
    print("Token leído desde Colab Secrets (no se muestra).")
except Exception as e:  # no es Colab, el secreto no existe o no tiene permiso
    print(f"Colab Secrets no disponible ({type(e).__name__}).")

if HF_TOKEN:
    login(token=HF_TOKEN, add_to_git_credential=False)
elif USAR_LOGIN_INTERACTIVO:
    login()
else:
    print("Se continúa sin autenticación: los tres modelos son públicos.")
""")
modulo("config.py")
py(r"""
from src.config import MODELOS

api = HfApi()
info_hub = {}
for nombre, meta in MODELOS.items():
    info = api.model_info(meta["id"], files_metadata=True)
    pesos = {s.rfilename: s.size for s in info.siblings if s.rfilename.endswith((".safetensors", ".bin"))}
    info_hub[nombre] = {
        "id": meta["id"],
        "sha": info.sha,
        "pipeline_tag": info.pipeline_tag,
        "licencia": next((t.split(":", 1)[1] for t in info.tags if t.startswith("license:")), None),
        "gated": bool(info.gated),
        "parametros_safetensors": info.safetensors.total if info.safetensors else None,
        "idioma_es_en_tags": "es" in info.tags,
        "archivos_pesos_mb": {k: round(v / 1024**2, 1) for k, v in pesos.items() if v},
    }
    # Validaciones de disponibilidad y compatibilidad con la tarea
    assert info_hub[nombre]["pipeline_tag"] == "zero-shot-classification", nombre
    assert not info_hub[nombre]["gated"], f"{nombre} requiere aceptar condiciones de acceso"
    assert info_hub[nombre]["idioma_es_en_tags"], f"{nombre} no declara soporte de español"

tabla_hub = pd.DataFrame(info_hub).T
display(tabla_hub[["id", "pipeline_tag", "licencia", "parametros_safetensors", "idioma_es_en_tags", "sha"]])
with open("results/modelos_hub.json", "w", encoding="utf-8") as f:
    json.dump(info_hub, f, ensure_ascii=False, indent=2, default=str)
""")

# =============================================================================
# Módulos de apoyo
# =============================================================================
md(r"""
### Código de apoyo

Las siguientes celdas escriben en `src/` los mismos módulos que contiene el repositorio de GitHub (`datos.py`, `clasificador.py`, `evaluacion.py` y el generador del dataset). Así el cuaderno funciona por sí solo en Colab y el código es idéntico al probado con `pytest`.
""")
modulo("generar_dataset.py")
modulo("datos.py")
modulo("clasificador.py")
modulo("evaluacion.py")
py(r"""
import importlib
import src.config, src.datos, src.clasificador, src.evaluacion
for m in (src.config, src.datos, src.clasificador, src.evaluacion):
    importlib.reload(m)

from src.config import (CATEGORIAS, CATEGORIAS_CRITICAS, VARIANTES_ETIQUETAS, N_CALENTAMIENTO,
                        UMBRAL_ACCURACY, UMBRAL_F1_MACRO, UMBRAL_RECALL_CRITICO,
                        UMBRAL_PUNTUACION_MINIMA, UMBRAL_MARGEN_MINIMO)
from src.datos import cargar_dataset, validar_dataset, separar_particiones
from src.clasificador import cargar_modelo, clasificar_textos, liberar_modelo
from src.evaluacion import (invertir_etiquetas, salidas_a_dataframe, calcular_metricas, resumen_latencia,
                            evaluar_umbrales, errores_frecuentes, salida_voreko, a_json)
print("Módulos cargados correctamente.")
""")

# =============================================================================
# Celda 5. Dataset
# =============================================================================
md(r"""
## 5. Dataset

`data/reportes_obra_sinteticos.csv` es un **dataset sintético elaborado con fines académicos** (150 reportes, 30 por categoría). **No contiene reportes reales de VOREKO.** Los textos se redactaron con apoyo de IA generativa y revisión del autor, imitando el lenguaje de residentes y clientes de obras residenciales en México, con distintas extensiones, expresiones coloquiales, negaciones y casos ambiguos. La etiqueta representa el significado del texto, no la predicción de un modelo.

Si el CSV no se subió a la sesión, se regenera de forma idéntica con `src/generar_dataset.py` (semilla 2026). Además se carga con la biblioteca `datasets` de Hugging Face para mostrar el uso del componente **Datasets** del ecosistema.

| Campo | Descripción |
|---|---|
| `id_reporte` | Identificador único (VRK-<clase>-NNN) |
| `texto_reporte` | Observación escrita por un usuario simulado |
| `categoria_real` | Categoría principal asignada por el autor |
| `origen` | Siempre `sintetico_academico` |
| `fecha_simulada` | Fecha ficticia entre enero y septiembre de 2026 |
| `descripcion_contexto` | Tipo de obra y etapa simuladas |
| `tipo_redaccion` | directo, coloquial, negación, ambiguo o contraste |
| `multiples_incidencias` | `True` si el texto contiene más de una incidencia |
| `particion` | `exploracion` (30) para ajustes, `evaluacion` (120) para métricas finales |
""")
py(r"""
RUTA_DATOS = Path("data/reportes_obra_sinteticos.csv")
if not RUTA_DATOS.exists():
    # Alternativa: el CSV pudo subirse a /content en lugar de data/
    if Path("reportes_obra_sinteticos.csv").exists():
        shutil.copy("reportes_obra_sinteticos.csv", RUTA_DATOS)
    else:
        print("CSV no encontrado: se regenera con src/generar_dataset.py")
        !python src/generar_dataset.py --salida data/reportes_obra_sinteticos.csv

df = cargar_dataset(RUTA_DATOS)
resumen = validar_dataset(df, n_por_clase=30)   # lanza AssertionError si algo no cuadra

# Comprobación de reproducibilidad: el CSV debe coincidir con una regeneración
from src.generar_dataset import construir_registros
regenerado = pd.DataFrame(construir_registros())
assert regenerado["texto_reporte"].tolist() == df["texto_reporte"].tolist(), "El CSV no coincide con el generador"
assert regenerado["categoria_real"].tolist() == df["categoria_real"].tolist()

print(f"Registros: {resumen['registros']} | con múltiples incidencias: {resumen['multiples_incidencias']}")
print("Tipos de redacción:", resumen["tipos_redaccion"])
display(resumen["por_particion"])
display(df.sample(5, random_state=SEMILLA)[["id_reporte", "texto_reporte", "categoria_real", "tipo_redaccion"]])

# Componente Datasets de Hugging Face
from datasets import load_dataset
ds = load_dataset("csv", data_files=str(RUTA_DATOS), split="train")
assert ds.num_rows == len(df)
print(ds)
""")
py(r"""
import matplotlib.pyplot as plt

# Paleta categórica fija (slots 1-3, validados para daltonismo) y tinta de texto neutra
COLORES = {"MiniLMv2-L6": "#2a78d6", "mDeBERTa-v3-base": "#eb6834", "XLM-RoBERTa-large": "#1baf7a"}
TINTA, TINTA_SECUNDARIA, REJILLA = "#1f1f1e", "#5f5e58", "#e4e3dc"
plt.rcParams.update({"axes.edgecolor": REJILLA, "axes.labelcolor": TINTA_SECUNDARIA, "xtick.color": TINTA_SECUNDARIA,
                     "ytick.color": TINTA_SECUNDARIA, "axes.titleweight": "bold", "axes.titlesize": 12,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})

conteo = df.groupby(["categoria_real", "particion"]).size().unstack().reindex(CATEGORIAS)
fig, ax = plt.subplots(figsize=(8, 4))
izq = np.zeros(len(conteo))
for part, color in [("evaluacion", "#2a78d6"), ("exploracion", "#9fc3ee")]:
    ax.barh(conteo.index, conteo[part], left=izq, color=color, edgecolor="white", linewidth=2, label=part)
    izq += conteo[part].values
for i, total in enumerate(izq):
    ax.text(total + 0.5, i, f"{int(total)}", va="center", color=TINTA)
ax.invert_yaxis(); ax.set_xlabel("Número de reportes"); ax.set_xlim(0, 34)
ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.2))
ax.set_title("Distribución de clases por partición (dataset sintético)")
plt.tight_layout(); plt.savefig("results/figuras/distribucion_clases.png", dpi=150); plt.show()
""")
md(r"""
**Conclusión parcial (dataset).** El conjunto está balanceado (30 por clase), sin duplicados ni valores faltantes, y separado en 30 registros de exploración y 120 de evaluación. Al ser sintético, sus resultados sirven para comparar modelos entre sí, no para estimar el desempeño con usuarios reales.
""")

# =============================================================================
# Celda 6. Preparación
# =============================================================================
md(r"""
## 6. Preparación de la evaluación

La clasificación *zero-shot* convierte cada etiqueta en una **hipótesis** (por ejemplo, *"En este reporte de obra se describe un retraso o atraso en los trabajos o entregas."*). El modelo NLI estima si el reporte **implica** (*entailment*) cada hipótesis y, con `multi_label=False`, aplica *softmax* sobre las cinco para elegir una sola categoría.

**Efecto de la redacción de etiquetas.** La palabra exacta de la etiqueta cambia la hipótesis y, por tanto, el resultado. Nombres muy cortos ("sobrecosto") pueden ser poco frecuentes en los datos de entrenamiento NLI; descripciones más naturales suelen funcionar mejor, pero también pueden sesgar hacia ciertas palabras. Por eso se prueban dos variantes **sólo con la partición de exploración** (ajuste mínimo, Tema 10) y se aplica la elegida, idéntica, a los tres modelos en la evaluación final.

**Condiciones idénticas para los tres modelos:** mismos textos y orden, misma plantilla y etiquetas, `multi_label=False`, precisión `float32`, un reporte por llamada (como llegaría desde VOREKO), `N_CALENTAMIENTO` llamadas previas sin medir y sincronización CUDA antes y después de cada medición.
""")
py(r"""
df_exp, df_eval = separar_particiones(df)
assert len(df_exp) == 30 and len(df_eval) == 120
assert set(df_exp["id_reporte"]).isdisjoint(df_eval["id_reporte"])

for nombre, v in VARIANTES_ETIQUETAS.items():
    inverso = invertir_etiquetas(v["etiquetas"])          # valida correspondencia 1 a 1
    print(f"\nVariante {nombre} — plantilla: '{v['plantilla']}'")
    for cat, etq in v["etiquetas"].items():
        print(f"  {cat:<28} → hipótesis: {v['plantilla'].format(etq)}")

print(f"\nCategorías críticas (recall mínimo {UMBRAL_RECALL_CRITICO}): {CATEGORIAS_CRITICAS}")
""")

# =============================================================================
# Celda 7. Carga de modelos + ajuste mínimo
# =============================================================================
md(r"""
## 7. Carga de modelos y ajuste mínimo (partición de exploración)

Cada modelo se carga **de forma secuencial** y se libera la memoria GPU antes de cargar el siguiente. Los errores de descarga, de memoria insuficiente o de compatibilidad se capturan, **se muestran** y se registran; el cuaderno no los oculta y las pruebas finales fallarán si algún modelo no terminó.

Con cada modelo se clasifican los 30 reportes de exploración usando las dos variantes de etiquetas. La variante con mejor F1 macro promedio se usa en la evaluación final.
""")
py(r"""
from src.config import MODELOS

def ejecutar_seguro(nombre, funcion):
    # Ejecuta una etapa capturando errores conocidos sin ocultarlos
    try:
        return funcion(), None
    except torch.cuda.OutOfMemoryError as e:
        msg = f"Memoria GPU insuficiente: {e}"
    except OSError as e:
        msg = f"Error de descarga o de archivos del modelo: {e}"
    except (ValueError, ImportError, AssertionError) as e:
        msg = f"Error de compatibilidad: {type(e).__name__}: {e}"
    print(f"❌ {nombre}: {msg}")
    return None, msg

errores = {}
info_carga, filas_exp, pred_exp = {}, [], []

for nombre, meta in MODELOS.items():
    cargado, err = ejecutar_seguro(nombre, lambda: cargar_modelo(nombre, meta["id"], token=HF_TOKEN))
    if err:
        errores[nombre] = err
        liberar_modelo(None)
        continue
    memoria_tras_carga = torch.cuda.memory_allocated() / 1024**2 if GPU_DISPONIBLE else None
    info_carga[nombre] = {"dispositivo": cargado.dispositivo, "dtype": cargado.dtype,
                          "parametros_contados": cargado.parametros_contados,
                          "segundos_carga_incluye_descarga": cargado.segundos_carga,
                          "memoria_gpu_tras_carga_mb": memoria_tras_carga, "revision": cargado.revision}
    if GPU_DISPONIBLE:
        assert str(cargado.clasificador.device).startswith("cuda"), f"{nombre} no quedó en GPU"
    print(f"✅ {nombre}: {cargado.parametros_contados/1e6:.1f} M parámetros | {cargado.dispositivo} | "
          f"{cargado.dtype} | carga {cargado.segundos_carga:.1f} s")

    for nombre_var, v in VARIANTES_ETIQUETAS.items():
        inverso = invertir_etiquetas(v["etiquetas"])
        r, err = ejecutar_seguro(nombre, lambda: clasificar_textos(
            cargado, df_exp["texto_reporte"].tolist(), list(v["etiquetas"].values()), v["plantilla"], N_CALENTAMIENTO))
        if err:
            errores[f"{nombre}/{nombre_var}"] = err
            continue
        p = salidas_a_dataframe(r["salidas"], df_exp, inverso, nombre, r["latencias_s"]).assign(variante=nombre_var)
        m = calcular_metricas(p["categoria_real"].tolist(), p["categoria_predicha"].tolist())
        pred_exp.append(p)
        filas_exp.append({"modelo": nombre, "variante": nombre_var, "accuracy": m["accuracy"], "f1_macro": m["f1_macro"]})
    liberar_modelo(cargado)
    del cargado

tabla_exp = pd.DataFrame(filas_exp)
tabla_exp.to_csv("results/exploracion_variantes.csv", index=False, encoding="utf-8")
display(tabla_exp.pivot(index="modelo", columns="variante", values=["accuracy", "f1_macro"]).round(3))

assert not errores, f"Hubo errores en la exploración: {errores}"
VARIANTE = tabla_exp.groupby("variante")["f1_macro"].mean().idxmax()
print(f"\nVariante elegida con la partición de exploración: {VARIANTE}")
""")
md(r"""
**Conclusión parcial (ajuste mínimo).** La tabla anterior muestra cuánto cambia el desempeño sólo por redactar distinto las etiquetas. La variante elegida se fija aquí y **no se vuelve a modificar** después de ver la partición de evaluación, para no sobreajustar el resultado final.
""")

# =============================================================================
# Celda 8. Inferencia
# =============================================================================
md(r"""
## 8. Inferencia sobre la partición de evaluación

Se aplican los tres modelos sobre los **mismos 120 reportes** con la variante elegida. Para cada modelo se registran predicción, puntuación, latencia por reporte, memoria GPU máxima y el modelo utilizado. La inferencia se ejecuta dentro de `torch.inference_mode()` (sin gradientes).
""")
py(r"""
v = VARIANTES_ETIQUETAS[VARIANTE]
INVERSO = invertir_etiquetas(v["etiquetas"])
CANDIDATAS = list(v["etiquetas"].values())
PLANTILLA = v["plantilla"]

predicciones, crudos = [], {}
for nombre, meta in MODELOS.items():
    cargado, err = ejecutar_seguro(nombre, lambda: cargar_modelo(nombre, meta["id"], token=HF_TOKEN))
    if err:
        errores[nombre] = err; liberar_modelo(None); continue
    r, err = ejecutar_seguro(nombre, lambda: clasificar_textos(
        cargado, df_eval["texto_reporte"].tolist(), CANDIDATAS, PLANTILLA, N_CALENTAMIENTO))
    if err:
        errores[nombre] = err; liberar_modelo(cargado); continue
    p = salidas_a_dataframe(r["salidas"], df_eval, INVERSO, nombre, r["latencias_s"])
    # Revisión exacta: Transformers 5 ya no la guarda en config, se toma del Hub (celda 4)
    p["version_modelo"] = f"{meta['id']}@{(info_hub[nombre].get('sha') or cargado.revision or 'desconocida')[:12]}"
    p["dispositivo"] = cargado.dispositivo
    predicciones.append(p)
    crudos[nombre] = {"memoria_pico_gpu_mb": r["memoria_pico_gpu_mb"], "tiempo_total_s": r["tiempo_total_s"]}
    print(f"✅ {nombre}: {len(p)} reportes en {r['tiempo_total_s']:.2f} s ({cargado.dispositivo})")
    liberar_modelo(cargado); del cargado

assert not errores, f"Hubo errores durante la inferencia: {errores}"
df_pred = pd.concat(predicciones, ignore_index=True)
df_pred.to_csv("results/predicciones_evaluacion.csv", index=False, encoding="utf-8")
display(df_pred.groupby("modelo").head(3)[["modelo", "id_reporte", "categoria_real", "categoria_predicha",
                                           "puntuacion_modelo", "latencia_s"]])
""")

# =============================================================================
# Celda 9. Métricas
# =============================================================================
md(r"""
## 9. Métricas de desempeño

Para cada modelo se calculan *accuracy*, *precision*, *recall* y *F1-score* (macro y por categoría, con `zero_division=0`), la matriz de confusión, el tiempo total, la latencia media y la memoria GPU máxima.

> **Puntuación ≠ precisión.** La `puntuacion_modelo` es el *softmax* del pipeline entre las cinco etiquetas: indica qué tan convencido está el modelo *en relación con las otras etiquetas*, pero no es una probabilidad calibrada. La precisión estadística sólo se obtiene comparando contra la etiqueta real, como en esta celda.
""")
py(r"""
metricas = {}
for nombre in MODELOS:
    p = df_pred[df_pred["modelo"] == nombre]
    m = calcular_metricas(p["categoria_real"].tolist(), p["categoria_predicha"].tolist())
    m.update(resumen_latencia(p["latencia_s"].tolist()))
    m["memoria_pico_gpu_mb"] = crudos[nombre]["memoria_pico_gpu_mb"]
    m["puntuacion_media"] = float(p["puntuacion_modelo"].mean())
    m["puntuacion_media_aciertos"] = float(p.loc[p["acierto"], "puntuacion_modelo"].mean())
    m["puntuacion_media_errores"] = float(p.loc[~p["acierto"], "puntuacion_modelo"].mean()) if (~p["acierto"]).any() else float("nan")
    metricas[nombre] = m
    print(f"\n=== {nombre} ===  accuracy={m['accuracy']:.3f} | F1 macro={m['f1_macro']:.3f} | "
          f"latencia media={m['latencia_media_ms']:.1f} ms")
    display(m["por_categoria"].round(3))

por_categoria = pd.concat({n: m["por_categoria"] for n, m in metricas.items()}, names=["modelo", "categoria"])
por_categoria.to_csv("results/metricas_por_categoria.csv", encoding="utf-8")
""")
py(r"""
fig, ejes = plt.subplots(1, 3, figsize=(17, 5.2))
etiquetas_cortas = ["Sobrecosto", "Retraso", "Calidad", "Seguridad", "Sin incid."]
for ax, (nombre, m) in zip(ejes, metricas.items()):
    mat = m["matriz_confusion"].values
    ax.imshow(mat, cmap="Blues", vmin=0, vmax=24)
    for i in range(5):
        for j in range(5):
            ax.text(j, i, mat[i, j], ha="center", va="center", fontsize=10,
                    color="white" if mat[i, j] > 14 else TINTA)
    ax.set_xticks(range(5), etiquetas_cortas, rotation=35, ha="right")
    ax.set_yticks(range(5), etiquetas_cortas)
    ax.set_xlabel("Predicción"); ax.set_ylabel("Categoría real")
    ax.set_title(f"{nombre}\naccuracy {m['accuracy']:.2f} · F1 macro {m['f1_macro']:.2f}")
plt.suptitle("Matrices de confusión — partición de evaluación (24 reportes por clase)", fontweight="bold")
plt.tight_layout(); plt.savefig("results/figuras/matrices_confusion.png", dpi=150); plt.show()
""")
md(r"""
**Conclusión parcial (métricas).** Las matrices muestran *dónde* se equivoca cada modelo. La salida de la celda 10 resume automáticamente las confusiones más frecuentes para interpretar estas cifras.
""")

# =============================================================================
# Celda 10. Comparación
# =============================================================================
md(r"""
## 10. Comparación consolidada

Tabla única con desempeño, eficiencia y recursos, gráficas comparativas (una medida por gráfica, sin dobles ejes) y análisis de errores frecuentes, por tipo de redacción y en reportes con múltiples incidencias.
""")
py(r"""
filas = []
for nombre, m in metricas.items():
    filas.append({
        "modelo": nombre,
        "parametros_M": round(info_carga[nombre]["parametros_contados"] / 1e6, 1),
        "licencia": info_hub[nombre]["licencia"],
        "dispositivo": info_carga[nombre]["dispositivo"],
        "accuracy": m["accuracy"], "precision_macro": m["precision_macro"],
        "recall_macro": m["recall_macro"], "f1_macro": m["f1_macro"],
        "latencia_media_ms": m["latencia_media_ms"], "latencia_p95_ms": m["latencia_p95_ms"],
        "tiempo_total_s": m["tiempo_total_s"], "reportes_por_segundo": m["reportes_por_segundo"],
        "memoria_pico_gpu_mb": m["memoria_pico_gpu_mb"],
        "puntuacion_media": m["puntuacion_media"],
        **{f"recall_{c}": m["por_categoria"].loc[c, "recall"] for c in CATEGORIAS},
    })
tabla = pd.DataFrame(filas).set_index("modelo")
tabla.to_csv("results/metricas_comparativas.csv", encoding="utf-8")
display(tabla.round(3).T)
""")
py(r"""
modelos = list(tabla.index)
colores = [COLORES[m] for m in modelos]

def barras(ax, valores, titulo, formato, xlabel, limite=None, referencia=None):
    y = np.arange(len(modelos))
    ax.barh(y, valores, color=colores, height=0.55, edgecolor="white", linewidth=2)
    for i, val in enumerate(valores):
        ax.text(val, i, f"  {formato.format(val)}", va="center", color=TINTA)
    ax.set_yticks(y, modelos); ax.invert_yaxis(); ax.set_title(titulo); ax.set_xlabel(xlabel)
    ax.grid(axis="x", color=REJILLA, linewidth=0.8); ax.set_axisbelow(True)
    if limite: ax.set_xlim(0, limite)
    if referencia is not None:
        ax.axvline(referencia, color=TINTA_SECUNDARIA, linestyle="--", linewidth=1)
        ax.text(referencia, -0.42, f" umbral {referencia}", va="center", color=TINTA_SECUNDARIA, fontsize=8)

fig, ejes = plt.subplots(2, 2, figsize=(13, 7))
barras(ejes[0, 0], tabla["accuracy"], "Accuracy", "{:.3f}", "proporción de aciertos", 1.15, UMBRAL_ACCURACY)
barras(ejes[0, 1], tabla["f1_macro"], "F1 macro", "{:.3f}", "media de F1 por categoría", 1.15, UMBRAL_F1_MACRO)
barras(ejes[1, 0], tabla["latencia_media_ms"], "Latencia media por reporte", "{:.1f} ms", "milisegundos (menos es mejor)",
       tabla["latencia_media_ms"].max() * 1.3)
if tabla["memoria_pico_gpu_mb"].notna().all():
    barras(ejes[1, 1], tabla["memoria_pico_gpu_mb"], "Memoria GPU máxima", "{:.0f} MB", "MB (menos es mejor)",
           tabla["memoria_pico_gpu_mb"].max() * 1.3)
else:
    barras(ejes[1, 1], tabla["parametros_M"], "Parámetros (sin GPU para medir memoria)", "{:,.1f} M", "millones",
           tabla["parametros_M"].max() * 1.3)
dispositivo = "GPU " + str(entorno["gpu"]) if GPU_DISPONIBLE else "CPU (sin GPU)"
plt.suptitle(f"Comparación de modelos — 120 reportes de evaluación · {dispositivo}", fontweight="bold")
plt.tight_layout(); plt.savefig("results/figuras/comparacion_modelos.png", dpi=150); plt.show()

# Relación eficiencia-precisión
fig, ax = plt.subplots(figsize=(7, 4.5))
# Desplazamiento de etiquetas por orden de F1 para que no se encimen puntos cercanos
orden_f1 = tabla["f1_macro"].sort_values(ascending=False).index.tolist()
desplazamientos = {m: d for m, d in zip(orden_f1, [(10, 10), (10, -26), (10, -4)])}
for m in modelos:
    ax.scatter(tabla.loc[m, "latencia_media_ms"], tabla.loc[m, "f1_macro"], s=140, color=COLORES[m],
               edgecolor="white", linewidth=2, zorder=3)
    ax.annotate(f"{m}\n{tabla.loc[m, 'parametros_M']:,.1f} M parámetros",
                (tabla.loc[m, "latencia_media_ms"], tabla.loc[m, "f1_macro"]),
                textcoords="offset points", xytext=desplazamientos.get(m, (10, -4)), fontsize=9, color=TINTA)
ax.axhline(UMBRAL_F1_MACRO, color=TINTA_SECUNDARIA, linestyle="--", linewidth=1)
ax.set_xlabel("Latencia media por reporte (ms)"); ax.set_ylabel("F1 macro")
ax.set_xlim(0, tabla["latencia_media_ms"].max() * 1.6); ax.set_ylim(0, 1.05)
ax.grid(color=REJILLA, linewidth=0.8); ax.set_axisbelow(True)
ax.set_title("Eficiencia frente a precisión")
plt.tight_layout(); plt.savefig("results/figuras/eficiencia_vs_precision.png", dpi=150); plt.show()
""")
py(r"""
# Errores de clasificación más frecuentes
errs = errores_frecuentes(df_pred, top=5)
errs.to_csv("results/errores_frecuentes.csv", index=False, encoding="utf-8")
display(errs)

# Exactitud por tipo de redacción y en reportes con múltiples incidencias
por_tipo = df_pred.pivot_table(index="tipo_redaccion", columns="modelo", values="acierto", aggfunc="mean")
por_tipo["n_reportes"] = df_pred[df_pred["modelo"] == modelos[0]].groupby("tipo_redaccion").size()
display(por_tipo.round(3))
multi = df_pred.pivot_table(index="multiples_incidencias", columns="modelo", values="acierto", aggfunc="mean")
display(multi.round(3))

# Ejemplos de errores del modelo con mejor F1
mejor_f1 = tabla["f1_macro"].idxmax()
display(df_pred[(df_pred["modelo"] == mejor_f1) & (~df_pred["acierto"])]
        [["id_reporte", "texto_reporte", "categoria_real", "categoria_predicha", "puntuacion_modelo"]].head(10))

# Conclusión parcial generada a partir de los datos (no escrita a mano)
for m in modelos:
    e = errs[errs["modelo"] == m]
    if len(e):
        top = e.iloc[0]
        print(f"• {m}: el error más frecuente es '{top['categoria_real']}' → '{top['categoria_predicha']}' "
              f"({top['casos']} casos).")
peor_tipo = por_tipo[modelos].mean(axis=1).idxmin()
print(f"• El tipo de redacción más difícil en promedio fue '{peor_tipo}' "
      f"(exactitud media {por_tipo.loc[peor_tipo, modelos].mean():.2f}).")
""")

# =============================================================================
# Celda 11. Umbrales
# =============================================================================
md(r"""
## 11. Evaluación de umbrales y revisión humana

Umbrales **de investigación definidos para este prototipo** (no provienen de la rúbrica ni son resultados garantizados):

| Criterio | Umbral |
|---|---|
| Accuracy mínima | 0.80 |
| F1 macro mínimo | 0.80 |
| Recall mínimo en cada categoría crítica (sobrecosto, retraso, calidad, seguridad) | 0.80 |

**Criterio de revisión humana.** Una predicción se envía a revisión cuando: (a) la puntuación de la categoría principal es menor a 0.50; (b) la diferencia entre la primera y la segunda categoría es menor a 0.15 (predicción ambigua); o (c) la categoría predicha es *Riesgos de seguridad*, que siempre debe confirmar una persona. En la evaluación también se cuentan los **errores en categorías críticas** que el criterio *no* habría enviado a revisión, porque son el riesgo principal del sistema.
""")
py(r"""
filas_u = []
for nombre, m in metricas.items():
    u = evaluar_umbrales(m)
    p = df_pred[df_pred["modelo"] == nombre]
    criticos_no_detectados = p[(p["categoria_real"].isin(CATEGORIAS_CRITICAS)) & (~p["acierto"]) & (~p["requiere_revision_humana"])]
    filas_u.append({
        "modelo": nombre,
        "accuracy": round(m["accuracy"], 3), "cumple_accuracy": u["cumple_accuracy"],
        "f1_macro": round(m["f1_macro"], 3), "cumple_f1_macro": u["cumple_f1_macro"],
        "recall_critico_min": round(u["recall_critico_minimo"], 3), "categoria_mas_debil": u["categoria_recall_minimo"],
        "cumple_recall_critico": u["cumple_recall_critico"], "cumple_todos": u["cumple_todos"],
        "pct_revision_humana": round(p["requiere_revision_humana"].mean() * 100, 1),
        "errores_criticos_sin_revision": len(criticos_no_detectados),
    })
tabla_umbrales = pd.DataFrame(filas_u).set_index("modelo")
tabla_umbrales.to_csv("results/evaluacion_umbrales.csv", encoding="utf-8")
display(tabla_umbrales)
""")

# =============================================================================
# Celda 12. Recomendación
# =============================================================================
md(r"""
## 12. Recomendación del modelo

La recomendación se calcula **después** de obtener los resultados, con una regla definida de antemano:

1. Entre los modelos que cumplen los tres umbrales, se elige el de **menor latencia media** (VOREKO clasificará una nota a la vez y el costo de servidor crece con el tamaño del modelo).
2. Si ningún modelo cumple todos los umbrales, se recomienda el de **mayor F1 macro** como candidato para la siguiente etapa, se declara que **todavía no es apto para uso sin revisión humana** y se plantea el ajuste fino (*fine-tuning*) con datos reales.

La licencia (las tres son MIT) y la viabilidad de despliegue se consideran en la justificación.
""")
py(r"""
cumplen = tabla_umbrales[tabla_umbrales["cumple_todos"]].index.tolist()
if cumplen:
    RECOMENDADO = tabla.loc[cumplen, "latencia_media_ms"].idxmin()
    motivo = "cumple los tres umbrales y es el más rápido entre los que los cumplen"
else:
    RECOMENDADO = tabla["f1_macro"].idxmax()
    motivo = ("ningún modelo cumple los tres umbrales; se elige el de mayor F1 macro como candidato, "
              "condicionado a revisión humana y a un ajuste fino posterior")

t = tabla.loc[RECOMENDADO]
print(f"Modelo recomendado: {RECOMENDADO} ({MODELOS[RECOMENDADO]['id']})")
print(f"Motivo: {motivo}.")
print(f"Accuracy {t['accuracy']:.3f} · F1 macro {t['f1_macro']:.3f} · latencia media {t['latencia_media_ms']:.1f} ms · "
      f"{t['parametros_M']:.0f} M parámetros · licencia {t['licencia']} · {t['dispositivo']}")
for otro in [m for m in modelos if m != RECOMENDADO]:
    d_f1 = t["f1_macro"] - tabla.loc[otro, "f1_macro"]
    r_lat = tabla.loc[otro, "latencia_media_ms"] / t["latencia_media_ms"]
    print(f"  vs {otro}: diferencia F1 macro {d_f1:+.3f}; {otro} tarda {r_lat:.2f} veces lo del recomendado")

recomendacion = {"modelo": RECOMENDADO, "id": MODELOS[RECOMENDADO]["id"], "motivo": motivo,
                 "variante_etiquetas": VARIANTE, "modelos_que_cumplen": cumplen}
with open("results/recomendacion.json", "w", encoding="utf-8") as f:
    json.dump(recomendacion, f, ensure_ascii=False, indent=2)
""")
md(r"""
**Conclusión parcial (recomendación).** La salida anterior es la base de la justificación del documento de análisis. La interpretación del autor se redacta en el reporte Word con las cifras reales de esta ejecución.
""")

# =============================================================================
# Celda 13. Prueba funcional VOREKO
# =============================================================================
md(r"""
## 13. Prueba funcional VOREKO

Se prueba el modelo recomendado con **comentarios nuevos** que no forman parte del dataset, y se genera la salida estructurada que devolvería un futuro servicio de inferencia conectado a VOREKO (FlutterFlow → Supabase → servicio de inferencia). No se conecta todavía con la aplicación.
""")
py(r"""
COMENTARIOS_NUEVOS = [
    "El de la pipa no llegó y nos quedamos sin agua para el colado de mañana.",
    "Me facturaron el cemento gris a precio de cemento blanco, revisen la nota.",
    "La escalera quedó con huellas de distinto tamaño, el último escalón está más alto.",
    "El chalán anda trepado en la barda sin nada que lo sostenga.",
    "Se terminaron de colocar las luminarias y todas encienden.",
    "La loseta llegó tarde y además más cara de lo cotizado.",
]
assert not set(COMENTARIOS_NUEVOS) & set(df["texto_reporte"]), "Los comentarios de prueba deben ser nuevos"

cargado = cargar_modelo(RECOMENDADO, MODELOS[RECOMENDADO]["id"], token=HF_TOKEN)
version_modelo = f"{MODELOS[RECOMENDADO]['id']}@{(info_hub[RECOMENDADO].get('sha') or cargado.revision or 'desconocida')[:12]}"
salidas_voreko = []
with torch.inference_mode():
    for texto in COMENTARIOS_NUEVOS:
        s = cargado.clasificador(texto, candidate_labels=CANDIDATAS, hypothesis_template=PLANTILLA, multi_label=False)
        salidas_voreko.append(salida_voreko(texto, s, INVERSO, version_modelo))
liberar_modelo(cargado); del cargado

display(pd.DataFrame(salidas_voreko)[["texto_reporte", "categoria_predicha", "puntuacion_modelo",
                                      "requiere_revision_humana", "motivo_revision"]])
json_voreko = a_json(salidas_voreko)
Path("results/ejemplo_respuesta_voreko.json").write_text(json_voreko, encoding="utf-8")
print(json_voreko[:900])
""")
md(r"""
El último comentario contiene **dos incidencias** (retraso y sobrecosto). Con `multi_label=False` el sistema sólo puede devolver una; esta es la limitación que justifica, en una etapa posterior, probar `multi_label=True` con un umbral por etiqueta.
""")

# =============================================================================
# Revisión técnica automatizada
# =============================================================================
md(r"""
## 14. Revisión técnica automatizada

Comprobaciones con `assert` sobre la ejecución completa. Si alguna falla, el cuaderno se detiene con el mensaje correspondiente y **la ejecución no debe reportarse como exitosa**.
""")
py(r"""
resultados_pruebas = []
def prueba(descripcion, condicion):
    resultados_pruebas.append({"prueba": descripcion, "resultado": "OK" if condicion else "FALLA"})
    assert condicion, f"FALLA: {descripcion}"

prueba("1. Dataset leído con 150 registros y 5 clases", len(df) == 150 and set(df["categoria_real"]) == set(CATEGORIAS))
prueba("2. Sin valores faltantes ni textos vacíos", df.isna().sum().sum() == 0 and df["texto_reporte"].str.strip().str.len().gt(0).all())
prueba("3. Los tres modelos terminaron sin errores", not errores and set(df_pred["modelo"]) == set(MODELOS))
prueba("4. 120 predicciones por modelo", (df_pred.groupby("modelo").size() == 120).all())
prueba("5. Mismos reportes y orden en los tres modelos",
       all((df_pred[df_pred.modelo == m]["id_reporte"].values == df_eval["id_reporte"].values).all() for m in MODELOS))
prueba("6. Predicciones dentro del catálogo de categorías", set(df_pred["categoria_predicha"]) <= set(CATEGORIAS))
prueba("7. Puntuaciones en [0, 1] y sin NaN", df_pred["puntuacion_modelo"].between(0, 1).all())
prueba("8. Accuracy recalculada a mano coincide con sklearn",
       all(abs(df_pred[df_pred.modelo == m]["acierto"].mean() - metricas[m]["accuracy"]) < 1e-9 for m in MODELOS))
prueba("9. Matrices de confusión suman 120", all(m["matriz_confusion"].values.sum() == 120 for m in metricas.values()))
prueba("10. Métricas sin NaN", not tabla[["accuracy", "precision_macro", "recall_macro", "f1_macro"]].isna().any().any())
prueba("11. Latencias positivas y tiempo total consistente",
       (df_pred["latencia_s"] > 0).all() and all(abs(df_pred[df_pred.modelo == m]["latencia_s"].sum() - tabla.loc[m, "tiempo_total_s"]) < 1e-6 for m in MODELOS))
prueba("12. Uso de GPU cuando está disponible",
       (not GPU_DISPONIBLE) or df_pred["dispositivo"].str.startswith("cuda").all())
prueba("13. Memoria GPU medida cuando hay GPU", (not GPU_DISPONIBLE) or tabla["memoria_pico_gpu_mb"].gt(0).all())
prueba("14. Tabla consolidada coherente con las predicciones", set(tabla.index) == set(MODELOS))
prueba("15. Variante elegida sólo con exploración", VARIANTE in VARIANTES_ETIQUETAS and len(tabla_exp) == 2 * len(MODELOS))
prueba("16. Salida VOREKO con los campos requeridos",
       all({"texto_reporte", "categoria_predicha", "puntuacion_modelo", "requiere_revision_humana", "version_modelo"} <= set(s) for s in salidas_voreko))
archivos = ["entorno_ejecucion.json", "modelos_hub.json", "exploracion_variantes.csv", "predicciones_evaluacion.csv",
            "metricas_por_categoria.csv", "metricas_comparativas.csv", "errores_frecuentes.csv", "evaluacion_umbrales.csv",
            "recomendacion.json", "ejemplo_respuesta_voreko.json", "figuras/comparacion_modelos.png",
            "figuras/matrices_confusion.png", "figuras/eficiencia_vs_precision.png"]
entorno.update({"variante_etiquetas": VARIANTE, "info_carga": info_carga})
with open("results/entorno_ejecucion.json", "w", encoding="utf-8") as f:
    json.dump(entorno, f, ensure_ascii=False, indent=2, default=str)
prueba("17. Resultados exportados en results/", all(Path("results", a).exists() for a in archivos))
prueba("18. Ningún token en los archivos exportados",
       not HF_TOKEN or all(HF_TOKEN not in Path(r).read_text(encoding="utf-8", errors="ignore")
                           for r in Path("results").rglob("*") if r.suffix in {".json", ".csv"}))

df_pruebas = pd.DataFrame(resultados_pruebas)
df_pruebas.to_csv("results/revision_tecnica.csv", index=False, encoding="utf-8")
display(df_pruebas)
print(f"\n✅ {len(df_pruebas)} de {len(df_pruebas)} comprobaciones superadas en {'GPU ' + str(entorno['gpu']) if GPU_DISPONIBLE else 'CPU'}.")
""")

# =============================================================================
# Exportación
# =============================================================================
md(r"""
## 15. Exportación de resultados

Se comprime la carpeta `results/` para descargarla y copiarla a la carpeta `results/` del repositorio de GitHub. Guarda también este cuaderno con sus salidas (*Archivo → Descargar → Descargar .ipynb*) como evidencia de la ejecución.
""")
py(r"""
shutil.make_archive("resultados_voreko_ia", "zip", "results")
print("Archivo generado: resultados_voreko_ia.zip")
try:
    from google.colab import files
    files.download("resultados_voreko_ia.zip")
except ImportError:
    print("Fuera de Colab: el ZIP queda en la carpeta de trabajo.")
""")

# =============================================================================
# Bitácora
# =============================================================================
md("## 16. Bitácora de cambios\n\nResumen de `BITACORA_CAMBIOS.md` (el detalle completo está en el archivo del repositorio).\n\n" + tabla_bitacora())


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb["cells"] = celdas
    nb["metadata"] = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4", "toc_visible": True},
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, SALIDA)
    print(f"Notebook generado: {SALIDA} ({len(celdas)} celdas)")


if __name__ == "__main__":
    main()
