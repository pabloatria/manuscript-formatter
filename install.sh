#!/usr/bin/env bash
# manuscript-formatter skill installer (macOS / Linux)
# Installs Python dependencies and prints next steps.

set -e

echo "▸ manuscript-formatter skill setup"
echo ""

# Detect Python 3
if ! command -v python3 &> /dev/null; then
    echo "✗ python3 not found."
    echo "  macOS:         brew install python3"
    echo "  Debian/Ubuntu: sudo apt install python3"
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓ python3 found: $PY_VERSION"

# Detect pip — on minimal Linux images python3-pip is a separate package.
if ! python3 -m pip --version &> /dev/null; then
    echo "✗ pip not found for python3."
    echo "  macOS:         python3 -m ensurepip --upgrade"
    echo "  Debian/Ubuntu: sudo apt install python3-pip"
    echo "  Fedora:        sudo dnf install python3-pip"
    exit 1
fi

# Install dependencies. Try clean first; fall back to --break-system-packages for newer macOS Pythons.
# On the fallback failure branch we intentionally do NOT suppress stderr so the
# user sees the real reason (network, permissions, PEP 668 without the flag, etc.).
echo ""
echo "▸ Installing python-docx, citeproc-py, bibtexparser, pyyaml, rapidfuzz..."
if python3 -m pip install --quiet --upgrade python-docx citeproc-py bibtexparser pyyaml rapidfuzz 2>/dev/null; then
    echo "✓ installed cleanly"
elif python3 -m pip install --quiet --upgrade --break-system-packages python-docx citeproc-py bibtexparser pyyaml rapidfuzz; then
    echo "✓ installed (used --break-system-packages for system Python)"
else
    echo "✗ install failed. Retrying with full output so you can see the error:"
    python3 -m pip install --upgrade --break-system-packages python-docx citeproc-py bibtexparser pyyaml rapidfuzz || true
    echo ""
    echo "  If the error above is about PEP 668 or an externally-managed environment,"
    echo "  install into a venv instead:"
    echo "    python3 -m venv ~/.manuscript-formatter-venv"
    echo "    source ~/.manuscript-formatter-venv/bin/activate"
    echo "    pip install python-docx citeproc-py bibtexparser pyyaml rapidfuzz"
    exit 1
fi

# Verify imports
echo ""
echo "▸ Verifying imports..."
python3 -c "import docx, citeproc, bibtexparser, yaml, rapidfuzz; print('✓ all imports work')"

# Print next steps
SKILL_DIR=$(cd "$(dirname "$0")" && pwd)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup complete."
echo ""
echo "Skill location: $SKILL_DIR"
echo ""
echo "Quick test (print the CLI help):"
echo ""
echo "  python3 \"$SKILL_DIR/scripts/format_manuscript.py\" --help"
echo ""
echo "Full usage:"
echo ""
echo "  python3 \"$SKILL_DIR/scripts/format_manuscript.py\" \\"
echo "    ~/Downloads/draft.docx \\"
echo "    --references ~/Downloads/library.json \\"
echo "    --journal jpd \\"
echo "    --out-dir ~/Downloads/ \\"
echo "    --cover-letter --editor \"Dr. Last Name\""
echo ""
echo "For the full pipeline, ask Claude (Desktop or Code) to use the"
echo "manuscript-formatter skill, e.g. \"reformat my manuscript for JOMI\"."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
