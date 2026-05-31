#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p outputs/buss425/report docs/assets

uv run --no-project --with polars --with pandas --with pyarrow python scripts/build_buss425_adjacency.py
uv run --no-project --with pandas --with networkx --with matplotlib python scripts/build_simplified_broker_map.py

pandoc docs/buss425_final_report.md --resource-path=docs -o outputs/buss425/report/buss425_final_report.docx
uv run --no-project --with python-docx python scripts/style_buss425_report_tables.py

if [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]; then
  soffice --headless --convert-to pdf --outdir outputs/buss425/report outputs/buss425/report/buss425_final_report.docx
elif [ -d /Applications/Pages.app ]; then
  osascript - "$ROOT/outputs/buss425/report/buss425_final_report.docx" "$ROOT/outputs/buss425/report/buss425_final_report.pdf" <<'APPLESCRIPT'
on run argv
set inputFile to POSIX file (item 1 of argv)
set outputFile to POSIX file (item 2 of argv)
tell application "Pages"
  set theDoc to open inputFile
  export theDoc to outputFile as PDF
  close theDoc saving no
end tell
end run
APPLESCRIPT
else
  echo "No DOCX-to-PDF converter found. The DOCX was created successfully." >&2
  exit 1
fi

echo "Wrote outputs/buss425/report/buss425_final_report.docx"
echo "Wrote outputs/buss425/report/buss425_final_report.pdf"
