from __future__ import annotations
import argparse, json
from PIL import Image
from .engine import reconstruct
from .models import ReconstructionOptions

def main():
    p = argparse.ArgumentParser(prog="pixelforge")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reconstruct")
    r.add_argument("input")
    r.add_argument("--target", help="e.g. 64x64")
    r.add_argument("--palette", type=int, default=32)
    r.add_argument("--out", required=True)
    r.add_argument("--diff")
    args = p.parse_args()

    if args.cmd == "reconstruct":
        tw = th = None
        if args.target:
            tw, th = map(int, args.target.lower().split("x"))
        src = Image.open(args.input).convert("RGBA")
        res = reconstruct(src, ReconstructionOptions(
            target_width=tw, target_height=th, max_palette=args.palette
        ))
        res.image.save(args.out)
        if args.diff:
            res.diff.save(args.diff)
        print(res.diagnostics.model_dump_json(indent=2))
