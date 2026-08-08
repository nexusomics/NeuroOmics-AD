#!/usr/bin/env bash
# ==========================================================================
# Build the production frontend bundle with cache-busted (hashed) filenames.
#
# Emits:
#   dist/index.html                (references hashed assets; no-cache served)
#   dist/assets/index.<hash>.js    (long-cache immutable)
#   dist/assets/index.<hash>.css
#
# Usage:  scripts/build_frontend.sh   (from repo root, after `npm install`)
# ==========================================================================
set -euo pipefail
cd "$(dirname "$0")/../frontend"

echo "==> building CSS (tailwind)"
./node_modules/.bin/tailwindcss -i src/styles/index.css -o /tmp/na_css.css --minify

echo "==> building JS (esbuild)"
./node_modules/.bin/esbuild src/main.tsx \
  --bundle --outfile=/tmp/na_js.js \
  --loader:.tsx=tsx --loader:.ts=ts \
  --format=esm --jsx=automatic --minify \
  --define:import.meta.env.VITE_API_BASE='"/api/v1"' \
  --loader:.css=empty --log-level=warning

echo "==> hashing assets"
JS_HASH=$(md5sum /tmp/na_js.js | cut -c1-12)
CSS_HASH=$(md5sum /tmp/na_css.css | cut -c1-12)

rm -rf dist
mkdir -p dist/assets
cp /tmp/na_js.js   "dist/assets/index.${JS_HASH}.js"
cp /tmp/na_css.css "dist/assets/index.${CSS_HASH}.css"

cat > dist/index.html <<EOF
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>NeuroOmics-AD — Multi-Omics & Drug Repurposing Platform</title>
    <meta name="description" content="AI-driven multi-omics analysis and drug repurposing for Alzheimer's disease research." />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="/assets/index.${CSS_HASH}.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/index.${JS_HASH}.js"></script>
  </body>
</html>
EOF

echo "==> done: dist/index.html -> index.${JS_HASH}.js"
rm -f /tmp/na_js.js /tmp/na_css.css
