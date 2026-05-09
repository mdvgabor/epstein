---
title: MS3 Text Model Settings
---

# MS3 Text Model Settings

This file contains the vectorizer and topic-model settings used for the final project paper. It is kept separate from the main report body to save space.

## Model Choice

The main text model used for topic discovery is non-negative matrix factorization fitted on a TF-IDF document-term matrix. It was chosen because the project needs interpretable results rather than black-box prediction. NMF topics can be explained through their highest-weighted terms and manually checked against representative emails. NMF was also more appropriate than supervised classification because the project does not have a manually labeled training set.

## Vectorizer and Model Parameters

| Component | Parameter | Value | Justification |
|---|---|---|---|
| CountVectorizer | tokenizer | Custom email tokenizer | Keeps meaningful word-like tokens and removes corpus-specific email artifacts. |
| CountVectorizer | lowercase | `False` | Lowercasing is already handled by the custom tokenizer. |
| CountVectorizer | min_df | `10` | Removes rare terms that are unlikely to support stable corpus-level interpretation. |
| CountVectorizer | max_df | `0.45` | Removes terms appearing in too many documents, which are less useful for distinguishing themes. |
| CountVectorizer | ngram_range | `(1, 2)` | Keeps both single words and meaningful two-word phrases such as institution or travel terms. |
| TF-IDF vectorizer | tokenizer | Custom email tokenizer | Uses the same cleaned vocabulary as the count model for comparability. |
| TF-IDF vectorizer | lowercase | `False` | Lowercasing is already handled before vectorization. |
| TF-IDF vectorizer | min_df | `10` | Reduces noise from rare OCR fragments, names, and one-off artifacts. |
| TF-IDF vectorizer | max_df | `0.45` | Downweights terms that are too general across the archive. |
| TF-IDF vectorizer | ngram_range | `(1, 2)` | Allows distinctive phrases as well as individual terms. |
| NMF | n_components | `8` | Produces enough topics to separate broad functions while remaining readable in a short report. |
| NMF | init | `nndsvda` | Provides a stable initialization suitable for sparse TF-IDF matrices. |
| NMF | max_iter | `250` | Gives the model enough iterations to converge without excessive runtime. |
| NMF | random_state | `7` | Makes the topic output reproducible. |

## Additional Notes

The keyword-defined communication functions are not a supervised model. They are transparent rule-based indicators used to estimate broad communication functions such as travel, finance, legal communication, media/reputation, and operational coordination. Their simplicity is a limitation, so they are interpreted cautiously and checked with manual validation examples.
