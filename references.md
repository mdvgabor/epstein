# People Sources

Checked on 2026-04-17. The pipeline uses one master file:

```text
people.csv
```

The expected columns are:

```csv
slug,name,description,email_count,url,aliases,emails
```

`aliases` and `emails` are JSON arrays. `email_count` can be blank. Inclusion means a name appears in a source index or extracted records; it does not imply guilt, wrongdoing, or a verified relationship beyond source context.

## Master File

### `people.csv`

- Rows: 1426 people plus header.
- Used directly by `preprocess.py`.
- Built from the existing Jmail people export, Epstein Document Archive entities CSV, and Kaggle "Epstein Files - Persons of Interest List".
- Deduped by normalized display name while preserving the preferred row from the highest-priority source.
- Aliases and emails from duplicate rows were merged into the preferred row.

Source priority used to assemble the current master:

1. Existing Jmail people export.
2. Epstein Document Archive entities CSV: https://www.epsteininvestigation.org/api/download/entities
3. Kaggle persons-of-interest dataset: https://www.kaggle.com/datasets/wilomentena/epstein-list-persons-of-interest

## Source Notes

### Jmail People

- Original local source: `data/jmail_people.csv`.
- Original URL pattern: `https://jmail.world/person/<slug>`.
- Jmail rows are now carried in `people.csv`.
- Extra emails from `data/jmail_person_emails.csv` were evaluated during master construction. Runtime preprocessing now uses only the consolidated `emails` values in `people.csv`.

### Epstein Document Archive

- URL: https://www.epsteininvestigation.org/api/download/entities
- Download page: https://www.epsteininvestigation.org/download
- Original fields: `name`, `entity_type`, `slug`, `role_description`, `document_count`, `flight_count`, `email_count`.
- Mapping: `role_description` became `description`; source `email_count` was preserved.

### Kaggle Persons Of Interest

- URL: https://www.kaggle.com/datasets/wilomentena/epstein-list-persons-of-interest
- Kaggle ref: `wilomentena/epstein-list-persons-of-interest`
- License shown by Kaggle: Community Data License Agreement - Sharing - Version 1.0.
- Original fields: `Name`, `Category`, `Bio`, `Aliases`, `Flights`, `Documents`, `Connections`, `In Black Book`, `Nationality`.
- Mapping: `Name` was slugified when no higher-priority row existed; `Aliases` became the JSON `aliases` column; other extra fields were folded into `description`.

## Other Leads

### Kaggle: Epstein Ranked Dataset (U.S. House Oversight)

- URL: https://www.kaggle.com/datasets/linogova/epstein-ranker-dataset-u-s-house-oversight
- Kaggle ref: `linogova/epstein-ranker-dataset-u-s-house-oversight`
- Shape: 25k+ OCR text files with LLM-generated scores and `power_mentions`.
- Use: document triage and lead generation, not a clean people CSV.

### Kaggle: The Epstein Files

- URL: https://www.kaggle.com/datasets/jazivxt/the-epstein-files
- Kaggle ref: `jazivxt/the-epstein-files`
- Shape: roughly 39 GB text/NLP corpus.
- Use: possible NER source if you want to mine names yourself.

### Hugging Face: Epstein_Files_20K

- URL: https://huggingface.co/datasets/tensonaut/Epstein_Files_20K
- Shape: 25k+ text/OCR documents derived from the House Oversight release.
- Use: corpus for extraction/RAG; upstream source referenced by the Kaggle ranker.

### Epstein Files Explorer

- URL: https://search.epsteincoverup.us/
- Shape: searchable web app with people and aliases across 1.24M indexed files.
- Use: manual cross-check and alias discovery.

### Epstein Files Public Interest Index

- URL: https://epstein-stats.vercel.app/
- Shape: dashboard with official named individuals and release/source history.
- Counts observed: 305 official named individuals and 1516 total indexed people.
- Use: cross-checking source coverage.

### Epstein Archive

- URL: https://epstein-docs.github.io/
- Shape: searchable processed archive of documents, people, organizations, locations, dates, and AI summaries.
- Counts observed: 12243 people and 8175 documents.
- Use: broad mention discovery.
