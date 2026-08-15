from __future__ import annotations

import base64
import os
import secrets
from io import BytesIO
from pathlib import Path

from PIL import Image

from . import __version__
from .engine import reconstruct
from .learning import LearningLedger
from .models import ContributionEvent, ReconstructionOptions


def _default_root() -> Path:
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/trupixel-data")
    return Path("trupixel-data")


class JobStore:
    def __init__(self, root: str | Path | None = None, ledger: LearningLedger | None = None):
        self.root = Path(root) if root is not None else _default_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger or LearningLedger(self.root / "learning.sqlite3")

    def create_reconstruction(self, src: Image.Image, opts: ReconstructionOptions, share_artwork: bool = False) -> dict:
        job_id = secrets.token_hex(8)
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        result = reconstruct(src, opts)

        result_buffer = BytesIO()
        result.image.save(result_buffer, format="PNG")
        result_bytes = result_buffer.getvalue()
        diff_buffer = BytesIO()
        result.diff.save(diff_buffer, format="PNG")
        diff_bytes = diff_buffer.getvalue()

        (job_dir / "result.png").write_bytes(result_bytes)
        (job_dir / "diff.png").write_bytes(diff_bytes)
        (job_dir / "diagnostics.json").write_text(result.diagnostics.model_dump_json(indent=2), encoding="utf-8")

        artwork_persisted = False
        if share_artwork and not os.getenv("VERCEL"):
            src.convert("RGBA").save(job_dir / "shared-source.png")
            artwork_persisted = True

        recipe_ids = ["core:block-median-v1", "core:palette-mediancut-v1"]
        if opts.cleanup_isolated:
            recipe_ids.append("core:isolated-cleanup-v1")

        event = ContributionEvent(
            event_type="operation",
            engine_version=__version__,
            job_id=job_id,
            operation="reconstruct",
            source_size=result.diagnostics.source_size,
            target_size=result.diagnostics.target_size,
            grid_confidence=result.diagnostics.grid_confidence,
            palette_before=result.diagnostics.palette_before,
            palette_after=result.diagnostics.palette_after,
            changed_pixels=result.diagnostics.changed_pixels_cleanup,
            recipe_ids=recipe_ids,
            artwork_shared=artwork_persisted,
        )
        self.ledger.record(event)

        return {
            "job_id": job_id,
            "diagnostics": result.diagnostics.model_dump(),
            "result_png_base64": base64.b64encode(result_bytes).decode("ascii"),
            "diff_png_base64": base64.b64encode(diff_bytes).decode("ascii"),
            "result_path": str(job_dir / "result.png"),
            "diff_path": str(job_dir / "diff.png"),
            "community_contribution_recorded": True,
            "learning_backend": self.ledger.backend,
            "artwork_shared": artwork_persisted,
            "artwork_share_note": None if not share_artwork or artwork_persisted else "Hosted raw-artwork corpus storage is not enabled yet; only privacy-preserving learning metadata was persisted.",
        }

    def feedback(self, job_id: str, outcome: str, recipe_ids: list[str] | None = None) -> None:
        event = ContributionEvent(
            event_type="feedback",
            engine_version=__version__,
            job_id=job_id,
            operation="feedback",
            recipe_ids=recipe_ids or ["core:block-median-v1", "core:palette-mediancut-v1", "core:isolated-cleanup-v1"],
            outcome=outcome,
        )
        self.ledger.record(event)
