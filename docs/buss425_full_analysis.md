---
title: BUSS425 Full Network Centrality Analysis
---

# BUSS425 Full Network Centrality Analysis

## Title

**Email Co-presence Network Centrality in the Epstein Email Archive**

## Research Question

This assignment asks:

> **Which actors are structurally central in the Epstein email co-presence network, and what does centrality reveal beyond the expected dominance of Jeffrey Epstein?**

This is a suitable network-analysis question because the answer depends on actor positions in a network, not only on individual attributes. In this project, the main task is not to identify who appears in the archive, but to identify who occupies structurally important positions in the communication metadata. Centrality measures are useful because they can distinguish actors who appear with many others, actors who appear repeatedly, and actors who bridge otherwise less connected parts of the graph.

The initial expectation was that Jeffrey Epstein would appear as the dominant central actor. That result is partly expected because the archive boundary is Epstein-centered. Therefore, the more interesting analytical question is what appears beyond that expected center: which intermediaries structure different parts of the visible email metadata, and whether they are central because of broad reach, repeated co-presence, brokerage, or some combination of these.

## Important Interpretation Caveat

The network in this assignment is a **co-presence network**, not a verified friendship, collaboration, or conspiracy network. An edge means that two actors appeared in the same email metadata record, such as sender, recipient, cc, or bcc. It does **not** necessarily mean that they directly communicated with each other, had a close relationship, collaborated, shared intent, or engaged in wrongdoing.

This caveat is especially important because the topic is sensitive. Centrality and proximity in this graph should be interpreted only as structural positions inside the released email metadata. The analysis describes the archive's visible communication structure, not the complete real-world network around Epstein.

## Network Boundary and Data

The network boundary is the released Epstein email archive used in the project. The relevant actors are people who appear in the email metadata after filtering unknown and redacted actor labels. This creates a bounded informal communication network based on archived metadata.

The project uses three linked data tables:

| Data table | Role in analysis |
|---|---|
| `fact_emails.parquet` | One row per email, including cleaned text and metadata |
| `bridge_email_people.parquet` | Links emails to people appearing in sender, recipient, cc, or bcc fields |
| `dim_people.parquet` | Canonical person identifiers and display names |

The final filtered network contains:

| Network property | Value |
|---|---:|
| Nodes | 1,224 |
| Weighted edges | 5,426 |
| Edge rule | Two actors appeared in the same email metadata record |
| Edge weight | Number of repeated retained co-presences |
| Actor filter | Unknown and redacted actors removed |
| Crowded-email cutoff | Emails with more than 25 actors skipped |
| Minimum edge weight | 2 repeated co-presences |

The network satisfies the assignment requirements because it has more than 10 nodes and accounts for relationship strength through weighted edges. A weight of 10, for example, means that two actors appeared together in 10 retained email metadata records. It does not mean they had 10 direct conversations.

## Adjacency Matrix Construction

The weighted adjacency matrix was constructed from the filtered co-presence edge list. Rows and columns represent actors. Each cell contains the edge weight between two actors:

- `0` means no retained repeated co-presence edge between the two actors.
- A positive value means the number of retained email metadata records where both actors appeared.
- The matrix is symmetric because the main graph is undirected.
- The diagonal is zero because actors are not connected to themselves.

The full matrix is available here:

`outputs/buss425/full_weighted_adjacency_matrix.csv`

Because the full matrix is 1,224 by 1,224, it is too large to display clearly in slides. A slide-friendly top-15 version is included here:

`docs/buss425_top15_adjacency_matrix.md`

This top-15 matrix should be used in the presentation to show how the adjacency matrix works, while the full CSV demonstrates that the complete assignment matrix exists.

## Network Measures

Three centrality measures were used.

| Measure | What it captures | Why it matters here |
|---|---|---|
| Degree centrality | Number of distinct actors connected to a node | Shows broad reach in the metadata network |
| Weighted degree | Sum of edge weights connected to a node | Shows repeated co-presence intensity |
| Betweenness centrality | How often a node lies on shortest paths between others | Identifies possible brokers or intermediaries |

