import re
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import polars as pl


Path("outputs/ms3/report_assets").mkdir(parents=True, exist_ok=True)


def write_csv(frame, name):
    frame.write_csv(Path("outputs/ms3/report_assets") / name)


def clean_snippet(text):
    return re.sub(r"\s+", " ", text or "").strip()[:260]


def actor_filter(frame):
    return frame.with_columns(
        pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key")
    ).filter(
        pl.col("person_id").is_not_null()
        & pl.col("person_name").is_not_null()
        & pl.col("person_id").is_in(["unknown", "redacted"]).not_()
        & pl.col("person_name_key").str.contains(r"unknown|redacted|\[redacted\]|█").not_()
    ).drop("person_name_key")


def topic_report_label(topic):
    return topic_labels[int(topic)][0]


def topic_interpretation(topic):
    return topic_labels[int(topic)][1]


def actor_report_role(name):
    return actor_roles.get(name, ("secondary actor", "Appears in the top centrality table and should be interpreted from its network position."))[0]


def actor_interpretation(name):
    return actor_roles.get(name, ("secondary actor", "Appears in the top centrality table and should be interpreted from its network position."))[1]


theme_interpretations = {
    "meetings_and_scheduling": (
        "Operational coordination",
        "The largest detected theme is ordinary coordination: calls, meetings, appointments, reservations, and availability.",
        "This supports the interpretation that the corpus is primarily a coordination archive rather than only a collection of legal or scandal-specific documents.",
    ),
    "travel_and_logistics": (
        "Movement and itinerary management",
        "Travel terms capture flights, hotels, cars, airports, itineraries, and arrivals/departures.",
        "This shows that logistical movement is one of the archive's main practical functions.",
    ),
    "finance_and_assets": (
        "Financial administration",
        "Financial vocabulary includes payments, banks, invoices, accounts, tax, investments, and property.",
        "This indicates that administrative and asset-management communication is a major component of the corpus.",
    ),
    "media_and_reputation": (
        "Public narrative management",
        "Media vocabulary captures press, reporters, articles, statements, interviews, and reputation-related terms.",
        "This suggests that public image and reputational response form a smaller but distinct communication function.",
    ),
    "legal_and_investigation": (
        "Legal and investigative communication",
        "Legal vocabulary includes lawyers, court language, filings, investigations, witnesses, depositions, and settlements.",
        "This is not the largest theme, but it marks a clear legal/investigative layer inside the archive.",
    ),
}


topic_labels = {
    1: ("Address/contact boilerplate", "Office-address and contact-signature terms; useful mainly as a remaining artifact/administrative topic."),
    2: ("Travel service administration", "American Express, itinerary, airline, and service terms point to travel-booking workflows."),
    3: ("General interpersonal coordination", "A broad everyday-email topic containing meeting, office, phone, work, and short coordination terms."),
    4: ("Banking and wealth-management correspondence", "Deutsche Bank, securities, trust, park avenue, and management terms indicate financial-administrative material."),
    5: ("Calendar and notification artifacts", "Google/Gmail invitation and reminder terms identify automated calendar or notification material."),
    6: ("Mitchell Holdings / address cluster", "Entity and address-specific cluster around David Mitchell / Mitchell Holdings material."),
    7: ("Travel itinerary timing", "Paris, flight, ticket, arrive, return, leave, and trip terms indicate itinerary-specific travel messages."),
    8: ("Legal confidentiality / SDNY material", "Confidential, Fed. Crim., SDNY, and classification terms indicate legal-document or court-related material."),
}


theme_coverage = pl.read_csv("outputs/ms3/ms3_theme_keyword_coverage.csv")
write_csv(
    theme_coverage.with_columns(
        pl.col("theme").replace({key: value[0] for key, value in theme_interpretations.items()}).alias("report_label"),
        pl.col("theme").replace({key: value[1] for key, value in theme_interpretations.items()}).alias("interpretation"),
        pl.col("theme").replace({key: value[2] for key, value in theme_interpretations.items()}).alias("report_use"),
    ).select("theme", "report_label", "documents", "document_share_pct", "interpretation", "report_use"),
    "report_theme_results.csv",
)
theme_report = pl.read_csv("outputs/ms3/report_assets/report_theme_results.csv")
theme_plot = theme_report.sort("documents").with_columns(
    pl.col("report_label").str.replace_all(" ", "\n").alias("wrapped_label")
)
plt.figure(figsize=(8.5, 4.8))
plt.barh(theme_plot["wrapped_label"].to_list(), theme_plot["document_share_pct"].to_list(), color="#3d7ea6")
plt.xlabel("Share of final analysis corpus (%)")
plt.title("Detected Communication Functions in the Epstein Email Corpus")
plt.tight_layout()
plt.savefig(Path("outputs/ms3/report_assets") / "report_theme_coverage.png", dpi=180)
plt.close()

