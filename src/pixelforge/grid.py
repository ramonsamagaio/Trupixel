from __future__ import annotations
import numpy as np
from PIL import Image
from .models import GridCandidate

def _gradient_signal(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb = arr[..., :3].astype(np.float32)
    gx = np.mean(np.abs(rgb[:, 1:] - rgb[:, :-1]), axis=(0, 2))
    gy = np.mean(np.abs(rgb[1:, :] - rgb[:-1, :]), axis=(1, 2))
    return gx, gy

def _period_score(signal: np.ndarray, period: int) -> float:
    if period <= 1 or signal.size < period * 2: return 0.0
    idx = np.arange(signal.size)
    edge = signal[(idx + 1) % period == 0]; inner = signal[(idx + 1) % period != 0]
    if edge.size == 0 or inner.size == 0: return 0.0
    e = float(edge.mean()); i = float(inner.mean()) + 1e-6
    contrast = max(0.0, (e - i) / (e + i + 1e-6))
    regularity = 1.0 / (1.0 + float(edge.std()) / (e + 1e-6))
    return contrast * 0.75 + regularity * 0.25

def infer_grid(image: Image.Image, top_k: int = 8) -> list[GridCandidate]:
    rgba = np.array(image.convert("RGBA")); h, w = rgba.shape[:2]; gx, gy = _gradient_signal(rgba)
    candidates = []
    max_scale = min(64, w, h)
    for sx in range(2, max_scale + 1):
        if w % sx != 0: continue
        for sy in range(max(2, sx - 1), min(max_scale, sx + 1) + 1):
            if h % sy != 0: continue
            wx, hy = w // sx, h // sy
            if wx < 4 or hy < 4: continue
            score_x, score_y = _period_score(gx, sx), _period_score(gy, sy)
            isotropy = 1.0 - min(1.0, abs(sx - sy) / max(sx, sy))
            score = (score_x + score_y) * 0.45 + isotropy * 0.10
            candidates.append(GridCandidate(width=wx, height=hy, scale_x=float(sx), scale_y=float(sy), confidence=max(0.0, min(1.0, score))))
    for tw in (16, 24, 32, 48, 64, 96, 128, 256):
        if w % tw == 0:
            scale = w / tw; th = int(round(h / scale))
            if th >= 4 and abs(th * scale - h) < 1e-6:
                candidates.append(GridCandidate(width=tw, height=th, scale_x=scale, scale_y=scale, confidence=0.12))
    dedup = {}
    for c in candidates:
        key = (c.width, c.height)
        if key not in dedup or c.confidence > dedup[key].confidence: dedup[key] = c
    return sorted(dedup.values(), key=lambda c: c.confidence, reverse=True)[:top_k]
