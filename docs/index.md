---
title: Reading an Email Archive as Text and Network
---

<style>
  body {
    margin: 0;
    background: #fbfaf7;
    color: #18212b;
    font-family: "Times New Roman", Times, serif;
  }
  main,
  .page-content,
  .wrapper {
    max-width: none;
  }
  .paper-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(420px, 0.72fr);
    min-height: 100vh;
  }
  .paper {
    max-width: 940px;
    padding: 46px min(6vw, 76px) 80px;
  }
  .graph-side {
    position: sticky;
    top: 0;
    height: 100vh;
    border-left: 1px solid #d9d5cd;
    background: #f6f3ee;
  }
  .graph-side iframe {
    width: 100%;
    height: 100%;
    border: 0;
    display: block;
  }
  h1 {
    margin-top: 0;
    font-size: 42px;
    line-height: 1.05;
  }
  h2 {
    margin-top: 38px;
    padding-top: 12px;
    border-top: 1px solid #d9d5cd;
    font-size: 26px;
  }
  h3 {
    margin-top: 24px;
    font-size: 20px;
  }
  p,
  li {
    font-size: 17px;
    line-height: 1.55;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 18px 0 24px;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 13px;
  }
  th,
  td {
    border-bottom: 1px solid #d9d5cd;
    padding: 8px 9px;
    text-align: left;
    vertical-align: top;
  }
  img {
    max-width: 100%;
    border: 1px solid #d9d5cd;
    background: white;
  }
  .mobile-graph {
    display: none;
    height: 620px;
    border: 1px solid #d9d5cd;
    margin: 22px 0;
  }
  .mobile-graph iframe {
    width: 100%;
    height: 100%;
    border: 0;
  }
  .note {
    padding: 14px 16px;
    border-left: 4px solid #c47b28;
    background: rgba(255, 255, 255, 0.72);
  }
  @media (max-width: 1100px) {
    .paper-shell {
      display: block;
    }
    .paper {
      padding: 32px 20px 64px;
    }
    .graph-side {
      display: none;
    }
    .mobile-graph {
      display: block;
    }
    table {
      display: block;
      overflow-x: auto;
    }
  }
</style>

<div class="paper-shell">
<article class="paper" markdown="1">

# Reading an Email Archive as Text and Network

**Course:** Text Mining and Analysis  
**Group:** Gepallatok  
**Team members:** Bernath Mate, Kossuth Hugo, Medvegy Gabor, Salomon Bruno  
**Date:** May 2026  
**Project artifact:** [3D network graph](./network_3d.html) and [standalone report copy](./report.html)

## Abstract

This project analyzes the Epstein email corpus as both a textual archive and a communication network. The final analysis corpus contains 1,101,455 likely-English emails after filtering very short rows, visibly redacted senders, and likely non-English material. We combine interpretable text-mining methods, including term frequencies, TF-IDF, keyword-defined communication functions, and non-negative matrix factorization, with an email co-presence network built from sender, recipient, cc, and bcc metadata. The main result is that the archive is dominated by operational coordination rather than a single scandal-specific vocabulary: meetings and scheduling appear in 18.78% of analyzed emails, travel and logistics in 10.43%, and finance/assets in 8.46%. The filtered co-presence network contains 1,224 nodes and 5,426 edges and is highly centralized around Jeffrey Epstein and a small set of intermediaries. These findings suggest that the released email archive is best understood as a communication infrastructure archive: it records routine coordination, and that coordination is structurally concentrated around a small number of actors.

<div class="mobile-graph">
  <iframe src="./network_3d.html" title="Interactive 3D Epstein email network"></iframe>
</div>

## 1. Introduction

Email archives are often treated as administrative residue: routine messages about meetings, travel, payments, introductions, reminders, and forwarded documents. Yet precisely because email records everyday coordination, large email corpora can reveal patterns that are difficult to observe in formal reports or public narratives. They show not only what topics recur, but also how communication is organized: who appears repeatedly, who connects otherwise separate groups, and which practical functions dominate the flow of information. This project studies the Epstein email corpus from that perspective. Rather than treating the archive as a list of names or isolated messages, we analyze it as a large textual and relational dataset whose structure can be examined through text mining and network analysis.

