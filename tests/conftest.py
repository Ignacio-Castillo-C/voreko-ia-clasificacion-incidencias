# Permite ejecutar `pytest` desde la raíz del repositorio importando `src.*`
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
