from __future__ import annotations
import secrets
from pathlib import Path
from PIL import Image
from .engine import reconstruct
from .models import ReconstructionOptions, ContributionEvent
from .learning import LearningLedger
from . import __version__

class JobStore:
    def __init__(self, root: str | Path = "pixelforge-data", ledger: LearningLedger | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = ledger or LearningLedger(self.root / "learning.sqlite3")

    def create_reconstruction(self, src: Image.Image, opts: ReconstructionOptions, share_artwork: bool = False) -> dict:
        job_id = secrets.token_hex(8)
        job_dir = self.root / job_id
        job_dir.mkdir()
        result = reconstruct(src, opts)
        result.image.save(job_dir / "result.png")
        result.diff.save(job_dir / "diff.png")
        (job_dir / "diagnostics.json").write_text(result.diagnostics.model_dump_json(indent=2), encoding="utf-8")
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
            recipe_ids=["core:block-median-v1", "core:palette-mediancut-v1"] + (["core:isolated-cleanup-v1"] if opts.cleanup_isolated else []),
            artwork_shared=share_artwork,
        )
        self.ledger.record(event)
        if share_artwork:
            src.convert("RGBA").save(job_dir / "shared-source.png")
        return {"job_id": job_id, "diagnostics": result.diagnostics.model_dump(), "result_path": str(job_dir / "result.png"), "diff_path": str(job_dir / "diff.png")}

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