The broader context of the project is the public importance of the Epstein case and the continuing release, indexing, and analysis of documents connected to it. The corpus is socially sensitive: it concerns a case involving serious criminal allegations, elite networks, institutional failure, and public accountability. For that reason, our goal is not to infer guilt, intention, or real-world relationships from email metadata alone. Instead, we ask a more limited but empirically answerable question: what communicative functions does the released email archive contain, and how are these communications structurally organized? This distinction matters because an email connection is not the same as a personal relationship, and absence from the corpus is not evidence of absence from the broader case. However, when analyzed carefully and transparently, aggregate email patterns can still provide useful evidence about coordination, centrality, brokerage, and thematic focus within the archive.

Our approach builds on two related research traditions. First, computational text analysis has long used document representations such as bag-of-words, term frequency, TF-IDF, and topic models to identify recurring themes in large corpora. Methods such as non-negative matrix factorization are especially useful when interpretability matters, because they represent documents through additive topic-like components that can be inspected through their highest-weighted terms. Second, social network analysis provides tools for studying relational structure, including degree, weighted degree, betweenness centrality, communities, and shortest-path distance. Classic work on centrality emphasizes that important actors are not only those with many connections, but also those positioned between otherwise separated parts of a network.

This project adds to the existing literature by applying a combined text-mining and network-science framework to the Epstein email corpus specifically. Previous work on email archives demonstrates that communication data can expose organizational structure, and previous public-facing Epstein resources provide searchable documents, named entities, and investigative context. Our contribution is to connect these perspectives in a reproducible analysis pipeline. We construct a cleaned analysis corpus, remove unknown and redacted actors from the main network summaries, filter to likely English-language emails for interpretable text analysis, and produce both statistical outputs and an interactive 3D network visualization. The result is not simply a descriptive list of frequent words or central names. Instead, it is an integrated account of what the corpus is mostly about and who structures its communication patterns.

The central research question is:

<p class="note"><strong>How can text mining and network analysis reveal the main communicative functions of the Epstein email corpus and the key actors who structured the communication network?</strong></p>

The motivation for the project is both methodological and substantive. Methodologically, the corpus is a useful case for demonstrating how text mining and network science complement each other. Word-level analysis alone can show that certain themes are frequent, but it cannot show which actors connect those themes across the communication network. Network analysis alone can identify central actors, but it cannot explain what types of communication make those actors central. Combining the two approaches gives a fuller account of the archive. Substantively, the project contributes a cautious, reproducible, and interpretable analysis of a public-interest dataset where overclaiming would be especially harmful.

## 2. Data and Corpus Construction

The project uses three main analysis tables. The first is `fact_emails.parquet`, with one row per email and cleaned text and metadata. The second is `bridge_email_people.parquet`, which links emails to participants. The third is `dim_people.parquet`, which stores canonical person identifiers and display names. The unit of analysis for text mining is the individual email. The unit of analysis for network analysis is the person-email participation link.

The raw email table contains 1,758,382 rows. The final corpus construction procedure removes rows with fewer than ten tokens, removes rows with visibly redacted senders, and applies a likely-English text filter. This produces 1,101,455 emails for the final text-mining analysis. The valid year range in this filtered corpus is 1990-2019, with a median length of 28 tokens. The data dictionary is kept as a separate CSV file rather than embedded in the report body, following the milestone feedback.

| Corpus construction step | Rows | Interpretation |
|---|---:|---|
| Raw email rows | 1,758,382 | All available email rows before final analysis filtering. |
| Rows with at least 10 tokens | 1,197,760 | Removes empty or extremely short rows that are weak text-mining units. |
| After redacted-sender filter | 1,103,480 | Removes rows where sender metadata is visibly redacted. |
| Likely-English analysis corpus | 1,101,455 | Main corpus used for final text-mining outputs. |

