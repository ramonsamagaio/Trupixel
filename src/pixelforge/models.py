from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal

class ReconstructionOptions(BaseModel):
    target_width: int | None = Field(default=None, ge=1, le=4096)
    target_height: int | None = Field(default=None, ge=1, le=4096)
    max_palette: int | None = Field(default=32, ge=2, le=256)
    cleanup_isolated: bool = True
    isolated_threshold: int = Field(default=1, ge=0, le=8)
    preserve_alpha: bool = True

class GridCandidate(BaseModel):
    width: int
    height: int
    scale_x: float
    scale_y: float
    confidence: float

class Diagnostics(BaseModel):
    source_size: tuple[int, int]
    target_size: tuple[int, int]
    inferred: bool
    grid_confidence: float
    palette_before: int
    palette_after: int
    changed_pixels_cleanup: int
    changed_ratio_from_nearest: float
    warnings: list[str] = []

class ContributionEvent(BaseModel):
    event_type: str
    engine_version: str
    job_id: str
    operation: str
    source_size: tuple[int, int] | None = None
    target_size: tuple[int, int] | None = None
    grid_confidence: float | None = None
    palette_before: int | None = None
    palette_after: int | None = None
    changed_pixels: int | None = None
    recipe_ids: list[str] = []
    outcome: Literal["unknown", "accepted", "rejected", "reverted"] = "unknown"
    artwork_shared: bool = False
