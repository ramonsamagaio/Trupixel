# PixelForge

PixelForge is a headless pixel-art reconstruction engine designed for AI agents, web apps,
MCP clients, and Pixelorama-compatible workflows.

The first goal is simple:

> Take an image that visually imitates pixel art, infer its underlying logical grid, rebuild
> it as actual pixel-perfect art, then perform deterministic cleanup passes.

## What is already in this MVP

- automatic logical-grid hypothesis scoring;
- explicit target-size reconstruction;
- block-color reconstruction with alpha support;
- palette reduction;
- isolated-pixel cleanup;
- diagonal/jaggy diagnostics;
- before/after/diff export;
- job diagnostics as JSON;
- FastAPI service;
- MCP server surface;
- SQLite learning ledger;
- community recipe scoring;
- required non-content contribution events for hosted/online operations;
- optional explicit sharing of artwork for public datasets;
- `SKILL.md` describing how an AI should use the engine.

## Privacy / community learning model

Online use contributes to PixelForge's learning loop, but **raw artwork is private by default**.

Every hosted operation records a minimal contribution event such as:

- engine version;
- operation/pass names;
- source and target dimensions;
- inferred-grid confidence;
- palette size before/after;
- amount of changed pixels;
- recipe IDs used;
- acceptance/rejection if the user later provides feedback.

It does **not** upload/store the source image as a training example unless the user explicitly
enables `share_artwork=true`.

This gives the community a useful mandatory contribution without quietly harvesting artists' files.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

pixelforge reconstruct input.png --target 64x64 --out output.png
```

Run the web API:

```bash
uvicorn pixelforge.api:app --host 0.0.0.0 --port 8080
```

Run MCP:

```bash
python -m pixelforge.mcp_server
```

## Hosted architecture

```text
ChatGPT / Claude / Gemini / Hermes / custom client
                    |
                    | MCP / HTTPS
                    v
             PixelForge Server
      +-------------+-------------+
      |                           |
 Reconstruction Engine      Learning Ledger
      |                           |
      v                           v
 PNG / spritesheet        recipe effectiveness
 diagnostics/diff         anonymous usage signals
```

## Important design rule

The model decides *what should change*.
PixelForge performs pixel operations deterministically.

That avoids making thousands of individual model tool calls for a single sprite.

## Status

This is an MVP foundation, not a finished replacement for Pixelorama.
The next major milestone is temporal animation stabilization and `.pxo` import/export.