nmf_topics = pl.read_csv("outputs/ms3/ms3_nmf_topics.csv")
write_csv(
    nmf_topics.with_columns(
        pl.col("topic").map_elements(topic_report_label, return_dtype=pl.String).alias("report_label"),
        pl.col("topic").map_elements(topic_interpretation, return_dtype=pl.String).alias("interpretation"),
    ).select("topic", "report_label", "top_terms", "documents_primary_topic", "share_of_sample_pct", "interpretation"),
    "report_nmf_topic_labels.csv",
)

actor_roles = {
    "Jeffrey Epstein": ("central ego / dominant broker", "Largest degree, weighted degree, and betweenness; communication is structurally centered on him."),
    "Lesley Groff": ("administrative intermediary", "High brokerage and repeated co-presence suggest a major coordination role."),
    "Richard Kahn": ("financial/administrative intermediary", "High degree and betweenness place him near the center of repeated administrative exchanges."),
    "Stewart Oldfield": ("operational intermediary", "Strong broker score relative to degree, connecting parts of the co-presence graph."),
    "Brad Edwards": ("legal cluster connector", "Lower degree than administrative actors but high betweenness, consistent with a bridge into legal material."),
    "Karyna Shuliak": ("frequent direct-contact actor", "High weighted degree and brokerage indicate repeated participation in central communication."),
    "Ghislaine Maxwell": ("social/legal cluster connector", "Moderate degree with high betweenness, indicating bridge-like position in the filtered graph."),
    "Paul Morris": ("operational/administrative connector", "High weighted degree and betweenness suggest repeated co-presence across central exchanges."),
    "Daphne Wallace": ("administrative connector", "High degree and weighted degree indicate repeated participation in core operational communication."),
    "Noam Chomsky": ("intellectual/social contact cluster", "Not among the highest weighted-degree actors, but betweenness suggests a bridge to a distinct communication cluster."),
}
centrality = pl.read_csv("outputs/ms3/ms3_network_centrality_filtered.csv").head(15)
write_csv(
    centrality.with_columns(
        pl.col("person_name").map_elements(actor_report_role, return_dtype=pl.String).alias("report_role"),
        pl.col("person_name").map_elements(actor_interpretation, return_dtype=pl.String).alias("interpretation"),
    ),
    "report_top_broker_interpretation.csv",
)

emails = pl.read_parquet("data/ms3_clean_corpus.parquet")
fact_emails = pl.read_parquet("data/fact_emails.parquet")
bridge = pl.read_parquet("data/bridge_email_people.parquet")

keyword_groups = {
    "meetings_and_scheduling": r"\b(?:meeting|schedule|call|lunch|dinner|appointment|available|calendar|invite|reservation)\b",
    "travel_and_logistics": r"\b(?:flight|airport|plane|travel|trip|itinerary|hotel|passport|car|driver|arrival|departure|island|palm beach)\b",
    "finance_and_assets": r"\b(?:bank|payment|invoice|account|wire|tax|investment|fund|estate|property|money|financial)\b",
    "media_and_reputation": r"\b(?:press|media|article|story|news|reporter|interview|statement|public|reputation)\b",
    "legal_and_investigation": r"\b(?:court|lawyer|attorney|legal|case|deposition|settlement|judge|filing|witness|victim|investigation)\b",
}
example_rows = []
for theme, pattern in keyword_groups.items():
    matches = emails.filter(pl.col("text_clean").str.contains(pattern, literal=False).fill_null(False))
    for row in matches.sample(n=min(6, matches.height), seed=19).select("email_id", "year", "subject", "text_clean").iter_rows(named=True):
        example_rows.append(
            {
                "theme": theme,
                "email_id": row["email_id"],
                "year": row["year"],
                "subject": clean_snippet(row["subject"]),
                "short_excerpt_for_manual_validation": clean_snippet(row["text_clean"]),
                "validation_note": theme_interpretations[theme][0],
            }
        )
write_csv(pl.DataFrame(example_rows), "manual_validation_examples_by_theme.csv")

