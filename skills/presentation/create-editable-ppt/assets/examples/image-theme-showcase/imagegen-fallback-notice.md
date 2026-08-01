# Imagegen fallback notice

The 24 requested imagegen jobs were prepared but could not run in the current environment: the primary channel returned `403 no active plan`, and the fallback channel was blocked. This showcase therefore uses existing, local theme-showcase screenshots as a temporary visual fallback.

These PNGs are marked `existing-theme-showcase-fallback` in each `generation_manifest.json`. They are complete slide images and preserve the shared three-page narrative, but they are not claimed as fresh imagegen output. Configure an active imagegen plan, then rerun the `imagegen-jobs.jsonl` files into each theme's `slides/` directory and run `node scripts/ppt.mjs render <project>` plus `node scripts/build-image-gallery.mjs --root <showcase>`.
