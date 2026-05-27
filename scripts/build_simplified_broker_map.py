from pathlib import Path
import math

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "buss425" / "report"
DOCS_ASSETS = ROOT / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
DOCS_ASSETS.mkdir(parents=True, exist_ok=True)


MAIN_ACTORS = [
    "jeffrey-epstein",
    "lesley-groff",
    "richard-kahn",
    "daphne-wallace-gmail",
    "stewart-oldfield-",
    "paul-morris-gmail",
    "karyna-shuliak",
    "brad-edwards-epllc",
    "ghislaine-maxwell",
    "noam-chomsky",
]

SELECTED_TIES = {
    tuple(sorted(pair))
    for pair in [
        ("jeffrey-epstein", "lesley-groff"),
        ("jeffrey-epstein", "richard-kahn"),
        ("jeffrey-epstein", "karyna-shuliak"),
        ("jeffrey-epstein", "daphne-wallace-gmail"),
        ("jeffrey-epstein", "paul-morris-gmail"),
        ("jeffrey-epstein", "noam-chomsky"),
        ("jeffrey-epstein", "ghislaine-maxwell"),
        ("lesley-groff", "karyna-shuliak"),
        ("richard-kahn", "stewart-oldfield-"),
        ("lesley-groff", "richard-kahn"),
        ("richard-kahn", "paul-morris-gmail"),
        ("brad-edwards-epllc", "jeffrey-epstein"),
    ]
}

ROLES = {
    "jeffrey-epstein": "expected center",
    "lesley-groff": "administrative/financial",
    "richard-kahn": "administrative/financial",
    "daphne-wallace-gmail": "administrative/financial",
    "stewart-oldfield-": "operational",
    "paul-morris-gmail": "operational",
    "karyna-shuliak": "operational",
    "brad-edwards-epllc": "bridge/legal/social",
    "ghislaine-maxwell": "bridge/legal/social",
    "noam-chomsky": "bridge/legal/social",
}

COLORS = {
    "expected center": "#d5a31d",
    "administrative/financial": "#2b83ba",
    "operational": "#1a9850",
    "bridge/legal/social": "#b3589e",
}

POSITIONS = {
    "jeffrey-epstein": (0.0, 0.0),
    "lesley-groff": (-1.25, 0.65),
    "richard-kahn": (-1.25, -0.45),
    "daphne-wallace-gmail": (-0.2, 1.05),
    "karyna-shuliak": (0.95, 0.65),
    "paul-morris-gmail": (-0.1, -1.1),
    "stewart-oldfield-": (-1.25, -1.35),
    "ghislaine-maxwell": (1.75, 0.15),
    "noam-chomsky": (1.65, 1.05),
    "brad-edwards-epllc": (1.65, -1.05),
}


def main() -> None:
    edges = pd.read_csv(ROOT / "outputs" / "buss425" / "full_copresence_edges_filtered.csv")
    centrality = pd.read_csv(ROOT / "outputs" / "ms3" / "ms3_network_centrality_filtered.csv")

    name_by_id = {}
    for row in edges.itertuples(index=False):
        name_by_id[row.source] = row.source_name
        name_by_id[row.target] = row.target_name

    graph = nx.Graph()
    for actor_id in MAIN_ACTORS:
        graph.add_node(actor_id, name=name_by_id.get(actor_id, actor_id))

    for row in edges.itertuples(index=False):
        if tuple(sorted((row.source, row.target))) in SELECTED_TIES:
            graph.add_edge(row.source, row.target, weight=float(row.weight))

    weighted_degree = dict(zip(centrality.person_id, centrality.weighted_degree))
    max_weighted_degree = max(weighted_degree.get(node, 1) for node in graph.nodes)
    node_sizes = [
        560 + 3300 * math.sqrt(weighted_degree.get(node, 1) / max_weighted_degree)
        for node in graph.nodes
    ]
    node_colors = [COLORS[ROLES[node]] for node in graph.nodes]

    plt.figure(figsize=(10.8, 7.0), facecolor="white")
    axis = plt.gca()
    axis.set_facecolor("white")

    max_edge_weight = max([data["weight"] for _, _, data in graph.edges(data=True)] or [1])
    for source, target, data in graph.edges(data=True):
        strength = math.sqrt(data["weight"] / max_edge_weight)
        nx.draw_networkx_edges(
            graph,
            POSITIONS,
            edgelist=[(source, target)],
            width=1 + 5.4 * strength,
            alpha=0.28 + 0.55 * strength,
            edge_color="#707070",
        )

    nx.draw_networkx_nodes(
        graph,
        POSITIONS,
        node_size=node_sizes,
        node_color=node_colors,
        edgecolors="white",
        linewidths=1.5,
        alpha=0.97,
    )

    for node, (x_pos, y_pos) in POSITIONS.items():
        y_offset = -0.24 if node == "jeffrey-epstein" else 0.2
        axis.text(
            x_pos,
            y_pos + y_offset,
            graph.nodes[node]["name"],
            fontsize=10,
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=.18", "fc": "white", "ec": "none", "alpha": 0.78},
        )

    edge_labels = {
        (source, target): f"{int(data['weight']):,}"
        for source, target, data in graph.edges(data=True)
        if data["weight"] >= 2500 or source == "brad-edwards-epllc" or target == "brad-edwards-epllc"
    }
    nx.draw_networkx_edge_labels(
        graph,
        POSITIONS,
        edge_labels=edge_labels,
        font_size=8,
        font_color="#444444",
        rotate=False,
        bbox={"boxstyle": "round,pad=.1", "fc": "white", "ec": "none", "alpha": 0.65},
    )

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label=role, markerfacecolor=color, markersize=9)
        for role, color in COLORS.items()
    ]
    plt.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(0.02, 0.98),
        frameon=True,
        fontsize=8.5,
        title="Node interpretation",
    )
    plt.title("Strongest core ties and bridge actors.", fontsize=14, pad=10)
    plt.text(
        0.02,
        0.02,
        "Presentation view: only the main interpreted actors and selected strongest/bridge ties are shown.\n"
        "Node size = weighted degree; edge width = repeated metadata co-presence. "
        "Full graph: 1,224 nodes, 5,426 weighted edges.",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#333333",
        va="bottom",
    )
    plt.xlim(-1.9, 2.15)
    plt.ylim(-1.75, 1.55)
    plt.axis("off")
    plt.tight_layout()

    for output_path in [OUT / "simplified_broker_map.png", DOCS_ASSETS / "simplified_broker_map.png"]:
        plt.savefig(output_path, dpi=240, bbox_inches="tight")

    print(f"Wrote simplified broker map with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} ties.")


if __name__ == "__main__":
    main()
