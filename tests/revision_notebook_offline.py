# -*- coding: utf-8 -*-
"""
revision_notebook_offline.py
============================
Arnés de revisión técnica: ejecuta el notebook COMPLETO sin Internet ni GPU,
sustituyendo los tres modelos por modelos NLI diminutos con pesos ALEATORIOS.
Comprueba que todas las celdas corren y que las 18 verificaciones finales
pasan. Sus métricas no significan nada y NUNCA deben reportarse.

    python tests/revision_notebook_offline.py
"""
import sys, shutil, json
from pathlib import Path
import nbformat
from nbclient import NotebookClient
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import torch
from tokenizers import Tokenizer, models, normalizers, pre_tokenizers, processors, trainers
from transformers import BertConfig, BertForSequenceClassification, PreTrainedTokenizerFast
import pandas as pd


import tempfile
W = Path(tempfile.mkdtemp(prefix="voreko_revision_"))
print("Carpeta de trabajo:", W)
df = pd.read_csv(REPO/"data/reportes_obra_sinteticos.csv")
corpus = df.texto_reporte.tolist() + ["En este reporte de obra se describe", "Este reporte de obra trata sobre"]
paths = []
for k, (h, L) in enumerate([(32, 1), (48, 2), (64, 3)]):
    d = W/f"tiny{k}"
    tok = Tokenizer(models.WordPiece(unk_token="[UNK]")); tok.normalizer = normalizers.BertNormalizer(lowercase=True)
    tok.pre_tokenizer = pre_tokenizers.BertPreTokenizer()
    tok.train_from_iterator(corpus, trainers.WordPieceTrainer(vocab_size=800, special_tokens=["[PAD]","[UNK]","[CLS]","[SEP]","[MASK]"]))
    tok.post_processor = processors.TemplateProcessing(single="[CLS] $A [SEP]", pair="[CLS] $A [SEP] $B:1 [SEP]:1",
        special_tokens=[("[CLS]", tok.token_to_id("[CLS]")), ("[SEP]", tok.token_to_id("[SEP]"))])
    f = PreTrainedTokenizerFast(tokenizer_object=tok, unk_token="[UNK]", pad_token="[PAD]", cls_token="[CLS]", sep_token="[SEP]", mask_token="[MASK]")
    f.save_pretrained(d); torch.manual_seed(k)
    BertForSequenceClassification(BertConfig(vocab_size=f.vocab_size, hidden_size=h, num_hidden_layers=L, num_attention_heads=2,
        intermediate_size=2*h, max_position_embeddings=128, id2label={0:"contradiction",1:"neutral",2:"entailment"},
        label2id={"contradiction":0,"neutral":1,"entailment":2})).save_pretrained(d)
    paths.append(str(d))

nb = nbformat.read(REPO/"notebooks/VOREKO_IA_comparacion_modelos.ipynb", 4)
ids = ["MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", "joeddav/xlm-roberta-large-xnli"]
for c in nb.cells:
    if c.cell_type != "code": continue
    if c.source.startswith("%pip"):
        c.source = "\n".join(l for l in c.source.split("\n") if not l.startswith("%pip"))
    elif c.source.startswith("%%writefile src/config.py"):
        for i, p in zip(ids, paths): c.source = c.source.replace(f'"{i}"', f'"{p}"')
    elif "api = HfApi()" in c.source:
        c.source = ("from src.config import MODELOS\n# STUB OFFLINE\ninfo_hub = {n: {'id': m['id'], 'licencia': 'mit', 'sha': None} for n, m in MODELOS.items()}\n"
                    "Path('results/modelos_hub.json').write_text(json.dumps(info_hub))")
client = NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(W)}})
try:
    client.execute()
    print("EJECUCION COMPLETA")
finally:
    nbformat.write(nb, W/"ejecutado.ipynb")
