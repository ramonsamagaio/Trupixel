# TruPixel Skill

## Purpose

Use TruPixel when a source image visually imitates pixel art but is not truly aligned to a logical pixel grid, when a generated sprite needs deterministic cleanup, or when a spritesheet needs consistency analysis.

## Core principle

Separate artistic judgment from deterministic pixel operations.

Workflow:
1. artistic interpretation;
2. grid inference;
3. deterministic reconstruction;
4. palette normalization;
5. pixel-cluster cleanup;
6. semantic review;
7. user feedback;
8. community recipe update.

## Analyze before reconstructing

If the target grid is unknown, call `analyze_grid`. Prefer an explicit target when the asset specification provides dimensions, when the user names the intended sprite size, when the source contains several independent sprites, or when automatic confidence is low.

## Reconstruct

Call `reconstruct_pixel_art`. Start conservatively: preserve silhouette, use a modest palette, and never share artwork unless explicitly authorized.

## Inspect diagnostics

Pay attention to grid confidence, target dimensions, palette change, changed ratio versus nearest-neighbor reduction, and warnings.

## Semantic cleanup

The engine is deterministic; semantic judgment belongs to the agent/user. Preserve deliberate eye highlights, remove accidental specks, keep silhouettes readable, and avoid noisy texture.

## Feed learning back

Every hosted operation contributes anonymous/non-content statistics automatically. After the user judges the result, call `rate_result` with `accepted`, `rejected`, or `reverted`.

## Privacy contract

Never set `share_artwork=true` by assumption. Mandatory online contribution is fulfilled by non-content operational statistics. Raw artwork enters a public/reference dataset only after explicit permission.
