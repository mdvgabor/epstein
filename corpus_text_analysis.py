from collections import Counter
import json
from pathlib import Path
import re
from time import perf_counter
import urllib.request

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import polars as pl
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


out_dir = Path("outputs_colab_full")
out_dir.mkdir(exist_ok=True)
started_at = perf_counter()
last_at = started_at
token_pattern = re.compile(r"\b[a-zA-Z][a-zA-Z']{2,}\b")
sentence_pattern = re.compile(r"[.!?]+")
stop_words = set(ENGLISH_STOP_WORDS)


def log(label):
    global last_at
    now = perf_counter()
    print(f"[full-analysis] {label}: phase={now - last_at:.2f}s total={now - started_at:.2f}s", flush=True)
    last_at = now


def write_frame(frame, path):
    frame.write_csv(out_dir / path)
    print(f"[full-analysis] wrote {out_dir / path}", flush=True)


def prune(counter, keep):
    if len(counter) <= keep * 2:
        return counter
    return Counter(dict(counter.most_common(keep)))


def tokenize(text):
    return [
        token
        for token in (match.group(0).lower() for match in token_pattern.finditer(text or ""))
        if token not in stop_words
    ]


def ngrams(tokens, size):
    return (" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1))


def count_syllables(word):
    cleaned = re.sub(r"[^a-z]", "", word.lower())
    if not cleaned:
        return 0
    count = len(re.findall(r"[aeiouy]+", cleaned))
    if cleaned.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def text_metrics(text):
    raw_tokens = token_pattern.findall(text or "")
    sentences = [part for part in sentence_pattern.split(text or "") if part.strip()]
    if not raw_tokens or not sentences:
        return None
    syllables = sum(count_syllables(token) for token in raw_tokens)
    words = len(raw_tokens)
    sentence_count = len(sentences)
    types = len(set(token.lower() for token in raw_tokens))
    return {
        "tokens": words,
        "sentences": sentence_count,
        "types": types,
        "type_token_ratio": types / words,
        "flesch_reading_ease": 206.835 - 1.015 * (words / sentence_count) - 84.6 * (syllables / words),
        "flesch_kincaid_grade": 0.39 * (words / sentence_count) + 11.8 * (syllables / words) - 15.59,
    }


def kwic(term, frame, window=80, limit=500):
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    rows = []
    for row in frame.select("email_id", "sent_at", "subject", "text_clean").iter_rows(named=True):
        text = row["text_clean"] or ""
        for match in pattern.finditer(text):
            rows.append(
                {
                    "email_id": row["email_id"],
                    "sent_at": row["sent_at"],
                    "subject": row["subject"],
                    "left": text[max(0, match.start() - window) : match.start()].replace("\n", " "),
                    "keyword": text[match.start() : match.end()],
                    "right": text[match.end() : match.end() + window].replace("\n", " "),
                }
            )
            if len(rows) >= limit:
                return pl.DataFrame(rows)
    return pl.DataFrame(rows)


def plot_barh(labels, values, path, title, xlabel, color):
    plt.figure(figsize=(9, 7))
    plt.barh(labels, values, color=color)
    plt.xlabel(xlabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_dir / path, dpi=160)
    plt.close()


def compact_language_text(text):
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact.replace("\n", " ")


def load_language_model():
    try:
        import fasttext

        model_path = Path("models") / "lid.176.ftz"
        model_path.parent.mkdir(exist_ok=True)
        if not model_path.exists():
            urllib.request.urlretrieve(
                "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
                model_path,
            )
        return fasttext.load_model(str(model_path))
    except Exception as error:
        print(f"[full-analysis] fastText language detection unavailable: {error}", flush=True)
        return None


def fallback_language_indicator(text):
    compact = compact_language_text(text)
    if len(compact) < 80:
        return "too_short"
    raw_tokens = [match.group(0).lower() for match in token_pattern.finditer(compact[:1000])]
    if sum(1 for token in raw_tokens[:200] if token in stop_words) >= 3:
        return "likely_en"
    if compact.isascii():
        return "unknown_ascii"
    return "unknown_non_ascii"


def flush_language_batch(language_model, language_batch, language_counter, confidence_counter):
    if not language_batch:
        return
    labels, probabilities = language_model.predict(language_batch, k=1)
    for label_values, probability_values in zip(labels, probabilities):
        label = label_values[0].replace("__label__", "")
        language_counter[label] += 1
        confidence_counter[label] += float(probability_values[0])
    language_batch.clear()


emails = pl.read_parquet("data/fact_emails.parquet")
bridge = pl.read_parquet("data/bridge_email_people.parquet")
people = pl.read_parquet("data/dim_people.parquet")
analysis_emails = emails.filter(
    pl.col("duplicate_id_flag").not_() & pl.col("duplicate_signature_flag").not_() & (pl.col("text_token_len") > 0)
)
valid_dated_emails = emails.filter(pl.col("year").is_not_null())
log("loaded parquet")

summary_rows = [
    ("raw_documents", f"{emails.height}"),
    ("analysis_documents", f"{analysis_emails.height}"),
    ("average_document_tokens", f"{float(emails.get_column('text_token_len').mean()):.2f}"),
    ("median_document_tokens", f"{float(emails.get_column('text_token_len').median()):.0f}"),
    ("average_document_characters", f"{float(emails.get_column('text_char_len').mean()):.2f}"),
    ("median_document_characters", f"{float(emails.get_column('text_char_len').median()):.0f}"),
    ("empty_text_rows", f"{emails.filter(pl.col('text_token_len') == 0).height}"),
    ("very_short_rows_under_10_tokens", f"{emails.filter(pl.col('text_token_len') < 10).height}"),
    ("duplicate_id_rows", f"{emails.filter(pl.col('duplicate_id_flag')).height}"),
    ("duplicate_signature_rows", f"{emails.filter(pl.col('duplicate_signature_flag')).height}"),
    ("sender_redacted_rows", f"{emails.filter(pl.col('sender_redacted')).height}"),
    ("raw_min_sent_at", f"{emails.get_column('sent_at').min()}"),
    ("raw_max_sent_at", f"{emails.get_column('sent_at').max()}"),
    ("valid_dated_rows_1990_2019", f"{valid_dated_emails.height}"),
    ("missing_or_out_of_range_date_rows", f"{emails.height - valid_dated_emails.height}"),
    ("min_valid_sent_at", f"{valid_dated_emails.get_column('sent_at').min()}"),
    ("max_valid_sent_at", f"{valid_dated_emails.get_column('sent_at').max()}"),
    ("distinct_valid_years", f"{valid_dated_emails.get_column('year').n_unique()}"),
    ("people_rows", f"{people.height}"),
    ("email_person_links", f"{bridge.height}"),
]
write_frame(pl.DataFrame(summary_rows, schema=["metric", "value"], orient="row"), "corpus_summary.csv")

missing_exprs = []
for column in emails.columns:
    expr = pl.col(column).is_null()
    if emails.schema[column] == pl.String:
        expr = expr | (pl.col(column).str.strip_chars() == "")
    missing_exprs.append(expr.mean().alias(column))
missingness = (
    emails.select(missing_exprs)
    .transpose(include_header=True, header_name="field", column_names=["missing_rate"])
    .with_columns((pl.col("missing_rate") * 100).round(2).alias("missing_pct"))
    .sort("missing_rate", descending=True)
)
write_frame(missingness, "metadata_missingness.csv")

date_anomalies = (
    emails.filter(pl.col("sent_at").is_not_null() & pl.col("year").is_null())
    .select("email_id", "doc_id", "subject", "sent_at", "release_batch", "folder_path", "text_token_len")
    .sort("sent_at")
)
missing_sent_at_rows = emails.filter(pl.col("sent_at").is_null()).height
write_frame(
    pl.DataFrame(
        [
            ("missing_sent_at_rows", f"{missing_sent_at_rows}"),
            ("parsed_but_out_of_range_year_rows", f"{date_anomalies.height}"),
            ("missing_or_out_of_range_date_rows", f"{missing_sent_at_rows + date_anomalies.height}"),
            ("earliest_raw_sent_at", f"{emails.get_column('sent_at').min()}"),
            ("latest_raw_sent_at", f"{emails.get_column('sent_at').max()}"),
        ],
        schema=["metric", "value"],
        orient="row",
    ),
    "date_anomaly_summary.csv",
)
write_frame(date_anomalies.head(1000), "date_anomalies_sample.csv")

by_year = emails.group_by("year").agg(pl.len().alias("documents")).sort("year")
release_batch_coverage = emails.group_by("release_batch").agg(pl.len().alias("documents")).sort("release_batch")
write_frame(by_year, "documents_by_year.csv")
write_frame(release_batch_coverage, "release_batch_coverage.csv")
log("corpus metadata")

term_tf = Counter()
term_df = Counter()
ngram_tf = Counter()
ngram_df = Counter()
readability_rows = []
language_counter = Counter()
language_confidence = Counter()
language_model = load_language_model()
language_batch = []
kwic_rows = {term: [] for term in ["island", "flight", "passport", "massage", "Maxwell"]}
kwic_patterns = {term: re.compile(re.escape(term), re.IGNORECASE) for term in kwic_rows}
doc_count = analysis_emails.height

for index, row in enumerate(
    analysis_emails.select("email_id", "sent_at", "subject", "text_clean").iter_rows(named=True),
    start=1,
):
    text = row["text_clean"] or ""
    tokens = tokenize(text)
    language_text = compact_language_text(text)
    if len(language_text) < 80:
        language_counter["too_short"] += 1
    elif language_model is None:
        language_counter[fallback_language_indicator(text)] += 1
    else:
        language_batch.append(language_text[:1000])
        if len(language_batch) >= 4096:
            flush_language_batch(language_model, language_batch, language_counter, language_confidence)
    unique_terms = set(tokens)
    term_tf.update(tokens)
    term_df.update(unique_terms)
    doc_ngrams = []
    if len(tokens) >= 2:
        doc_ngrams.extend(ngrams(tokens, 2))
    if len(tokens) >= 3:
        doc_ngrams.extend(ngrams(tokens, 3))
    ngram_tf.update(doc_ngrams)
    ngram_df.update(set(doc_ngrams))
    if len(tokens) >= 50:
        metrics = text_metrics(text)
        if metrics:
            readability_rows.append(metrics)
    for term, pattern in kwic_patterns.items():
        if len(kwic_rows[term]) >= 500:
            continue
        for match in pattern.finditer(text):
            kwic_rows[term].append(
                {
                    "email_id": row["email_id"],
                    "sent_at": row["sent_at"],
                    "subject": row["subject"],
                    "left": text[max(0, match.start() - 80) : match.start()].replace("\n", " "),
                    "keyword": text[match.start() : match.end()],
                    "right": text[match.end() : match.end() + 80].replace("\n", " "),
                }
            )
            if len(kwic_rows[term]) >= 500:
                break
    if index % 100_000 == 0:
        term_tf = prune(term_tf, 300_000)
        term_df = Counter({term: term_df[term] for term in term_tf})
        ngram_tf = prune(ngram_tf, 500_000)
        ngram_df = Counter({term: ngram_df[term] for term in ngram_tf})
        print(f"[full-analysis] counted {index:,}", flush=True)

if language_model is not None:
    flush_language_batch(language_model, language_batch, language_counter, language_confidence)

language_distribution = (
    pl.DataFrame(
        [
            (
                language,
                documents,
                None if language_confidence[language] == 0 else round(language_confidence[language] / documents, 4),
            )
            for language, documents in language_counter.items()
        ],
        schema=["language", "documents", "avg_confidence"],
        orient="row",
    )
    .with_columns((pl.col("documents") / pl.col("documents").sum() * 100).round(2).alias("pct"))
    .sort("documents", descending=True)
)
write_frame(language_distribution, "language_distribution.csv")
log("language indicators, readability, terms, n-grams, kwic")

term_rows = [
    {
        "term": term,
        "frequency": frequency,
        "document_frequency": term_df[term],
        "document_frequency_pct": term_df[term] / doc_count * 100,
    }
    for term, frequency in term_tf.most_common(100_000)
]
term_frequency_table = pd.DataFrame(term_rows)
term_frequency_table.to_csv(out_dir / "term_frequencies.csv", index=False)
top_terms = term_frequency_table.head(25).iloc[::-1]
plot_barh(top_terms["term"], top_terms["frequency"], "top_terms.png", "Top unigram frequencies", "Frequency", "#72b7b2")

ngram_rows = [
    {
        "ngram": term,
        "frequency": frequency,
        "document_frequency": ngram_df[term],
        "document_frequency_pct": ngram_df[term] / doc_count * 100,
    }
    for term, frequency in ngram_tf.most_common(100_000)
]
ngram_table = pd.DataFrame(ngram_rows)
ngram_table.to_csv(out_dir / "ngrams.csv", index=False)
top_ngrams = ngram_table.head(25).iloc[::-1]
plot_barh(top_ngrams["ngram"], top_ngrams["frequency"], "top_ngrams.png", "Top n-grams", "Frequency", "#b279a2")
log("term and n-gram outputs")

tfidf_rows = []
for row in term_rows:
    score = row["frequency"] * (1 + __import__("math").log((1 + doc_count) / (1 + row["document_frequency"])))
    tfidf_rows.append({"term": row["term"], "tfidf_keyness": score, "frequency": row["frequency"], "document_frequency": row["document_frequency"]})
for row in ngram_rows:
    score = row["frequency"] * (1 + __import__("math").log((1 + doc_count) / (1 + row["document_frequency"])))
    tfidf_rows.append({"term": row["ngram"], "tfidf_keyness": score, "frequency": row["frequency"], "document_frequency": row["document_frequency"]})
tfidf_table = pd.DataFrame(tfidf_rows).sort_values("tfidf_keyness", ascending=False).reset_index(drop=True)
tfidf_table.to_csv(out_dir / "tfidf_key_terms.csv", index=False)
top_tfidf = tfidf_table.head(25).iloc[::-1]
plot_barh(top_tfidf["term"], top_tfidf["tfidf_keyness"], "top_tfidf_terms.png", "TF-IDF-style key terms", "TF-IDF keyness", "#ff9da6")
log("tf-idf-style keyness")

for term, rows in kwic_rows.items():
    pl.DataFrame(rows).write_csv(out_dir / f"kwic_{term.lower()}.csv")
log("kwic")

readability_table = pd.DataFrame(readability_rows)
readability_table.describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9]).to_csv(out_dir / "readability_lexical_summary.csv")
readability_table.sample(n=min(100_000, len(readability_table)), random_state=7).to_csv(
    out_dir / "readability_lexical_sample.csv", index=False
)
plt.figure(figsize=(8, 4))
plt.hist(readability_table["type_token_ratio"], bins=50, color="#9d755d")
plt.xlabel("Type-token ratio")
plt.ylabel("Documents")
plt.title("Lexical diversity")
plt.tight_layout()
plt.savefig(out_dir / "lexical_diversity.png", dpi=160)
plt.close()
plt.figure(figsize=(8, 4))
plt.hist(readability_table["flesch_reading_ease"], bins=50, color="#bab0ac")
plt.xlabel("Flesch reading ease")
plt.ylabel("Documents")
plt.title("Readability")
plt.tight_layout()
plt.savefig(out_dir / "readability.png", dpi=160)
plt.close()
log("readability")

