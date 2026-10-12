# -*- coding: utf-8 -*-
"""Pruebas de métricas, umbrales, revisión humana y salida estructurada."""

import json

import pandas as pd
import pytest

from src.config import CATEGORIAS, VARIANTES_ETIQUETAS
from src.evaluacion import (
    a_json,
    calcular_metricas,
    errores_frecuentes,
    evaluar_umbrales,
    invertir_etiquetas,
    requiere_revision,
    resumen_latencia,
    salida_voreko,
    salidas_a_dataframe,
)


def test_variantes_biyectivas():
    for v in VARIANTES_ETIQUETAS.values():
        inv = invertir_etiquetas(v["etiquetas"])
        assert set(inv.values()) == set(CATEGORIAS)
        assert "{}" in v["plantilla"]


def test_metricas_caso_conocido():
    # 10 casos con resultado calculable a mano
    real = ["Sobrecosto"] * 4 + ["Riesgos de seguridad"] * 4 + ["Sin incidencia identificada"] * 2
    pred = ["Sobrecosto"] * 3 + ["Retraso de ejecución"] + ["Riesgos de seguridad"] * 4 + ["Sobrecosto"] * 2
    m = calcular_metricas(real, pred)
    assert m["accuracy"] == pytest.approx(0.7)
    pc = m["por_categoria"]
    assert pc.loc["Sobrecosto", "precision"] == pytest.approx(3 / 5)
    assert pc.loc["Sobrecosto", "recall"] == pytest.approx(3 / 4)
    assert pc.loc["Riesgos de seguridad", "f1"] == pytest.approx(1.0)
    # Clases sin predicciones -> zero_division=0, sin advertencias ni NaN
    assert pc.loc["Problemas de calidad", "precision"] == 0
    assert not pc.isna().any().any()
    assert m["matriz_confusion"].values.sum() == 10
    assert m["recall_macro"] == pytest.approx(pc["recall"].mean())


def test_metricas_rechaza_categoria_desconocida():
    with pytest.raises(AssertionError):
        calcular_metricas(["Sobrecosto"], ["Inventada"])


def test_umbrales():
    real = CATEGORIAS * 4
    m_perfecta = calcular_metricas(real, real)
    assert evaluar_umbrales(m_perfecta)["cumple_todos"]
    pred = ["Sin incidencia identificada"] * len(real)
    assert not evaluar_umbrales(calcular_metricas(real, pred))["cumple_todos"]


def test_revision_humana():
    assert requiere_revision("Sobrecosto", 0.9, 0.8) == (False, "")
    assert requiere_revision("Sobrecosto", 0.4, 0.3)[0]
    assert "prediccion_ambigua" in requiere_revision("Sobrecosto", 0.55, 0.05)[1]
    assert "categoria_seguridad" in requiere_revision("Riesgos de seguridad", 0.99, 0.9)[1]


def test_latencia():
    r = resumen_latencia([0.1, 0.2, 0.3])
    assert r["tiempo_total_s"] == pytest.approx(0.6)
    assert r["latencia_media_ms"] == pytest.approx(200)


def _salida_simulada(texto, etiquetas_orden, puntuaciones):
    return {"sequence": texto, "labels": etiquetas_orden, "scores": puntuaciones}


def test_salidas_a_dataframe_y_controles():
    mapa = VARIANTES_ETIQUETAS["A_nombres_cortos"]["etiquetas"]
    inv = invertir_etiquetas(mapa)
    cand = list(mapa.values())
    df = pd.DataFrame(
        {
            "id_reporte": ["X1", "X2"],
            "texto_reporte": ["texto uno", "texto dos"],
            "categoria_real": ["Sobrecosto", "Problemas de calidad"],
        }
    )
    salidas = [
        _salida_simulada("texto uno", cand, [0.6, 0.1, 0.1, 0.1, 0.1]),
        _salida_simulada("texto dos", cand, [0.3, 0.25, 0.2, 0.15, 0.1]),
    ]
    out = salidas_a_dataframe(salidas, df, inv, "m", [0.01, 0.02])
    assert out["acierto"].tolist() == [True, False]
    assert out.loc[1, "requiere_revision_humana"]

    # Resultados incompletos
    with pytest.raises(AssertionError):
        salidas_a_dataframe(salidas[:1], df, inv, "m", [0.01, 0.02])
    # Desfase de textos
    malas = [_salida_simulada("otro", cand, [0.6, 0.1, 0.1, 0.1, 0.1]), salidas[1]]
    with pytest.raises(AssertionError):
        salidas_a_dataframe(malas, df, inv, "m", [0.01, 0.02])
    # Etiqueta inesperada
    raras = [_salida_simulada("texto uno", ["x"] + cand[1:], [0.6, 0.1, 0.1, 0.1, 0.1]), salidas[1]]
    with pytest.raises(AssertionError):
        salidas_a_dataframe(raras, df, inv, "m", [0.01, 0.02])
    # Puntuaciones multietiqueta (no suman 1)
    multi = [_salida_simulada("texto uno", cand, [0.9, 0.8, 0.1, 0.1, 0.1]), salidas[1]]
    with pytest.raises(AssertionError):
        salidas_a_dataframe(multi, df, inv, "m", [0.01, 0.02])

    errs = errores_frecuentes(out)
    assert errs["casos"].sum() == 1


def test_salida_voreko_json():
    mapa = VARIANTES_ETIQUETAS["B_descriptivas"]["etiquetas"]
    inv = invertir_etiquetas(mapa)
    cand = list(mapa.values())
    s = _salida_simulada("Hay cables pelados", [cand[3]] + cand[:3] + [cand[4]], [0.7, 0.1, 0.1, 0.05, 0.05])
    reg = salida_voreko("Hay cables pelados", s, inv, "modelo@abc123")
    for campo in ["texto_reporte", "categoria_predicha", "puntuacion_modelo", "requiere_revision_humana", "version_modelo"]:
        assert campo in reg
    assert reg["categoria_predicha"] == "Riesgos de seguridad"
    assert reg["requiere_revision_humana"] is True
    assert json.loads(a_json([reg]))[0]["texto_reporte"] == "Hay cables pelados"
