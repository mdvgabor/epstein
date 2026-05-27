---
title: Email Co-presence Network Centrality in the Epstein Email Archive
---

\newpage

# Email Co-presence Network Centrality in the Epstein Email Archive

**Course:** BUSS425  
**Assignment:** 2nd Assignment: Analysis of an Informal Network  
**Group:** Gépállatok  
**Team members:** Bernáth Máté, Kossuth Hugó, Medvegy Gábor, Salomon Brúnó  
**Date:** June 2026  
**External research artifact:** 3D network graph  

\newpage

# Table of Contents

Abstract  
1. Introduction  
2. Data and Network Construction  
3. Methods  
3.1 Network Definition and Adjacency Matrix  
3.2 Centrality Measures  
3.3 Visualization and Robustness Checks  
4. Results  
4.1 Descriptive Network Structure  
4.2 Centrality Rankings  
4.3 Intermediaries Beyond the Expected Center  
4.4 Network Visualization  
4.5 Robustness Checks  
4.6 Simplified Broker Map and Additional Result  
5. Discussion  
6. Error Analysis and Threats to Validity  
7. Conclusion and Next Steps  
Appendix  
References  

# Abstract

This research analyzes the released Epstein email archive as an informal co-presence network. The purpose is to answer a network-centrality question: **which actors are structurally central in the Epstein email co-presence network, and what does centrality reveal beyond the expected dominance of Jeffrey Epstein?** The final filtered network contains 1,224 visible actors and 5,426 weighted co-presence edges after excluding unknown and redacted actor labels. An edge is created when two actors appear in the same email metadata record, such as sender, recipient, cc, or bcc, and edge weight counts repeated co-presence across retained records. This design accounts for relationship strength rather than only relationship presence.

The analysis uses degree, weighted degree, and betweenness centrality to identify different kinds of structural importance. Jeffrey Epstein is the highest-ranked actor by all three measures, with degree 730, weighted degree 343,926, and betweenness 0.904. This result is important but partly expected because the archive boundary is Epstein-centered. The more informative finding is the second layer of central actors. Lesley Groff, Richard Kahn, Stewart Oldfield, Brad Edwards, Karyna Shuliak, Ghislaine Maxwell, Paul Morris, Daphne Wallace, and Noam Chomsky become visible through different combinations of reach, repeated co-presence, and brokerage. The research therefore shows that the visible email metadata is not only centered around Epstein, but also structured through a small set of intermediaries who connect administrative, financial, operational, legal, and social parts of the archive.

The interpretation is intentionally cautious. A co-presence edge does not prove direct communication, friendship, collaboration, shared intent, responsibility, or wrongdoing. It only records that two actors appeared in the same released email metadata. The research therefore treats centrality as evidence about structure inside the released archive, not as a complete reconstruction of the broader real-world Epstein network.

# 1. Introduction

Social network analysis is useful when the main question is not only about who the actors are, but about how those actors are positioned in a system of relationships. In organizational and informal networks, outcomes can depend heavily on structure: who is connected to many others, who appears repeatedly in important flows, who bridges otherwise separate groups, and who becomes a dependency point for coordination. This research asks a problem where network analysis, and specifically centrality analysis, can help produce a better answer. The Epstein email archive provides a suitable case because the archive is large, relational, and organized through repeated communication metadata.

The research question is:

> **Which actors are structurally central in the Epstein email co-presence network, and what does centrality reveal beyond the expected dominance of Jeffrey Epstein?**

This question is deliberately phrased in two parts. The first part asks who is central. The second part asks what can be learned after acknowledging an obvious expectation: since the archive is centered around Epstein, it is not surprising if Epstein appears as the dominant node. If the analysis stopped there, it would add little. The stronger contribution is to ask which other actors are structurally important, what kinds of centrality they have, and whether they appear as high-volume participants, repeated co-presence actors, or brokers between different parts of the graph.

Email archives are often administrative residue. They contain routine messages about meetings, travel, payments, introductions, reminders, documents, legal communication, and social coordination. Precisely because these records are ordinary, they can reveal structures that are not visible from public narratives alone. Previous research on email archives, especially the Enron corpus, shows that email data can be studied not only as text but also as organizational communication data (Klimt & Yang, 2004; Diesner et al., 2005). Network analysis is particularly relevant because email metadata can be transformed into actor-level networks.