For network analysis, participants are linked through sender, to, cc, and bcc fields. Unknown and redacted actors are excluded from the main centrality tables and graph summaries. This decision prevents placeholder labels from dominating the network and makes the actor-level findings more interpretable. The limitation is that the resulting network describes the visible released corpus, not the complete real-world network.

## 3. Methods

### 3.1 Text Mining

The text-mining pipeline represents each email through cleaned text after removing common email artifacts, boilerplate, attachment residue, and extremely short rows. We use four interpretable representations. Term frequency identifies common corpus vocabulary after email-artifact filtering. TF-IDF identifies terms that are relatively distinctive across documents. Non-negative matrix factorization identifies broad topic-like clusters from the TF-IDF matrix. Finally, keyword-defined communication functions are used to produce interpretable theme coverage estimates for meetings/scheduling, travel/logistics, finance/assets, media/reputation, and legal/investigation.

These methods were chosen because the project requires interpretability. More complex models could potentially produce stronger classification performance, but they would make it harder to explain why a theme is present and how it relates to the underlying emails. The keyword categories are not treated as perfect classifiers. They are used as transparent indicators of broad communication functions, and their interpretation is supported by manual validation examples.

### 3.2 Network Analysis

The network pipeline builds an undirected co-presence graph. Two actors are connected when they appear in the same email metadata as sender, recipient, cc, or bcc participants. Edge weights count repeated co-presence. Crowded emails with more than 25 actors are skipped to reduce the effect of bulk messages and distribution lists. The main network is filtered to remove unknown and redacted actors.

We report degree, weighted degree, and betweenness centrality. Degree measures how many distinct actors a node is connected to. Weighted degree captures repeated communication co-presence. Betweenness centrality identifies actors positioned on shortest paths between other parts of the graph and is therefore useful for identifying brokers. We also produce a robustness check by increasing the minimum repeated co-presence threshold from 2 to 100.

The interactive 3D visualization uses a readable subset of the filtered graph. Nodes are arranged into distance shells around Jeffrey Epstein. A one-step distance means direct co-presence with Epstein in at least one email; two steps means an actor is connected through one intermediary; and so on. This is a graph-theoretic distance, not proof of a real-world relationship.

## 4. Results

### 4.1 Communication Functions

The main text-mining result is that the archive is dominated by operational coordination rather than a single scandal-specific vocabulary. The largest keyword-defined communication function is meetings and scheduling, which appears in 206,843 emails, or 18.78% of the final analysis corpus. Travel and logistics appear in 114,917 emails (10.43%), finance and assets in 93,179 emails (8.46%), media and reputation in 40,916 emails (3.71%), and legal or investigative communication in 36,473 emails (3.31%).

![Detected communication functions](./assets/report_theme_coverage.png)

| Communication function | Emails | Share | Interpretation |
|---|---:|---:|---|
| Operational coordination | 206,843 | 18.78% | Calls, meetings, appointments, reservations, and availability dominate the corpus. |
| Movement and itinerary management | 114,917 | 10.43% | Flights, hotels, cars, airports, itineraries, and arrivals/departures form a major practical layer. |
| Financial administration | 93,179 | 8.46% | Payments, banks, invoices, accounts, tax, investments, and property appear frequently. |
| Public narrative management | 40,916 | 3.71% | Press, reporters, articles, statements, interviews, and reputation-related terms form a smaller distinct theme. |
| Legal and investigative communication | 36,473 | 3.31% | Court, lawyer, filing, investigation, witness, deposition, and settlement vocabulary marks the legal layer. |

These results support the interpretation that the corpus is primarily a coordination archive. The most frequent functions are ordinary but important: arranging time, movement, money, and communication. Legal and media material are present, but they are not the dominant communication functions by volume.

### 4.2 Topic Model Interpretation

The NMF outputs point in the same direction. Several topics capture everyday interpersonal coordination, travel-service administration, itinerary timing, banking and wealth-management correspondence, calendar notifications, and legal confidentiality material. Some topics are partly contaminated by address and notification artifacts, which is itself an important validation result: the corpus remains noisy even after cleaning, so topic outputs should be interpreted as evidence of broad communication functions rather than precise semantic categories.

