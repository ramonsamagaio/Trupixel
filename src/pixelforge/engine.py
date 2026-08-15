from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
import numpy as np
from PIL import Image, ImageChops
from . import __version__
from .models import ReconstructionOptions, Diagnostics
from .grid import infer_grid
from .palette import count_colors, quantize_rgba
from .cleanup import cleanup_isolated_pixels

@dataclass
class ReconstructionResult:
    image: Image.Image
    diff: Image.Image
    diagnostics: Diagnostics

def _block_reconstruct(src: Image.Image, tw: int, th: int) -> Image.Image:
    rgba = np.asarray(src.convert("RGBA"), dtype=np.uint8)
    h, w = rgba.shape[:2]
    x_edges = np.linspace(0, w, tw + 1)
    y_edges = np.linspace(0, h, th + 1)
    out = np.zeros((th, tw, 4), dtype=np.uint8)
    for ty in range(th):
        y0 = int(np.floor(y_edges[ty])); y1 = max(y0 + 1, int(np.ceil(y_edges[ty + 1])))
        for tx in range(tw):
            x0 = int(np.floor(x_edges[tx])); x1 = max(x0 + 1, int(np.ceil(x_edges[tx + 1])))
            block = rgba[y0:min(y1,h), x0:min(x1,w)].reshape(-1, 4)
            if block.size == 0: continue
            alpha_nonzero = block[:, 3] > 8
            if alpha_nonzero.mean() < 0.35:
                out[ty, tx] = (0, 0, 0, 0); continue
            out[ty, tx] = np.median(block[alpha_nonzero], axis=0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")

def reconstruct(src: Image.Image, opts: ReconstructionOptions) -> ReconstructionResult:
    src = src.convert("RGBA"); sw, sh = src.size
    inferred = False; confidence = 1.0
    if opts.target_width and opts.target_height:
        tw, th = opts.target_width, opts.target_height
    else:
        candidates = infer_grid(src)
        if candidates:
            best = candidates[0]; tw, th = best.width, best.height; confidence = best.confidence; inferred = True
        else:
            tw, th = max(1, sw // 8), max(1, sh // 8); confidence = 0.0; inferred = True
    base = _block_reconstruct(src, tw, th)
    palette_before = count_colors(base)
    out = quantize_rgba(base, opts.max_palette)
    changed_cleanup = 0
    if opts.cleanup_isolated:
        out, changed_cleanup = cleanup_isolated_pixels(out, opts.isolated_threshold)
    palette_after = count_colors(out)
    nearest = src.resize((tw, th), Image.Resampling.NEAREST)
    diff = ImageChops.difference(out, nearest.convert("RGBA"))
    d = np.asarray(diff); changed_ratio = float(np.any(d != 0, axis=2).mean())
    warnings = []
    if inferred and confidence < 0.25: warnings.append("Low grid confidence; specify target dimensions for production use.")
    if palette_after > 64: warnings.append("Large palette for pixel art; consider a smaller max_palette.")
    diag = Diagnostics(source_size=(sw, sh), target_size=(tw, th), inferred=inferred, grid_confidence=confidence, palette_before=palette_before, palette_after=palette_after, changed_pixels_cleanup=changed_cleanup, changed_ratio_from_nearest=changed_ratio, warnings=warnings)
    return ReconstructionResult(image=out, diff=diff, diagnostics=diag)