At the same time, this research requires special caution. The network constructed here is a **co-presence network**. An edge means that two actors appeared in the same email metadata record, such as sender, recipient, cc, or bcc. It does not necessarily mean that the two actors directly communicated with each other. It does not prove a close relationship, collaboration, shared intent, responsibility, or wrongdoing. This distinction is central to the entire analysis because the topic is sensitive and because network diagrams can easily be overread. The goal is to describe structural patterns in the released archive, not to infer guilt or reconstruct the complete real-world network.

The research contributes in three ways. First, it constructs a bounded informal network with more than the required minimum of ten actors. Second, it uses weighted ties, meaning that the analysis accounts for the strength of repeated co-presence rather than only the presence or absence of a tie. Third, it applies multiple centrality measures to distinguish different kinds of structural importance. Degree centrality captures broad reach, weighted degree captures repeated co-presence intensity, and betweenness centrality captures brokerage between parts of the graph.

# 2. Data and Network Construction

The network boundary is the released Epstein email archive used in the project. The network does not attempt to represent every person connected to Epstein in the real world. It represents only actors who appear in the available email metadata after filtering. This boundary is important because centrality is always relative to the network being analyzed. A person who is central in the released email archive is not necessarily central in every possible Epstein-related network.

The research uses three linked data tables produced from the local analysis pipeline. The first table, `fact_emails.parquet`, stores email-level information, including cleaned text and metadata. The second table, `bridge_email_people.parquet`, links emails to actors appearing in sender, recipient, cc, or bcc fields. The third table, `dim_people.parquet`, stores canonical person identifiers and display names. The unit of analysis for the network is the person-email participation link.

The raw email table contains 1,758,382 rows. The broader project filters very short rows, visibly redacted senders, and likely non-English rows for text-mining purposes. For the network, the main actor-level filter removes unknown and redacted actor labels so that placeholder identities do not dominate the centrality ranking. This improves interpretability, but it also means that the final network describes the visible released metadata rather than the complete underlying communication environment.

The final filtered co-presence network has the following structure:

| Network property | Value |
|---|---:|
| Nodes | 1,224 |
| Weighted edges | 5,426 |
| Edge rule | Two actors appeared in the same email metadata record |
| Edge weight | Number of retained repeated co-presences |
| Actor filter | Unknown and redacted actors removed |
| Crowded-email cutoff | Emails with more than 25 actors skipped |
| Minimum edge threshold | At least 2 repeated co-presences |

The crowded-email cutoff is used because very large email records can behave like distribution lists. If an email contains many actors, connecting every actor to every other actor may create artificial density. The cutoff therefore reduces the risk that bulk messages dominate the network structure. The minimum edge threshold of two repeated co-presences is also important. It removes one-off metadata associations and focuses the analysis on repeated appearances.

The edge weight is the main way the analysis accounts for relationship strength. For example, if two actors appear together in 50 retained email metadata records, their edge has weight 50. This does not mean that they communicated directly 50 times; it means that the released metadata places them together 50 times. The wording matters because the network is a representation of metadata co-presence, not verified social closeness.

# 3. Methods

Before presenting the results, it is necessary to define the main network terms. A **node** is an actor in the network. An **edge** is a connection between two actors. In this research, an edge means co-presence in the same email metadata record. A **weighted edge** is an edge with a numerical value representing repeated co-presence. A **centrality measure** is a statistic that describes how structurally important a node is in a network. A **broker** is an actor whose position connects otherwise less connected parts of the graph.

## 3.1 Network Definition and Adjacency Matrix

The network is an undirected weighted co-presence graph. It is undirected because the main edge definition does not distinguish direction. If two actors appear in the same metadata record, they are connected regardless of whether one is sender and the other is recipient, or whether both appear in recipient-related fields. This is a conservative choice for the main analysis because the goal is to describe shared participation in email records, not to infer direct message flow.

