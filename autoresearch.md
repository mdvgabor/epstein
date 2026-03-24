# Autoresearch: match famous correspondents to Economist counts

## Objective
Use `data/emails.normalized.parquet` to reproduce the people-level totals and sent/received ratios in `data/famous_correspondents.csv` for Epstein's famous correspondents.

The ratio is interpreted as `sent_to_jeff / received_from_jeff`, where `sent_to_jeff` counts messages from the correspondent to Jeffrey and `received_from_jeff` counts messages from Jeffrey to the correspondent. The workload is matching noisy header names and email aliases to the intended real person without pulling in relatives, staff, quoted-thread garbage, or fake/example addresses.

## Metrics
- **Primary**: `combined_error` (unitless, lower is better) — sum over all target people of `abs(total_delta)/target_total + abs(log(matched_ratio/target_ratio))`
- **Secondary**:
  - `total_abs_delta` — sum of absolute total-email deltas across all people
  - `ratio_log_error` — sum of absolute log-ratio errors
  - `worst_person_error` — largest per-person combined error
  - `matched_rows` — rows in the output table

## How to Run
`./autoresearch.sh` — runs `python correspondace.py` and emits `METRIC ...` lines.

## Files in Scope
- `correspondace.py` — main matching logic, alias filtering, scoring, output
- `nb.py` — reference notebook/script if useful for ideas or helper logic
- `jmail.py` — read-only helper for dataset download paths; avoid changing unless absolutely necessary
- `autoresearch.md` — session memory
- `autoresearch.sh` — benchmark wrapper
- `autoresearch.ideas.md` — backlog for promising but deferred ideas

## Off Limits
- `data/*` source files
- dependency definitions unless absolutely necessary

## Constraints
- Keep it simple.
- No new dependencies.
- Optimize for correctness of matched correspondents, not runtime.
- Prefer explicit heuristics grounded in observed aliases over broad fuzzy matching that drags in family/staff false positives.
- Avoid magic numbers & heuristics.
- Paralelise work using polars builtins

## What's Been Tried
- Initial `correspondace.py` reparses sender/to/cc/bcc from `data/emails.normalized.parquet`, derives simplified `name_key`, hand-picks a few Jeffrey aliases, and searches combinations of candidate name keys to approximate the Economist totals.
- Best kept improvement so far: fill missing person keys with an email-derived fallback key (`search_key = coalesce(name_key, email_key)`). That reduced `combined_error` from about `3.10` to about `3.06`.
- This kept version is already close for `Larry Summers`, `Michael Wolff`, `Thomas Pritzker`, and `Steve Bannon`.
- Biggest remaining misses are `Ariane de Rothschild`, `Elon Musk`, `Bill Gates`, `Reid Hoffman`, `Kathryn Ruemmler`, and `Lawrence Krauss`.
- Failed experiments:
  - broad tightening of include tokens made totals much worse by removing legitimate noisy aliases
  - broad Jeffrey alias auto-expansion improved total coverage but distorted ratios
  - exhaustive directional sender/recipient subset search looked promising but timed out
  - greedy directional search overfit junk high-volume keys like `billconover` and `jermaine`
  - global penalties for non-preferred aliases cleaned up some local cases but hurt the overall metric
- Strong current belief: the hard cases need either person-specific directional alias handling or a different counting model, not just more generic alias tweaks.
