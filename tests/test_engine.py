from PIL import Image
from pixelforge.engine import reconstruct
from pixelforge.models import ReconstructionOptions

def test_reconstruct_exact_target():
    src = Image.new("RGBA", (64, 64), (0,0,0,0))
    for y in range(16, 48):
        for x in range(16, 48):
            src.putpixel((x,y), (100 + x % 3, 120, 80, 255))
    res = reconstruct(src, ReconstructionOptions(target_width=16, target_height=16, max_palette=8))
    assert res.image.size == (16,16)
    assert res.diagnostics.target_size == (16,16)
    assert res.diagnostics.palette_after <= 8

def test_inference_returns_something():
    src = Image.new("RGBA", (128, 128), (10,20,30,255))
    res = reconstruct(src, ReconstructionOptions(max_palette=8))
    assert res.image.width > 0
    assert res.image.height > 0