The adjacency matrix is the formal representation of the graph. Rows and columns represent actors. Each cell contains the weight of the edge between the row actor and the column actor. A zero means that no retained repeated co-presence edge exists between those two actors. Since the graph is undirected, the matrix is symmetric: the value from actor A to actor B is the same as the value from actor B to actor A. The diagonal is zero because actors are not connected to themselves.

The full weighted adjacency matrix is stored as:

`outputs/buss425/full_weighted_adjacency_matrix.csv`

The full matrix is 1,224 by 1,224, which is too large to display clearly in a slide or printed report. For presentation purposes, a top-15 matrix is also provided:

`docs/buss425_top15_adjacency_matrix.md`

The top-15 matrix is only a readable excerpt. The full CSV is the actual matrix used for the analysis.

## 3.2 Centrality Measures

The analysis uses three centrality measures: degree, weighted degree, and betweenness centrality. These were chosen because they answer different versions of the centrality question.

Degree centrality measures how many distinct actors a node is connected to. In this research, a high-degree actor appears with many different actors in the retained metadata. Degree is useful for measuring breadth of connection, but it does not distinguish between repeated and occasional co-presences.

Weighted degree adds the weights of a node's edges. It captures repeated co-presence intensity. This is especially important because the network should account for relationship strength. In this case, relationship strength means repeated metadata co-presence, not necessarily relationship closeness.

Betweenness centrality measures how often a node lies on shortest paths between other nodes. It identifies actors who may serve as brokers or bridges in the graph. In a co-presence network, high betweenness suggests that an actor connects parts of the metadata network that would otherwise be farther apart. For weighted betweenness, repeated co-presence is treated as a stronger connection by using `1 / weight` as the distance. This means that frequently repeated co-presence creates shorter paths than weaker co-presence.

The three measures are complementary. A node can have high degree but low betweenness if it is broadly connected inside one dense area. Another node can have lower degree but meaningful betweenness if it links separate clusters. This distinction is central to the research question because the goal is not simply to count contacts but to understand structural roles.

## 3.3 Visualization and Robustness Checks

The project includes an interactive 3D visualization of a readable subset of the graph. The visualization arranges nodes into distance shells around Jeffrey Epstein. Epstein is shown as the center node. Actors one graph step away appear in the first shell, actors two steps away in the second shell, and so on. This helps make the centralized structure easier to see.

However, the visualization is not treated as standalone evidence. The analytical claims rely on the adjacency matrix, centrality table, and robustness checks. Visual proximity in the graph is graph-theoretic proximity only. It does not prove direct communication, real-world closeness, or shared intent.

The robustness checks test whether the main conclusion depends on weak ties or on the undirected co-presence design. First, the minimum repeated co-presence threshold is increased from 2 to 100. This checks whether centralization remains when only stronger repeated ties are retained. Second, a directed sender-recipient graph is used as an alternative check. In that graph, edges go from senders to to/cc/bcc participants. This does not replace the main graph, but it tests whether the centralization result appears when direction is preserved.

# 4. Results

## 4.1 Descriptive Network Structure

The filtered network contains 1,224 actors and 5,426 weighted co-presence edges. This makes the network large enough for meaningful centrality analysis. The edge threshold removes one-off co-presence, so the graph is built from repeated metadata association. The largest connected component includes most of the retained actors, which means that the graph is not just a collection of isolated fragments. Instead, the visible metadata forms a connected communication structure around a central core.

The network is highly centralized. This is partly expected because the archive is organized around Epstein. The important question is therefore not whether Epstein is central, but how much of the remaining structure can be explained by other intermediaries. The centrality results show that several actors occupy structurally important positions beyond the focal actor.

## 4.2 Centrality Rankings

The main centrality results are shown below.

![Figure 1: Top broker nodes by approximate weighted betweenness centrality](assets/ms3_network_top_brokers_filtered.png)

| Actor | Degree | Weighted degree | Betweenness |
|---|---:|---:|---:|
| Jeffrey Epstein | 730 | 343,926 | 0.904 |
| Lesley Groff | 390 | 110,003 | 0.246 |
| Richard Kahn | 242 | 74,112 | 0.154 |
| Stewart Oldfield | 96 | 32,757 | 0.091 |
| Brad Edwards | 24 | 903 | 0.038 |
| Karyna Shuliak | 153 | 25,042 | 0.035 |
| Ghislaine Maxwell | 56 | 3,753 | 0.030 |
| Paul Morris | 84 | 28,679 | 0.029 |
| Daphne Wallace | 114 | 22,983 | 0.028 |
| Noam Chomsky | 33 | 6,589 | 0.025 |

