#!/bin/bash
set -euo pipefail

uv run python - <<'PY'
import py_compile
py_compile.compile('preprocess.py', doraise=True)
py_compile.compile('address_processing.py', doraise=True)
PY

out_dir="data/preprocess_autoresearch"
rm -rf "$out_dir"
mkdir -p "$out_dir"

start=$(uv run python - <<'PY'
from time import perf_counter
print(perf_counter())
PY
)

PREPROCESS_SAMPLE_ROWS="${PREPROCESS_SAMPLE_ROWS:-100000}" PREPROCESS_SAMPLE_SEED="${PREPROCESS_SAMPLE_SEED:-42}" PREPROCESS_OUT_DIR="$out_dir" uv run python preprocess.py >/tmp/preprocess_autoresearch.log 2>&1
status=$?
end=$(uv run python - <<'PY'
from time import perf_counter
print(perf_counter())
PY
)

elapsed=$(uv run python - <<PY
start = float("$start")
end = float("$end")
print(f"{end-start:.4f}")
PY
)

echo "METRIC preprocess_seconds=$elapsed"

uv run python - <<'PY'
import polars as pl
from pathlib import Path
out_dir = Path('data/preprocess_autoresearch')
df = pl.read_parquet(out_dir / 'dim_people.parquet')
discovered = df.filter(pl.col('person_id').str.starts_with('discovered-email-'))
low = pl.col('person_name').str.to_lowercase()
patterns = r'\b(news|breaking|update|digest|alert|newsletter|calendar|security|support|service|office|staff|team|group|mail|reply|noreply|notification|welcome|unsubscribe|assurant|protect|brief|post|times|postmaster|daemon|admin|marketing|sales|billing|payments|travel|reservation|reservations|bank|portal|home|mobile|security)\b'
junk = discovered.filter(
    low.str.contains(patterns) |
    pl.col('person_name').str.contains(r'[0-9]') |
    pl.col('person_name').str.contains(r'&|/|:|;|\||@|<|>') |
    pl.col('person_name').str.contains(r'(?i)\b(from|subject|re|fw|fwd|sent|to|cc|bcc|original message|forwarded|begin forwarded message)\b')
)
print(f'METRIC junk_people={junk.height}')
print(f'METRIC discovered_people={discovered.height}')
print(f'METRIC junk_rate_pct={0 if discovered.height == 0 else (junk.height / discovered.height) * 100:.4f}')
print(f'METRIC bridge_rows={pl.read_parquet(out_dir / "bridge_email_people.parquet").height}')
PY

exit $status