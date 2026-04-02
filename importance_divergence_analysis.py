import math
import re
from pathlib import Path

import polars as pl


def canonical_person(value):
    if value is None:
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^A-Za-z\s\-.']", " ", value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    if not value or "@" in value:
        return None
    if value in {
        "unknown",
        "google calendar",
        "calendar",
        "staff",
        "office",
        "team",
        "support",
        "admin",
        "legal",
        "communications",
        "newsletter",
        "updates",
    }:
        return None
    tokens = re.findall(r"[a-z]+", value)
    if len(tokens) < 2 or len(tokens) > 4:
        return None
    if sum(len(token) > 1 for token in tokens) < 2:
        return None
    if any(token in {"com", "net", "org", "gmail", "yahoo"} for token in tokens):
        return None
    return " ".join(token.capitalize() for token in tokens)


def percentile_map(values):
    ordered = sorted((value, key) for key, value in values.items())
    total = max(len(ordered) - 1, 1)
    result = {}
    for rank, (_, key) in enumerate(ordered):
        result[key] = rank / total
    return result


out_dir = Path("data")

clean = pl.read_parquet(out_dir / "emails.cleaned.analysis_ready.parquet").select(
    "id", "sender_name_best", "text_clean", "sent_at", "year"
)

recipient_actor_map = (
    pl.read_parquet(out_dir / "email_addresses.parquet")
    .filter(pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"]))
    .select("id", "display_name")
    .with_columns(
        pl.col("display_name").map_elements(canonical_person, return_dtype=pl.String).alias("recipient_actor")
    )
    .filter(pl.col("recipient_actor").is_not_null())
    .select("id", "recipient_actor")
    .unique()
)

sender_actor_map = clean.select("id", "sender_name_best").with_columns(
    pl.col("sender_name_best").map_elements(canonical_person, return_dtype=pl.String).alias("sender_actor")
)

edges = (
    sender_actor_map.join(recipient_actor_map, on="id", how="inner")
    .filter(
        pl.col("sender_actor").is_not_null()
        & pl.col("recipient_actor").is_not_null()
        & pl.col("sender_actor").ne(pl.col("recipient_actor"))
    )
    .group_by("sender_actor", "recipient_actor")
    .len()
    .rename({"len": "weight"})
    .sort("weight", descending=True)
)

network = pl.concat(
    [
        edges.group_by("sender_actor")
        .agg(
            pl.col("weight").sum().alias("sent_weight"),
            pl.col("recipient_actor").n_unique().alias("out_neighbors"),
        )
        .rename({"sender_actor": "actor"}),
        edges.group_by("recipient_actor")
        .agg(
            pl.col("weight").sum().alias("received_weight"),
            pl.col("sender_actor").n_unique().alias("in_neighbors"),
        )
        .rename({"recipient_actor": "actor"}),
    ],
    how="diagonal_relaxed",
).group_by("actor").agg(
    pl.col("sent_weight").sum().fill_null(0).alias("sent_weight"),
    pl.col("received_weight").sum().fill_null(0).alias("received_weight"),
    pl.col("out_neighbors").sum().fill_null(0).alias("out_neighbors"),
    pl.col("in_neighbors").sum().fill_null(0).alias("in_neighbors"),
)

network = network.with_columns(
    (pl.col("sent_weight") + pl.col("received_weight")).alias("weighted_degree"),
    (pl.col("out_neighbors") + pl.col("in_neighbors")).alias("unique_neighbors"),
).sort("weighted_degree", descending=True)

network_scores = network.to_dicts()
degree_pct = percentile_map({row["actor"]: row["weighted_degree"] for row in network_scores})
neighbor_pct = percentile_map({row["actor"]: row["unique_neighbors"] for row in network_scores})
for row in network_scores:
    row["network_score"] = (degree_pct[row["actor"]] + neighbor_pct[row["actor"]]) / 2

network_scores = sorted(network_scores, key=lambda row: row["network_score"], reverse=True)
actor_pool = [row["actor"] for row in network_scores[:120]]

actor_pattern = re.compile(
    r"\b(" + "|".join(re.escape(actor.lower()) for actor in sorted(actor_pool, key=len, reverse=True)) + r")\b"
)

mention_docs = {actor: 0 for actor in actor_pool}
mention_total = {actor: 0 for actor in actor_pool}

for row in clean.select("text_clean").iter_rows(named=True):
    text = (row["text_clean"] or "").lower()
    if not text:
        continue
    matches = actor_pattern.findall(text)
    if not matches:
        continue
    seen = set()
    for match in matches:
        actor = " ".join(token.capitalize() for token in match.split())
        if actor not in mention_total:
            continue
        mention_total[actor] += 1
        seen.add(actor)
    for actor in seen:
        mention_docs[actor] += 1

content_rows = []
docs_pct = percentile_map(mention_docs)
total_pct = percentile_map(mention_total)
for actor in actor_pool:
    content_rows.append(
        {
            "actor": actor,
            "mention_docs": mention_docs[actor],
            "mention_total": mention_total[actor],
            "content_score": (docs_pct[actor] + total_pct[actor]) / 2,
        }
    )

content = pl.DataFrame(content_rows)
comparison = (
    pl.DataFrame(network_scores)
    .join(content, on="actor", how="left")
    .with_columns(
        pl.col("mention_docs").fill_null(0),
        pl.col("mention_total").fill_null(0),
        pl.col("content_score").fill_null(0.0),
    )
)

comparison_rows = comparison.to_dicts()
network_ranked = sorted(comparison_rows, key=lambda row: row["network_score"], reverse=True)
content_ranked = sorted(comparison_rows, key=lambda row: row["content_score"], reverse=True)
network_rank = {row["actor"]: index + 1 for index, row in enumerate(network_ranked)}
content_rank = {row["actor"]: index + 1 for index, row in enumerate(content_ranked)}

for row in comparison_rows:
    row["network_rank"] = network_rank[row["actor"]]
    row["content_rank"] = content_rank[row["actor"]]
    row["rank_gap"] = row["content_rank"] - row["network_rank"]
    row["abs_rank_gap"] = abs(row["rank_gap"])

ranked = pl.DataFrame(comparison_rows).sort("abs_rank_gap", descending=True)
ranked.write_csv(out_dir / "importance_divergence_actor_comparison.csv")
edges.write_csv(out_dir / "importance_divergence_edges.csv")

top_network = [row["actor"] for row in network_ranked[:20]]
top_content = [row["actor"] for row in content_ranked[:20]]
top_overlap = len(set(top_network) & set(top_content))
top_union = len(set(top_network) | set(top_content))
jaccard = top_overlap / top_union if top_union else 0.0

paired = [row for row in comparison_rows if row["mention_docs"] > 0]
n = len(paired)
sum_sq = sum((network_rank[row["actor"]] - content_rank[row["actor"]]) ** 2 for row in paired)
spearman = 1 - (6 * sum_sq) / (n * (n**2 - 1)) if n > 1 else math.nan

summary = pl.DataFrame(
    [
        {"metric": "actor_pool_size", "value": len(actor_pool)},
        {"metric": "paired_actors_with_mentions", "value": n},
        {"metric": "top_20_overlap", "value": top_overlap},
        {"metric": "top_20_jaccard", "value": round(jaccard, 4)},
        {"metric": "spearman_rank_correlation", "value": round(spearman, 4)},
    ]
)
summary.write_csv(out_dir / "importance_divergence_summary.csv")

network_heavy = ranked.filter(pl.col("rank_gap") > 0).sort("rank_gap", descending=True).head(15)
content_heavy = ranked.filter(pl.col("rank_gap") < 0).sort("rank_gap").head(15)
network_heavy.write_csv(out_dir / "importance_divergence_network_heavy.csv")
content_heavy.write_csv(out_dir / "importance_divergence_content_heavy.csv")

report = f"""# Content vs Network Importance Divergence

## Research Question

How much do content-based importance and network-based importance diverge in the cleaned Epstein email corpus?

## Operationalization

- Network-based importance: actor score from the cleaned person-to-person email graph, using weighted degree and unique-neighbor breadth.
- Content-based importance: actor score from explicit name mentions in cleaned email text, using document frequency and total mention count.
- Actor universe: the top 120 structurally visible actors with plausible person names derived from the cleaned corpus and parsed addresses.

## Main Result

The two importance rankings diverge substantially rather than trivially aligning.

- Actor pool size: {len(actor_pool)}
- Actors with at least one text mention: {n}
- Top-20 overlap: {top_overlap}
- Top-20 Jaccard overlap: {jaccard:.3f}
- Spearman rank correlation: {spearman:.3f}

This means the network and the text are capturing related but clearly different kinds of prominence. Structurally central actors are not always the ones most explicitly discussed in message content, and some heavily mentioned actors are less central in the communication graph itself.

## Most Network-Heavy Actors

"""

for row in network_heavy.to_dicts()[:10]:
    report += f"- {row['actor']}: network rank {row['network_rank']}, content rank {row['content_rank']}, weighted degree {row['weighted_degree']}, mentions {row['mention_total']}\n"

report += "\n## Most Content-Heavy Actors\n\n"
for row in content_heavy.to_dicts()[:10]:
    report += f"- {row['actor']}: content rank {row['content_rank']}, network rank {row['network_rank']}, weighted degree {row['weighted_degree']}, mentions {row['mention_total']}\n"

report += """
## Interpretation

The divergence indicates that the corpus has at least two different attention systems:

1. Communication structure:
Actors who coordinate, route, schedule, or repeatedly exchange mail with many others rise in the network ranking.

2. Discursive salience:
Actors who are talked about, forwarded, discussed, or referenced in threads rise in the content ranking even if they are less central as direct communicators.

So the cleaned corpus should not treat "importance" as a single dimension. Network centrality and textual salience overlap only partly.
"""

(out_dir / "importance_divergence_report.md").write_text(report)

print(f"Wrote actor comparison for {len(comparison_rows)} actors")
print(f"Spearman correlation: {spearman:.3f}")
print(f"Top-20 overlap: {top_overlap}")