Degree centrality is useful for identifying actors who appear with many different people. Weighted degree is useful because this assignment requires relationship strength, not just presence or absence of ties. Betweenness centrality is especially important because the interesting result is not only who has many ties, but who connects otherwise separate parts of the archive.

For betweenness, repeated co-presence was treated as a stronger connection by using `1 / weight` as the graph distance. This means that a repeated metadata association counts as a shorter network path than a weak one-off association.

## Main Centrality Results

The centrality table shows a strongly centralized network.

| Actor | Degree | Weighted degree | Betweenness | Interpretation |
|---|---:|---:|---:|---|
| Jeffrey Epstein | 730 | 343,926 | 0.904 | Expected central ego in this archive-bounded graph |
| Lesley Groff | 390 | 110,003 | 0.246 | Major administrative intermediary in the metadata |
| Richard Kahn | 242 | 74,112 | 0.154 | Financial/administrative intermediary |
| Stewart Oldfield | 96 | 32,757 | 0.091 | Operational intermediary |
| Brad Edwards | 24 | 903 | 0.038 | Legal-cluster connector with high betweenness relative to degree |
| Karyna Shuliak | 153 | 25,042 | 0.035 | Frequent metadata co-presence actor near the center |
| Ghislaine Maxwell | 56 | 3,753 | 0.030 | Bridge-like actor in social/legal parts of the graph |
| Paul Morris | 84 | 28,679 | 0.029 | Operational/administrative connector |
| Daphne Wallace | 114 | 22,983 | 0.028 | Administrative connector |
| Noam Chomsky | 33 | 6,589 | 0.025 | Bridge to a distinct intellectual/social communication cluster |

The first result is that Epstein is highest on all three measures. This is not surprising because the archive itself is centered around him. His high degree means he is connected to many distinct actors in the retained metadata. His high weighted degree means he repeatedly appears with many actors. His high betweenness means many shortest paths in the graph pass through him.

The more important assignment finding is the second layer of central actors. Lesley Groff and Richard Kahn have both high degree and high weighted degree, suggesting repeated metadata co-presence across many parts of the archive. Stewart Oldfield has a lower degree than Groff or Kahn but still has high betweenness, suggesting an intermediary position. Brad Edwards is especially interesting because his degree is much lower than the administrative actors, but his betweenness is relatively high. This indicates that he may connect a more distinct legal cluster to the broader graph.

Again, these are structural interpretations of metadata positions. They do not prove direct communication, collaboration, social closeness, shared intent, or responsibility.

## What the Network Reveals Beyond Epstein

If the analysis stopped at "Epstein is central," it would be weak because that result is expected. The stronger contribution is that the network separates different kinds of centrality beyond Epstein.

Lesley Groff and Richard Kahn appear as high-volume intermediaries. Their weighted degree values are much higher than most other actors, which means they repeatedly co-occur with many actors in the metadata. This is consistent with administrative and financial communication roles inside the archive.

Stewart Oldfield and Paul Morris appear as operational connectors. Their centrality is not only about appearing with many actors, but also about connecting parts of the graph through repeated co-presence paths.

Brad Edwards and Ghislaine Maxwell are different. They do not rank as high by weighted degree as the main administrative actors, but their betweenness values make them visible as connectors. This matters because betweenness can reveal actors who are not simply high-volume participants but who sit between different regions of the graph.

Therefore, the analysis reveals a layered structure:

| Layer | Actors | Network meaning |
|---|---|---|
| Expected central ego | Jeffrey Epstein | Archive-centered focal actor |
| Administrative/financial intermediaries | Lesley Groff, Richard Kahn, Daphne Wallace | High repeated metadata co-presence |
| Operational intermediaries | Stewart Oldfield, Paul Morris, Karyna Shuliak | Repeated participation across central communication records |
| Bridge-like cluster connectors | Brad Edwards, Ghislaine Maxwell, Noam Chomsky | Higher betweenness relative to their volume |

This layered interpretation is the main value of the centrality analysis. It shows that the archive is not only centered around Epstein. It is also structured through a small group of intermediaries who connect different parts of the visible metadata network.

