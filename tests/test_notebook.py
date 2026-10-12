# -*- coding: utf-8 -*-
"""Pruebas estáticas del notebook: estructura, sintaxis y consistencia con src/."""

import ast
from pathlib import Path

import nbformat
import pytest

RAIZ = Path(__file__).resolve().parents[1]
NB = RAIZ / "notebooks" / "VOREKO_IA_comparacion_modelos.ipynb"


@pytest.fixture(scope="module")
def nb():
    cuaderno = nbformat.read(NB, as_version=4)
    nbformat.validate(cuaderno)
    return cuaderno


def test_sintaxis_de_todas_las_celdas(nb):
    for i, c in enumerate(nb.cells):
        if c.cell_type != "code":
            continue
        src = c.source.split("\n", 1)[1] if c.source.startswith("%%writefile") else c.source
        # Las líneas mágicas (!, %) se sustituyen por `pass` para validar el resto con ast
        lineas = ["pass" if l.lstrip().startswith(("!", "%")) else l for l in src.split("\n")]
        ast.parse("\n".join(lineas), filename=f"celda {i}")


def test_modulos_incrustados_identicos_a_src(nb):
    incrustados = {
        c.source.split("\n", 1)[0].split()[-1]: c.source.split("\n", 1)[1]
        for c in nb.cells
        if c.cell_type == "code" and c.source.startswith("%%writefile")
    }
    assert set(incrustados) == {"src/config.py", "src/generar_dataset.py", "src/datos.py",
                                "src/clasificador.py", "src/evaluacion.py"}
    for ruta, contenido in incrustados.items():
        assert contenido == (RAIZ / ruta).read_text(encoding="utf-8").strip("\n"), f"{ruta} difiere del repositorio"


def test_etapas_obligatorias_presentes(nb):
    titulos = " ".join(c.source for c in nb.cells if c.cell_type == "markdown")
    for etapa in ["1. Introducción", "2. Instalación de dependencias", "3. GPU", "4. Autenticación",
                  "5. Dataset", "6. Preparación", "7. Carga de modelos", "8. Inferencia", "9. Métricas",
                  "10. Comparación", "11. Evaluación de umbrales", "12. Recomendación",
                  "13. Prueba funcional VOREKO", "14. Revisión técnica", "16. Bitácora"]:
        assert etapa in titulos, f"Falta la etapa '{etapa}'"


def test_sin_tokens_en_el_codigo(nb):
    for c in nb.cells:
        assert "hf_" not in c.source.replace("hf_token", "").lower().replace("hf_token", ""), \
            "Posible token de Hugging Face escrito en el notebook"


def test_sin_salidas_inventadas(nb):
    """El notebook se entrega sin ejecutar: no debe contener salidas previas."""
    for c in nb.cells:
        if c.cell_type == "code":
            assert not c.get("outputs"), "El notebook contiene salidas que no provienen de una ejecución en Colab"
