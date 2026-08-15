from __future__ import annotations

import base64
import os
from io import BytesIO

from PIL import Image
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from .grid import infer_grid
from .jobs import JobStore
from .models import ReconstructionOptions

mcp = MCPServer(
    "TruPixel",
    instructions=(
        "Use TruPixel for deterministic pixel-art reconstruction. "
        "Every hosted reconstruction contributes privacy-preserving effectiveness metadata "
        "to the community learning ledger. Raw artwork is never added to a shared corpus "
        "unless explicit artwork-sharing support is enabled and the user opts in."
    ),
)
store = JobStore()


def _public_hosts() -> list[str]:
    hosts = {
        "localhost:*",
        "127.0.0.1:*",
        "trupixel.vercel.app",
        "trupixel-shinebright1.vercel.app",
        "trupixel-git-main-shinebright1.vercel.app",
    }
    for key in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL"):
        value = os.getenv(key)
        if value:
            hosts.add(value.removeprefix("https://").removeprefix("http://").rstrip("/"))
    return sorted(hosts)


def _allowed_origins() -> list[str]:
    origins = {
        "http://localhost:*",
        "http://127.0.0.1:*",
        "https://chatgpt.com",
        "https://chat.openai.com",
        "https://trupixel.vercel.app",
        "https://trupixel-shinebright1.vercel.app",
    }
    for key in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_BRANCH_URL"):
        value = os.getenv(key)
        if value:
            host = value.removeprefix("https://").removeprefix("http://").rstrip("/")
            origins.add(f"https://{host}")
    extra = os.getenv("TRUPIXEL_ALLOWED_ORIGINS")
    if extra:
        origins.update(item.strip() for item in extra.split(",") if item.strip())
    return sorted(origins)


transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=_public_hosts(),
    allowed_origins=_allowed_origins(),
)


@mcp.tool()
def server_status() -> dict:
    """Return TruPixel deployment and community-learning status."""
    return {
        "ok": True,
        "service": "trupixel",
        "version": "0.1.1",
        "learning_backend": store.ledger.backend,
        "community_learning_required_online": True,
    }


@mcp.tool()
def analyze_grid(image_base64: str, top_k: int = 8) -> dict:
    """Infer likely logical pixel grids from a base64-encoded PNG/JPEG/WebP."""
    raw = base64.b64decode(image_base64)
    img = Image.open(BytesIO(raw)).convert("RGBA")
    return {"candidates": [candidate.model_dump() for candidate in infer_grid(img, top_k=top_k)]}


@mcp.tool()
def reconstruct_pixel_art(
    image_base64: str,
    target_width: int | None = None,
    target_height: int | None = None,
    max_palette: int = 32,
    cleanup_isolated: bool = True,
    share_artwork: bool = False,
) -> dict:
    """Reconstruct an image as true pixel art and return result/diff PNGs as base64."""
    raw = base64.b64decode(image_base64)
    src = Image.open(BytesIO(raw)).convert("RGBA")
    opts = ReconstructionOptions(
        target_width=target_width,
        target_height=target_height,
        max_palette=max_palette,
        cleanup_isolated=cleanup_isolated,
    )
    job = store.create_reconstruction(src, opts, share_artwork=share_artwork)
    return {
        "job_id": job["job_id"],
        "diagnostics": job["diagnostics"],
        "result_png_base64": job["result_png_base64"],
        "diff_png_base64": job["diff_png_base64"],
        "community_contribution_recorded": True,
        "learning_backend": job["learning_backend"],
        "artwork_shared": job["artwork_shared"],
        "artwork_share_note": job["artwork_share_note"],
    }


@mcp.tool()
def rate_result(job_id: str, outcome: str) -> dict:
    """Record accepted, rejected or reverted feedback, improving recipe ranking."""
    if outcome not in {"accepted", "rejected", "reverted"}:
        raise ValueError("outcome must be accepted, rejected, or reverted")
    store.feedback(job_id, outcome)
    return {"ok": True, "community_contribution_recorded": True, "learning_backend": store.ledger.backend}


@mcp.tool()
def community_recipe_stats() -> dict:
    """Return aggregate effectiveness of reconstruction and cleanup recipes."""
    return {"recipes": store.ledger.recipe_stats(), "learning_backend": store.ledger.backend}


def create_http_app(streamable_http_path: str = "/api"):
    """Build the production ASGI app for Vercel or another ASGI host."""
    return mcp.streamable_http_app(
        streamable_http_path=streamable_http_path,
        json_response=True,
        stateless_http=True,
        transport_security=transport_security,
        host="0.0.0.0",
    )


if __name__ == "__main__":
    mcp.run(
        "streamable-http",
        host="0.0.0.0",
        port=8000,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=transport_security,
    )
