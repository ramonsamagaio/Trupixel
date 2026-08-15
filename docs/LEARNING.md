# Community Learning

TruPixel separates **learning signals** from **artwork collection**.

## Mandatory hosted contribution

Every online/hosted job contributes:

- feature/pass identifiers;
- engine version;
- anonymous job ID;
- dimensions;
- inferred-grid confidence;
- palette statistics;
- count of deterministic cleanup edits;
- user outcome when available.

These signals improve recipe weighting without requiring raw artwork.

## Explicit artwork contribution

Artwork itself is a separate permission. `share_artwork=false` is the default.

If true, a source may be stored for benchmark/community-dataset work and must be associated with a declared content license before public redistribution.

## Principle

A community tool should get smarter from use without converting private artists' work into an implicit dataset.
