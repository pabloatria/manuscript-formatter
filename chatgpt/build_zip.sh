#!/usr/bin/env bash
# Build the Knowledge upload for the manuscript-formatter Custom GPT.
# Reproducible from the current scripts/ tree — no parallel maintenance.
#
# Output: manuscript_formatter.zip in the repo root.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/manuscript_formatter.zip"
rm -f "$OUT"

cd "$REPO"
zip -qr "$OUT" \
    scripts/__init__.py \
    scripts/format_manuscript.py \
    scripts/journal_config.py \
    scripts/docx_helpers.py \
    scripts/validators.py \
    scripts/cover_letter.py \
    scripts/report.py \
    scripts/references.py \
    scripts/_bibtex_to_csl.py \
    scripts/_endnote_xml_to_csl.py \
    scripts/_ris_to_csl.py \
    scripts/journals/ \
    scripts/csl/ \
    -x "*.pyc" "*/__pycache__/*"

SIZE=$(du -h "$OUT" | cut -f1)
COUNT=$(unzip -l "$OUT" | tail -1 | awk '{print $2}')
echo "✓ wrote $OUT (${SIZE}, ${COUNT} files)"