Jeffrey Epstein has the highest degree, highest weighted degree, and highest betweenness centrality. His degree of 730 means that he is connected to 730 distinct actors in the retained co-presence graph. His weighted degree of 343,926 means that his ties are not only numerous but repeated many times across the metadata. His betweenness score of 0.904 means that he lies on a large share of shortest paths between other actors.

This result confirms that the graph reflects the archive boundary, but it should not be overinterpreted. Since the archive is Epstein-centered, Epstein's dominance is not surprising. It is better understood as the baseline result. The more interesting interpretation comes from the next-ranked actors.

Lesley Groff has degree 390, weighted degree 110,003, and betweenness 0.246. This combination indicates both broad reach and repeated co-presence. Richard Kahn has degree 242, weighted degree 74,112, and betweenness 0.154, also suggesting a structurally important administrative or financial position in the visible metadata. Stewart Oldfield has lower degree but still high betweenness, which points toward an intermediary position. Brad Edwards has much lower degree and weighted degree than the highest-volume actors, but his betweenness is relatively high, suggesting a bridge-like position into a legal cluster.

## 4.3 Intermediaries Beyond the Expected Center

The key finding is that the second layer of central actors is not homogeneous. Different actors are central in different ways.

Lesley Groff and Richard Kahn appear as high-volume intermediaries. Their high weighted degree values show repeated co-presence across many retained email records. This suggests that their structural importance comes not only from the number of distinct actors connected to them, but from repeated participation in central metadata records. They are not simply present in the network; they are strongly connected through repeated weighted ties.

Stewart Oldfield, Paul Morris, and Karyna Shuliak appear as operational connectors. Their positions indicate repeated participation in the central communication structure, although not always at the same scale as Groff or Kahn. They help show that the network is not a simple star around Epstein. Instead, there are secondary actors who structure parts of the graph.

Brad Edwards, Ghislaine Maxwell, and Noam Chomsky illustrate why betweenness matters. These actors do not necessarily have the highest weighted degree, but their betweenness values make them visible as connectors between parts of the graph. Brad Edwards is especially clear because his degree is only 24, yet his betweenness is the fifth-highest in the reported table. This means he is not central because he appears with the largest number of actors. He is central because of where he sits in the network.

This distinction is the main value of using multiple centrality measures. Degree and weighted degree identify high-volume actors. Betweenness identifies bridge positions. Together, they reveal a layered network structure:

| Layer | Actors | Network meaning |
|---|---|---|
| Expected central ego | Jeffrey Epstein | Archive-centered focal actor |
| Administrative/financial intermediaries | Lesley Groff, Richard Kahn, Daphne Wallace | High repeated metadata co-presence |
| Operational intermediaries | Stewart Oldfield, Paul Morris, Karyna Shuliak | Repeated participation across central records |
| Bridge-like cluster connectors | Brad Edwards, Ghislaine Maxwell, Noam Chomsky | Higher betweenness relative to communication volume |

This interpretation answers the research question more fully than a single centrality ranking. It shows that the network is centralized around Epstein, but also that important intermediary positions exist beyond him.

## 4.4 Network Visualization

The interactive 3D visualization is used as a companion artifact. It arranges the graph into distance shells around Epstein. The gold center node represents Epstein. Green nodes are one graph step away, blue nodes are two graph steps away, purple nodes are three graph steps away, and pink nodes are four or more graph steps away.

The visualization makes two features clear. First, the graph has a strong central core. Second, many actors are connected to the broader network through a relatively small number of intermediary paths. This supports the centrality interpretation because the visual structure is consistent with the numerical rankings.

However, the visualization also creates interpretive risk. Network diagrams can make actors look socially close even when the actual edge definition is much narrower. In this research, graph distance means co-presence-network distance only. A one-step connection to Epstein means that an actor appeared with Epstein in at least one retained metadata record. It does not prove that the actor had a close personal relationship with him. For this reason, the visualization should be used to illustrate structure, not to make claims beyond the data.

