from __future__ import annotations
import numpy as np
from PIL import Image

def count_colors(img: Image.Image, cap: int = 100000) -> int:
    arr = np.array(img.convert("RGBA")).reshape(-1, 4)
    if arr.shape[0] > cap:
        step = max(1, arr.shape[0] // cap)
        arr = arr[::step]
    return int(np.unique(arr, axis=0).shape[0])

def quantize_rgba(img: Image.Image, max_colors: int | None) -> Image.Image:
    if not max_colors:
        return img.convert("RGBA")
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = rgba.convert("RGB").quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out
