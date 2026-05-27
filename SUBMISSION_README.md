# Preliminary Submission Manifest

This branch contains the files needed for the preliminary MS3 submission and for reproducing the reported analysis. It has also been adapted for the BUSS425 network-centrality assignment by foregrounding the informal network question, centrality measures, visualization, conclusion, and adjacency-matrix requirement.

## Report and Website Files

- `docs/index.md` - GitHub Pages homepage with the BUSS425 centrality-focused report text.
- `docs/report.md` - standalone copy of the same BUSS425 centrality-focused report text.
- `docs/buss425_final_report.md` - long-form BUSS425 final report matching the style and length of the provided MS3 report.
- `docs/buss425_full_analysis.md` - complete BUSS425 assignment analysis organized around the five required components.
- `docs/buss425_video_slide_outline.md` - complete 5-minute slide content and speaker-note script organized around the assignment requirements.
- `docs/buss425_top15_adjacency_matrix.md` - slide-friendly weighted adjacency matrix for the 15 highest-ranked centrality actors.
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
- `scripts/build_buss425_adjacency.py` - BUSS425 full and top-15 weighted adjacency matrix generation.
- `scripts/build_simplified_broker_map.py` - simplified broker-map figure generation.
- `scripts/style_buss425_report_tables.py` - deterministic table styling for the DOCX report.
- `scripts/build_buss425_report.sh` - one-command BUSS425 report rebuild: matrices, figure, DOCX styling, and PDF export.
- `data/fact_emails.parquet` - email-level source table.
- `data/bridge_email_people.parquet` - email-person bridge table.
- `data/dim_people.parquet` - canonical person table.
- `data/ms3_clean_corpus.parquet` - cleaned MS3 analysis corpus.
- `outputs/ms3/` - generated CSV outputs, figures, metadata, report assets, and interactive network output.
- `outputs/buss425/full_weighted_adjacency_matrix.csv` - full 1,224-node weighted adjacency matrix for the assignment.
- `outputs/buss425/top15_weighted_adjacency_matrix.csv` - compact weighted adjacency matrix for slides.
- `outputs/buss425/report/buss425_final_report.docx` - Word export of the long-form BUSS425 report.
- `outputs/buss425/report/buss425_final_report.pdf` - PDF export of the long-form BUSS425 report.

## BUSS425 Framing Notes

The assignment version uses the following research question:

> Which actors are structurally central in the Epstein email co-presence network, and what does centrality reveal beyond the expected dominance of Jeffrey Epstein?

The edge definition is intentionally conservative. A co-presence edge means that two actors appeared in the same email metadata record, such as sender, recipient, cc, or bcc. It does not prove direct communication, close relationship, collaboration, shared intent, or wrongdoing. Because the archive boundary is Epstein-centered, Epstein's top centrality ranking is treated as an expected baseline. The substantive contribution is the second layer of intermediaries identified through degree, weighted degree, and betweenness centrality.

## Reproduction Notes

Use `uv` from the repository root.

```bash
uv run python scripts/ms3_analysis.py
uv run python scripts/ms3_report_assets.py
uv run python scripts/ms3_theme_over_time.py
uv run python scripts/ms3_directed_network_check.py
uv run python scripts/build_3d_network.py
uv run python scripts/build_buss425_adjacency.py
```

The generated report outputs are written under `outputs/ms3/`, while the website-ready copies are under `docs/`.

To rebuild the BUSS425 assignment artifacts from the existing data and report source, run:

```bash
./scripts/build_buss425_report.sh
```

This regenerates the weighted adjacency matrices, simplified broker map, Word report, centered/styled report tables, and PDF export.

## Files Intentionally Excluded

This branch excludes exploratory notebooks, old preprocessing helpers, local project notes, OS metadata, draft documents, and duplicate ZIP exports. The remaining files are the final report/site files, required data inputs, MS3 scripts, generated outputs, and dependency metadata.
