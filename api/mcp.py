from __future__ import annotations

import sys
from pathlib import Path

from starlette.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pixelforge.mcp_server import create_http_app, store  # noqa: E402

mcp_app = create_http_app("/api/mcp")


class TruPixelMCPVercelApp:
    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") == "http"
            and scope.get("method") == "GET"
            and b"status=1" in scope.get("query_string", b"")
        ):
            response = JSONResponse(
                {
                    "ok": True,
                    "service": "trupixel-mcp",
                    "mcp_endpoint": "/api/mcp",
                    "learning_backend": store.ledger.backend,
                    "community_learning_required_online": True,
                }
            )
            await response(scope, receive, send)
            return

        await mcp_app(scope, receive, send)


app = TruPixelMCPVercelApp()
