# -*- coding: utf-8 -*-
"""
construir_documento_formato.py
==============================
Genera el "Análisis comparativo VOREKO IA" sobre el formato institucional
FORMATO_TAREA_SEPT2026.docx, conservando su portada, estilos, márgenes y las
bandas de sección (Introducción, Desarrollo del Ejercicio, Conclusiones,
Referencias).

    python docs/construir_documento_formato.py <formato.docx> <salida.docx>
"""

from __future__ import annotations

import re
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

DIR = Path(__file__).resolve().parent
VERDE = "006057"
GRIS_BANDA = "595959"
GRIS_TEXTO = "5F5E58"
ANCHO_TEXTO = 10224  # 12240 - 2 x 1008 (márgenes del formato)

# =============================================================================
# Primitivas XML
# =============================================================================
_num_listas: list[int] = []  # numIds nuevos para listas numeradas que reinician


def _runs(texto: str, size: int | None = None, color: str | None = None, bold=False, italic=False) -> str:
    """Convierte texto con **negritas** y *cursivas* en runs de WordprocessingML."""
    partes = [p for p in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", texto) if p]
    xml = []
    for p in partes:
        b, i, t = bold, italic, p
        if p.startswith("**"):
            b, t = True, p[2:-2]
        elif p.startswith("*"):
            i, t = True, p[1:-1]
        rpr = "<w:rPr>" + ("<w:b/>" if b else "") + ("<w:i/>" if i else "")
        if color:
            rpr += f'<w:color w:val="{color}"/>'
        if size:
            rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        rpr += '<w:lang w:val="es-MX"/></w:rPr>'
        xml.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(t)}</w:t></w:r>')
    return "".join(xml)


def P(texto: str, jc="both", after=120, size=None, color=None, italic=False, keep_next=False) -> str:
    kn = "<w:keepNext/>" if keep_next else ""
    return (f'<w:p><w:pPr>{kn}<w:spacing w:after="{after}" w:line="276" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr>'
            f"{_runs(texto, size=size, color=color, italic=italic)}</w:p>")


def H2(texto: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:spacing w:before="280" w:after="120"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="{VERDE}"/><w:sz w:val="24"/>'
            f'<w:lang w:val="es-MX"/></w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>')


def H3(texto: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:spacing w:before="200" w:after="80"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="{GRIS_BANDA}"/><w:sz w:val="21"/>'
            f'<w:lang w:val="es-MX"/></w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>')


def B(texto: str) -> str:
    """Viñeta con el estilo List Bullet del formato."""
    return (f'<w:p><w:pPr><w:pStyle w:val="ListBullet"/><w:spacing w:after="60" w:line="264" w:lineRule="auto"/>'
            f'<w:jc w:val="both"/></w:pPr>{_runs(texto)}</w:p>')


def nueva_lista() -> None:
    _num_listas.append(100 + len(_num_listas))


def N(texto: str) -> str:
    """Elemento de lista numerada; cada nueva_lista() reinicia en 1."""
    num_id = _num_listas[-1]
    return (f'<w:p><w:pPr><w:pStyle w:val="ListNumber"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>'
            f'<w:spacing w:after="60" w:line="264" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>{_runs(texto)}</w:p>')


def NOTA(texto: str) -> str:
    return (f'<w:p><w:pPr><w:pBdr><w:left w:val="single" w:sz="24" w:space="8" w:color="{VERDE}"/></w:pBdr>'
            f'<w:shd w:val="clear" w:color="auto" w:fill="E3EFEE"/><w:spacing w:before="120" w:after="200" w:line="264" w:lineRule="auto"/>'
            f'<w:ind w:left="200" w:right="200"/><w:jc w:val="both"/></w:pPr>{_runs(texto, size=19)}</w:p>')


def PIE(texto: str) -> str:
    return P(texto, jc="center", after=200, size=17, color=GRIS_TEXTO, italic=True)


def CODIGO(texto: str) -> str:
    return (f'<w:p><w:pPr><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/><w:spacing w:after="200"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="16"/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>')


def TABLA(encabezados: list[str], filas: list[list[str]], pesos: list[float], size=17) -> str:
    total = sum(pesos)
    anchos = [round(ANCHO_TEXTO * p / total) for p in pesos]
    anchos[-1] += ANCHO_TEXTO - sum(anchos)
    borde = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>'
    bordes = "".join(borde.format(b) for b in ("top", "left", "bottom", "right", "insideH", "insideV"))

    def celda(texto, ancho, encabezado):
        relleno = VERDE if encabezado else ("F2F2F2" if str(texto).startswith("Pendiente") else None)
        shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{relleno}"/>' if relleno else ""
        runs = _runs(str(texto), size=size, color="FFFFFF" if encabezado else None, bold=encabezado,
                     italic=str(texto).startswith("Pendiente"))
        return (f'<w:tc><w:tcPr><w:tcW w:w="{ancho}" w:type="dxa"/>{shd}<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>{runs}</w:p></w:tc>')

    grid = "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos)
    xml = (f'<w:tbl><w:tblPr><w:tblW w:w="{ANCHO_TEXTO}" w:type="dxa"/><w:jc w:val="center"/>'
           f'<w:tblBorders>{bordes}</w:tblBorders><w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:top w:w="50" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
           f'<w:bottom w:w="50" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>'
           f'<w:tblGrid>{grid}</w:tblGrid>')
    xml += '<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + "".join(celda(e, a, True) for e, a in zip(encabezados, anchos)) + "</w:tr>"
    for f in filas:
        xml += '<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(celda(c, a, False) for c, a in zip(f, anchos)) + "</w:tr>"
    return xml + "</w:tbl>" + '<w:p><w:pPr><w:spacing w:after="80"/></w:pPr></w:p>'


_imagenes: list[tuple[str, Path]] = []


