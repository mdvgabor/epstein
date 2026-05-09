---
title: MS3 Data Dictionary
---

# MS3 Data Dictionary

This file contains the analysis-ready corpus column descriptions used for the final project paper. It is kept separate from the main report body so the report can stay concise.

## `fact_emails.parquet`

| Column | Data type | Description |
|---|---|---|
| `email_id` | String | Stable email identifier used for joins. |
| `doc_id` | String | Source document identifier from the corpus release. Example: `EFTA02255570`. |
| `message_index` | Int64 | Message position within the source document. |
| `subject` | String | Cleaned email subject line; nullable. |
| `subject_base` | String | Subject after removing reply and forward prefixes; nullable. |
| `sent_at` | Datetime | Parsed timestamp where available. |
| `year` | Int32 | Year derived from `sent_at`; set to null outside the valid 1990-2019 range. |
| `folder_path` | String | Folder metadata such as inbox or sent folder; mostly missing and not used for final analysis. |
| `release_batch` | Int64 | Source release batch identifier. |
| `body_clean` | String | Cleaned email body after HTML, footer, quote, encoding, and artifact removal. |
| `text_clean` | String | Primary analysis text: cleaned subject plus cleaned body. |
| `text_char_len` | UInt32 | Character length of `text_clean`. |
| `text_token_len` | UInt32 | Regex token count for `text_clean`. |
| `sender_redacted` | Boolean | True when the raw sender field appears visibly redacted. |

## `bridge_email_people.parquet`

| Column | Data type | Description |
|---|---|---|
| `email_id` | String | Join key to `fact_emails`. |
| `person_id` | String | Canonical or discovered person identifier. |
| `person_name` | String | Display name from known, inferred, or discovered person mapping. |
| `involvement_role` | String | Participant role in the email metadata: sender, to, cc, bcc, or account_email. |
| `role_index` | Int64 | Position within the original role list. |
| `match_source` | String | Source of person resolution, such as known email, display-name match, inferred email, or discovered email. |
| `display_name` | String | Display name extracted from the original address field. |
| `raw_value` | String | Original raw address value before person resolution. |

## `dim_people.parquet`

| Column | Data type | Description |
|---|---|---|
| `person_id` | String | Canonical person identifier. |
| `person_name` | String | Canonical display name. |
| `description` | String | Description from source metadata or discovered-person note. |

## `ms3_clean_corpus.parquet`

| Column | Data type | Description |
|---|---|---|
| `is_likely_english` | Boolean | Heuristic inclusion decision used to remove non-English or too-short rows from the final text-mining corpus. |
