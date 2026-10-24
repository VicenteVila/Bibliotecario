import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_RAIZ = Path(__file__).resolve().parents[1]
if (_RAIZ_WS := _RAIZ / "workspace").is_dir():
    sys.path.insert(0, str(_RAIZ_WS))