def IMAGEN(ruta: Path, ancho_pulg: float) -> str:
    with open(ruta, "rb") as f:
        cab = f.read(24)
    w, h = struct.unpack(">II", cab[16:24])
    cx = int(ancho_pulg * 914400)
    cy = int(cx * h / w)
    rid = f"rIdImg{len(_imagenes) + 1}"
    _imagenes.append((rid, ruta))
    n = len(_imagenes) + 10
    return (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{n}" name="Figura {n}"/><wp:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            f'</wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr>'
            f'<pic:cNvPr id="{n}" name="{ruta.name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'</pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# =============================================================================
# CONTENIDO
# =============================================================================
PEND = "Pendiente: ejecutar en Colab"

introduccion = [
    P("En las obras residenciales pequeñas y medianas buena parte de la información de seguimiento no está en el presupuesto ni en el programa, sino en las notas que escriben el residente, el maestro de obra o el propio cliente: \"no llegó la bomba\", \"el aplanado quedó ondulado\", \"los muchachos se suben a la azotea sin protección\". Estas notas son valiosas, pero cuando se acumulan es fácil que una incidencia importante se pierda entre comentarios rutinarios."),
    P("Este trabajo forma parte del desarrollo de **VOREKO**, una aplicación que estoy construyendo para administrar proyectos de construcción residencial. El objetivo es evaluar si un modelo preentrenado de Hugging Face puede leer esas observaciones en español y sugerir a qué tipo de incidencia corresponden, de modo que la aplicación ayude a decidir qué revisar primero."),
    P("Siguiendo lo planteado en el Tema 9, la decisión no se toma por la popularidad del modelo, sino comparando tres alternativas con un conjunto de datos propio, bajo condiciones idénticas, y considerando la precisión, la latencia y el consumo de recursos. Del Tema 10 se retoman el flujo de prototipado en Google Colab con GPU, los ajustes mínimos y la documentación del proyecto en GitHub."),
    P("**Objetivo general.** Identificar, mediante una comparación experimental, el modelo preentrenado de Hugging Face más adecuado para clasificar observaciones de obra escritas en español en una de cinco categorías de incidencia, considerando el equilibrio entre precisión, latencia y recursos para una futura integración en VOREKO.", keep_next=True),
    P("**Objetivos específicos:**", after=60, keep_next=True),
]
nueva_lista()
introduccion += [
    N("Seleccionar tres modelos de clasificación *zero-shot* multilingües con criterios técnicos y prácticos explícitos."),
    N("Construir un dataset sintético, balanceado y documentado de 150 reportes de obra en español."),
    N("Implementar en Google Colab con GPU un flujo reproducible de carga, inferencia y evaluación de los tres modelos."),
    N("Comparar accuracy, precision, recall, F1-score, latencia y memoria, y analizar el balance entre eficiencia y precisión."),
    N("Definir umbrales de investigación y un criterio de revisión humana, y justificar la recomendación con base en los resultados."),
    N("Proponer una arquitectura conceptual para integrar el modelo con FlutterFlow y Supabase."),
    NOTA("**Nota de integridad.** Este documento se elaboró antes de ejecutar el notebook en Google Colab con GPU. El entorno donde se preparó el proyecto no tenía GPU ni acceso de red a huggingface.co, por lo que **no contiene métricas experimentales**. La información sobre los modelos proviene de sus fichas técnicas publicadas y se identifica como tal. Las tablas de resultados están preparadas y marcadas como *Pendiente* para llenarse con las salidas reales del notebook (carpeta results/)."),
]

d = []  # Desarrollo del ejercicio
d += [
    H2("1. Descripción de VOREKO y problema identificado"),
    P("VOREKO es una aplicación móvil y web para el seguimiento de obras residenciales, construida con FlutterFlow en el frente y Supabase como base de datos y servicios de backend. Contempla el registro de proyectos, presupuestos, gastos, fotografías y avances físicos, y la presentación de indicadores de seguimiento."),
    P("El problema que se aborda es concreto: **las observaciones de texto libre no se clasifican** y, por lo tanto, no alimentan los indicadores. Un residente puede registrar diez notas en un día y sólo una de ellas describir un riesgo de seguridad. Si la aplicación sugiere una categoría para cada nota, el panel de seguimiento puede mostrar cuántas incidencias de cada tipo tiene cada obra y señalar las que requieren atención. Se definieron cinco categorías:", keep_next=True),
    TABLA(["Categoría", "Qué describe", "Ejemplo del dataset"], [
        ["Sobrecosto", "Gastos o precios por encima de lo presupuestado", "\"Se compraron 40 bultos de cemento a $265 cuando en el presupuesto venían a $228.\""],
        ["Retraso de ejecución", "Trabajos o entregas que no ocurren en el tiempo previsto", "\"No llegó la bomba para el colado y la cuadrilla estuvo parada medio día.\""],
        ["Problemas de calidad", "Defectos en trabajos ejecutados o instalaciones", "\"Las losetas del pasillo suenan huecas al pisarlas, no quedaron bien adheridas.\""],
        ["Riesgos de seguridad", "Condiciones que ponen en peligro a personas", "\"La excavación de la cisterna no tiene ademe y la orilla ya se está desmoronando.\""],
        ["Sin incidencia identificada", "Avance normal o resultados satisfactorios", "\"La prueba hidrostática de la red de agua salió bien, no se detectaron fugas.\""],
    ], [2, 3, 5]),
    P("Es importante delimitar el alcance: el modelo identifica **posibles** incidencias a partir del lenguaje utilizado. No verifica montos, no compara contra el programa de obra y no determina incumplimientos contractuales. Su función es de apoyo a la priorización, y la decisión final sigue siendo de una persona."),

    H2("2. Rama de inteligencia artificial seleccionada"),
    P("El caso se ubica en el **procesamiento de lenguaje natural (NLP)**, específicamente en la clasificación de texto. Como VOREKO todavía no tiene observaciones reales etiquetadas, no es posible entrenar un clasificador supervisado desde el inicio. Por eso se eligió la **clasificación zero-shot basada en inferencia de lenguaje natural (NLI)**, propuesta por Yin et al. (2019)."),
    P("Un modelo entrenado para decidir si una oración *implica*, *contradice* o es *neutral* respecto a otra puede reutilizarse como clasificador. Cada categoría se convierte en una hipótesis (por ejemplo, \"En este reporte de obra se describe un retraso o atraso en los trabajos o entregas\") y el modelo estima qué tan probable es que el reporte implique cada hipótesis. La categoría con mayor puntuación es la predicción. Esto permite cambiar o agregar categorías sin reentrenar, algo útil en una etapa temprana del producto."),

    H2("3. Ecosistema Hugging Face"),
    P("Hugging Face organiza su plataforma en tres componentes principales (Tecmilenio, 2026a). La tabla resume cómo se usó cada uno y qué papel podría tener en VOREKO:", keep_next=True),
    TABLA(["Componente", "Qué es", "Uso en esta actividad", "Función futura en VOREKO"], [
        ["Models", "Repositorio de modelos preentrenados con ficha técnica, licencia y archivos", "Búsqueda por tarea zero-shot-classification e idioma español; descarga de los tres modelos con Transformers; revisión de fichas y licencias", "Fuente del modelo recomendado y, más adelante, repositorio privado para versionar un modelo ajustado con datos de VOREKO"],
        ["Datasets", "Repositorio y biblioteca para cargar y versionar conjuntos de datos", "El CSV sintético se carga también con load_dataset(\"csv\")", "Dataset privado y anonimizado de observaciones reales etiquetadas por especialistas"],
        ["Spaces", "Alojamiento de aplicaciones interactivas (Gradio o Streamlit)", "No se usó en el experimento; se consideró como opción de demostración", "Demo interna para que residentes y supervisores prueben el clasificador antes de integrarlo"],
    ], [1.4, 2.4, 3.1, 3.1]),
    P("Además se utilizaron la biblioteca **Transformers** (pipeline zero-shot-classification) y **huggingface_hub** para la autenticación y para consultar la API del Hub, de modo que el notebook registra la revisión exacta (*commit*) de cada modelo descargado."),

    H2("4. Criterios para seleccionar los modelos"),
    P("Retomando la recomendación del Tema 9 de no basar la decisión sólo en benchmarks o en la popularidad, se definieron criterios técnicos y prácticos antes de revisar resultados:", keep_next=True),
    TABLA(["Tipo", "Criterio", "Por qué importa en VOREKO"], [
        ["Técnico", "Tarea zero-shot-classification compatible con el pipeline de Transformers", "No hay datos reales etiquetados todavía"],
        ["Técnico", "Soporte explícito de español en el entrenamiento NLI (XNLI)", "Todas las observaciones están en español de México"],
        ["Técnico", "Tamaño y arquitectura diferentes entre sí", "Permite estudiar el balance entre precisión y costo"],
        ["Técnico", "Latencia por reporte y memoria GPU", "Cada nota se clasificaría al registrarse; un servidor pequeño reduce costos"],
        ["Práctico", "Licencia que permita uso comercial", "VOREKO es un producto, no sólo un ejercicio académico"],
        ["Práctico", "Disponibilidad pública, sin acceso restringido", "Reproducibilidad y continuidad"],
        ["Práctico", "Explicabilidad básica", "La salida debe poder explicarse: categoría, puntuación y motivo de revisión"],
    ], [1.3, 4.4, 4.3]),
    P("La disponibilidad se verificó el 9 de octubre de 2026 consultando la API pública del Hub: los tres modelos existen, son públicos (no *gated*), tienen licencia MIT, declaran la tarea zero-shot-classification y el idioma español. No fue necesario sustituir ninguno. El notebook repite esta verificación antes de descargar los modelos."),

    H2("5. Características de los tres modelos"),
    P("Los datos de esta sección provienen de las fichas técnicas publicadas por los autores en Hugging Face y **no son mediciones propias**.", keep_next=True),
    TABLA(["Característica", "MiniLMv2-L6", "mDeBERTa-v3-base", "XLM-RoBERTa-large"], [
        ["Identificador", "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", "joeddav/xlm-roberta-large-xnli"],
        ["Arquitectura", "MiniLMv2, 6 capas, destilado de XLM-RoBERTa-large", "mDeBERTa-v3-base, 12 capas", "XLM-RoBERTa-large, 24 capas"],
        ["Parámetros (Hub)", "107.0 millones", "278.8 millones", "560.9 millones"],
        ["Archivo de pesos", "428 MB (F32)", "558 MB (publicado en F16)", "2,244 MB (F32)"],
        ["Memoria estimada de pesos en float32", "≈ 0.4 GB", "≈ 1.1 GB", "≈ 2.1 GB"],
        ["Datos de ajuste NLI", "MNLI + XNLI dev (15 idiomas)", "MNLI + XNLI dev (15 idiomas)", "MNLI + XNLI dev y test (15 idiomas)"],
        ["Exactitud XNLI publicada (español)", "0.748", "0.845", "No publicada en la ficha"],
        ["Licencia", "MIT", "MIT", "MIT"],
        ["Observaciones de la ficha", "Recomendado cuando se prioriza velocidad (~6,200 textos/s en español con GPU A100)", "Recomendado cuando se prioriza desempeño; no admite FP16", "Mayor capacidad; uno de los más descargados para zero-shot multilingüe"],
    ], [2.2, 2.6, 2.6, 2.6], size=16),
    P("**Ventajas y limitaciones esperadas.** MiniLMv2-L6 es el más ligero y probablemente el más rápido, pero al ser destilado pierde algo de comprensión. mDeBERTa-v3-base reporta la mejor exactitud XNLI en español de los modelos de Laurer y tiene un tamaño intermedio; su limitación práctica es que no funciona en media precisión. XLM-RoBERTa-large es el de mayor capacidad, pero quintuplica los parámetros del más pequeño, lo que en producción implica un servidor con más memoria y mayor latencia. La exactitud XNLI mide inferencia entre oraciones generales, no clasificación de reportes de obra, así que sirve como referencia y no como predicción del resultado en VOREKO."),

    H2("6. Dataset y metodología"),
    H3("6.1 Origen del dataset"),
    P("El archivo **reportes_obra_sinteticos.csv** es un **dataset sintético elaborado con fines académicos**; no contiene reportes reales de usuarios de VOREKO. Los 150 textos se redactaron con apoyo de IA generativa y los revisé a partir de situaciones frecuentes en obras residenciales en México: aumento del precio de materiales, compras por encima del presupuesto, retraso en la entrega de concreto, ausencia de trabajadores, acabados deficientes, instalaciones defectuosas, falta de equipo de protección y actividades terminadas satisfactoriamente."),
    P("Para evitar un conjunto artificialmente fácil, los textos tienen diferentes extensiones (de 9 a 23 palabras) e incluyen cinco tipos de redacción: directa (78), con negaciones (32), coloquial (20), ambigua (12) y de contraste (8), en la que aparecen palabras de otra categoría con sentido distinto, por ejemplo \"el gasto se mantuvo dentro de lo presupuestado\". Menos del 5 % de los textos contiene literalmente el nombre de su categoría, lo cual se comprueba con una prueba automatizada."),
    H3("6.2 Estructura"),
    TABLA(["Campo", "Descripción"], [
        ["id_reporte", "Identificador único con prefijo por clase (VRK-SOB-001, VRK-SEG-014…)"],
        ["texto_reporte", "Observación en español tal como la escribiría un usuario"],
        ["categoria_real", "Categoría principal asignada según la regla de etiquetado"],
        ["origen", "Siempre sintetico_academico"],
        ["fecha_simulada", "Fecha ficticia entre enero y septiembre de 2026 (AAAA-MM-DD)"],
        ["descripcion_contexto", "Tipo de obra y etapa simuladas"],
        ["tipo_redaccion", "directo, coloquial, negacion, ambiguo o contraste"],
        ["multiples_incidencias", "True si el texto contiene más de una incidencia (11 casos)"],
        ["particion", "exploracion (30 registros) o evaluacion (120 registros)"],
    ], [2.6, 7.4]),
    H3("6.3 Regla de etiquetado"),
    P("La etiqueta representa el significado del texto y la asigné antes de ejecutar cualquier modelo. Se asigna la incidencia que el texto expresa como problema principal. Si hay dos incidencias con peso similar, se aplica la prioridad Riesgos de seguridad > Problemas de calidad > Retraso de ejecución > Sobrecosto, y el registro se marca con multiples_incidencias = True. \"Sin incidencia identificada\" sólo se usa cuando el texto describe avance normal o un resultado satisfactorio."),
    H3("6.4 Reproducibilidad y partición"),
    P("El script **src/generar_dataset.py** contiene los textos y genera el CSV en UTF-8 con una semilla fija (2026), que determina las fechas simuladas, el tipo de obra, el orden de los registros y la partición. La partición es estratificada: 6 reportes por clase (30) para **exploración**, usados sólo en el ajuste mínimo de etiquetas, y 24 por clase (120) para la **evaluación final**. Las verificaciones automáticas confirman 150 registros, 30 por clase, cero valores faltantes, cero duplicados, clases válidas, particiones sin traslape y que el CSV es idéntico a una regeneración del script."),
    IMAGEN(DIR / "figuras" / "distribucion_clases.png", 5.4),
    PIE("Figura 1. Distribución de clases por partición del dataset sintético."),
    H3("6.5 Límites de validez"),
    P("Al ser sintético, el dataset tiene limitaciones: los textos tienden a estar mejor redactados que las notas reales (sin faltas de ortografía, abreviaturas extremas o mensajes de voz transcritos); la distribución equilibrada no refleja la frecuencia real, donde probablemente predominen los reportes sin incidencia; y quien redactó los textos también asignó las etiquetas, por lo que no hay medición de acuerdo entre anotadores. Los resultados sirven para **comparar los modelos entre sí**, no para estimar el desempeño con usuarios reales. Antes de cualquier uso en producción se recomienda validar con observaciones reales, anonimizadas y etiquetadas por al menos dos especialistas en obra."),
    H3("6.6 Métricas"),
    P("Se usan las métricas del Tema 9: **accuracy** (proporción de predicciones correctas), **precision** (de lo que el modelo predijo como una clase, cuánto lo era realmente), **recall** (de los casos reales de una clase, cuántos detectó) y **F1-score** (media armónica de precision y recall) (Muñoz, 2023; GeeksforGeeks, 2026). Se reportan en promedio macro, que da el mismo peso a las cinco categorías, y por categoría. Para la eficiencia se miden la latencia por reporte (media y percentil 95), el tiempo total, la memoria GPU máxima y el número de parámetros."),
    P("Es importante distinguir la **puntuación del modelo** de su precisión. La puntuación que devuelve el pipeline es un *softmax* entre las cinco etiquetas candidatas: indica qué tan convencido está el modelo en relación con las otras opciones, pero no es una probabilidad calibrada; un modelo puede asignar 0.90 a una predicción incorrecta. La precisión sólo se conoce comparando contra la etiqueta real."),

    H2("7. Implementación en Google Colab"),
    P("El notebook **VOREKO_IA_comparacion_modelos.ipynb** está organizado en 16 secciones con celdas de texto y de código, comentarios en español y conclusiones parciales, siguiendo el flujo del Tema 10:", keep_next=True),
    TABLA(["Sección", "Contenido"], [
        ["1. Introducción", "Objetivo, categorías, alcance y limitación de una sola etiqueta"],
        ["2. Dependencias", "transformers, datasets, huggingface_hub, accelerate, sentencepiece, protobuf y scikit-learn; no se reinstala torch para no romper la compatibilidad con CUDA de Colab"],
        ["3. GPU y entorno", "nvidia-smi, torch.cuda, versiones y hardware en results/entorno_ejecucion.json; aviso explícito si no hay GPU"],
        ["4. Autenticación", "Token desde Colab Secrets (HF_TOKEN) o login() interactivo; el token nunca se escribe ni se guarda. Consulta a la API del Hub para validar tarea, licencia, idioma y revisión"],
        ["5. Dataset", "Carga, validación, comparación con el generador y carga con la biblioteca datasets"],
        ["6. Preparación", "Plantillas de hipótesis, etiquetas, multi_label=False y condiciones idénticas"],
        ["7. Carga y ajuste mínimo", "Carga secuencial con liberación de memoria; control de errores de descarga, memoria y compatibilidad; elección de la variante de etiquetas con la partición de exploración"],
        ["8. Inferencia", "120 reportes por modelo, uno por llamada, con calentamiento, torch.inference_mode() y sincronización CUDA"],
        ["9–10. Métricas y comparación", "Métricas macro y por clase, matrices de confusión, tabla consolidada, gráficas y análisis de errores"],
        ["11–12. Umbrales y recomendación", "Comparación con umbrales, revisión humana y regla de recomendación definida de antemano"],
        ["13. Prueba VOREKO", "Comentarios nuevos y respuesta JSON para un futuro servicio de inferencia"],
        ["14–16. Revisión y bitácora", "18 comprobaciones automáticas con assert, exportación de resultados y bitácora de cambios"],
    ], [2.6, 7.4]),
    P("**Decisiones técnicas relevantes.** Los tres modelos se cargan en **float32**. La ficha de mDeBERTa indica que no admite FP16, y desde la versión 5 de Transformers el valor por defecto de dtype es \"auto\", lo que cargaría mDeBERTa en float16 porque sus pesos están publicados así. Forzar float32 y validarlo con un assert garantiza que los tres modelos se comparan con la misma precisión numérica. También se decidió clasificar **un reporte por llamada** y no por lotes, porque así llegarían las observaciones desde la aplicación; esto da una latencia más realista para VOREKO, aunque menor rendimiento total que el procesamiento por lotes."),
    P("**Verificación del código.** Antes de entregar, el proyecto se sometió a una revisión técnica: 20 pruebas con pytest (dataset, métricas contra un caso calculado a mano, controles de salidas incompletas o inesperadas y consistencia entre el notebook y los módulos de src/) y la ejecución completa del notebook en un kernel limpio, sustituyendo los tres modelos por modelos diminutos con pesos aleatorios, porque el entorno de preparación no tenía acceso a Hugging Face. Esa ejecución sólo valida que el código corre de punta a punta y que las 18 comprobaciones internas pasan; **sus números no tienen significado** y no se reportan. La revisión detectó y corrigió tres defectos de presentación en las gráficas y una instrucción de instalación frágil, registrados en la bitácora de cambios."),

    H2("8. Comparación de métricas y desempeño"),
    NOTA("**Resultados pendientes de ejecución.** Las celdas marcadas como *Pendiente* se llenan con los valores de results/metricas_comparativas.csv y results/metricas_por_categoria.csv, generados por el notebook en Colab con GPU. No deben llenarse con estimaciones."),
    P("La siguiente tabla corresponde a la tabla comparativa solicitada (tarea, tamaño, licencia, precisión, latencia y recursos). Las columnas de tamaño y licencia son datos publicados; las de precisión, latencia y recursos son mediciones propias.", keep_next=True),
    TABLA(["Modelo", "Tarea", "Tamaño", "Licencia", "Accuracy (medida)", "F1 macro (medido)", "Latencia media (ms)", "Memoria GPU máx. (MB)"], [
        ["MiniLMv2-L6", "Zero-shot (NLI)", "107 M · 428 MB", "MIT", PEND, PEND, PEND, PEND],
        ["mDeBERTa-v3-base", "Zero-shot (NLI)", "279 M · 558 MB", "MIT", PEND, PEND, PEND, PEND],
        ["XLM-RoBERTa-large", "Zero-shot (NLI)", "561 M · 2,244 MB", "MIT", PEND, PEND, PEND, PEND],
    ], [1.6, 1.1, 1.3, 0.8, 1.3, 1.3, 1.3, 1.3], size=16),
    P("**Recall por categoría (partición de evaluación, 24 reportes por clase):**", keep_next=True),
    TABLA(["Categoría", "MiniLMv2-L6", "mDeBERTa-v3-base", "XLM-RoBERTa-large"], [
        ["Sobrecosto", PEND, PEND, PEND],
        ["Retraso de ejecución", PEND, PEND, PEND],
        ["Problemas de calidad", PEND, PEND, PEND],
        ["Riesgos de seguridad", PEND, PEND, PEND],
        ["Sin incidencia identificada", PEND, PEND, PEND],
    ], [3, 2.3, 2.3, 2.4]),
    P("**Guía de interpretación.** Al tener los resultados conviene revisar: (1) si las diferencias de F1 macro entre modelos son mayores que lo que cambiaría con dos o tres aciertos más (con 120 reportes, un acierto equivale a 0.8 puntos porcentuales de accuracy, así que diferencias menores a unos 3 puntos no son concluyentes); (2) qué categorías se confunden entre sí en las matrices de confusión; y (3) cómo se comportan los modelos con los textos de negación, contraste y múltiples incidencias, que el notebook reporta por separado."),

    H2("9. Análisis de eficiencia frente a precisión"),
    P("El conflicto que plantea el Tema 9 entre mayor precisión y menor costo computacional se presenta claramente en este caso. Con base en la información publicada, la expectativa, que el experimento debe confirmar o refutar, es la siguiente:"),
    B("El tamaño crece de forma importante: XLM-RoBERTa-large tiene unas 5.2 veces los parámetros de MiniLMv2-L6 y unas 2 veces los de mDeBERTa-v3-base. En GPU, la latencia por reporte y la memoria deberían crecer en el mismo sentido."),
    B("La mejora de precisión no necesariamente acompaña al tamaño. En XNLI español, mDeBERTa-v3-base supera a MiniLMv2-L6 por casi 10 puntos (0.845 frente a 0.748); para XLM-RoBERTa-large no hay cifra publicada comparable."),
    B("En zero-shot, la redacción de las etiquetas puede pesar tanto como la arquitectura. Por eso el ajuste de etiquetas se hizo con la partición de exploración y se aplicó igual a los tres modelos."),
    P("La gráfica de eficiencia frente a precisión que genera el notebook sitúa cada modelo según su latencia media y su F1 macro; el modelo ideal estaría arriba a la izquierda. Si dos modelos tienen un F1 macro similar, para VOREKO conviene el más ligero, porque el costo de hospedar un servicio de inferencia depende principalmente de la memoria que requiere el modelo."),
    P("Desde la perspectiva de una pequeña constructora, unos cientos de milisegundos de latencia no son relevantes para el usuario: la observación se guarda y la clasificación puede llegar segundos después. Lo que sí importa es el **costo mensual del servidor** y la **cantidad de incidencias que el sistema deja pasar**. Por eso, en el análisis final pesan más el recall de las categorías críticas y el tamaño del modelo que la latencia en sí."),

    H2("10. Ajustes mínimos aplicados"),
    P("Siguiendo el Tema 10, se aplicaron ajustes que adaptan el modelo al caso de uso **sin modificar sus parámetros internos**:", keep_next=True),
    TABLA(["Tipo de ajuste", "Qué se hizo"], [
        ["Configuración del modelo", "Pipeline zero-shot-classification, GPU con device=0, float32 forzado, multi_label=False e inferencia sin gradientes"],
        ["Ajuste de entradas", "Plantilla de hipótesis en español y dos variantes de etiquetas: A (nombres cortos, \"sobrecosto\") y B (descriptivas, \"un gasto mayor al presupuestado o un aumento de precios\"). La variante se elige con la partición de exploración (mejor F1 macro promedio) y no se modifica después"],
        ["Ajuste de salidas", "Conversión de la etiqueta candidata a la categoría de negocio, margen entre las dos primeras etiquetas, marca de revisión humana y salida JSON con versión del modelo"],
        ["Preparación de datos", "Validación de textos vacíos, duplicados, clases y partición antes de la inferencia"],
        ["Evaluación con umbrales", "Comparación con los umbrales del prototipo para decidir si se requiere ajuste fino"],
    ], [2.6, 7.4]),
    P("Variante de etiquetas elegida en la exploración: **Pendiente: ejecutar en Colab** (results/exploracion_variantes.csv)."),
    P("No se aplicó *fine-tuning*. El Tema 10 lo plantea sólo cuando el modelo no alcanza los umbrales del negocio y, además, requiere datos reales etiquetados que todavía no existen. Entrenar con el mismo dataset sintético que se usa para evaluar produciría resultados engañosos."),

    H2("11. Umbrales, riesgos y limitaciones"),
    H3("11.1 Umbrales de investigación"),
    P("Los siguientes umbrales son **objetivos que definí para el prototipo**; no provienen de la rúbrica y no son resultados garantizados. El 80 % retoma la referencia del caso del restaurante del Tema 10.", keep_next=True),
    TABLA(["Criterio", "Umbral", "Justificación", "MiniLMv2-L6", "mDeBERTa", "XLM-R-large"], [
        ["Accuracy", "≥ 0.80", "Cuatro de cada cinco notas bien clasificadas", PEND, PEND, PEND],
        ["F1 macro", "≥ 0.80", "Evita que una clase fuerte oculte otra débil", PEND, PEND, PEND],
        ["Recall en cada categoría crítica", "≥ 0.80", "El error más costoso es dejar pasar una incidencia", PEND, PEND, PEND],
    ], [1.7, 0.9, 2.6, 1.6, 1.6, 1.6], size=16),
    P("Se consideran **categorías críticas** las cuatro que representan una incidencia (sobrecosto, retraso, calidad y seguridad), porque clasificar una de ellas como \"Sin incidencia\" significa que el problema no se revisa."),
    H3("11.2 Criterio de revisión humana"),
    P("Una predicción se envía a revisión cuando ocurre cualquiera de estas condiciones:", after=60, keep_next=True),
    B("La puntuación de la categoría principal es menor a 0.50."),
    B("La diferencia entre la primera y la segunda categoría es menor a 0.15 (predicción ambigua)."),
    B("La categoría predicha es Riesgos de seguridad: siempre debe confirmarla una persona, porque ignorarla puede derivar en un accidente."),
    P("El notebook reporta además cuántos errores en categorías críticas **no** habrían llegado a revisión con este criterio; ese número es el indicador más honesto del riesgo residual del sistema."),
    H3("11.3 Riesgos y limitaciones"),
    TABLA(["Riesgo o limitación", "Consecuencia", "Mitigación propuesta"], [
        ["Dataset sintético", "Las métricas pueden ser optimistas frente a notas reales", "Validación con observaciones reales anonimizadas antes de producción"],
        ["Una sola categoría por reporte", "Se pierde la segunda incidencia de un comentario (11 casos en el dataset)", "Etapa posterior con multi_label=True y umbral por etiqueta"],
        ["Sensibilidad a la redacción de etiquetas", "Cambios pequeños alteran las predicciones", "Fijar la variante con exploración y versionarla junto con el modelo"],
        ["Puntuación no calibrada", "Una puntuación alta puede ser un error", "No mostrarla como porcentaje de certeza; usar margen y revisión humana"],
        ["Falsos negativos en seguridad", "Riesgo físico no atendido", "Recall mínimo por categoría y revisión obligatoria de seguridad"],
        ["Expectativa de automatización", "Usar la categoría como dictamen de costos o atrasos", "Presentarla como sugerencia en la interfaz"],
        ["Privacidad", "Las notas pueden incluir nombres o datos de clientes", "Anonimizar antes de enviar a un servicio externo"],
    ], [2.6, 3.6, 3.8]),

    H2("12. Modelo recomendado y justificación"),
    NOTA("**Pendiente de ejecución.** La recomendación se toma **únicamente después** de obtener los resultados, aplicando la regla definida de antemano. No se adelanta una conclusión."),
    P("La regla de decisión, implementada en la sección 12 del notebook, es:", after=60, keep_next=True),
]
nueva_lista()
d += [
    N("Entre los modelos que cumplan los tres umbrales, se recomienda el de **menor latencia media**, porque en VOREKO el costo del servidor crece con el tamaño del modelo y los tres tienen la misma licencia (MIT)."),
    N("Si ningún modelo cumple todos los umbrales, se recomienda el de **mayor F1 macro** como candidato, condicionado a revisión humana de todas sus predicciones y a una etapa de ajuste fino con datos reales."),
    P("**Modelo recomendado:** Pendiente: ejecutar en Colab (results/recomendacion.json)."),
    P("**Justificación con métricas:** Pendiente: completar con accuracy, F1 macro, recall de categorías críticas, latencia, memoria y porcentaje de revisión humana del modelo recomendado, comparados con los otros dos."),

    H2("13. Aplicación futura en VOREKO"),
    P("La integración no se implementa en esta actividad. Se propone la siguiente arquitectura conceptual para una etapa posterior:", keep_next=True),
    IMAGEN(DIR / "figuras" / "arquitectura_voreko_ia.png", 6.9),
    PIE("Figura 2. Arquitectura conceptual de integración (propuesta, no implementada)."),
]
nueva_lista()
d += [
    N("El usuario registra una observación en la aplicación de VOREKO hecha con FlutterFlow."),
    N("Supabase almacena la observación en una tabla con estado \"pendiente de clasificar\"."),
    N("Un *trigger* de base de datos o *webhook* activa una Edge Function de Supabase."),
    N("La función envía el texto a un servicio externo de inferencia con el modelo recomendado (por ejemplo, un Inference Endpoint de Hugging Face o un contenedor propio)."),
    N("El servicio devuelve categoría, puntuación, motivo de revisión y versión del modelo, y la función los guarda en Supabase."),
    N("El panel de seguimiento muestra las incidencias clasificadas por obra y por tipo."),
    N("Los casos ambiguos y todos los de seguridad pasan a una bandeja de revisión humana; la corrección del usuario se guarda como nueva etiqueta y, con el tiempo, forma el dataset real para el ajuste fino."),
    P("**Google Colab no es un backend de producción.** Las sesiones se desconectan, la GPU no está garantizada y no hay una dirección estable para recibir solicitudes. Colab cumple aquí el papel de entorno de experimentación; el servicio real debe ejecutarse en una infraestructura con disponibilidad continua."),
    P("La respuesta que devolvería el servicio (results/ejemplo_respuesta_voreko.json) tiene esta estructura; los valores reales se obtienen al ejecutar el notebook:", keep_next=True),
    CODIGO('{ "texto_reporte": "…", "categoria_predicha": "…", "puntuacion_modelo": 0.0, "requiere_revision_humana": true, "motivo_revision": "…", "version_modelo": "<id>@<commit>", "fecha_clasificacion_utc": "…" }'),

    H2("14. Archivos entregados"),
    TABLA(["Archivo", "Contenido"], [
        ["VOREKO_IA_comparacion_modelos.ipynb", "Notebook de Google Colab (sin salidas hasta ejecutarse)"],
        ["reportes_obra_sinteticos.csv", "Dataset sintético de 150 reportes"],
        ["src/generar_dataset.py", "Script reproducible que genera el dataset"],
        ["src/config.py, datos.py, clasificador.py, evaluacion.py", "Módulos de configuración, carga, clasificación y evaluación"],
        ["src/ejecutar_experimento.py", "Ejecución del experimento completo desde terminal"],
        ["tests/", "20 pruebas automatizadas y arnés de ejecución offline"],
        ["results/", "Resultados generados por el notebook (vacía hasta ejecutarlo)"],
        ["BITACORA_CAMBIOS.md", "Bitácora de cambios, comprobaciones y pruebas pendientes"],
        ["docs/MATRIZ_CUMPLIMIENTO_RUBRICA.md", "Matriz de cumplimiento de la rúbrica"],
    ], [4.2, 5.8]),
]

conclusiones = [
    P("La primera lección de esta actividad fue que elegir un modelo es, sobre todo, definir bien el problema. Antes de abrir Hugging Face tuve que decidir qué categorías le sirven a un residente de obra, qué significa \"sobrecosto\" cuando el texto sólo dice \"nos salió carísimo el flete\" y qué hacer cuando un comentario habla de un atraso y de un gasto extra al mismo tiempo. Esas decisiones de etiquetado condicionan el resultado tanto como la arquitectura del modelo."),
    P("La segunda fue el valor de separar los datos que uso para ajustar de los que uso para medir. Es tentador probar varias redacciones de etiquetas hasta que la accuracy suba, pero si se hace sobre el mismo conjunto de evaluación el número final deja de significar algo. Reservar una partición de exploración fue una forma sencilla de evitarlo."),
    P("También aprendí a desconfiar de los detalles que parecen menores. El cambio de valor por defecto de dtype en Transformers 5 habría cargado uno de los tres modelos en media precisión sin ningún aviso, y la comparación habría quedado sesgada. Las pruebas automatizadas y la bitácora no son trámite: son lo que permite que otra persona, o yo mismo dentro de seis meses, confíe en los resultados."),
    P("Sobre la utilidad de la IA para pequeñas obras, considero que el valor no está en reemplazar al residente, sino en que ninguna nota importante se quede sin leer. Una constructora pequeña no tiene un área de control de proyectos; si la aplicación puede señalar las tres observaciones de la semana que merecen atención, el beneficio es real. Al mismo tiempo, los límites son claros: el modelo no sabe si un precio es alto, no conoce el contrato y puede equivocarse con seguridad aparente. Por eso la revisión humana no es un complemento opcional, sino parte del diseño."),
    P("*Esta sección se complementará con la reflexión sobre los resultados obtenidos una vez ejecutado el notebook en Google Colab con GPU.*", color=GRIS_TEXTO),
]

referencias_txt = [
    "Conneau, A., Khandelwal, K., Goyal, N., Chaudhary, V., Wenzek, G., Guzmán, F., Grave, E., Ott, M., Zettlemoyer, L., y Stoyanov, V. (2020). Unsupervised cross-lingual representation learning at scale. *Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics*, 8440–8451. https://doi.org/10.18653/v1/2020.acl-main.747",
    "Conneau, A., Rinott, R., Lample, G., Williams, A., Bowman, S., Schwenk, H., y Stoyanov, V. (2018). XNLI: Evaluating cross-lingual sentence representations. *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing*, 2475–2485. https://doi.org/10.18653/v1/D18-1269",
    "Davison, J. (s.f.). *joeddav/xlm-roberta-large-xnli* [Ficha del modelo]. Hugging Face. Recuperado el 9 de octubre de 2026 de https://huggingface.co/joeddav/xlm-roberta-large-xnli",
    "GeeksforGeeks. (2026). *F1 Score in Machine Learning*. Recuperado de https://www.geeksforgeeks.org/machine-learning/f1-score-in-machine-learning/",
    "Google. (s.f.). *Colab: preguntas frecuentes*. Recuperado de https://research.google.com/colaboratory/faq.html",
    "He, P., Gao, J., y Chen, W. (2021). *DeBERTaV3: Improving DeBERTa using ELECTRA-style pre-training with gradient-disentangled embedding sharing*. arXiv. https://arxiv.org/abs/2111.09543",
    "Hugging Face. (s.f.). *Pipelines: ZeroShotClassificationPipeline* [Documentación de Transformers]. Recuperado de https://huggingface.co/docs/transformers/main_classes/pipelines",
    "Laurer, M. (s.f.-a). *MoritzLaurer/mDeBERTa-v3-base-mnli-xnli* [Ficha del modelo]. Hugging Face. Recuperado el 9 de octubre de 2026 de https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
    "Laurer, M. (s.f.-b). *MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli* [Ficha del modelo]. Hugging Face. Recuperado el 9 de octubre de 2026 de https://huggingface.co/MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli",
    "Laurer, M., van Atteveldt, W., Casas, A., y Welbers, K. (2024). Less annotating, more classifying: Addressing the data scarcity issue of supervised machine learning with deep transfer learning and BERT-NLI. *Political Analysis, 32*(1), 84–100. https://doi.org/10.1017/pan.2023.20",
    "Muñoz, R. (2023). *Accuracy* y *Recall*. Foqum. Recuperado de https://foqum.io/es/termino/accuracy-exactitud/",
    "Stryker, C. (s.f.). *What is a pretrained model?* IBM. Recuperado de https://www.ibm.com/think/topics/pretrained-model",
    "Tecmilenio. (2026a). *Tema 9. Selección de modelos preentrenados* [Material del curso Gestión de Proyectos de Inteligencia Artificial]. Universidad Tecmilenio.",
    "Tecmilenio. (2026b). *Tema 10. Prototipado rápido y documentación técnica* [Material del curso Gestión de Proyectos de Inteligencia Artificial]. Universidad Tecmilenio.",
    "Wang, W., Bao, H., Huang, S., Dong, L., y Wei, F. (2021). MiniLMv2: Multi-head self-attention relation distillation for compressing pretrained transformers. *Findings of the Association for Computational Linguistics: ACL-IJCNLP 2021*, 2140–2151. https://doi.org/10.18653/v1/2021.findings-acl.188",
    "Wolf, T., Debut, L., Sanh, V., Chaumond, J., Delangue, C., Moi, A., … Rush, A. (2020). Transformers: State-of-the-art natural language processing. *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing: System Demonstrations*, 38–45. https://doi.org/10.18653/v1/2020.emnlp-demos.6",
    "Yin, W., Hay, J., y Roth, D. (2019). Benchmarking zero-shot text classification: Datasets, evaluation and entailment approach. *Proceedings of EMNLP-IJCNLP 2019*, 3914–3923. https://doi.org/10.18653/v1/D19-1404",
]
referencias = [
    (f'<w:p><w:pPr><w:spacing w:after="120" w:line="252" w:lineRule="auto"/><w:ind w:left="720" w:hanging="720"/></w:pPr>'
     f"{_runs(r)}</w:p>") for r in referencias_txt
]
referencias.append(P("*Distinción de fuentes: los datos de arquitectura, parámetros, licencia y exactitud XNLI provienen de las fichas publicadas por los autores de los modelos. Las métricas sobre reportes de obra serán resultados propios generados por el notebook.*", size=17, color=GRIS_TEXTO))


# =============================================================================
# Ensamble sobre el formato
# =============================================================================
def _bloques_banda(xml: str) -> list[tuple[int, int, str]]:
    """Ubica cada tabla-banda (<w:tbl>…</w:tbl>) y su título."""
    bloques = []
    for m in re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S):
        titulo = re.findall(r"<w:t>([^<]*)</w:t>", m.group(0))
        bloques.append((m.start(), m.end(), "".join(titulo)))
    return bloques