| Topic | Label | Share | Interpretation |
|---:|---|---:|---|
| 1 | Address/contact boilerplate | 5.39% | Office-address and contact-signature terms; useful mainly as a remaining artifact/administrative topic. |
| 2 | Travel service administration | 2.60% | American Express, itinerary, airline, and service terms point to travel-booking workflows. |
| 3 | General interpersonal coordination | 77.00% | A broad everyday-email topic containing meeting, office, phone, work, and short coordination terms. |
| 4 | Banking and wealth-management correspondence | 3.57% | Deutsche Bank, securities, trust, Park Avenue, and management terms indicate financial-administrative material. |
| 5 | Calendar and notification artifacts | 4.29% | Google/Gmail invitation and reminder terms identify automated calendar or notification material. |
| 6 | Mitchell Holdings / address cluster | 1.62% | Entity and address-specific cluster around David Mitchell / Mitchell Holdings material. |
| 7 | Travel itinerary timing | 3.88% | Paris, flight, ticket, arrive, return, leave, and trip terms indicate itinerary-specific travel messages. |
| 8 | Legal confidentiality / SDNY material | 1.67% | Confidential, Fed. Crim., SDNY, and classification terms indicate legal-document or court-related material. |

![Top TF-IDF terms](./assets/ms3_top_tfidf_terms.png)

### 4.3 Network Centralization

The filtered co-presence network contains 1,224 nodes and 5,426 edges after excluding unknown and redacted actors from the main reported graph. Jeffrey Epstein is the dominant actor by degree, weighted degree, and betweenness centrality. Lesley Groff and Richard Kahn are the next strongest brokers, followed by actors such as Stewart Oldfield, Brad Edwards, Karyna Shuliak, Ghislaine Maxwell, Paul Morris, and Daphne Wallace. This supports the network-level conclusion that the archive is not diffuse: communication is highly centralized around Epstein and a small set of intermediaries.

![Top broker nodes](./assets/ms3_network_top_brokers_filtered.png)

| Actor | Degree | Weighted degree | Betweenness | Interpretation |
|---|---:|---:|---:|---|
| Jeffrey Epstein | 730 | 343,926 | 0.904 | Dominant central ego and broker; communication is structurally centered on him. |
| Lesley Groff | 390 | 110,003 | 0.246 | Administrative intermediary with repeated co-presence and high brokerage. |
| Richard Kahn | 242 | 74,112 | 0.154 | Financial/administrative intermediary near the center of repeated exchanges. |
| Stewart Oldfield | 96 | 32,757 | 0.091 | Operational intermediary connecting parts of the co-presence graph. |
| Brad Edwards | 24 | 903 | 0.038 | Legal cluster connector with relatively high betweenness despite lower degree. |
| Karyna Shuliak | 153 | 25,042 | 0.035 | Frequent direct-contact actor with repeated participation in central communication. |
| Ghislaine Maxwell | 56 | 3,753 | 0.030 | Social/legal cluster connector with a bridge-like network position. |
| Paul Morris | 84 | 28,679 | 0.029 | Operational/administrative connector across central exchanges. |

### 4.4 Interactive 3D Network

The interactive graph below is a companion artifact to the report. It is designed for exploration while reading, not as standalone evidence. Epstein is the gold center node. Green nodes are one network step away, blue nodes are two steps away, purple nodes are three steps away, and pink nodes are four or more steps away. Node size decreases with distance from Epstein.

<iframe src="./network_3d.html" title="Interactive 3D Epstein email network" style="width:100%; height:720px; border:1px solid #d9d5cd;"></iframe>

### 4.5 Robustness Check

The edge-threshold robustness check strengthens the centralization interpretation. When the minimum repeated co-presence threshold is increased from 2 to 100, the network becomes smaller, but Epstein remains the top weighted-degree actor at every threshold. The largest connected component also remains very large, ranging from 95.75% of nodes at threshold 2 to 98.30% at threshold 100. This suggests that the centralization result is not only driven by one-off weak email co-presences.

