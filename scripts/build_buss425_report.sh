#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p outputs/buss425/report docs/assets

uv run --no-project --with polars --with pandas --with pyarrow python scripts/build_buss425_adjacency.py
uv run --no-project --with pandas --with networkx --with matplotlib python scripts/build_simplified_broker_map.py

pandoc docs/buss425_final_report.md --resource-path=docs -o outputs/buss425/report/buss425_final_report.docx
uv run --no-project --with python-docx python scripts/style_buss425_report_tables.py
soffice --headless --convert-to pdf --outdir outputs/buss425/report outputs/buss425/report/buss425_final_report.docx

echo "Wrote outputs/buss425/report/buss425_final_report.docx"
echo "Wrote outputs/buss425/report/buss425_final_report.pdf"
