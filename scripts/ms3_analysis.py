import json
import os
import re
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import polars as pl
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


Path("outputs/ms3").mkdir(parents=True, exist_ok=True)
sample_rows = int(os.environ.get("MS3_SAMPLE_ROWS", "200000") or "0")
sample_seed = int(os.environ.get("MS3_SAMPLE_SEED", "7") or "7")


def write_csv(frame, name):
    frame.write_csv(Path("outputs/ms3") / name)


def normalized_people(frame):
    return frame.with_columns(
        pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key")
    ).filter(
        pl.col("person_id").is_not_null()
        & pl.col("person_name").is_not_null()
        & pl.col("person_id").is_in(["unknown", "redacted"]).not_()
        & pl.col("person_name_key").str.contains(r"unknown|redacted|\[redacted\]|█").not_()
    ).drop("person_name_key")


def likely_english_text(text):
    compact = re.sub(r"\s+", " ", text or "").strip().lower()
    if len(compact) < 40:
        return False
    letters = re.findall(r"[a-z]", compact)
    words = re.findall(r"[a-z][a-z']{1,}", compact)
    if not words:
        return False
    english_hits = sum(
        word in {
            "the", "and", "you", "that", "for", "with", "this", "have", "not", "are", "from",
            "will", "can", "your", "please", "would", "about", "there", "when", "what", "just",
        }
        for word in words[:300]
    )
    ascii_share = len(letters) / max(1, len(re.findall(r"[^\W\d_]", compact)))
    return english_hits >= 2 or ascii_share >= 0.94


def token_pattern():
    return re.compile(r"\b[a-zA-Z][a-zA-Z']{2,}\b")


def text_tokens(text):
    return [
        match.group(0).lower()
        for match in token_pattern().finditer(text or "")
    ]