raw_rows = fact_emails.height
ten_plus_rows = fact_emails.filter(pl.col("text_token_len") >= 10).height
after_redacted_sender = fact_emails.filter((pl.col("text_token_len") >= 10) & pl.col("sender_redacted").not_()).height
likely_english_rows = emails.height
unknown_redacted_links = bridge.with_columns(
    pl.col("person_name").fill_null("").str.to_lowercase().alias("person_name_key")
).filter(
    pl.col("person_id").is_in(["unknown", "redacted"])
    | pl.col("person_name_key").str.contains(r"unknown|redacted|\[redacted\]|█")
).height
write_csv(
    pl.DataFrame(
        [
            {
                "issue": "Very short or empty emails",
                "evidence": f"{raw_rows - ten_plus_rows:,} rows removed by the 10-token filter.",
                "risk": "Short operational replies are weak text-mining units and can distort language detection or topic modeling.",
                "mitigation": "Use them for corpus context only; exclude them from final text-model outputs.",
            },
            {
                "issue": "Redacted sender metadata",
                "evidence": f"{ten_plus_rows - after_redacted_sender:,} rows removed after the redacted-sender filter.",
                "risk": "Sender-level and network findings are incomplete when identities are hidden.",
                "mitigation": "Remove unknown/redacted actors from main centrality tables and report this as a limitation.",
            },
            {
                "issue": "Language uncertainty",
                "evidence": f"{after_redacted_sender - likely_english_rows:,} rows removed by likely-English filtering after sender filtering.",
                "risk": "Some short English-like messages may be excluded, while some OCR-heavy English messages may remain noisy.",
                "mitigation": "Frame the final text results as English-focused and avoid multilingual claims.",
            },
            {
                "issue": "Unknown/redacted actor links",
                "evidence": f"{unknown_redacted_links:,} person-email links contain unknown/redacted labels.",
                "risk": "Placeholder actors can dominate network statistics if left in the graph.",
                "mitigation": "Filter them out of the main reported network and mention that this reduces but does not eliminate metadata bias.",
            },
            {
                "issue": "Email co-presence is not a real-world tie",
                "evidence": "Edges mean actors appeared in the same email metadata, not that they met, collaborated, or had a verified relationship.",
                "risk": "Network visuals can be overread as evidence of social proximity or wrongdoing.",
                "mitigation": "Define edge semantics clearly in Methods and repeat the caveat in Results/Discussion.",
            },
        ]
    ),
    "report_error_analysis.csv",
)

filtered_links = actor_filter(bridge).join(emails.select("email_id"), on="email_id", how="semi").unique(
    subset=["email_id", "person_id", "involvement_role"]
)
name_by_person = dict(filtered_links.select("person_id", "person_name").unique().iter_rows())
edge_counts = {}
for _, group in filtered_links.select("email_id", "person_id").unique().group_by("email_id"):
    people_in_email = sorted(group["person_id"].drop_nulls().unique().to_list())
    if len(people_in_email) < 2 or len(people_in_email) > 25:
        continue
    for left, right in combinations(people_in_email, 2):
        edge_counts[(left, right)] = edge_counts.get((left, right), 0) + 1

robustness_rows = []
for threshold in [2, 5, 10, 25, 50, 100]:
    graph = nx.Graph()
    for (left, right), weight in edge_counts.items():
        if weight >= threshold:
            graph.add_edge(left, right, weight=weight)
    if graph.number_of_nodes():
        largest_component = max(nx.connected_components(graph), key=len)
        weighted_degree = dict(graph.degree(weight="weight"))
        top_actor = max(weighted_degree, key=weighted_degree.get)
        top_actor_name = name_by_person.get(top_actor, top_actor)
        largest_component_pct = round(len(largest_component) / graph.number_of_nodes() * 100, 2)
    else:
        top_actor_name = ""
        largest_component_pct = 0
    robustness_rows.append(
        {
            "edge_weight_threshold": threshold,
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "largest_component_pct": largest_component_pct,
            "top_weighted_degree_actor": top_actor_name,
            "interpretation": "Centralized structure remains if Epstein stays the top weighted-degree actor and the largest component remains substantial.",
        }
    )
write_csv(pl.DataFrame(robustness_rows), "network_edge_threshold_robustness.csv")
robustness_plot = pl.DataFrame(robustness_rows)
plt.figure(figsize=(8.5, 4.8))
plt.plot(robustness_plot["edge_weight_threshold"].to_list(), robustness_plot["nodes"].to_list(), marker="o", label="Nodes")
plt.plot(robustness_plot["edge_weight_threshold"].to_list(), robustness_plot["edges"].to_list(), marker="o", label="Edges")
plt.xscale("log")
plt.xlabel("Minimum repeated co-presence edge weight")
plt.ylabel("Count")
plt.title("Network Robustness Across Edge-Weight Thresholds")
plt.legend()
plt.tight_layout()
plt.savefig(Path("outputs/ms3/report_assets") / "network_edge_threshold_robustness.png", dpi=180)
plt.close()

