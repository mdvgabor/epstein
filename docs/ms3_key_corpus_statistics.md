---
title: MS3 Key Corpus Statistics
---

# MS3 Key Corpus Statistics

This file contains the key corpus statistics for the final project paper. It is separate from the main report body to keep the report concise.

## Corpus Construction

| Metric | Value | Interpretation |
|---|---:|---|
| Raw email rows | 1,758,382 | All available rows before final analysis filtering. |
| Rows with at least 10 tokens | 1,197,760 | Removes empty or extremely short rows that are weak text-mining units. |
| Rows after redacted-sender filter | 1,103,480 | Removes rows where sender metadata is visibly redacted. |
| Likely-English rows for analysis | 1,101,455 | Main corpus used for final text-mining outputs. |
| Sampled rows used for MS3 tables | 1,101,455 | Full filtered corpus was used; no sampling in final MS3 outputs. |
| Valid year minimum | 1990 | Earliest valid year retained in the final corpus. |
| Valid year maximum | 2019 | Latest valid year retained in the final corpus. |
| Median tokens in analysis rows | 28 | Median document length after final filtering. |

## Model and Network Scale

| Metric | Value | Interpretation |
|---|---:|---|
| TF-IDF features | 395,222 | Number of unigram and bigram features after filtering. |
| Count-vectorizer features | 395,222 | Same vocabulary size used for interpretable term frequencies. |
| NMF topics | 8 | Number of topic-like components used for interpretation. |
| Median pairwise cosine similarity, first 1,000 emails | 0.0000 | Most emails are textually distinct after TF-IDF weighting. |
| 95th percentile pairwise cosine similarity, first 1,000 emails | 0.0241 | Even relatively similar emails remain weakly similar in the TF-IDF space. |
| Filtered network nodes | 1,224 | Actors retained in the main co-presence network after removing unknown/redacted labels. |
| Filtered network edges | 5,426 | Repeated co-presence ties retained at the main edge threshold. |

## Main Communication Functions

| Communication function | Emails | Share |
|---|---:|---:|
| Operational coordination | 206,843 | 18.78% |
| Movement and itinerary management | 114,917 | 10.43% |
| Financial administration | 93,179 | 8.46% |
| Public narrative management | 40,916 | 3.71% |
| Legal and investigative communication | 36,473 | 3.31% |
