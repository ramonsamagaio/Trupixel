# TruPixel

TruPixel is a headless pixel-art reconstruction engine designed for AI agents, web apps, MCP clients, and Pixelorama-compatible workflows.

The first goal is simple:

> Take an image that visually imitates pixel art, infer its underlying logical grid, rebuild it as actual pixel-perfect art, then perform deterministic cleanup passes.

## What is already in this MVP

- automatic logical-grid hypothesis scoring;
- explicit target-size reconstruction;
- block-color reconstruction with alpha support;
- palette reduction;
- isolated-pixel cleanup;
- before/after/diff export;
- job diagnostics as JSON;
- FastAPI service;
- remote MCP server surface;
- SQLite learning ledger;
- community recipe scoring;
- required non-content contribution events for hosted/online operations;
- optional explicit sharing of artwork for public datasets;
- `skill/SKILL.md` describing how an AI should use the engine.

## Privacy / community learning model

Online use contributes to TruPixel's learning loop, but **raw artwork is private by default**.

Every hosted operation records a minimal contribution event such as engine version, passes used, source/target dimensions, grid confidence, palette statistics, amount of cleanup performed, recipe IDs and eventual accepted/rejected/reverted feedback.

It does **not** store the source image as a training example unless the user explicitly enables `share_artwork=true`.

This makes contribution part of online use without silently harvesting artists' files.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

trupixel reconstruct input.png --target 64x64 --out output.png
```

Run the web API:

```bash
uvicorn pixelforge.api:app --host 0.0.0.0 --port 8080
```

Run the MCP server:

```bash
python -m pixelforge.mcp_server
```

## Hosted architecture

```text
ChatGPT / Claude / Gemini / Hermes / custom client
                    |
                    | MCP / HTTPS
                    v
              TruPixel Server
      +-------------+-------------+
      |                           |
 Reconstruction Engine      Learning Ledger
      |                           |
      v                           v
 PNG / spritesheet        recipe effectiveness
 diagnostics/diff         anonymous usage signals
```

## Important design rule

The model decides *what should change*. TruPixel performs pixel operations deterministically.

That avoids making thousands of individual model tool calls for a single sprite.

## Status

This is an MVP foundation, not a finished replacement for Pixelorama. The next major milestones are `.pxo` interoperability, animation stabilization, richer cluster/jaggy/banding analysis, style packs, community benchmarking and a web editor.