top_people = (
    bridge.group_by("person_id", "person_name")
    .agg(pl.col("email_id").n_unique().alias("documents"), pl.len().alias("links"))
    .sort("documents", descending=True)
    .head(100)
)
role_counts = (
    bridge.group_by("involvement_role")
    .agg(pl.len().alias("links"), pl.col("email_id").n_unique().alias("documents"))
    .sort("links", descending=True)
)
linked_document_count = bridge.select(pl.col("email_id").n_unique()).item()
people_coverage = pl.DataFrame(
    [
        ("documents_with_people", f"{linked_document_count}"),
        ("analysis_documents", f"{analysis_emails.height}"),
        ("documents_with_people_pct", f"{linked_document_count / analysis_emails.height * 100:.2f}"),
    ],
    schema=["metric", "value"],
    orient="row",
)
write_frame(top_people, "top_people.csv")
write_frame(role_counts, "involvement_role_counts.csv")
write_frame(people_coverage, "people_coverage.csv")
top_people_plot = top_people.to_pandas().head(25).iloc[::-1]
plot_barh(top_people_plot["person_name"], top_people_plot["documents"], "top_people.png", "Top linked people", "Linked documents", "#59a14f")
log("people")

metadata = {
    "documents_processed": doc_count,
    "term_counter_rows": len(term_rows),
    "ngram_counter_rows": len(ngram_rows),
    "keyness_method": "full-corpus frequency times smoothed inverse document frequency over retained top term and n-gram counters",
    "language_detection": "fastText lid.176.ftz when fasttext is installed; fallback buckets otherwise",
    "runtime_seconds": round(perf_counter() - started_at, 2),
}
(out_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2), flush=True)