![Network robustness across edge thresholds](./assets/network_edge_threshold_robustness.png)

| Minimum edge weight | Nodes | Edges | Largest component | Top weighted-degree actor |
|---:|---:|---:|---:|---|
| 2 | 1,224 | 5,426 | 95.75% | Jeffrey Epstein |
| 5 | 610 | 3,005 | 97.21% | Jeffrey Epstein |
| 10 | 434 | 2,116 | 97.24% | Jeffrey Epstein |
| 25 | 326 | 1,352 | 97.24% | Jeffrey Epstein |
| 50 | 271 | 969 | 98.15% | Jeffrey Epstein |
| 100 | 235 | 710 | 98.30% | Jeffrey Epstein |

## 5. Discussion

The results answer the research question in two connected ways. Text mining reveals that the corpus is mostly about practical coordination: scheduling, travel, finance, media/reputation, and legal communication. Network analysis reveals that this coordination is structurally concentrated around Epstein and a small set of intermediaries. The combination of methods is important because the textual results explain what the archive is mostly used for, while the network results explain who structures the communication.

The findings also clarify what kind of archive this is. It is not best understood as only a collection of scandal keywords or legal documents. Instead, it is a communication infrastructure archive. Its most visible patterns are routine and administrative, but those routines are precisely what make the structure observable. Travel arrangements, meetings, financial administration, and legal/media communication are not separate from the network; they are the communicative practices through which the network appears in the data.

There are business and societal implications. From an organizational-risk perspective, the project shows how routine communication metadata can reveal centralization, dependency on intermediaries, and operational patterns. From a public-interest perspective, it shows why transparent, reproducible analysis matters for sensitive document archives. The project avoids turning computational patterns into accusations, but it still provides a structured way to understand the released corpus.

## 6. Error Analysis and Threats to Validity

The main threats to validity are metadata incompleteness, redaction, short-message noise, remaining OCR/cleaning artifacts, and the interpretation of email co-presence. The 10-token filter removes 560,622 very short rows; this improves text mining, but it may exclude short operational replies. Redacted sender metadata removes another 94,280 rows after the length filter, and 179,993 person-email links contain unknown or redacted labels. These records could change actor-level conclusions if identities were known.

| Issue | Evidence | Risk | Mitigation |
|---|---|---|---|
| Very short or empty emails | 560,622 rows removed by the 10-token filter. | Short replies are weak text-mining units and can distort topic modeling. | Exclude from final text-model outputs; keep in corpus context. |
| Redacted sender metadata | 94,280 rows removed after the redacted-sender filter. | Sender-level and network findings are incomplete when identities are hidden. | Remove unknown/redacted actors from main centrality tables and report as limitation. |
| Language uncertainty | 2,025 rows removed by likely-English filtering after sender filtering. | Some short English-like messages may be excluded; some OCR-heavy English may remain noisy. | Frame final text results as English-focused. |
| Unknown/redacted actor links | 179,993 person-email links contain unknown/redacted labels. | Placeholder actors can dominate network statistics. | Filter from main network and mention metadata bias. |
| Email co-presence interpretation | Edges mean actors appeared in the same email metadata. | Network visuals can be overread as real-world relationships. | Define edge semantics clearly and repeat the caveat. |

The language filter removes 2,025 rows after sender filtering, but language detection remains uncertain for short or OCR-heavy messages. Therefore, the final text-mining results should be described as English-focused rather than multilingual. Finally, a co-presence edge means that two actors appeared in the same email metadata field, not that they had a verified real-world relationship. The network results should therefore be interpreted as communication-structure evidence within the released corpus, not as proof of social closeness, intent, or wrongdoing.

## 7. Responsible AI and LLM Use

LLMs were used to support coding, report planning, wording, and interpretation drafting. The numerical outputs were generated by local Python scripts and checked against produced CSV files, images, and graph artifacts. LLMs were not used to invent facts, assign guilt, infer private intent, or identify hidden relationships. Sensitive claims are limited to aggregate corpus and network patterns. The workflow used manual verification of the generated outputs, explicit caveats around co-presence edges, and conservative language for actor interpretation.

