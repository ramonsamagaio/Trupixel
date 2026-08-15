from __future__ import annotations

from io import BytesIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

from .jobs import JobStore
from .models import ReconstructionOptions

app = FastAPI(title="TruPixel", version="0.1.1", description="Headless pixel-art reconstruction with privacy-preserving community learning.")
store = JobStore()


@app.get("/")
def home():
    return {
        "ok": True,
        "service": "trupixel",
        "version": "0.1.1",
        "health": "/health",
        "docs": "/docs",
        "mcp": "/mcp",
        "learning_backend": store.ledger.backend,
    }


@app.get("/health")
def health():
    return {"ok": True, "service": "trupixel", "learning_backend": store.ledger.backend}


@app.post("/v1/reconstruct")
async def reconstruct_endpoint(
    image: UploadFile = File(...),
    target_width: int | None = Form(None),
    target_height: int | None = Form(None),
    max_palette: int = Form(32),
    cleanup_isolated: bool = Form(True),
    share_artwork: bool = Form(False),
):
    raw = await image.read()
    try:
        src = Image.open(BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        raise HTTPException(400, f"Invalid image: {exc}") from exc

    opts = ReconstructionOptions(
        target_width=target_width,
        target_height=target_height,
        max_palette=max_palette,
        cleanup_isolated=cleanup_isolated,
    )
    return store.create_reconstruction(src, opts, share_artwork=share_artwork)


@app.get("/v1/jobs/{job_id}/result")
def job_result(job_id: str):
    path = store.root / job_id / "result.png"
    if not path.exists():
        raise HTTPException(404, "Ephemeral result not found. Use result_png_base64 returned by the reconstruct request.")
    return FileResponse(path, media_type="image/png", filename=f"{job_id}.png")


@app.get("/v1/jobs/{job_id}/diff")
def job_diff(job_id: str):
    path = store.root / job_id / "diff.png"
    if not path.exists():
        raise HTTPException(404, "Ephemeral diff not found. Use diff_png_base64 returned by the reconstruct request.")
    return FileResponse(path, media_type="image/png", filename=f"{job_id}-diff.png")


@app.post("/v1/jobs/{job_id}/feedback")
def feedback(job_id: str, outcome: str = Form(...)):
    if outcome not in {"accepted", "rejected", "reverted"}:
        raise HTTPException(400, "outcome must be accepted, rejected, or reverted")
    store.feedback(job_id, outcome)
    return {"ok": True, "community_contribution_recorded": True, "learning_backend": store.ledger.backend}


@app.get("/v1/community/recipes")
def recipe_stats():
    return {"recipes": store.ledger.recipe_stats(), "learning_backend": store.ledger.backend}