## Network Visualization

The project includes an interactive 3D network graph:

`docs/network_3d.html`

The visualization arranges nodes in distance shells around Jeffrey Epstein:

| Color / shell | Meaning |
|---|---|
| Gold center | Epstein as the focal center node |
| Green | One graph step from Epstein |
| Blue | Two graph steps from Epstein |
| Purple | Three graph steps from Epstein |
| Pink | Four or more graph steps from Epstein |

The graph is useful because it visually communicates centralization and distance from the focal actor. However, the visualization should not be treated as standalone evidence. The analytical claims come from the centrality table, adjacency matrix, and robustness checks. A short graph distance means closeness in the co-presence network only. It does not mean real-world closeness.

## Robustness Checks

The project tests whether the centralization result depends on weak one-off ties by increasing the minimum repeated co-presence threshold.

| Minimum edge weight | Nodes | Edges | Largest component | Top weighted-degree actor |
|---:|---:|---:|---:|---|
| 2 | 1,224 | 5,426 | 95.75% | Jeffrey Epstein |
| 5 | 610 | 3,005 | 97.21% | Jeffrey Epstein |
| 10 | 434 | 2,116 | 97.24% | Jeffrey Epstein |
| 25 | 326 | 1,352 | 97.24% | Jeffrey Epstein |
| 50 | 271 | 969 | 98.15% | Jeffrey Epstein |
| 100 | 235 | 710 | 98.30% | Jeffrey Epstein |

Epstein remains the top weighted-degree actor at every threshold. Because this is expected, the main interpretation is not simply that Epstein remains central. The stronger point is that the graph remains highly connected even when weak repeated co-presence edges are removed. This supports the conclusion that the centralization pattern is not only driven by one-off metadata co-presences.

The project also includes a directed sender-recipient robustness check. In that version, edges go from sender to recipient, cc, or bcc participants. The directed graph contains 1,028 nodes and 4,815 repeated directed ties. Epstein is both the top weighted sender and the top weighted recipient. This suggests that the centralization result is not only an artifact of treating all email participants as undirected co-presences.

## Conclusion and Discussion

The research question can be answered as follows:

> The filtered Epstein email co-presence network is highly centralized around Jeffrey Epstein, but that result is partly expected because the archive boundary is Epstein-centered. The more meaningful finding is that a second layer of intermediaries structures the visible communication metadata. Lesley Groff, Richard Kahn, Stewart Oldfield, Brad Edwards, Karyna Shuliak, Ghislaine Maxwell, Paul Morris, Daphne Wallace, and Noam Chomsky become visible through different combinations of degree, weighted degree, and betweenness centrality.

The analysis is consistent with the initial expectation that Epstein would be the dominant node. However, it also adds information beyond that expectation. Centrality measures reveal that not all important actors are important in the same way. Some are central because they appear repeatedly with many others. Some are central because they connect otherwise separate parts of the graph. This distinction is exactly why multiple centrality measures are useful.

The main limitation is interpretive. Co-presence edges are not direct relationships. The graph does not prove friendship, collaboration, intent, wrongdoing, or responsibility. It only shows repeated shared appearance in released email metadata. Redactions, missing metadata, entity-resolution issues, and filtering choices may also affect actor-level rankings.

Despite these limitations, the analysis is useful for the assignment because it shows how network centrality can answer a concrete question. It identifies the expected center, then uses centrality to reveal the structure beyond that center. The final interpretation is cautious but meaningful: the archive is a centralized metadata network organized around Epstein and a small set of structurally important intermediaries.

## Assignment Component Checklist

| Required component | Where it is addressed |
|---|---|
| 1. Identify a problem or question | Research Question section |
| 2. Construct a relevant network | Network Boundary and Data section |
| 3. Use appropriate network measures | Network Measures and Main Centrality Results sections |
| 4. Visualize the network | Network Visualization section |
| 5. Conclusion/discussion | Conclusion and Discussion section |
| Include adjacency matrix | Full and top-15 adjacency matrix files |

