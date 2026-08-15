from __future__ import annotations

import base64
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from .jobs import JobStore
from .models import ReconstructionOptions
from .web_ui import HTML

app = FastAPI(title="TruPixel Web", version="0.3.0")
store = JobStore()

MAX_BATCH_FILES = 8
MAX_SHEET_FRAMES = 64
MAX_UPLOAD_BYTES = 12 * 1024 * 1024


def _decode_png_b64(value: str) -> Image.Image:
    return Image.open(BytesIO(base64.b64decode(value))).convert("RGBA")


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _png_b64(image: Image.Image) -> str:
    return base64.b64encode(_png_bytes(image)).decode("ascii")


def _zip_b64(files: list[tuple[str, bytes]]) -> str:
    buf = BytesIO()
    with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
        for name, payload in files:
            zf.writestr(name, payload)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _safe_stem(filename: str | None, fallback: str) -> str:
    raw = (filename or fallback).rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = raw.rsplit(".", 1)[0] or fallback
    clean = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
    return clean[:80] or fallback


def _crop_transparent_margins(image: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return rgba, {"cropped": False, "reason": "fully_transparent"}
    if bbox == (0, 0, rgba.width, rgba.height):
        return rgba, {"cropped": False, "reason": "no_transparent_margin"}
    cropped = rgba.crop(bbox)
    return cropped, {
        "cropped": True,
        "bbox": list(bbox),
        "before": [rgba.width, rgba.height],
        "after": [cropped.width, cropped.height],
    }


async def _read_upload(upload: UploadFile) -> Image.Image:
    raw = await upload.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Arquivo maior que 12 MB.")
    try:
        return Image.open(BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Imagem inválida: {exc}") from exc


def _run_one(
    image: Image.Image,
    opts: ReconstructionOptions,
    *,
    auto_crop: bool,
    filename: str | None,
) -> dict[str, Any]:
    crop_info: dict[str, Any] = {"cropped": False, "reason": "disabled"}
    source = image
    if auto_crop:
        source, crop_info = _crop_transparent_margins(source)

    job = store.create_reconstruction(source, opts, share_artwork=False)
    return {
        "filename": filename,
        "job_id": job["job_id"],
        "result_png_base64": job["result_png_base64"],
        "diff_png_base64": job["diff_png_base64"],
        "diagnostics": {
            **job["diagnostics"],
            "auto_crop": crop_info,
            "learning_backend": job["learning_backend"],
            "community_contribution_recorded": job["community_contribution_recorded"],
        },
    }


@app.get("/", response_class=HTMLResponse)
async def home(status: int | None = Query(default=None)):
    if status == 1:
        return JSONResponse(
            {
                "ok": True,
                "service": "trupixel-web",
                "version": "0.3.0",
                "learning_backend": store.ledger.backend,
                "community_learning_required_online": True,
                "mcp_endpoint": "/api/mcp",
            }
        )
    return HTML


@app.post("/")
async def action_endpoint(
    action: str = Form(default="reconstruct"),
    images: list[UploadFile] | None = File(default=None),
    mode: str = Form(default="single"),
    target_width: int | None = Form(default=None),
    target_height: int | None = Form(default=None),
    max_palette: int = Form(default=32),
    cleanup_isolated: bool = Form(default=True),
    auto_crop: bool = Form(default=True),
    frame_width: int | None = Form(default=None),
    frame_height: int | None = Form(default=None),
    job_ids: str | None = Form(default=None),
    outcome: str | None = Form(default=None),
):
    if action == "feedback":
        if outcome not in {"accepted", "rejected", "reverted"}:
            raise HTTPException(status_code=400, detail="Feedback inválido.")
        ids = [item.strip() for item in (job_ids or "").split(",") if item.strip()]
        if not ids:
            raise HTTPException(status_code=400, detail="Nenhum job_id informado.")
        for job_id in ids[:MAX_SHEET_FRAMES]:
            store.feedback(job_id, outcome)
        return {
            "ok": True,
            "feedback_recorded": len(ids[:MAX_SHEET_FRAMES]),
            "learning_backend": store.ledger.backend,
        }

    uploads = images or []
    if not uploads:
        raise HTTPException(status_code=400, detail="Selecione pelo menos uma imagem.")

    opts = ReconstructionOptions(
        target_width=target_width,
        target_height=target_height,
        max_palette=max_palette,
        cleanup_isolated=cleanup_isolated,
    )

    if mode == "batch":
        if len(uploads) > MAX_BATCH_FILES:
            raise HTTPException(status_code=400, detail=f"O batch aceita no máximo {MAX_BATCH_FILES} imagens por vez.")

        results = []
        zip_files: list[tuple[str, bytes]] = []
        for index, upload in enumerate(uploads):
            image = await _read_upload(upload)
            item = _run_one(image, opts, auto_crop=auto_crop, filename=upload.filename)
            stem = _safe_stem(upload.filename, f"image_{index+1}")
            zip_files.append((f"{stem}_trupixel.png", base64.b64decode(item["result_png_base64"])))
            zip_files.append((f"{stem}_diff.png", base64.b64decode(item["diff_png_base64"])))
            results.append(item)

        return {
            "mode": "batch",
            "results": results,
            "batch_zip_base64": _zip_b64(zip_files),
            "job_ids": [item["job_id"] for item in results],
            "learning_backend": store.ledger.backend,
            "community_contribution_recorded": True,
        }

    source_upload = uploads[0]
    source = await _read_upload(source_upload)

    if mode == "sheet":
        if not frame_width or not frame_height:
            raise HTTPException(status_code=400, detail="No modo spritesheet, informe frame width e frame height.")
        if frame_width <= 0 or frame_height <= 0:
            raise HTTPException(status_code=400, detail="Frame width e frame height devem ser maiores que zero.")
        if source.width % frame_width != 0 or source.height % frame_height != 0:
            raise HTTPException(status_code=400, detail="A spritesheet não divide exatamente pelo tamanho de frame informado.")

        cols = source.width // frame_width
        rows = source.height // frame_height
        total = cols * rows
        if total > MAX_SHEET_FRAMES:
            raise HTTPException(status_code=400, detail=f"A spritesheet pode ter no máximo {MAX_SHEET_FRAMES} frames por processamento.")

        processed = []
        frame_zip: list[tuple[str, bytes]] = []
        for row in range(rows):
            for col in range(cols):
                idx = row * cols + col
                box = (
                    col * frame_width,
                    row * frame_height,
                    (col + 1) * frame_width,
                    (row + 1) * frame_height,
                )
                frame = source.crop(box).convert("RGBA")
                item = _run_one(frame, opts, auto_crop=False, filename=f"frame_{idx:03d}.png")
                processed.append(item)
                frame_zip.append((f"frame_{idx:03d}.png", base64.b64decode(item["result_png_base64"])))

        first_img = _decode_png_b64(processed[0]["result_png_base64"])
        out_fw, out_fh = first_img.size
        stitched = Image.new("RGBA", (out_fw * cols, out_fh * rows), (0, 0, 0, 0))
        stitched_diff = Image.new("RGBA", stitched.size, (0, 0, 0, 0))

        for idx, item in enumerate(processed):
            row, col = divmod(idx, cols)
            stitched.paste(_decode_png_b64(item["result_png_base64"]), (col * out_fw, row * out_fh))
            stitched_diff.paste(_decode_png_b64(item["diff_png_base64"]), (col * out_fw, row * out_fh))

        frame_zip.append(("spritesheet_trupixel.png", _png_bytes(stitched)))
        frame_zip.append(("spritesheet_diff.png", _png_bytes(stitched_diff)))

        avg_conf = sum(float(item["diagnostics"].get("grid_confidence", 0.0)) for item in processed) / len(processed)
        diagnostics = {
            "mode": "spritesheet",
            "source_size": [source.width, source.height],
            "frames": total,
            "grid": {"columns": cols, "rows": rows, "frame_width": frame_width, "frame_height": frame_height},
            "frame_output_size": [out_fw, out_fh],
            "target_size": [stitched.width, stitched.height],
            "grid_confidence_average": avg_conf,
            "learning_backend": store.ledger.backend,
            "community_contribution_recorded": True,
            "job_ids": [item["job_id"] for item in processed],
        }

        return {
            "mode": "spritesheet",
            "result_png_base64": _png_b64(stitched),
            "diff_png_base64": _png_b64(stitched_diff),
            "frames_zip_base64": _zip_b64(frame_zip),
            "diagnostics": diagnostics,
            "job_ids": diagnostics["job_ids"],
        }

    item = _run_one(source, opts, auto_crop=auto_crop, filename=source_upload.filename)
    return {
        "mode": "single",
        **item,
        "job_ids": [item["job_id"]],
    }
