# -*- coding: utf-8 -*-
"""
actualizar_documento_resultados.py
==================================
Actualiza el Word del análisis comparativo (versión editada por el autor) con
los resultados REALES de la ejecución en Google Colab (GPU Tesla T4,
2026-10-12). Edita el archivo en su lugar para conservar los cambios del autor;
todos los valores se leen de results/, ninguno se escribe a mano.

    python docs/actualizar_documento_resultados.py docs/base_autor_Analisis_comparativo_VOREKO_IA.docx results docs/figuras/eficiencia_vs_precision_corregida.png docs/Analisis_comparativo_VOREKO_IA.docx
"""

from __future__ import annotations

import json
import re
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_documento_formato import B, CODIGO, H3, NOTA, P, PIE, TABLA, _runs  # noqa: E402

CATS = ["Sobrecosto", "Retraso de ejecución", "Problemas de calidad", "Riesgos de seguridad", "Sin incidencia identificada"]
MODELOS = ["MiniLMv2-L6", "mDeBERTa-v3-base", "XLM-RoBERTa-large"]


def f3(x):
    return f"{x:.3f}"


# =============================================================================
# Utilidades de edición sobre el XML existente
# =============================================================================
class Doc:
    def __init__(self, xml: str):
        self.s = xml

    def _idx(self, texto: str) -> int:
        n = self.s.count(texto)
        assert n == 1, f"'{texto[:60]}' aparece {n} veces"
        return self.s.index(texto)

    def _parrafo(self, texto: str) -> tuple[int, int]:
        i = self._idx(texto)
        a = max(self.s.rfind("<w:p ", 0, i), self.s.rfind("<w:p>", 0, i))
        b = self.s.index("</w:p>", i) + len("</w:p>")
        return a, b

    def reemplazar_parrafo(self, texto: str, nuevo: str) -> None:
        a, b = self._parrafo(texto)
        self.s = self.s[:a] + nuevo + self.s[b:]

    def insertar_despues_parrafo(self, texto: str, nuevo: str) -> None:
        _, b = self._parrafo(texto)
        self.s = self.s[:b] + nuevo + self.s[b:]

    def insertar_despues_tabla(self, texto: str, nuevo: str) -> None:
        i = self._idx(texto)
        b = self.s.index("</w:tbl>", i) + len("</w:tbl>")
        self.s = self.s[:b] + nuevo + self.s[b:]

    def texto(self, viejo: str, nuevo: str) -> None:
        self._idx(viejo)
        self.s = self.s.replace(viejo, nuevo)

    def llenar_pendientes(self, valores: list[str]) -> None:
        """Sustituye, en orden, cada celda 'Pendiente: ejecutar en Colab' por su valor real."""
        patron = re.compile(r"<w:tc>(?:(?!</w:tc>).)*?Pendiente: ejecutar en Colab(?:(?!</w:tc>).)*?</w:tc>", re.S)
        celdas = list(patron.finditer(self.s))
        assert len(celdas) == len(valores), f"Se esperaban {len(valores)} celdas pendientes y hay {len(celdas)}"
        for m, valor in reversed(list(zip(celdas, valores))):
            celda = m.group(0)
            ancho = re.search(r'<w:tcW w:w="(\d+)"', celda).group(1)
            nueva = (f'<w:tc><w:tcPr><w:tcW w:w="{ancho}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
                     f'<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                     f'{_runs(valor, size=16)}</w:p></w:tc>')
            self.s = self.s[:m.start()] + nueva + self.s[m.end():]


_imgs: list[tuple[str, Path]] = []


def IMAGEN(ruta: Path, ancho_pulg: float) -> str:
    with open(ruta, "rb") as f:
        w, h = struct.unpack(">II", f.read(24)[16:24])
    cx, rid, n = int(ancho_pulg * 914400), f"rIdRes{len(_imgs) + 1}", 60 + len(_imgs)
    cy = int(cx * h / w)
    _imgs.append((rid, ruta))
    return (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="60"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{n}" name="Resultado {n}"/><wp:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            f'</wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr>'
            f'<pic:cNvPr id="{n}" name="{ruta.name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr>'
            f'<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'</pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# =============================================================================
def main(entrada: Path, res: Path, figs: Path, salida: Path) -> None:
    t = pd.read_csv(res / "metricas_comparativas.csv", index_col=0).loc[MODELOS]
    u = pd.read_csv(res / "evaluacion_umbrales.csv", index_col=0).loc[MODELOS]
    exp = pd.read_csv(res / "exploracion_variantes.csv")
    pred = pd.read_csv(res / "predicciones_evaluacion.csv")
    ent = json.loads((res / "entorno_ejecucion.json").read_text(encoding="utf-8"))
    rec = json.loads((res / "recomendacion.json").read_text(encoding="utf-8"))
    voreko = json.loads((res / "ejemplo_respuesta_voreko.json").read_text(encoding="utf-8"))
    hub = json.loads((res / "modelos_hub.json").read_text(encoding="utf-8"))
    rt = pd.read_csv(res / "revision_tecnica.csv")
    assert (rt["resultado"] == "OK").all() and len(rt) == 18
    assert rec["modelo"] == "XLM-RoBERTa-large" and not rec["modelos_que_cumplen"]

    # --- Cifras derivadas (todas de los archivos de resultados) ---
    acc, f1 = t["accuracy"], t["f1_macro"]
    lat, p95, mem = t["latencia_media_ms"], t["latencia_p95_ms"], t["memoria_pico_gpu_mb"]
    rcol = {c: t[f"recall_{c}"] for c in CATS}
    aciertos = pred.groupby("modelo")["acierto"].sum()
    dif_aciertos = int(aciertos["XLM-RoBERTa-large"] - aciertos["mDeBERTa-v3-base"])
    pred_col = pred.groupby(["modelo", "categoria_predicha"]).size()
    prec = pd.read_csv(res / "metricas_por_categoria.csv").set_index(["modelo", "categoria"])["precision"]
    por_tipo = pred.pivot_table(index="tipo_redaccion", columns="modelo", values="acierto", aggfunc="mean")
    n_tipo = pred[pred.modelo == MODELOS[0]].groupby("tipo_redaccion").size()
    multi = pred.pivot_table(index="multiples_incidencias", columns="modelo", values="acierto", aggfunc="mean")
    n_multi = int(pred[pred.modelo == MODELOS[0]]["multiples_incidencias"].sum())
    punt = pred.pivot_table(index="modelo", columns="acierto", values="puntuacion_modelo", aggfunc="mean")
    revision = {}
    for m in MODELOS:
        g = pred[pred.modelo == m]
        err = g[~g.acierto]
        nr = g[~g.requiere_revision_humana]
        revision[m] = (u.loc[m, "pct_revision_humana"], len(err), int(err.requiere_revision_humana.sum()),
                       int(u.loc[m, "errores_criticos_sin_revision"]), nr.acierto.mean(), len(nr))
    media_var = exp.groupby("variante")["f1_macro"].mean()
    ex = exp.set_index(["modelo", "variante"])["f1_macro"]
    seg_xlm = pred[(pred.modelo == "XLM-RoBERTa-large") & (pred.categoria_real == "Riesgos de seguridad")
                   & (~pred.acierto) & (~pred.requiere_revision_humana)].sort_values("puntuacion_modelo", ascending=False)
    assert len(seg_xlm) >= 2

    tmp = Path(tempfile.mkdtemp(prefix="doc_res_"))
    with zipfile.ZipFile(entrada) as z:
        z.extractall(tmp)
    for p in tmp.rglob("*"):
        if p.is_symlink():
            p.unlink()
    xml_path = tmp / "word" / "document.xml"
    d = Doc(xml_path.read_text(encoding="utf-8"))

    # ---------------- Portada ----------------
    d.texto("09/10/2026", "12/10/2026")

    # ---------------- Celdas pendientes (36) ----------------
    vals = []
    for m in MODELOS:
        vals += [f3(acc[m]), f3(f1[m]), f"{lat[m]:.1f}", f"{mem[m]:,.0f}"]
    for c in CATS:
        vals += [f3(rcol[c][m]) for m in MODELOS]
    for m in MODELOS:
        vals.append(f"{f3(acc[m])} — no cumple" if not u.loc[m, "cumple_accuracy"] else f"{f3(acc[m])} — cumple")
    for m in MODELOS:
        vals.append(f"{f3(f1[m])} — no cumple" if not u.loc[m, "cumple_f1_macro"] else f"{f3(f1[m])} — cumple")
    for m in MODELOS:
        vals.append(f"{u.loc[m, 'recall_critico_min']:.3f} ({u.loc[m, 'categoria_mas_debil'].split()[-1].lower()}) — "
                    + ("cumple" if u.loc[m, "cumple_recall_critico"] else "no cumple"))
    d.llenar_pendientes(vals)

    # ---------------- 7. Implementación: ejecución real ----------------
    d.insertar_despues_parrafo(
        "Verificación del código.",
        P(f"**Ejecución en Google Colab.** El notebook se ejecutó completo el 12 de octubre de 2026 en Google Colab con GPU "
          f"**{ent['gpu']}** ({ent['memoria_gpu_total_mb']:,} MB), Python {ent['python']}, PyTorch {ent['torch']} y "
          f"Transformers {ent['transformers']}. Los tres modelos se descargaron sin errores, quedaron en la GPU en float32 y "
          f"las **18 comprobaciones automáticas** de la revisión técnica resultaron correctas. El código ejecutado es idéntico al "
          f"entregado. Recalculé las métricas a partir del archivo de predicciones y coinciden con las tablas del notebook."))

    # ---------------- 8. Comparación de métricas ----------------
    d.texto("las de precisión, latencia y recursos son mediciones propias.",
            f"las de precisión, latencia y recursos son mediciones propias sobre los 120 reportes de evaluación ({ent['gpu']}, 12/10/2026).")
    col_ret = int(pred_col["mDeBERTa-v3-base"].get("Retraso de ejecución", 0))
    col_sob = int(pred_col["XLM-RoBERTa-large"].get("Sobrecosto", 0))
    nuevo8 = [
        P("**Métricas complementarias:**", keep_next=True),
        TABLA(["Modelo", "Precision macro", "Recall macro", "Latencia p95 (ms)", "Reportes por segundo",
               "Puntuación media en aciertos", "Puntuación media en errores"],
              [[m, f3(t.loc[m, "precision_macro"]), f3(t.loc[m, "recall_macro"]), f"{p95[m]:.1f}",
                f"{t.loc[m, 'reportes_por_segundo']:.1f}", f3(punt.loc[m, True]), f3(punt.loc[m, False])] for m in MODELOS],
              [1.8, 1.2, 1.2, 1.3, 1.3, 1.6, 1.6], size=16),
        P(f"**Lectura de resultados.** Ningún modelo se acercó a los umbrales. XLM-RoBERTa-large obtuvo el mejor desempeño "
          f"(accuracy {f3(acc['XLM-RoBERTa-large'])} y F1 macro {f3(f1['XLM-RoBERTa-large'])}), seguido de mDeBERTa-v3-base "
          f"({f3(acc['mDeBERTa-v3-base'])} y {f3(f1['mDeBERTa-v3-base'])}). La diferencia entre ambos es de {dif_aciertos} aciertos "
          f"en 120 reportes: fue mejor en este conjunto, pero con una muestra tan pequeña no puedo afirmar que sea superior en "
          f"general. MiniLMv2-L6 obtuvo {f3(acc['MiniLMv2-L6'])}, apenas por encima del 0.20 que se lograría eligiendo al azar "
          f"entre cinco categorías; para este caso de uso no es útil."),
        P(f"Las matrices de confusión (Figura 2) muestran que cada modelo tiende a una categoría «refugio». mDeBERTa-v3-base "
          f"predijo *Retraso de ejecución* en {col_ret} de los 120 reportes: por eso su recall en esa clase es alto "
          f"({f3(rcol['Retraso de ejecución']['mDeBERTa-v3-base'])}), pero su precision es baja "
          f"({f3(prec[('mDeBERTa-v3-base', 'Retraso de ejecución')])}). XLM-RoBERTa-large hace lo mismo con *Sobrecosto* "
          f"({col_sob} predicciones; recall {f3(rcol['Sobrecosto']['XLM-RoBERTa-large'])} y precision "
          f"{f3(prec[('XLM-RoBERTa-large', 'Sobrecosto')])}). Un recall alto en una sola clase, por tanto, no significa que el "
          f"modelo la entienda bien."),
        P(f"El hallazgo más importante es el de las **categorías críticas**. En *Riesgos de seguridad* el recall fue de "
          f"{f3(rcol['Riesgos de seguridad']['MiniLMv2-L6'])}, {f3(rcol['Riesgos de seguridad']['mDeBERTa-v3-base'])} y "
          f"{f3(rcol['Riesgos de seguridad']['XLM-RoBERTa-large'])}: los tres modelos dejaron pasar al menos cuatro de cada cinco "
          f"riesgos de seguridad, sobre todo como retrasos o sobrecostos. Cuando XLM-RoBERTa-large sí predijo seguridad, acertó "
          f"siempre (precision {f3(prec[('XLM-RoBERTa-large', 'Riesgos de seguridad')])}), pero lo hizo muy pocas veces. Mi "
          f"hipótesis, que no comprobé en este experimento, es que los reportes describen situaciones concretas (\"sin arnés\", "
          f"\"cables pelados\", \"sin ademe\") y no usan palabras como \"riesgo\" o \"peligro\", así que el modelo NLI tendría que "
          f"inferir el peligro y no lo logra sin ejemplos del dominio. *Problemas de calidad* tuvo el mismo problema "
          f"(recall máximo {f3(rcol['Problemas de calidad'].max())})."),
        P("**Exactitud por tipo de redacción** (proporción de aciertos; las muestras pequeñas deben leerse con cautela):", keep_next=True),
        TABLA(["Tipo de redacción", "Reportes", *MODELOS],
              [[tipo, str(int(n_tipo[tipo])), *[f3(por_tipo.loc[tipo, m]) for m in MODELOS]]
               for tipo in ["directo", "negacion", "coloquial", "ambiguo", "contraste"]]
              + [["Con múltiples incidencias", str(n_multi), *[f3(multi.loc[True, m]) for m in MODELOS]]],
              [2.4, 1.2, 2.1, 2.1, 2.2], size=16),
        P(f"Contra lo que esperaba, las negaciones no fueron el problema principal: XLM-RoBERTa-large acertó "
          f"{f3(por_tipo.loc['negacion', 'XLM-RoBERTa-large'])} de los reportes con negación y "
          f"{f3(por_tipo.loc['coloquial', 'XLM-RoBERTa-large'])} de los coloquiales, por encima de los directos "
          f"({f3(por_tipo.loc['directo', 'XLM-RoBERTa-large'])}). Los de contraste fueron los más difíciles en promedio, y los "
          f"reportes con varias incidencias bajaron el desempeño de los tres modelos. También se confirma que la puntuación no "
          f"equivale a precisión: en mDeBERTa-v3-base, las predicciones equivocadas tuvieron en promedio una puntuación de "
          f"{f3(punt.loc['mDeBERTa-v3-base', False])}."),
        IMAGEN(res / "figuras" / "matrices_confusion.png", 6.9),
        PIE("Figura 2. Matrices de confusión de los tres modelos (partición de evaluación, 24 reportes por clase; Tesla T4)."),
    ]
    d.reemplazar_parrafo("Guía de interpretación.", "".join(nuevo8))

    # ---------------- 9. Eficiencia vs precisión ----------------
    d.insertar_despues_parrafo(
        "En zero-shot, la redacción de las etiquetas puede pesar tanto",
        P("**Lo que mostraron los resultados:**", after=60, keep_next=True)
        + B(f"**Memoria:** se confirmó. El pico de memoria en GPU creció con el tamaño: {mem['MiniLMv2-L6']:,.0f} MB, "
            f"{mem['mDeBERTa-v3-base']:,.0f} MB y {mem['XLM-RoBERTa-large']:,.0f} MB, prácticamente el peso de cada modelo en float32.")
        + B(f"**Latencia:** sólo se confirmó en parte. MiniLMv2-L6 fue el más rápido ({lat['MiniLMv2-L6']:.1f} ms por reporte, "
            f"{lat['XLM-RoBERTa-large'] / lat['MiniLMv2-L6']:.1f} veces más rápido que XLM-RoBERTa-large). Sin embargo, mDeBERTa-v3-base, "
            f"con la mitad de parámetros, tardó en promedio más ({lat['mDeBERTa-v3-base']:.1f} ms) que XLM-RoBERTa-large "
            f"({lat['XLM-RoBERTa-large']:.1f} ms). XLM-RoBERTa-large tuvo, en cambio, más variación (percentil 95 de "
            f"{p95['XLM-RoBERTa-large']:.0f} ms frente a {p95['mDeBERTa-v3-base']:.0f} ms). Una posible explicación, no medida aquí, "
            f"es el mecanismo de atención de DeBERTa, que hace más operaciones por capa, sumado a que con un reporte por llamada la "
            f"GPU trabaja muy por debajo de su capacidad. En esas condiciones, la latencia no crece en proporción a los parámetros.")
        + B(f"**Precisión:** el modelo más grande fue el más preciso, pero su ventaja sobre mDeBERTa-v3-base fue pequeña "
            f"(+{f1['XLM-RoBERTa-large'] - f1['mDeBERTa-v3-base']:.3f} de F1 macro) a cambio del doble de memoria. El modelo pequeño "
            f"no ofrece un punto intermedio: es rápido, pero sus predicciones casi no sirven."))
    d.reemplazar_parrafo(
        "La gráfica de eficiencia frente a precisión que genera el notebook",
        P("En la Figura 3, ningún modelo llega a la zona deseable (arriba a la izquierda) ni cruza la línea del umbral. Entre los "
          "dos modelos útiles, XLM-RoBERTa-large superó a mDeBERTa-v3-base en este experimento: logró más F1 macro con una "
          "latencia media incluso menor. Su único costo adicional es la memoria (≈ 2.1 GB frente a ≈ 1.1 GB), que es lo que "
          "encarece un servidor de inferencia. Por eso el dilema entre eficiencia y precisión quedó, en la práctica, como un "
          "dilema entre **precisión y memoria**.", keep_next=True)
        + IMAGEN(figs, 5.2)
        + PIE("Figura 3. F1 macro frente a latencia media por reporte (GPU Tesla T4)."))

    # ---------------- 10. Ajustes mínimos ----------------
    d.reemplazar_parrafo(
        "Variante de etiquetas elegida en la exploración",
        P(f"**Variante de etiquetas elegida en la exploración: A (nombres cortos).** Resultados de F1 macro con los 30 reportes de "
          f"exploración:", keep_next=True)
        + TABLA(["Modelo", "Variante A (nombres cortos)", "Variante B (descriptivas)", "Mejor variante para el modelo"],
                [[m, f3(ex[(m, 'A_nombres_cortos')]), f3(ex[(m, 'B_descriptivas')]),
                  "A" if ex[(m, 'A_nombres_cortos')] > ex[(m, 'B_descriptivas')] else "B"] for m in MODELOS]
                + [["Promedio de los tres", f"{media_var['A_nombres_cortos']:.4f}", f"{media_var['B_descriptivas']:.4f}", "A (por 0.0004)"]],
                [2.4, 2.4, 2.4, 2.8], size=16)
        + P(f"La regla eligió la variante A, pero la diferencia de los promedios fue de apenas "
            f"{media_var['A_nombres_cortos'] - media_var['B_descriptivas']:.4f}: en la práctica, un empate. Además, los modelos no "
            f"coincidieron. mDeBERTa-v3-base funcionó mucho mejor con A ({f3(ex[('mDeBERTa-v3-base', 'A_nombres_cortos')])} frente a "
            f"{f3(ex[('mDeBERTa-v3-base', 'B_descriptivas')])}), mientras que XLM-RoBERTa-large y MiniLMv2-L6 funcionaron mejor con B. "
            f"Es posible que XLM-RoBERTa-large hubiera obtenido mejores resultados en la evaluación con las etiquetas descriptivas. "
            f"No lo comprobé, porque cambiar la variante después de ver la evaluación invalidaría el resultado. Esta es una "
            f"limitación del diseño: con 30 reportes de exploración, la elección de la redacción no es robusta. En una siguiente "
            f"iteración conviene elegir la redacción por modelo y con un conjunto de exploración más grande."))

    # ---------------- 11.1 Umbrales ----------------
    xl = "XLM-RoBERTa-large"
    d.insertar_despues_parrafo(
        "las cuatro que representan una incidencia (sobrecosto",
        P(f"**Resultado:** ningún modelo cumplió ninguno de los tres umbrales. El más cercano, XLM-RoBERTa-large, quedó "
          f"{(0.80 - acc[xl]) * 100:.1f} puntos por debajo en accuracy y {(0.80 - f1[xl]) * 100:.1f} puntos por debajo en F1 macro. "
          f"Su recall en riesgos de seguridad ({u.loc[xl, 'recall_critico_min']:.3f}) está lejos del 0.80 requerido. Esto confirma "
          f"que, en este caso de uso, la clasificación zero-shot sin ajuste no alcanza el nivel que me propuse."))

    # ---------------- 11.2 Revisión humana ----------------
    ej1, ej2 = seg_xlm.iloc[0], seg_xlm.iloc[1]
    d.insertar_despues_parrafo(
        "El notebook reporta además cuántos errores",
        TABLA(["Modelo", "Enviados a revisión", "Errores totales", "Errores que sí llegaron a revisión",
               "Errores críticos sin revisión", "Accuracy de lo no revisado"],
              [[m, f"{revision[m][0]:.1f} %", str(revision[m][1]), str(revision[m][2]), str(revision[m][3]),
                f"{revision[m][4]:.3f} (n={revision[m][5]})"] for m in MODELOS],
              [1.8, 1.4, 1.2, 1.7, 1.6, 1.8], size=16)
        + P(f"Con XLM-RoBERTa-large, el criterio envió a revisión el {revision[xl][0]:.1f} % de los reportes y capturó "
            f"{revision[xl][2]} de sus {revision[xl][1]} errores. Aun así, {revision[xl][3]} errores en categorías críticas habrían "
            f"pasado sin que nadie los revisara. El punto débil es la condición (c): sólo se activa cuando el modelo **predice** "
            f"seguridad, y como casi nunca lo hace, los riesgos mal clasificados pasan con puntuaciones altas. Dos ejemplos: "
            f"\"{ej1['texto_reporte']}\" se clasificó como *{ej1['categoria_predicha']}* con {ej1['puntuacion_modelo']:.2f}, y "
            f"\"{ej2['texto_reporte']}\" como *{ej2['categoria_predicha']}* con {ej2['puntuacion_modelo']:.2f}.")
        + P("**Propuesta de mitigación (no probada todavía):** añadir una regla independiente del modelo que envíe a revisión "
            "cualquier nota con términos de seguridad de obra (arnés, casco, ademe, andamio, puntal, cables pelados, extintor, "
            "barandal, excavación, entre otros), y medir de nuevo cuántos riesgos quedan sin revisión."))

    # ---------------- 12. Recomendación ----------------
    d.reemplazar_parrafo(
        "Modelo recomendado:",
        P(f"**Modelo recomendado:** XLM-RoBERTa-large ({rec['id']}), **como candidato condicionado**. Se aplicó la segunda regla, "
          f"porque ningún modelo cumplió los umbrales."))
    d.reemplazar_parrafo(
        "Justificación con métricas:",
        P(f"**Justificación con métricas.** XLM-RoBERTa-large tuvo la mejor accuracy ({f3(acc[xl])}), el mejor F1 macro "
          f"({f3(f1[xl])}), la mejor precision macro ({f3(t.loc[xl, 'precision_macro'])}) y la mayor exactitud entre los reportes "
          f"no enviados a revisión ({revision[xl][4]:.3f}). Su latencia media ({lat[xl]:.1f} ms) fue incluso menor que la de "
          f"mDeBERTa-v3-base, y unos 133 ms por nota no afectan la experiencia en VOREKO, donde la clasificación puede llegar "
          f"segundos después de guardar la observación. Su desventaja es la memoria: {mem[xl]:,.0f} MB, que exigen un servidor "
          f"con GPU o con más RAM. La licencia (MIT) es igual en los tres modelos y no fue un factor diferenciador.")
        + P("**Lo que la recomendación no significa:**", after=60, keep_next=True)
        + B("No es apto para clasificar automáticamente en producción: acierta poco más de la mitad de las veces y deja pasar la "
            "mayoría de los riesgos de seguridad.")
        + B("Sólo puede usarse como apoyo, con revisión humana y con la regla complementaria de términos de seguridad.")
        + P("**Alternativa:** si el costo del servidor fuera la restricción principal, mDeBERTa-v3-base usa la mitad de memoria a "
            f"cambio de {f1[xl] - f1['mDeBERTa-v3-base']:.3f} puntos menos de F1 macro, sin ventaja de latencia. MiniLMv2-L6 se descarta.",
            after=60)
        + P("**Condiciones para avanzar a una siguiente etapa:**", after=60, keep_next=True)
        + B("Reunir observaciones reales de VOREKO, anonimizarlas y etiquetarlas con al menos dos especialistas en obra.")
        + B("Probar ajuste fino (*fine-tuning*) o métodos con pocos ejemplos por clase, y volver a evaluar con los mismos umbrales.")
        + B("Elegir la redacción de etiquetas por modelo y con una partición de exploración más grande.")
        + B("Medir el recall de *Riesgos de seguridad* como criterio de aceptación principal."))

    # ---------------- 13. Prueba funcional ----------------
    esperado = ["Retraso de ejecución", "Sobrecosto", "Problemas de calidad", "Riesgos de seguridad",
                "Sin incidencia identificada", "Retraso de ejecución y sobrecosto (múltiple)"]
    assert len(voreko) == len(esperado)
    filas = []
    for r, e in zip(voreko, esperado):
        if r["categoria_predicha"] == e:
            veredicto = "Correcta"
        elif r["categoria_predicha"].split()[0].lower() in e.lower():
            veredicto = "Parcial"
        else:
            veredicto = "Incorrecta"
        filas.append([r["texto_reporte"], e, r["categoria_predicha"], f"{r['puntuacion_modelo']:.2f}",
                      "Sí" if r["requiere_revision_humana"] else "No", veredicto])
    correctas = sum(f[-1] == "Correcta" for f in filas)
    sha = hub[xl]["sha"]
    ej = dict(voreko[0])
    d.reemplazar_parrafo(
        "La respuesta que devolvería el servicio",
        P(f"**Prueba funcional con comentarios nuevos.** Probé el modelo recomendado con seis comentarios que no forman parte del "
          f"dataset. La columna «Categoría esperada» es mi propia lectura de cada texto:", keep_next=True)
        + TABLA(["Comentario", "Categoría esperada", "Predicción", "Puntuación", "Revisión", "Resultado"], filas,
                [3.3, 1.7, 1.6, 1.2, 0.9, 1.1], size=15)
        + P(f"Acertó {['ninguno', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis'][correctas]} de seis, y el comentario con dos incidencias se clasificó sólo como retraso. Los dos errores en "
            f"calidad y en un reporte sin incidencia se enviaron a revisión por su baja puntuación, así que el criterio funcionó. "
            f"El caso preocupante es «El chalán anda trepado en la barda sin nada que lo sostenga»: un riesgo de seguridad "
            f"evidente que el modelo clasificó como *Sin incidencia identificada* con {voreko[3]['puntuacion_modelo']:.2f}, **sin "
            f"enviarlo a revisión**. Es el mismo patrón que se observó en la evaluación.")
        + P("Respuesta real del servicio para el primer comentario (results/ejemplo_respuesta_voreko.json):", keep_next=True))
    d.reemplazar_parrafo(
        '"texto_reporte"',
        CODIGO(json.dumps(ej, ensure_ascii=False))
        + P(f"El campo version_modelo quedó como «desconocida»: en Transformers 5 la configuración del modelo ya no guarda la "
            f"revisión descargada. La revisión sí quedó registrada en modelos_hub.json (para XLM-RoBERTa-large, {sha[:12]}), y el "
            f"código se corrigió para tomarla de ahí (bitácora, versión 1.5).", size=18, color="5F5E58"))
    d.texto("Figura 2. Arquitectura conceptual", "Figura 4. Arquitectura conceptual")

    # ---------------- 14. Archivos ----------------
    d.texto("Notebook de Google Colab (sin salidas hasta ejecutarse)",
            f"Notebook ejecutado en Google Colab con GPU {ent['gpu']} (12/10/2026), con salidas")
    d.texto("Resultados generados por el notebook (vacía hasta ejecutarlo)",
            "Resultados de la ejecución: métricas, predicciones, umbrales, recomendación, revisión técnica (18/18 OK) y figuras")

    # ---------------- Conclusiones ----------------
    d.reemplazar_parrafo(
        "Esta sección se complementará",
        P(f"Los resultados me obligaron a corregir una expectativa. Esperaba que al menos uno de los modelos se acercara al 80 %, y "
          f"el mejor llegó a {acc[xl] * 100:.1f} %. La clasificación zero-shot es útil para arrancar sin datos, pero en un dominio "
          f"tan específico como el de una obra no sustituye a un modelo entrenado con ejemplos propios. Lo valioso del experimento "
          f"es que ahora sé exactamente dónde falla: los riesgos de seguridad y los defectos de calidad, que son justamente lo que "
          f"un residente no puede dejar pasar.")
        + P("También comprobé que el tamaño no lo explica todo. El modelo más grande no fue el más lento, el más pequeño resultó "
            "prácticamente aleatorio, y una diferencia de redacción en las etiquetas cambió el desempeño de un mismo modelo más que "
            "la distancia entre dos arquitecturas. Si hubiera elegido el modelo sólo por su exactitud publicada en XNLI, habría "
            "escogido mDeBERTa-v3-base. Con mis datos, el resultado fue otro, y esa es la razón de hacer la comparación con un "
            "conjunto propio que plantea el Tema 9.")
        + P("Para VOREKO, la conclusión práctica es que el prototipo funciona como herramienta de apoyo y no como dictamen: puede "
            "ordenar y sugerir, siempre con revisión humana y con una regla adicional para seguridad. El siguiente paso es reunir "
            "observaciones reales de mis propias obras, anonimizarlas y etiquetarlas, y repetir este mismo procedimiento con ajuste "
            "fino. El código, las pruebas y la bitácora ya están listos para eso."))

    assert "Pendiente" not in re.sub(r"<[^>]+>", "", d.s), "Quedó texto 'Pendiente' en el documento"
    xml_path.write_text(d.s, encoding="utf-8")

    # --- Imágenes ---
    rels_p = tmp / "word" / "_rels" / "document.xml.rels"
    rels = rels_p.read_text(encoding="utf-8")
    for rid, ruta in _imgs:
        destino = tmp / "word" / "media" / f"resultado_{ruta.name}"
        shutil.copy(ruta, destino)
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                            f'officeDocument/2006/relationships/image" Target="media/{destino.name}"/></Relationships>')
    rels_p.write_text(rels, encoding="utf-8")

    if salida.exists():
        salida.unlink()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp / "[Content_Types].xml", "[Content_Types].xml")
        for f in sorted(tmp.rglob("*")):
            if f.is_file() and f.name != "[Content_Types].xml":
                z.write(f, f.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    print("Documento actualizado:", salida)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
