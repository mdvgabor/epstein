from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "buss425"
OUT.mkdir(parents=True, exist_ok=True)


def valid_people(frame: pl.DataFrame) -> pl.DataFrame:
    return (
        frame.with_columns(
            pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key")
        )
        .filter(
            pl.col("person_id").is_not_null()
            & pl.col("person_name").is_not_null()
            & pl.col("person_id").is_in(["unknown", "redacted"]).not_()
            & pl.col("person_name_key").str.contains(r"unknown|redacted|\[redacted\]|█").not_()
        )
        .drop("person_name_key")
    )


def build_edges() -> pd.DataFrame:
    bridge = pl.read_parquet(ROOT / "data" / "bridge_email_people.parquet")
    emails = pl.read_parquet(ROOT / "data" / "ms3_clean_corpus.parquet").select("email_id")
    links = (
        valid_people(bridge)
        .join(emails, on="email_id", how="semi")
        .select("email_id", "person_id", "person_name")
        .unique(subset=["email_id", "person_id"])
    )
    eligible_emails = (
        links.group_by("email_id")
        .len()
        .filter((pl.col("len") >= 2) & (pl.col("len") <= 25))
        .select("email_id")
    )
    links = links.join(eligible_emails, on="email_id", how="semi")

    left = links.rename({"person_id": "source", "person_name": "source_name"})
    right = links.rename({"person_id": "target", "person_name": "target_name"})
    pairs = (
        left.join(right, on="email_id")
        .filter(pl.col("source") < pl.col("target"))
        .group_by("source", "source_name", "target", "target_name")
        .len()
        .rename({"len": "weight"})
        .filter(pl.col("weight") >= 2)
        .sort(
            ["weight", "source", "source_name", "target", "target_name"],
            descending=[True, False, False, False, False],
        )
    )
    return pairs.to_pandas()


def build_matrices(edges: pd.DataFrame) -> None:
    name_by_id = {}
    for row in edges.itertuples(index=False):
        name_by_id[row.source] = row.source_name
        name_by_id[row.target] = row.target_name

    actor_ids = sorted(
        name_by_id, key=lambda person_id: (name_by_id[person_id].lower(), person_id)
    )
    actor_labels = [f"{name_by_id[person_id]} [{person_id}]" for person_id in actor_ids]
    actor_pos = {person_id: index for index, person_id in enumerate(actor_ids)}

    matrix = np.zeros((len(actor_ids), len(actor_ids)), dtype=np.int64)
    for row in edges.itertuples(index=False):
        source = actor_pos[row.source]
        target = actor_pos[row.target]
        weight = int(row.weight)
        matrix[source, target] = weight
        matrix[target, source] = weight

    adjacency = pd.DataFrame(matrix, index=actor_labels, columns=actor_labels)
    adjacency.to_csv(OUT / "full_weighted_adjacency_matrix.csv")

    centrality = pd.read_csv(ROOT / "outputs" / "ms3" / "ms3_network_centrality_filtered.csv")
    top_actor_ids = []
    for person_id in centrality["person_id"]:
        if person_id in name_by_id:
            top_actor_ids.append(person_id)
        if len(top_actor_ids) == 15:
            break
    top_actor_labels = [f"{name_by_id[person_id]} [{person_id}]" for person_id in top_actor_ids]
    top_adjacency = adjacency.loc[top_actor_labels, top_actor_labels]
    top_adjacency.to_csv(OUT / "top15_weighted_adjacency_matrix.csv")

    matrix_doc = ROOT / "docs" / "buss425_top15_adjacency_matrix.md"
    with matrix_doc.open("w", encoding="utf-8") as handle:
        handle.write("---\ntitle: BUSS425 Top-15 Weighted Adjacency Matrix\n---\n\n")
        handle.write("# BUSS425 Top-15 Weighted Adjacency Matrix\n\n")
        handle.write(
            "This slide-friendly matrix contains the first 15 centrality-ranked actors that are present "
            "in the retained weighted edge list. Cell values are weighted co-presence counts: the number "
            "of retained email metadata records in which two actors appeared together. A zero means no "
            "retained repeated co-presence edge in this filtered top-15 submatrix. The full matrix is "
            "available at `outputs/buss425/full_weighted_adjacency_matrix.csv`.\n\n"
        )
        handle.write("| Actor | " + " | ".join(top_actor_labels) + " |\n")
        handle.write("|---" + "|---:" * len(top_actor_labels) + "|\n")
        for actor, row in top_adjacency.iterrows():
            handle.write("| " + actor + " | " + " | ".join(str(int(value)) for value in row.values) + " |\n")


def main() -> None:
    edges = build_edges()
    edges.to_csv(OUT / "full_copresence_edges_filtered.csv", index=False)
    build_matrices(edges)
    print(f"Wrote {len(edges):,} weighted co-presence edges.")


if __name__ == "__main__":
    main()
