---
title: Complete Slide Script
---

# Complete Slide Script

This is a complete slide-by-slide script for the required maximum 5-minute video presentation. It is written so the slide file can contain the short bullet points, while the longer text can go in speaker notes.

## Slide 1: Title and Research Question

**Slide title:** Email Co-presence Network Centrality in the Epstein Email Archive

**On-slide content:**

- Research question: Which actors are structurally central in the Epstein email co-presence network?
- Main contribution: looking beyond Epstein's expected centrality to identify intermediary positions
- Method: weighted co-presence network plus degree, weighted degree, and betweenness centrality

**Speaker notes:**

This project analyzes the released Epstein email archive as an informal communication metadata network. The research question is: which actors are structurally central in the email co-presence network, and what does centrality reveal beyond the expected dominance of Jeffrey Epstein? This is a good network-analysis question because it cannot be answered only by counting names. It requires looking at actor positions, repeated ties, and brokerage roles. Since the archive is centered around Epstein, it is expected that he will rank highly. The more interesting contribution is identifying which other actors structure the visible network.

## Slide 2: Critical Interpretation Caveat

**Slide title:** What an Edge Means

**On-slide content:**

- Node = actor in released email metadata
- Edge = two actors appeared in the same sender, recipient, cc, or bcc metadata
- Weight = repeated co-presence count
- Not evidence of direct communication, closeness, collaboration, shared intent, or wrongdoing

**Speaker notes:**

The most important limitation is the meaning of an edge. This is a co-presence network. If two actors are connected, it means they appeared in the same email metadata record, such as sender, recipient, cc, or bcc. It does not necessarily mean they directly communicated with each other. It also does not prove closeness, collaboration, intent, or wrongdoing. Because the subject is sensitive, every centrality result has to be interpreted as a structural pattern in released metadata, not as a claim about real-world guilt or relationships.

## Slide 3: Network Boundary and Data Construction

**Slide title:** Constructing the Network

**On-slide content:**

- Boundary: released Epstein email archive
- Actors: visible non-redacted people in email metadata
- Filtered network: 1,224 nodes and 5,426 weighted edges
- Crowded emails above 25 actors removed
- Minimum edge threshold: 2 repeated co-presences

**Speaker notes:**

The boundary of the network is the released Epstein email archive. Actors are people who appear in the email metadata after unknown and redacted labels are removed. The final filtered network has 1,224 nodes and 5,426 weighted edges, I also remove crowded emails with more than 25 actors to reduce distortion from bulk messages or distribution lists. Finally, I keep only edges with at least two repeated co-presences, so the network is based on repeated metadata association rather than one-off appearances.

## Slide 4: Adjacency Matrix

**Slide title:** Weighted Adjacency Matrix

**On-slide content:**

- Full matrix: 1,224 by 1,224
- Rows and columns are actors
- Cell value = retained repeated co-presence count
- Matrix is symmetric because the main network is undirected
- Diagonal values are zero

**Speaker notes:**

The adjacency matrix is the formal representation of the network. Each row and column is an actor. A cell value shows the number of retained email metadata records in which the two actors appeared together. For example, a value of 20 means 20 repeated co-presences in the released metadata. It does not mean 20 direct conversations. The full matrix is too large for a slide, so I include a top-15 slide-friendly version in the appendix and keep the full 1,224 by 1,224 CSV as a separate output.

## Slide 5: Centrality Measures

**Slide title:** Measures Used

**On-slide content:**

| Measure | Meaning |
|---|---|
| Degree | Number of distinct connected actors |
| Weighted degree | Total repeated co-presence strength |
| Betweenness | How often an actor lies on shortest paths |

**Speaker notes:**

I use three centrality measures because each captures a different kind of importance. Degree centrality identifies actors who are connected to many distinct others. Weighted degree captures repeated co-presence intensity, which is important because the network accounts for relationship strength. Betweenness centrality identifies actors who sit on shortest paths between others, so it is useful for finding broker or intermediary positions. For betweenness, repeated co-presence is treated as a stronger tie by using one divided by the edge weight as the distance.

## Slide 6: Main Centrality Results

**Slide title:** Centrality Rankings

**On-slide content:**

| Actor | Degree | Weighted degree | Betweenness |
|---|---:|---:|---:|
| Jeffrey Epstein | 730 | 343,926 | 0.904 |
| Lesley Groff | 390 | 110,003 | 0.246 |
| Richard Kahn | 242 | 74,112 | 0.154 |
| Stewart Oldfield | 96 | 32,757 | 0.091 |
| Brad Edwards | 24 | 903 | 0.038 |

**Speaker notes:**