## 8. Conclusion and Next Steps

The research question can be answered directly: text mining reveals that the Epstein email corpus is primarily an operational coordination archive, while network analysis reveals that this coordination is highly centralized around Epstein and a small set of intermediaries. The strongest result is not a single keyword, topic, or name. It is the alignment between textual function and network structure. The archive is organized around routine coordination, and that coordination is structurally concentrated.

Future work should improve the pipeline in five ways. First, language detection should be strengthened for short and OCR-heavy messages. Second, entity resolution should be manually validated for high-centrality actors. Third, temporal network analysis should test whether centrality and theme composition shift around legally significant events. Fourth, supervised theme classification could replace transparent keyword groups after enough manually labeled examples are created. Fifth, the email co-presence network should be compared with external evidence such as court documents, flight logs, and investigative records to separate corpus-specific communication structure from broader real-world relationships.

## Appendix: Key Parameters and Outputs

| Parameter / output | Value |
|---|---|
| Minimum text length for final text analysis | 10 tokens |
| Language scope | Likely English |
| Sender-redacted rows | Excluded from final analysis corpus |
| Unknown/redacted actors | Excluded from main network tables |
| Co-presence edge rule | Two actors appear in the same email metadata |
| Crowded-email cutoff | Emails with more than 25 actors skipped for co-presence edges |
| Main network edge threshold | At least 2 repeated co-presences |
| NMF topics | 8 |
| Final corpus output | `data/ms3_clean_corpus.parquet` |
| Report-ready output directory | `outputs/ms3/report_assets/` |
| Interactive graph | `docs/network_3d.html` |

## Tasks and Responsibilities

| Team member | Responsibility |
|---|---|
| Bernath Mate | Report drafting, research-question narrowing, interpretation of exploratory findings. |
| Kossuth Hugo | Corpus statistics, metadata missingness, date coverage, and data dictionary documentation. |
| Medvegy Gabor | TF-IDF, n-grams, KWIC outputs, network baseline outputs, report asset generation, and chart integration. |
| Salomon Bruno | Preprocessing review, cleaned corpus preparation, readability and lexical diversity diagnostics. |

## References

Baker, W. E., & Faulkner, R. R. (1993). The social organization of conspiracy: Illegal networks in the heavy electrical equipment industry. *American Sociological Review, 58*(6), 837-860.

Blei, D. M., Ng, A. Y., & Jordan, M. I. (2003). Latent Dirichlet allocation. *Journal of Machine Learning Research, 3*, 993-1022.

Bird, S., Klein, E., & Loper, E. (2009). *Natural Language Processing with Python*. O'Reilly Media.

Freeman, L. C. (1978). Centrality in social networks: Conceptual clarification. *Social Networks, 1*(3), 215-239.

Granovetter, M. S. (1973). The strength of weak ties. *American Journal of Sociology, 78*(6), 1360-1380.

Hagberg, A. A., Schult, D. A., & Swart, P. J. (2008). Exploring network structure, dynamics, and function using NetworkX. In *Proceedings of the 7th Python in Science Conference*.

Jmail Data API. (2026). Public data API for the Jmail email archive.

Joulin, A., Grave, E., Bojanowski, P., & Mikolov, T. (2016). Bag of tricks for efficient text classification. arXiv:1607.01759.

Klimt, B., & Yang, Y. (2004). Introducing the Enron Corpus. *CEAS 2004*.

Lee, D. D., & Seung, H. S. (1999). Learning the parts of objects by non-negative matrix factorization. *Nature, 401*, 788-791.

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research, 12*, 2825-2830.

Pokorny, L. (2026). *Social Network Analysis of Jeffrey Epstein and Other Elite Offenders' Facilitation Networks Through a Psychopossession Lens*. Zenodo. https://doi.org/10.5281/zenodo.18795644

Porter, M. F. (2001). Snowball: A language for stemming algorithms. https://snowballstem.org

</article>

<aside class="graph-side">
  <iframe src="./network_3d.html" title="Interactive 3D Epstein email network"></iframe>
</aside>
</div>