## 4.5 Robustness Checks

The first robustness check increases the minimum repeated co-presence threshold from 2 to 100. The results are:

![Figure 2: Network robustness across edge thresholds](assets/network_edge_threshold_robustness.png)

| Minimum edge weight | Nodes | Edges | Largest component | Top weighted-degree actor |
|---:|---:|---:|---:|---|
| 2 | 1,224 | 5,426 | 95.75% | Jeffrey Epstein |
| 5 | 610 | 3,005 | 97.21% | Jeffrey Epstein |
| 10 | 434 | 2,116 | 97.24% | Jeffrey Epstein |
| 25 | 326 | 1,352 | 97.24% | Jeffrey Epstein |
| 50 | 271 | 969 | 98.15% | Jeffrey Epstein |
| 100 | 235 | 710 | 98.30% | Jeffrey Epstein |

As the threshold increases, the network becomes smaller because weaker repeated ties are removed. However, the largest connected component remains very large at every threshold, and Epstein remains the top weighted-degree actor. Again, Epstein's persistence is expected. The more useful interpretation is that the centralized structure remains visible even when one-off and weaker co-presence ties are excluded.

The second robustness check uses a directed sender-recipient graph. This alternative graph has 1,028 nodes and 4,815 repeated directed ties at the same minimum edge weight of 2. Epstein is both the top weighted sender and the top weighted recipient. This suggests that the centralization result is not only produced by treating all metadata co-presence as undirected. It also appears when direction is preserved.

Together, these checks increase confidence that the main structural finding is not only a modeling artifact. The results remain consistent when edge strength thresholds change and when a directed graph is considered. However, these checks do not remove the core interpretive limitation: all results still depend on released metadata.

## 4.6 Simplified Broker Map and Additional Result

To make the centrality results easier to interpret, the project also includes a simplified broker map. This graph is not a separate dataset and should not be interpreted as the full network. It is a presentation view extracted from the same filtered weighted co-presence network used in the centrality analysis. The full graph has 1,224 nodes and 5,426 weighted edges, which is too large and crowded to show clearly on one page. The simplified graph therefore displays only the main interpreted actors and selected strongest or bridge-relevant ties.

![Figure 3: Simplified broker map showing selected strongest ties and bridge actors](assets/simplified_broker_map.png)

In this graph, node size represents weighted degree. Larger nodes appear with others more repeatedly in the retained metadata. Edge width represents repeated co-presence strength. Node color represents the interpretation category used in the report: Epstein is shown as the expected center; administrative and financial intermediaries are shown separately from operational intermediaries; and bridge-like legal, social, or intellectual cluster connectors are shown as a third category.

The realistic additional result suggested by this simplified view is that the network has a **dense administrative-operational core plus several thinner bridge paths into more specialized clusters**. Lesley Groff, Richard Kahn, Daphne Wallace, Paul Morris, Stewart Oldfield, and Karyna Shuliak are visually embedded in the strongest repeated metadata co-presence ties. This supports the interpretation that these actors are not only individually central, but also part of the same core coordination environment in the released metadata.

By contrast, Brad Edwards, Ghislaine Maxwell, and Noam Chomsky appear more bridge-like in the visual extract. Their positions are less about being in the densest administrative core and more about connecting the core to more distinct peripheral areas. This is consistent with the betweenness centrality result. Brad Edwards, for example, has far lower weighted degree than Groff or Kahn, but his betweenness score is high enough to place him among the top reported brokers. The graph therefore gives a realistic visual explanation of a key centrality lesson: a person can be structurally important even without being one of the highest-volume actors.

This section provides the main visual result. The message should be stated carefully: the graph shows centrality and brokerage in the released email metadata, not verified relationship closeness or collaboration. The visual result supports the conclusion that the archive has a dense coordination core and several bridge-like paths into more specialized parts of the network.

# 5. Discussion

The research question can be answered in two steps. First, the network is highly centralized around Jeffrey Epstein. This is shown by his top rank in degree, weighted degree, and betweenness centrality. Second, and more importantly, the network reveals a set of structurally important intermediaries beyond Epstein. These actors are not central in identical ways. Some have broad reach, some have repeated co-presence, and some have broker positions.

