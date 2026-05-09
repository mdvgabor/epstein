---
title: MS3 Network Settings
---

# MS3 Network Settings

This file contains the network-analysis settings used for the final project paper. It is kept separate from the main report body to save space.

## Main Network Model

The main network model is an undirected weighted co-presence graph. It was chosen because the research question asks how communication is structurally organized inside the released email metadata. The graph does not claim that two actors had a verified real-world relationship; it only records that they appeared in the same email metadata.

| Component | Parameter | Value | Justification |
|---|---|---|---|
| Actor filter | Unknown/redacted actors | Removed | Prevents placeholder identities from dominating centrality rankings. |
| Co-presence rule | Edge creation | Two actors appear in the same email metadata | Captures shared communication records without claiming a real-world tie. |
| Crowded-email cutoff | Maximum actors per email | `25` | Reduces distortion from bulk emails and large distribution lists. |
| Main edge threshold | Minimum repeated co-presence | `2` | Removes one-off co-presences while preserving enough network structure. |
| Edge weight | Repeated co-presence count | Number of shared emails | Represents stronger repeated metadata association. |
| Betweenness distance | Edge distance | `1 / weight` | Treats repeated co-presence as a shorter/stronger connection. |
| Betweenness sampling | k | `min(300, number_of_nodes)` | Approximates betweenness efficiently on the full graph. |
| Betweenness normalization | normalized | `True` | Makes centrality values comparable across the graph. |
| Betweenness seed | random seed | `7` | Makes the approximate centrality calculation reproducible. |

## Directed Robustness Check

The directed robustness check uses sender-recipient edges from sender to to/cc/bcc participants. It is included to test whether the centralization result depends entirely on the undirected co-presence design.

| Component | Parameter | Value | Justification |
|---|---|---|---|
| Actor filter | Unknown/redacted actors | Removed | Keeps the directed check comparable to the main graph. |
| Directed edge rule | Edge creation | Sender to each to/cc/bcc participant | Preserves communication direction where metadata provides it. |
| Minimum edge threshold | Repeated directed ties | `2` | Removes one-off directed ties. |
| Resulting graph | Nodes | `1,028` | Actors retained after filtering. |
| Resulting graph | Directed edges | `4,815` | Repeated sender-recipient ties retained. |
| Weak connectivity | Largest weak component | `96.50%` | Shows that the directed graph remains highly connected when direction is ignored. |
| Top weighted sender | Actor | Jeffrey Epstein | Confirms centrality under a directed sender-recipient definition. |
| Top weighted recipient | Actor | Jeffrey Epstein | Confirms centrality under a directed incoming-tie definition. |
