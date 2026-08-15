from __future__ import annotations
import numpy as np
from PIL import Image

_NEIGHBORS = [(-1,0),(1,0),(0,-1),(0,1)]

def cleanup_isolated_pixels(img: Image.Image, threshold: int = 1) -> tuple[Image.Image, int]:
    arr = np.array(img.convert("RGBA"))
    h, w = arr.shape[:2]
    out = arr.copy()
    changed = 0

    for y in range(h):
        for x in range(w):
            px = arr[y, x]
            if px[3] == 0:
                continue
            neigh = []
            same = 0
            for dx, dy in _NEIGHBORS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    n = arr[ny, nx]
                    if n[3] > 0:
                        neigh.append(n)
                        if np.array_equal(n, px):
                            same += 1
            if same > threshold or len(neigh) < 2:
                continue

            # Only replace if a neighbor color clearly dominates.
            counts = {}
            for n in neigh:
                key = tuple(int(v) for v in n)
                counts[key] = counts.get(key, 0) + 1
            best, nbest = max(counts.items(), key=lambda kv: kv[1])
            if nbest >= 3 and best != tuple(int(v) for v in px):
                out[y, x] = np.array(best, dtype=np.uint8)
                changed += 1

    return Image.fromarray(out, "RGBA"), changed
