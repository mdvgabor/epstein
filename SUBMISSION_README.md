# Preliminary Submission Manifest

This branch contains the files needed for the preliminary MS3 submission and for reproducing the reported analysis.

## Report and Website Files

- `docs/index.md` - GitHub Pages homepage with the full report text.
- `docs/report.md` - standalone copy of the same report text.
- `docs/network_3d.html` - interactive 3D co-presence graph.
- `docs/assets/` - report figures used in the text.
- `docs/ms3_key_corpus_statistics.md` - separate key corpus statistics table.
- `docs/ms3_data_dictionary.md` - separate data dictionary.
- `docs/ms3_text_model_settings.md` - separate vectorizer and model settings.
- `docs/ms3_network_settings.md` - separate network construction settings.
- `docs/ms3_nmf_topic_table.md` - separate full NMF topic table.

## Reproducible Analysis Package

- `scripts/ms3_analysis.py` - main MS3 text-mining and network analysis script.
- `scripts/ms3_report_assets.py` - report chart and table asset generation.
- `scripts/ms3_theme_over_time.py` - communication-function time-series chart.
- `scripts/ms3_directed_network_check.py` - directed-network robustness check.
- `scripts/build_3d_network.py` - interactive 3D graph generation.
- `data/fact_emails.parquet` - email-level source table.
- `data/bridge_email_people.parquet` - email-person bridge table.
- `data/dim_people.parquet` - canonical person table.
- `data/ms3_clean_corpus.parquet` - cleaned MS3 analysis corpus.
- `outputs/ms3/` - generated CSV outputs, figures, metadata, report assets, and interactive network output.

## Reproduction Notes

Use `uv` from the repository root.

```bash
uv run python scripts/ms3_analysis.py
uv run python scripts/ms3_report_assets.py
uv run python scripts/ms3_theme_over_time.py
uv run python scripts/ms3_directed_network_check.py
uv run python scripts/build_3d_network.py
```

The generated report outputs are written under `outputs/ms3/`, while the website-ready copies are under `docs/`.

## Files Intentionally Excluded

This branch excludes exploratory notebooks, old preprocessing helpers, local project notes, OS metadata, draft documents, and duplicate ZIP exports. The remaining files are the final report/site files, required data inputs, MS3 scripts, generated outputs, and dependency metadata.