(Path("outputs/ms3/report_assets") / "report_results_summary.md").write_text(
    "\n".join(
        [
            "# MS3 Report-Ready Results Summary",
            "",
            "## Core Answer",
            "Text mining shows that the Epstein email corpus is primarily an operational coordination archive. Network analysis shows that this coordination is highly centralized around Epstein and a small set of administrative, legal, financial, and social intermediaries.",
            "",
            "## Main Quantitative Results",
            f"- Final likely-English analysis corpus: {likely_english_rows:,} emails.",
            "- Filtered co-presence network: 1,224 nodes and 5,426 edges.",
            "- Largest communication-function themes: meetings/scheduling, travel/logistics, finance/assets, media/reputation, and legal/investigation.",
            "- Main network result: Jeffrey Epstein has the highest degree, weighted degree, and betweenness; Lesley Groff and Richard Kahn are the next strongest brokers.",
            "",
            "## Figures/Tables To Include",
            "- Corpus construction summary table.",
            "- Theme coverage table with interpretation.",
            "- NMF topic labels table.",
            "- Top broker interpretation table.",
            "- Network edge-threshold robustness table.",
            "- Error analysis / threats to validity table.",
            "- One network figure and one text-mining figure; keep extra outputs in the appendix.",
            "",
            "## Missingness / Limitations Sentence",
            "Metadata limitations remain important: redacted/unknown actors, short messages, OCR artifacts, and incomplete metadata mean that results describe the released email corpus, not the complete real-world Epstein network.",
            "",
        ]
    )
    + "\n"
)

(Path("outputs/ms3/report_assets") / "paste_ready_results_and_limitations.md").write_text(
    "\n".join(
        [
            "## Results",
            "",
            "The final likely-English analysis corpus contains 1,101,455 emails after removing very short rows, visibly redacted senders, and likely non-English material. The main text-mining result is that the archive is dominated by operational coordination rather than a single scandal-specific vocabulary. The largest keyword-defined communication function is meetings and scheduling, which appears in 206,843 emails, or 18.78% of the corpus. Travel and logistics appear in 114,917 emails (10.43%), finance and assets in 93,179 emails (8.46%), media and reputation in 40,916 emails (3.71%), and legal or investigative communication in 36,473 emails (3.31%). These results support the interpretation that the corpus is best read as an operational coordination archive.",
            "",
            "The topic-model outputs point in the same direction. Several NMF topics capture everyday interpersonal coordination, travel-service administration, itinerary timing, banking and wealth-management correspondence, calendar notifications, and legal confidentiality material. Some topics are partly contaminated by address and notification artifacts, which is itself an important validation result: the corpus remains noisy even after cleaning, so topic outputs should be interpreted as evidence of broad communication functions rather than precise semantic categories.",
            "",
            "The filtered co-presence network contains 1,224 nodes and 5,426 edges after excluding unknown and redacted actors from the main reported graph. Jeffrey Epstein is the dominant actor by degree, weighted degree, and betweenness centrality. Lesley Groff and Richard Kahn are the next strongest brokers, followed by actors such as Stewart Oldfield, Brad Edwards, Karyna Shuliak, Ghislaine Maxwell, Paul Morris, and Daphne Wallace. This supports the network-level conclusion that the archive is not diffuse: communication is highly centralized around Epstein and a small set of intermediaries.",
            "",
            "The edge-threshold robustness check strengthens this interpretation. When the minimum repeated co-presence threshold is increased from 2 to 100, the network becomes smaller, but Epstein remains the top weighted-degree actor at every threshold. The largest connected component also remains very large, ranging from 95.75% of nodes at threshold 2 to 98.30% at threshold 100. This suggests that the centralization result is not only driven by one-off weak email co-presences.",
            "",
            "## Error Analysis and Threats to Validity",
            "",
            "The main threats to validity are metadata incompleteness, redaction, short-message noise, remaining OCR/cleaning artifacts, and the interpretation of email co-presence. The 10-token filter removes 560,622 very short rows; this improves text mining, but it may exclude short operational replies. Redacted sender metadata removes another 94,280 rows after the length filter, and 179,993 person-email links contain unknown or redacted labels. These records could change actor-level conclusions if identities were known.",
            "",
            "The language filter removes 2,025 rows after sender filtering, but language detection remains uncertain for short or OCR-heavy messages. Therefore, the final text-mining results should be described as English-focused rather than multilingual. Finally, a co-presence edge means that two actors appeared in the same email metadata field, not that they had a verified real-world relationship. The network results should therefore be interpreted as communication-structure evidence within the released corpus, not as proof of social closeness, intent, or wrongdoing.",
            "",
        ]
    )
    + "\n"
)
