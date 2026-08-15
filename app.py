from __future__ import annotations

import sys
from pathlib import Path

# Vercel detects this root-level FastAPI/ASGI entrypoint. The project itself
# keeps a src/ layout for normal packaging and local development.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pixelforge.web import app  # noqa: E402,F401