def plot_horizontal(frame, label_column, value_column, name, title, xlabel):
    rows = frame.head(20).reverse()
    plt.figure(figsize=(8.5, 6))
    plt.barh(rows[label_column].to_list(), rows[value_column].to_list(), color="#3f7f93")
    plt.xlabel(xlabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(Path("outputs/ms3") / name, dpi=180)
    plt.close()


emails = pl.read_parquet("data/fact_emails.parquet")
bridge = pl.read_parquet("data/bridge_email_people.parquet")
people = pl.read_parquet("data/dim_people.parquet")

analysis_emails = emails.filter(
    (pl.col("text_token_len") >= 10)
    & pl.col("text_clean").is_not_null()
    & pl.col("sender_redacted").not_()
)
english_flags = pl.DataFrame(
    {
        "email_id": analysis_emails["email_id"],
        "is_likely_english": [likely_english_text(text) for text in analysis_emails["text_clean"].to_list()],
    }
)
analysis_emails = analysis_emails.join(english_flags, on="email_id").filter(pl.col("is_likely_english"))

if sample_rows > 0 and analysis_emails.height > sample_rows:
    sampled_emails = analysis_emails.sample(n=sample_rows, seed=sample_seed)
else:
    sampled_emails = analysis_emails

sampled_emails.select(
    "email_id",
    "doc_id",
    "message_index",
    "subject",
    "sent_at",
    "year",
    "release_batch",
    "text_clean",
    "text_token_len",
).write_parquet("data/ms3_clean_corpus.parquet")

write_csv(
    pl.DataFrame(
        [
            ("raw_email_rows", emails.height),
            ("rows_with_10_plus_tokens", emails.filter(pl.col("text_token_len") >= 10).height),
            ("rows_after_redacted_sender_filter", emails.filter((pl.col("text_token_len") >= 10) & pl.col("sender_redacted").not_()).height),
            ("likely_english_rows_for_analysis", analysis_emails.height),
            ("sampled_rows_used_for_ms3_tables", sampled_emails.height),
            ("valid_year_min", int(analysis_emails["year"].min())),
            ("valid_year_max", int(analysis_emails["year"].max())),
            ("median_tokens_in_analysis_rows", float(analysis_emails["text_token_len"].median())),
        ],
        schema=["metric", "value"],
        orient="row",
    ),
    "ms3_corpus_construction_summary.csv",
)

write_csv(
    analysis_emails.group_by("year")
    .agg(pl.len().alias("documents"))
    .sort("year")
    .with_columns((pl.col("documents") / pl.col("documents").sum() * 100).round(2).alias("pct")),
    "ms3_documents_by_year.csv",
)

terms_to_remove = set(ENGLISH_STOP_WORDS).union(
    {
        "jeffrey", "epstein", "subject", "sent", "iphone", "ipad", "android", "blackberry",
        "wireless", "mailbox", "message", "email", "mail", "thank", "thanks", "please",
        "yes", "yeah", "okay", "ok", "hi", "hello", "regards", "best", "forwarded",
        "fwd", "fw", "original", "attachment", "attached", "txt", "jpg", "pdf", "doc",
        "com", "http", "www", "unsubscribe", "view", "browser", "time", "today",
        "tomorrow", "know", "let", "just", "like", "want", "going", "come", "note",
        "need", "good", "day", "week", "morning", "night", "think", "make", "tell",
        "look", "right", "said", "thing", "things", "way", "did", "got", "getting",
        "people", "person", "sorry", "typos", "hbrk", "calendar", "reminder",
        "receiving", "richard", "kahn", "lesley",
    }
)


def tokenize_for_model(text):
    return [
        token
        for token in text_tokens(text)
        if token not in terms_to_remove and not token.endswith("'s")
    ]


texts = sampled_emails["text_clean"].fill_null("").to_list()

count_vectorizer = CountVectorizer(
    tokenizer=tokenize_for_model,
    token_pattern=None,
    lowercase=False,
    min_df=10,
    max_df=0.45,
    ngram_range=(1, 2),
    dtype=np.int32,
)
count_matrix = count_vectorizer.fit_transform(texts)
count_terms = count_vectorizer.get_feature_names_out()
term_table = pl.DataFrame(
    {
        "term": count_terms,
        "frequency": count_matrix.sum(axis=0).A1,
        "document_frequency": count_matrix.getnnz(axis=0),
    }
).with_columns(
    (pl.col("document_frequency") / sampled_emails.height * 100).round(3).alias("document_frequency_pct")
).sort("frequency", descending=True)
write_csv(term_table.head(250), "ms3_interpretable_term_frequencies.csv")
plot_horizontal(term_table, "term", "frequency", "ms3_top_interpretable_terms.png", "Frequent interpretable terms after email-artifact filtering", "Frequency")

tfidf_vectorizer = TfidfVectorizer(
    tokenizer=tokenize_for_model,
    token_pattern=None,
    lowercase=False,
    min_df=10,
    max_df=0.45,
    ngram_range=(1, 2),
    dtype=np.float32,
)
tfidf_matrix = tfidf_vectorizer.fit_transform(texts)
tfidf_terms = tfidf_vectorizer.get_feature_names_out()
tfidf_table = pl.DataFrame(
    {
        "term": tfidf_terms,
        "summed_tfidf": tfidf_matrix.sum(axis=0).A1,
        "document_frequency": tfidf_matrix.getnnz(axis=0),
    }
).with_columns(
    (pl.col("document_frequency") / sampled_emails.height * 100).round(3).alias("document_frequency_pct")
).sort("summed_tfidf", descending=True)
write_csv(tfidf_table.head(250), "ms3_tfidf_key_terms.csv")
plot_horizontal(tfidf_table, "term", "summed_tfidf", "ms3_top_tfidf_terms.png", "Distinctive TF-IDF terms after email-artifact filtering", "Summed TF-IDF")

nmf = NMF(n_components=8, init="nndsvda", random_state=sample_seed, max_iter=250)
topic_weights = nmf.fit_transform(tfidf_matrix)
topic_rows = []
for topic_index, weights in enumerate(nmf.components_, start=1):
    top_indices = np.argsort(weights)[::-1][:12]
    topic_rows.append(
        {
            "topic": topic_index,
            "top_terms": "; ".join(tfidf_terms[index] for index in top_indices),
            "documents_primary_topic": int((topic_weights.argmax(axis=1) == topic_index - 1).sum()),
            "share_of_sample_pct": round(float((topic_weights.argmax(axis=1) == topic_index - 1).mean() * 100), 2),
        }
    )
write_csv(pl.DataFrame(topic_rows), "ms3_nmf_topics.csv")

keyword_groups = {
    "travel_and_logistics": r"\b(?:flight|airport|plane|travel|trip|itinerary|hotel|passport|car|driver|arrival|departure|island|palm beach)\b",
    "legal_and_investigation": r"\b(?:court|lawyer|attorney|legal|case|deposition|settlement|judge|filing|witness|victim|investigation)\b",
    "finance_and_assets": r"\b(?:bank|payment|invoice|account|wire|tax|investment|fund|estate|property|money|financial)\b",
    "meetings_and_scheduling": r"\b(?:meeting|schedule|call|lunch|dinner|appointment|available|calendar|invite|reservation)\b",
    "media_and_reputation": r"\b(?:press|media|article|story|news|reporter|interview|statement|public|reputation)\b",
}
keyword_rows = []
for label, pattern in keyword_groups.items():
    hits = sampled_emails.select(pl.col("text_clean").str.contains(pattern, literal=False).fill_null(False).alias("hit"))
    documents = int(hits["hit"].sum())
    keyword_rows.append((label, documents, round(documents / sampled_emails.height * 100, 2)))
write_csv(
    pl.DataFrame(keyword_rows, schema=["theme", "documents", "document_share_pct"], orient="row").sort("documents", descending=True),
    "ms3_theme_keyword_coverage.csv",
)

valid_people = normalized_people(bridge)
sampled_links = valid_people.join(sampled_emails.select("email_id"), on="email_id", how="semi").unique(
    subset=["email_id", "person_id", "involvement_role"]
)
sender_links = sampled_links.filter(pl.col("involvement_role") == "sender").select(
    "email_id",
    pl.col("person_id").alias("source"),
    pl.col("person_name").alias("source_name"),
)
recipient_links = sampled_links.filter(pl.col("involvement_role").is_in(["to", "cc", "bcc"])).select(
    "email_id",
    pl.col("person_id").alias("target"),
    pl.col("person_name").alias("target_name"),
)
directed_edges = sender_links.join(recipient_links, on="email_id").filter(
    pl.col("source") != pl.col("target")
).group_by("source", "source_name", "target", "target_name").agg(
    pl.len().alias("weight"),
    pl.col("email_id").n_unique().alias("emails"),
).filter(pl.col("weight") >= 2).sort("weight", descending=True)
write_csv(directed_edges.head(500), "ms3_directed_edges_filtered.csv")

name_by_person = dict(valid_people.select("person_id", "person_name").unique().iter_rows())
edge_counts = {}
for row in sampled_links.select("email_id", "person_id").unique().group_by("email_id"):
    people_in_email = sorted(row[1]["person_id"].drop_nulls().unique().to_list())
    if len(people_in_email) < 2 or len(people_in_email) > 25:
        continue
    for left, right in combinations(people_in_email, 2):
        edge_counts[(left, right)] = edge_counts.get((left, right), 0) + 1

copresence_edges = pl.DataFrame(
    [
        {
            "source": left,
            "source_name": name_by_person.get(left, left),
            "target": right,
            "target_name": name_by_person.get(right, right),
            "weight": weight,
        }
        for (left, right), weight in edge_counts.items()
        if weight >= 2
    ]
).sort("weight", descending=True)
write_csv(copresence_edges.head(500), "ms3_copresence_edges_filtered.csv")

graph = nx.Graph()
for row in copresence_edges.iter_rows(named=True):
    graph.add_edge(row["source"], row["target"], weight=float(row["weight"]), distance=1 / float(row["weight"]))
    graph.nodes[row["source"]]["name"] = row["source_name"]
    graph.nodes[row["target"]]["name"] = row["target_name"]

if graph.number_of_nodes() > 0:
    betweenness = nx.betweenness_centrality(
        graph,
        k=min(300, graph.number_of_nodes()),
        seed=sample_seed,
        weight="distance",
        normalized=True,
    )
    degree = dict(graph.degree())
    weighted_degree = dict(graph.degree(weight="weight"))
    centrality = pl.DataFrame(
        [
            {
                "person_id": person_id,
                "person_name": graph.nodes[person_id].get("name", person_id),
                "degree": degree.get(person_id, 0),
                "weighted_degree": weighted_degree.get(person_id, 0),
                "betweenness": betweenness.get(person_id, 0),
            }
            for person_id in graph.nodes
        ]
    ).sort(["betweenness", "weighted_degree"], descending=True)
else:
    centrality = pl.DataFrame(schema={"person_id": pl.String, "person_name": pl.String, "degree": pl.Int64, "weighted_degree": pl.Float64, "betweenness": pl.Float64})
write_csv(centrality.head(100), "ms3_network_centrality_filtered.csv")
plot_horizontal(centrality, "person_name", "betweenness", "ms3_network_top_brokers_filtered.png", "Broker positions after removing unknown/redacted actors", "Approx. weighted betweenness")

if graph.number_of_edges() > 0:
    communities = list(nx.community.greedy_modularity_communities(graph, weight="weight"))
else:
    communities = []
write_csv(
    pl.DataFrame(
        [
            {
                "community": index,
                "members": len(community),
                "top_members_by_betweenness": "; ".join(
                    centrality.filter(pl.col("person_id").is_in(list(community))).head(8)["person_name"].to_list()
                ),
            }
            for index, community in enumerate(communities, start=1)
        ]
    ).sort("members", descending=True),
    "ms3_network_communities_filtered.csv",
)

if sampled_emails.height >= 2:
    similarity_sample = min(5000, sampled_emails.height)
    similarity_matrix = tfidf_matrix[:similarity_sample]
    upper = cosine_similarity(similarity_matrix[:1000], similarity_matrix[:1000])
    np.fill_diagonal(upper, np.nan)
    robustness_rows = [
        ("sample_rows", sampled_emails.height),
        ("tfidf_features", len(tfidf_terms)),
        ("count_features", len(count_terms)),
        ("nmf_topics", 8),
        ("median_pairwise_cosine_first_1000", round(float(np.nanmedian(upper)), 4)),
        ("p95_pairwise_cosine_first_1000", round(float(np.nanpercentile(upper, 95)), 4)),
        ("network_nodes_filtered", graph.number_of_nodes()),
        ("network_edges_filtered", graph.number_of_edges()),
    ]
else:
    robustness_rows = []
write_csv(pl.DataFrame(robustness_rows, schema=["metric", "value"], orient="row"), "ms3_robustness_checks.csv")

write_csv(
    pl.DataFrame(
        [
            ("fact_emails", "email_id", "Unique email/message identifier used for joins."),
            ("fact_emails", "doc_id", "Source document identifier from the corpus release."),
            ("fact_emails", "message_index", "Message position within the source document."),
            ("fact_emails", "subject", "Cleaned email subject."),
            ("fact_emails", "subject_base", "Subject after removing reply/forward prefixes."),
            ("fact_emails", "sent_at", "Parsed send timestamp where available."),
            ("fact_emails", "year", "Validated year, restricted to 1990-2019."),
            ("fact_emails", "release_batch", "Corpus release batch/source grouping."),
            ("fact_emails", "text_clean", "Cleaned subject plus body text used for text mining."),
            ("fact_emails", "text_token_len", "Approximate token count after cleaning."),
            ("fact_emails", "sender_redacted", "Whether the raw sender field was visibly redacted."),
            ("bridge_email_people", "email_id", "Email identifier for participant links."),
            ("bridge_email_people", "person_id", "Canonical or discovered person identifier."),
            ("bridge_email_people", "person_name", "Best available display name for the participant."),
            ("bridge_email_people", "involvement_role", "Participant role: sender, to, cc, or bcc."),
            ("bridge_email_people", "match_source", "How the participant was linked to a person record."),
            ("dim_people", "person_id", "Canonical person identifier."),
            ("dim_people", "person_name", "Canonical person name."),
            ("dim_people", "description", "Short person description from source metadata or discovery."),
            ("ms3_clean_corpus", "is_likely_english", "Heuristic inclusion decision used to remove non-English/too-short rows."),
        ],
        schema=["table", "field", "description"],
        orient="row",
    ),
    "data_dictionary.csv",
)

(Path("outputs/ms3") / "ms3_run_metadata.json").write_text(
    json.dumps(
        {
            "sample_rows_env": sample_rows,
            "sample_seed": sample_seed,
            "analysis_rows_after_filters": analysis_emails.height,
            "sampled_rows": sampled_emails.height,
            "network_unknown_redacted_removed": True,
            "language_filter": "heuristic English filter; excludes very short texts and obvious non-English rows",
            "text_models": ["CountVectorizer", "TfidfVectorizer", "NMF", "cosine similarity robustness sample"],
        },
        indent=2,
    )
    + "\n"
)
