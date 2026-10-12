# -*- coding: utf-8 -*-
"""
Prueba de humo del flujo completo SIN acceso a Internet.

Se construye localmente un modelo NLI diminuto con pesos ALEATORIOS y un
tokenizador entrenado sobre los propios textos. Sus predicciones no tienen
ningún valor; sólo sirve para comprobar que la carga, el pipeline
zero-shot, la medición de tiempos, la conversión de salidas, las métricas y
la exportación funcionan de punta a punta. Los resultados de esta prueba
NUNCA deben reportarse como desempeño de un modelo.
"""

from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors, trainers  # noqa: E402
from transformers import BertConfig, BertForSequenceClassification, PreTrainedTokenizerFast  # noqa: E402

from src.clasificador import cargar_modelo, clasificar_textos, liberar_modelo  # noqa: E402
from src.config import VARIANTES_ETIQUETAS  # noqa: E402
from src.datos import cargar_dataset, separar_particiones  # noqa: E402
from src.evaluacion import (  # noqa: E402
    a_json,
    calcular_metricas,
    evaluar_umbrales,
    invertir_etiquetas,
    resumen_latencia,
    salida_voreko,
    salidas_a_dataframe,
)

RUTA = Path(__file__).resolve().parents[1] / "data" / "reportes_obra_sinteticos.csv"


@pytest.fixture(scope="module")
def modelo_local(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("nli_diminuto")
    df = cargar_dataset(RUTA)
    corpus = df["texto_reporte"].tolist()
    for v in VARIANTES_ETIQUETAS.values():
        corpus += list(v["etiquetas"].values()) + [v["plantilla"]]

    tok = Tokenizer(models.WordPiece(unk_token="[UNK]"))
    tok.normalizer = normalizers.BertNormalizer(lowercase=True)
    tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    tok.train_from_iterator(
        corpus, trainers.WordPieceTrainer(vocab_size=800, special_tokens=["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"])
    )
    tok.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]",
        pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", tok.token_to_id("[CLS]")), ("[SEP]", tok.token_to_id("[SEP]"))],
    )
    fast = PreTrainedTokenizerFast(
        tokenizer_object=tok, unk_token="[UNK]", pad_token="[PAD]", cls_token="[CLS]", sep_token="[SEP]", mask_token="[MASK]"
    )
    fast.save_pretrained(carpeta)

    torch.manual_seed(0)
    cfg = BertConfig(
        vocab_size=fast.vocab_size, hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
        intermediate_size=64, max_position_embeddings=128,
        id2label={0: "contradiction", 1: "neutral", 2: "entailment"},
        label2id={"contradiction": 0, "neutral": 1, "entailment": 2},
    )
    BertForSequenceClassification(cfg).save_pretrained(carpeta)
    return str(carpeta)


def test_flujo_completo(modelo_local, tmp_path):
    df = cargar_dataset(RUTA)
    _, df_eval = separar_particiones(df)
    muestra = df_eval.head(10)

    variante = VARIANTES_ETIQUETAS["B_descriptivas"]
    inverso = invertir_etiquetas(variante["etiquetas"])
    cargado = cargar_modelo("diminuto", modelo_local)
    assert cargado.dtype == "torch.float32"

    r = clasificar_textos(cargado, muestra["texto_reporte"].tolist(), list(variante["etiquetas"].values()),
                          variante["plantilla"], n_calentamiento=1)
    assert len(r["salidas"]) == len(muestra)
    assert all(lat > 0 for lat in r["latencias_s"])

    pred = salidas_a_dataframe(r["salidas"], muestra, inverso, "diminuto", r["latencias_s"])
    m = calcular_metricas(pred["categoria_real"].tolist(), pred["categoria_predicha"].tolist())
    assert 0.0 <= m["accuracy"] <= 1.0
    assert m["matriz_confusion"].values.sum() == len(muestra)
    evaluar_umbrales(m)
    resumen_latencia(r["latencias_s"])

    # Exportación
    salida_csv = tmp_path / "pred.csv"
    pred.to_csv(salida_csv, index=False, encoding="utf-8")
    assert salida_csv.stat().st_size > 0

    reg = salida_voreko(muestra.iloc[0]["texto_reporte"], r["salidas"][0], inverso, "diminuto@local")
    assert '"categoria_predicha"' in a_json([reg])

    liberar_modelo(cargado)
    assert cargado.clasificador is None
