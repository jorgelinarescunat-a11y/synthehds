"""Configuración compartida de tests: asegura que `app/` esté en sys.path
para poder importar como `from app.generators... import ...`."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]   # …/backend
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
