from pathlib import Path

import networkx as nx
import polars as pl


Path("outputs/ms3/report_assets").mkdir(parents=True, exist_ok=True)

emails = pl.read_parquet("data/ms3_clean_corpus.parquet")
bridge = pl.read_parquet("data/bridge_email_people.parquet")

filtered_links = (
    bridge.with_columns(pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key"))
    .filter(
        pl.col("person_id").is_not_null()
        & pl.col("person_name").is_not_null()
        & pl.col("person_id").is_in(["unknown", "redacted"]).not_()
        & pl.col("person_name_key").str.contains(r"unknown|redacted|\\[redacted\\]|█").not_()
    )
    .drop("person_name_key")
    .join(emails.select("email_id"), on="email_id", how="semi")
    .unique(subset=["email_id", "person_id", "involvement_role"])
)

senders = filtered_links.filter(pl.col("involvement_role") == "sender").select(
    "email_id",
    pl.col("person_id").alias("source"),
    pl.col("person_name").alias("source_name"),
)
recipients = filtered_links.filter(pl.col("involvement_role").is_in(["to", "cc", "bcc"])).select(
    "email_id",
    pl.col("person_id").alias("target"),
    pl.col("person_name").alias("target_name"),
)

edges = (
    senders.join(recipients, on="email_id")
    .filter(pl.col("source") != pl.col("target"))
    .group_by("source", "source_name", "target", "target_name")
    .agg(pl.len().alias("weight"))
    .filter(pl.col("weight") >= 2)
)

graph = nx.DiGraph()
for row in edges.iter_rows(named=True):
    graph.add_edge(row["source"], row["target"], weight=float(row["weight"]))
    graph.nodes[row["source"]]["name"] = row["source_name"]
    graph.nodes[row["target"]]["name"] = row["target_name"]

if graph.number_of_nodes():
    weak_component_pct = round(len(max(nx.weakly_connected_components(graph), key=len)) / graph.number_of_nodes() * 100, 2)
    weighted_out_degree = dict(graph.out_degree(weight="weight"))
    weighted_in_degree = dict(graph.in_degree(weight="weight"))
    top_sender = max(weighted_out_degree, key=weighted_out_degree.get)
    top_recipient = max(weighted_in_degree, key=weighted_in_degree.get)
    rows = [
        ("directed_nodes", graph.number_of_nodes(), "Actors retained in the directed sender-recipient check."),
        ("directed_edges", graph.number_of_edges(), "Repeated sender-recipient ties with weight >= 2."),
        ("largest_weak_component_pct", weak_component_pct, "Share of directed nodes connected if edge direction is ignored."),
        ("top_weighted_sender", graph.nodes[top_sender]["name"], "Actor with the largest repeated outgoing sender-recipient weight."),
        ("top_weighted_recipient", graph.nodes[top_recipient]["name"], "Actor with the largest repeated incoming sender-recipient weight."),
    ]
else:
    rows = []

pl.DataFrame(rows, schema=["metric", "value", "interpretation"], orient="row").write_csv(
    "outputs/ms3/report_assets/directed_network_check.csv"
)
