from __future__ import annotations
import base64
from io import BytesIO
from PIL import Image
from mcp.server import MCPServer
from .jobs import JobStore
from .models import ReconstructionOptions
from .grid import infer_grid

mcp = MCPServer(
    "TruPixel",
    instructions=(
        "Use TruPixel for deterministic pixel-art reconstruction. "
        "Hosted operations always contribute privacy-preserving effectiveness metadata "
        "to the community learning ledger. Raw artwork is never shared unless share_artwork=true."
    ),
)
store = JobStore()

@mcp.tool()
def analyze_grid(image_base64: str, top_k: int = 8) -> dict:
    """Infer likely logical pixel grids from a base64-encoded PNG/JPEG/WebP."""
    raw = base64.b64decode(image_base64)
    img = Image.open(BytesIO(raw)).convert("RGBA")
    return {"candidates": [c.model_dump() for c in infer_grid(img, top_k=top_k)]}

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
    opts = ReconstructionOptions(target_width=target_width, target_height=target_height, max_palette=max_palette, cleanup_isolated=cleanup_isolated)
    job = store.create_reconstruction(src, opts, share_artwork=share_artwork)
    result_bytes = open(job["result_path"], "rb").read()
    diff_bytes = open(job["diff_path"], "rb").read()
    return {
        "job_id": job["job_id"],
        "diagnostics": job["diagnostics"],
        "result_png_base64": base64.b64encode(result_bytes).decode("ascii"),
        "diff_png_base64": base64.b64encode(diff_bytes).decode("ascii"),
        "community_contribution_recorded": True,
        "artwork_shared": share_artwork,
    }

@mcp.tool()
def rate_result(job_id: str, outcome: str) -> dict:
    """Record accepted, rejected or reverted feedback, improving recipe ranking."""
    if outcome not in {"accepted", "rejected", "reverted"}: raise ValueError("outcome must be accepted, rejected, or reverted")
    store.feedback(job_id, outcome)
    return {"ok": True, "community_contribution_recorded": True}

@mcp.tool()
def community_recipe_stats() -> dict:
    """Return aggregate effectiveness of reconstruction and cleanup recipes."""
    return {"recipes": store.ledger.recipe_stats()}

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, stateless_http=True, json_response=True)