This finding is consistent with social network theory. Central actors often matter because they control or concentrate access to others, while brokers matter because they connect otherwise separated parts of a network (Freeman, 1978; Granovetter, 1973; Burt, 1992). Brokerage is especially useful because it shows why an actor with fewer direct ties can still be structurally important. Brad Edwards is an example: his degree is lower than several administrative actors, but his betweenness is high enough to make him visible as a connector.

The findings also show why weighted ties matter. If the analysis used only binary ties, it would treat a single co-presence and thousands of repeated co-presences as equivalent. Weighted degree avoids that problem by accounting for repeated metadata association. This is why Lesley Groff and Richard Kahn stand out: they are not only connected to many actors, but repeatedly appear in central metadata records.

The research also shows why the expected result should be handled carefully. It would be misleading to present Epstein's centrality as surprising. The archive boundary makes it likely. A stronger interpretation is that Epstein's centrality validates the basic structure of the graph, while the second layer of central actors provides the substantive contribution. The research is therefore not only about identifying the top node. It is about using centrality measures to interpret the structure around and beyond that top node.

From a broader perspective, the analysis shows how social network methods can help make sense of large document archives. Email metadata can reveal patterns of coordination even when the text itself is noisy or fragmented. However, the analysis also shows the limits of computational interpretation. A graph can identify structural positions, but it cannot by itself explain motives, legal responsibility, or real-world relationships.

# 6. Error Analysis and Threats to Validity

The most important threat to validity is the interpretation of co-presence edges. An edge means two actors appeared in the same email metadata record. It does not necessarily mean that they directly communicated or had a close relationship. This risk is especially high in visual network analysis because viewers may assume that spatial closeness in a graph means social closeness in real life. The report addresses this by repeating the edge definition in the abstract, methods, results, visualization interpretation, and conclusion.

A second threat is metadata incompleteness. Unknown and redacted actor labels are removed from the main network. This makes the results more interpretable, but it can also hide meaningful structure. If redacted actors were identifiable, some centrality rankings could change. Therefore, the results should be understood as applying to the visible released metadata only.

A third threat is entity resolution. Large archives often contain multiple spellings, email addresses, aliases, or inconsistent labels for the same person. The project uses canonical person identifiers, but entity resolution is never perfect. If one actor is split across multiple identifiers, their centrality may be underestimated. If two actors are incorrectly merged, centrality may be overestimated.

A fourth threat is the crowded-email cutoff. Excluding emails with more than 25 actors reduces distortion from bulk messages, but it may also remove some meaningful large-group communications. The cutoff is a modeling choice. It is justified because the research focuses on interpretable informal network structure, but it still affects the final graph.

A fifth threat is boundary specification. The network is bounded by the released Epstein email archive. This is a defensible analytical boundary, but it is not the same as the complete real-world network. A person absent from the email archive may still have been important elsewhere, and a person central in the archive may not be central in every other context.

| Issue | Risk | Mitigation |
|---|---|---|
| Co-presence interpretation | Edges may be overread as real relationships | Define edge semantics repeatedly and use cautious wording |
| Redacted actors | Hidden structure may affect centrality | Remove placeholders from main tables and report limitation |
| Entity resolution | Actor rankings may be split or merged | Use canonical person identifiers and interpret rankings cautiously |
| Crowded-email cutoff | Some group communications are excluded | Use cutoff to reduce bulk-message distortion and document the choice |
| Archive boundary | Results may not generalize beyond released metadata | Frame findings as structure inside the released archive |

These limitations do not make the analysis invalid. They define what the analysis can and cannot claim. The network is useful for describing structural centrality in the released email metadata. It is not sufficient for making claims about private relationships, legal responsibility, or hidden intent.

# 7. Conclusion and Next Steps

This research shows how centrality measures can identify structurally important actors in an informal communication metadata network. The filtered Epstein email co-presence graph contains 1,224 actors and 5,426 weighted edges. Epstein is the dominant actor by degree, weighted degree, and betweenness centrality, but this result is partly expected because the archive boundary is centered on him.

