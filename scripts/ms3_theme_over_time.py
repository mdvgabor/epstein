from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl


Path("outputs/ms3/report_assets").mkdir(parents=True, exist_ok=True)

emails = pl.read_parquet("data/ms3_clean_corpus.parquet").filter(
    pl.col("year").is_between(2009, 2019)
)

theme_patterns = {
    "Operational coordination": r"\b(?:meeting|schedule|call|lunch|dinner|appointment|available|calendar|invite|reservation)\b",
    "Movement and itinerary management": r"\b(?:flight|airport|plane|travel|trip|itinerary|hotel|passport|car|driver|arrival|departure|island|palm beach)\b",
    "Financial administration": r"\b(?:bank|payment|invoice|account|wire|tax|investment|fund|estate|property|money|financial)\b",
    "Public narrative management": r"\b(?:press|media|article|story|news|reporter|interview|statement|public|reputation)\b",
    "Legal and investigative communication": r"\b(?:court|lawyer|attorney|legal|case|deposition|settlement|judge|filing|witness|victim|investigation)\b",
}

year_totals = emails.group_by("year").agg(pl.len().alias("year_documents"))
rows = []

for label, pattern in theme_patterns.items():
    theme_by_year = (
        emails.with_columns(
            pl.col("text_clean").str.contains(pattern, literal=False).fill_null(False).alias("hit")
        )
        .group_by("year")
        .agg(pl.col("hit").sum().alias("theme_documents"))
        .join(year_totals, on="year")
        .with_columns(
            pl.lit(label).alias("theme"),
            (pl.col("theme_documents") / pl.col("year_documents") * 100).round(3).alias("theme_share_pct"),
        )
        .select("year", "theme", "theme_documents", "year_documents", "theme_share_pct")
    )
    rows.extend(theme_by_year.iter_rows(named=True))

theme_over_time = pl.DataFrame(rows).sort("year", "theme")
theme_over_time.write_csv("outputs/ms3/report_assets/theme_over_time.csv")

plt.figure(figsize=(9, 5.2))
colors = {
    "Operational coordination": "#2f6f8f",
    "Movement and itinerary management": "#3f8f6b",
    "Financial administration": "#9a6a2f",
    "Public narrative management": "#8a5fbf",
    "Legal and investigative communication": "#b84f5f",
}

for label in theme_patterns:
    series = theme_over_time.filter(pl.col("theme") == label).sort("year")
    plt.plot(
        series["year"].to_list(),
        series["theme_share_pct"].to_list(),
        marker="o",
        linewidth=2.2,
        label=label,
        color=colors[label],
    )

plt.title("Communication Functions Over Time, 2009-2019")
plt.xlabel("Year")
plt.ylabel("Share of that year's emails (%)")
plt.xticks(range(2009, 2020), rotation=35)
plt.grid(axis="y", alpha=0.25)
plt.legend(loc="upper left", fontsize=8, frameon=False)
plt.tight_layout()
plt.savefig("outputs/ms3/report_assets/theme_over_time.png", dpi=180)
plt.close()
