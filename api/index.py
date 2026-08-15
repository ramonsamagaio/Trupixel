from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixelforge.web import app as trupixel_app  # noqa: E402

# Vercel routes api/index.py as the catch-all Python Function for /api/*.
# Mounting at /api preserves TruPixel's internal paths (/health, /mcp, ...).
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", trupixel_app)