def construir(formato: Path, salida: Path) -> None:
    tmp = Path(tempfile.mkdtemp(prefix="formato_"))
    with zipfile.ZipFile(formato) as z:
        z.extractall(tmp)
    doc_path = tmp / "word" / "document.xml"
    xml = doc_path.read_text(encoding="utf-8")

    # --- Portada: actividad, título y fecha ---
    reemplazos = {
        "<w:t>Actividad 1</w:t>": "<w:t>Actividad 4</w:t>",
        "<w:t>Explorando datos de corpus con Python</w:t>":
            "<w:t>Análisis comparativo de modelos preentrenados: VOREKO IA</w:t>",
        "<w:t>: 15/05/2026</w:t>": "<w:t>: 09/10/2026</w:t>",
    }
    for viejo, nuevo in reemplazos.items():
        assert xml.count(viejo) == 1, f"No se encontró en el formato: {viejo}"
        xml = xml.replace(viejo, nuevo)
    # --- Contenido entre bandas ---
    contenido = {
        "Introducción": "".join(introduccion),
        "Desarrollo del Ejercicio": "".join(d),
        "Conclusiones": "".join(conclusiones),
        "Referencias": "".join(referencias),
    }
    bandas = _bloques_banda(xml)
    titulos = [b[2] for b in bandas]
    assert titulos == list(contenido), f"Bandas inesperadas en el formato: {titulos}"
    fin_cuerpo = xml.index("<w:sectPr")
    partes, cursor = [], 0
    for i, (ini, fin, titulo) in enumerate(bandas):
        siguiente = bandas[i + 1][0] if i + 1 < len(bandas) else fin_cuerpo
        partes.append(xml[cursor:fin])  # hasta el final de la banda
        espaciador = '<w:p><w:pPr><w:spacing w:after="60"/></w:pPr></w:p>'
        # Banda de "Desarrollo" empieza en página nueva (Introducción ya tiene salto en el formato)
        partes.append(espaciador + contenido[titulo])
        cursor = siguiente  # se descartan los párrafos vacíos del formato entre bandas
    partes.append(xml[fin_cuerpo:])
    xml = "".join(partes)
    # Salto de página antes de "Desarrollo del Ejercicio" para separarlo de la introducción
    xml = xml.replace(
        '<w:t>Desarrollo del Ejercicio</w:t>',
        '<w:t>Desarrollo del Ejercicio</w:t>', 1)
    idx = xml.index("<w:t>Desarrollo del Ejercicio</w:t>")
    tbl_ini = xml.rfind("<w:tbl>", 0, idx)
    xml = xml[:tbl_ini] + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + xml[tbl_ini:]
    # Referencias en página nueva
    idx = xml.index("<w:t>Referencias</w:t>")
    tbl_ini = xml.rfind("<w:tbl>", 0, idx)
    xml = xml[:tbl_ini] + '<w:p><w:r><w:br w:type="page"/></w:r></w:p>' + xml[tbl_ini:]
    doc_path.write_text(xml, encoding="utf-8")

    # --- Imágenes y relaciones ---
    rels_path = tmp / "word" / "_rels" / "document.xml.rels"
    rels = rels_path.read_text(encoding="utf-8")
    for rid, ruta in _imagenes:
        destino = tmp / "word" / "media" / f"voreko_{ruta.name}"
        shutil.copy(ruta, destino)
        rels = rels.replace("</Relationships>",
                            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                            f'Target="media/{destino.name}"/></Relationships>')
    rels_path.write_text(rels, encoding="utf-8")

    # --- Numeraciones que reinician (basadas en el abstractNum de List Number) ---
    num_path = tmp / "word" / "numbering.xml"
    num = num_path.read_text(encoding="utf-8")
    abstract = re.search(r'<w:num w:numId="5"[^>]*>\s*<w:abstractNumId w:val="(\d+)"/>', num).group(1)
    nuevos = "".join(
        f'<w:num w:numId="{n}"><w:abstractNumId w:val="{abstract}"/><w:lvlOverride w:ilvl="0">'
        f'<w:startOverride w:val="1"/></w:lvlOverride></w:num>' for n in _num_listas)
    num = num.replace("</w:numbering>", nuevos + "</w:numbering>")
    num_path.write_text(num, encoding="utf-8")

    # --- Propiedades del documento ---
    core = tmp / "docProps" / "core.xml"
    c = core.read_text(encoding="utf-8")
    c = re.sub(r"<dc:title>.*?</dc:title>", "<dc:title>Análisis comparativo VOREKO IA</dc:title>", c) if "<dc:title>" in c else c
    core.write_text(c, encoding="utf-8")

    # --- Empaquetar ---
    salida.parent.mkdir(parents=True, exist_ok=True)
    if salida.exists():
        salida.unlink()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        ct = tmp / "[Content_Types].xml"
        z.write(ct, "[Content_Types].xml")
        for f in sorted(tmp.rglob("*")):
            if f.is_file() and f != ct:
                z.write(f, f.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    print(f"Documento generado: {salida}")


if __name__ == "__main__":
    formato = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "FORMATO_TAREA_SEPT2026.docx"
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 else DIR / "Analisis_comparativo_VOREKO_IA.docx"
    construir(formato, salida)
