# Autoresearch: preprocess pipeline quality (junk reduction in discovered people)

## Objective
Improve `preprocess.py` so newly discovered people are more likely to be real human contacts (not OCR/email-body/newsletter junk), while keeping useful discovered contacts.

Workload:
- Run preprocessing on a stable sample of non-promotional emails.
- Evaluate `dim_people.parquet` output quality for discovered rows (`person_id` starting with `discovered-email-`).
- Prioritize reducing junk entities created from display names and noisy recipient fields.

## Metrics
- **Primary**: `junk_people` (count, lower is better) — discovered people that match a conservative junk heuristic.
- **Secondary**:
  - `discovered_people` — total discovered people rows in sample output.
  - `junk_rate_pct` — `junk_people / discovered_people * 100`.
  - `preprocess_seconds` — end-to-end preprocessing runtime from script timing.
  - `bridge_rows` — output size monitor for `bridge_email_people.parquet`.

## How to Run
`./autoresearch.sh`

The script prints structured lines:
- `METRIC junk_people=...`
- `METRIC discovered_people=...`
- `METRIC junk_rate_pct=...`
- `METRIC preprocess_seconds=...`
- `METRIC bridge_rows=...`

## Files in Scope
- `preprocess.py` — main preprocessing + discovered people logic.
- `address_processing.py` — text/email/display-name extraction and cleanup.
- `autoresearch.sh` — benchmark harness and quality scoring.
- `autoresearch.md` — running notes.
- `autoresearch.ideas.md` — backlog for larger ideas.

## Off Limits
- Source data files under `data/` (except benchmark output subdir used by script).
- Any external dependencies.

## Constraints
- Use existing dependencies only.
- Keep pipeline behavior simple and maintainable (KISS).
- Do not regress discovered human contacts more than necessary while reducing clear junk.

## What's Been Tried
- Initialized quality-focused benchmark for discovered people junk detection on `PREPROCESS_SAMPLE_ROWS=50000`.
- Need to tighten discovered-person creation heuristics around organization/newsletter names and email-body artifacts.