The main ranking shows that Jeffrey Epstein is the dominant central actor by all three measures. This means he is connected to many distinct actors, appears repeatedly in shared metadata records, and lies on many shortest paths through the graph. However, this result is partly expected because the archive itself is Epstein-centered. The more informative part of the table is the second layer. Lesley Groff and Richard Kahn have very high degree and weighted degree, while Stewart Oldfield and Brad Edwards are important because of their brokerage positions.

## Slide 7: Beyond Epstein

**Slide title:** The Second Layer Is the Main Finding

**On-slide content:**

| Actor group | Interpretation |
|---|---|
| Lesley Groff, Richard Kahn | High-volume administrative/financial intermediaries |
| Stewart Oldfield, Paul Morris, Karyna Shuliak | Operational connectors |
| Brad Edwards, Ghislaine Maxwell, Noam Chomsky | Bridge-like cluster connectors |

**Speaker notes:**

If the analysis only said that Epstein is central, it would not add much because that is expected from the archive boundary. The stronger finding is that the network identifies different types of intermediaries. Groff and Kahn appear as high-volume administrative or financial intermediaries because they have high repeated co-presence. Oldfield, Morris, and Shuliak appear as operational connectors. Brad Edwards, Ghislaine Maxwell, and Noam Chomsky are different because their importance is more visible through betweenness, meaning they connect more distinct parts of the graph. These are metadata roles only, not claims about direct collaboration or intent.

## Slide 8: Visualization

**Slide title:** Network Visualization

**On-slide content:**

- Interactive 3D graph arranges actors in distance shells around Epstein
- Gold = focal center node
- Green = one graph step away
- Blue = two graph steps away
- Purple/pink = farther graph distance

**Speaker notes:**

The visualization helps make the centralization visible. Epstein is placed at the center because the graph is arranged around the focal actor. Other actors are placed in distance shells based on shortest-path distance in the co-presence graph. The visualization is useful for exploration, but it is not the main evidence. The actual claims come from the centrality measures, the adjacency matrix, and the robustness checks. Also, distance in the graph is metadata distance only. It does not mean real-world closeness.

## Slide 9: Simplified Broker Map

**Slide title:** Strongest Core Ties and Bridge Actors

**On-slide content:**

- Node size = weighted degree
- Edge width = repeated co-presence weight
- Only 10 key actors and selected strongest/bridge ties shown
- Dense core: Groff, Kahn, Wallace, Morris, Oldfield, Shuliak
- Bridge-like paths: Edwards, Maxwell, Chomsky
- Result: high-volume actors and brokers are not the same thing

**Speaker notes:**

This simplified broker map gives a clearer 2D view of the centrality result. The full network is too large and crowded to show on one slide, so this graph displays only 10 key actors and selected strongest or bridge-relevant ties. The realistic result is that the archive has a dense administrative-operational core plus thinner bridge paths into more specialized clusters. Groff, Kahn, Wallace, Morris, Oldfield, and Shuliak are visually embedded in the strongest repeated co-presence ties. Edwards, Maxwell, and Chomsky appear more bridge-like. This supports the betweenness result: someone can be structurally important even without being one of the highest-volume actors. Again, this is about metadata co-presence, not verified relationship closeness or collaboration.

## Slide 10: Robustness Checks

**Slide title:** Robustness Checks

**On-slide content:**

- Edge threshold increased from 2 to 100 repeated co-presences
- Epstein remains top weighted-degree actor at every threshold
- Largest connected component remains above 95%
- Directed sender-recipient check also shows Epstein as top weighted sender and recipient

**Speaker notes:**

The robustness checks test whether the centrality result depends only on weak one-off ties. When the minimum repeated co-presence threshold increases from 2 to 100, the graph gets smaller, but the largest component remains above 95 percent. Epstein also remains the top weighted-degree actor at every threshold. Since that is expected, the more useful point is that the centralized structure remains even when weak ties are removed. A directed sender-recipient check gives a similar centralization pattern, so the result is not only caused by using an undirected co-presence graph.

## Slide 11: Conclusion

**Slide title:** Conclusion

**On-slide content:**

- The network is highly centralized around Epstein
- That result is expected given the archive boundary
- The main contribution is identifying structurally important intermediaries
- Centrality reveals different roles: reach, repeated presence, and brokerage
- Results describe released metadata only, not verified real-world relationships

**Speaker notes:**

The answer to the research question is that the filtered email co-presence network is highly centralized around Epstein, but that is only the baseline result. The more important finding is the second layer of intermediaries: actors such as Lesley Groff, Richard Kahn, Stewart Oldfield, Brad Edwards, Karyna Shuliak, Ghislaine Maxwell, Paul Morris, Daphne Wallace, and Noam Chomsky. Different centrality measures show different kinds of structural importance. Degree shows broad reach, weighted degree shows repeated metadata co-presence, and betweenness shows brokerage. The conclusion must stay cautious: these results describe structural positions in released email metadata, not direct communication, closeness, collaboration, shared intent, or wrongdoing.