The more meaningful finding is the second layer of intermediaries. Lesley Groff and Richard Kahn stand out as high-volume administrative and financial intermediaries. Stewart Oldfield, Paul Morris, and Karyna Shuliak appear as operational connectors. Brad Edwards, Ghislaine Maxwell, and Noam Chomsky are visible because of their bridge-like positions. These differences show why multiple centrality measures are useful: degree, weighted degree, and betweenness each reveal a different form of structural importance.

The conclusion is therefore cautious but substantive. The archive is not only a collection of isolated email records. It has a visible network structure centered around Epstein and shaped by a small set of intermediaries. At the same time, this structure exists inside released metadata. A co-presence edge does not prove direct communication, closeness, collaboration, shared intent, or wrongdoing.

Future work could improve the analysis in four ways. First, entity resolution should be manually validated for all high-centrality actors. Second, centrality could be analyzed over time to test whether intermediary roles change across different periods. Third, centrality could be compared across communication functions, such as legal, financial, travel, and scheduling records. Fourth, the email co-presence network could be compared with external documents, such as court records or flight logs, to separate archive-specific structure from broader real-world relationships.

# Appendix

## Component Checklist

| Required component | Where it is addressed |
|---|---|
| 1. Identify a problem or question | Introduction and research question |
| 2. Construct a relevant network | Data and Network Construction |
| 3. Use appropriate network measures | Methods and Results |
| 4. Visualize the network | Network Visualization |
| 5. Conclusion/discussion | Discussion and Conclusion |
| Include adjacency matrix | `outputs/buss425/full_weighted_adjacency_matrix.csv` |

## Key Parameters and Outputs

| Parameter or output | Value |
|---|---|
| Main graph type | Undirected weighted co-presence graph |
| Node definition | Visible actor in email metadata |
| Edge definition | Two actors appear in the same email metadata record |
| Edge weight | Number of repeated retained co-presences |
| Unknown/redacted actors | Removed from main network |
| Crowded-email cutoff | Emails with more than 25 actors skipped |
| Minimum edge threshold | At least 2 repeated co-presences |
| Full weighted adjacency matrix | `outputs/buss425/full_weighted_adjacency_matrix.csv` |
| Top-15 display matrix | `docs/buss425_top15_adjacency_matrix.md` |
| Centrality table | `outputs/ms3/ms3_network_centrality_filtered.csv` |
| Interactive graph | `docs/network_3d.html` |
| Simplified broker map | `outputs/buss425/report/simplified_broker_map.png` |

## Responsible Use Statement

Computational tools and LLMs were used to support coding, report planning, wording, and interpretation drafting. Numerical claims, tables, and figures were generated from local scripts and checked against project outputs. LLMs were not used to invent facts, assign guilt, infer private intent, or identify hidden relationships. Sensitive claims are limited to aggregate corpus and network patterns. The analysis uses explicit caveats around co-presence edges and conservative language for actor interpretation.

# References

Baker, W. E., & Faulkner, R. R. (1993). The social organization of conspiracy: Illegal networks in the heavy electrical equipment industry. *American Sociological Review, 58*(6), 837-860.

Burt, R. S. (1992). *Structural Holes: The Social Structure of Competition*. Harvard University Press.

Diesner, J., Frantz, T. L., & Carley, K. M. (2005). Communication networks from the Enron email corpus: "It's always about the people. Enron is no different." *Computational and Mathematical Organization Theory, 11*(3), 201-228.

Freeman, L. C. (1978). Centrality in social networks: Conceptual clarification. *Social Networks, 1*(3), 215-239.

Granovetter, M. S. (1973). The strength of weak ties. *American Journal of Sociology, 78*(6), 1360-1380.

Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). Exploring network structure, dynamics, and function using NetworkX. In *Proceedings of the 7th Python in Science Conference*.

Klimt, B., & Yang, Y. (2004). Introducing the Enron Corpus. In *Proceedings of the First Conference on Email and Anti-Spam*.

Volscho, T. (2025). Elite sex trafficking as a crime of the powerful: A comparative case study of Jeffrey Epstein and Peter Nygard's alleged trafficking enterprises. *Deviant Behavior*.
