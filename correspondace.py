import itertools
import math
import re

import polars as pl


def extract_email(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.search(r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})", value.lower())
    if match is None:
        return None
    return match.group(1).replace("@grnail.", "@gmail.").replace("@gmall.", "@gmail.").replace(".corn", ".com").replace(".con", ".com")


def name_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.lower()
    cleaned = re.sub(r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})", " ", cleaned)
    cleaned = cleaned.replace("&", "and")
    cleaned = re.sub(r"mailto:", " ", cleaned)
    cleaned = re.sub(r"[^a-z]+", "", cleaned)
    return cleaned or None


normalized = pl.read_parquet("data/emails.normalized.parquet")
targets = pl.read_csv("data/famous_correspondents.csv")

addresses = pl.concat(
    [
        normalized.select(
            "id",
            pl.lit("sender").alias("address_role"),
            pl.col("sender_normalized").alias("value"),
        ),
        normalized.select(
            "id",
            pl.lit("to_recipients").alias("address_role"),
            pl.col("to_recipients_normalized").alias("value"),
        ).explode("value"),
        normalized.select(
            "id",
            pl.lit("cc_recipients").alias("address_role"),
            pl.col("cc_recipients_normalized").alias("value"),
        ).explode("value"),
        normalized.select(
            "id",
            pl.lit("bcc_recipients").alias("address_role"),
            pl.col("bcc_recipients_normalized").alias("value"),
        ).explode("value"),
    ],
    how="diagonal_relaxed",
).filter(pl.col("value").is_not_null()).with_columns(
    pl.col("value").map_elements(extract_email, return_dtype=pl.String).alias("email"),
    pl.col("value").map_elements(name_key, return_dtype=pl.String).alias("name_key"),
)

jeff_sender_ids = set(
    addresses.filter(
        (pl.col("address_role") == "sender")
        & (
            pl.col("email").is_in(["jeevacation@gmail.com", "jeeproject@yahoo.com", "jeeyacation@gmail.com"])
            | pl.col("name_key").is_in(["jeffreye", "jeffreyepstein", "jepstein", "jeffrey"])
        )
    ).get_column("id")
)
jeff_recipient_ids = set(
    addresses.filter(
        pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"])
        & (
            pl.col("email").is_in(["jeevacation@gmail.com", "jeeproject@yahoo.com", "jeeyacation@gmail.com"])
            | pl.col("name_key").is_in(["jeffreye", "jeffreyepstein", "jepstein", "jeffrey"])
        )
    ).get_column("id")
)

search = {
    "Kathryn Ruemmler": {
        "include": ["ruemmler", "kathy", "kathryn"],
        "exclude": [],
        "prefer": ["kathyruemmler", "kathrynruemmler", "kathyruemmlerunknown", "ruemmlerkathydc", "kthyruemmler"],
    },
    "Lawrence Krauss": {
        "include": ["krauss", "lawrence", "lawkrauss", "drkrauss"],
        "exclude": ["alexandra", "marco"],
        "prefer": ["lawrencekrauss", "lawrencekraussunknown", "lawrencemkrauss", "lawkrauss", "drkrauss", "krauss"],
    },
    "Ariane de Rothschild": {
        "include": ["rothschild", "ariane", "ader"],
        "exclude": ["alice", "nathaniel", "benjamin"],
        "prefer": ["aderothschild", "arianederothschild", "arianaderothschild", "aderothschildunknown", "aderothschildredacted"],
    },
    "Thomas Pritzker": {
        "include": ["pritzker", "tom", "thomas", "tpritzker"],
        "exclude": ["nicholas", "nick", "jb", "jennifer", "liesel", "penny"],
        "prefer": ["pritzkertom", "tompritzker", "thomaspritzker", "pritzkertomi", "tompritzkerl"],
    },
    "Michael Wolff": {
        "include": ["wolff", "michael"],
        "exclude": [],
        "prefer": ["michaelwolff", "michaelwolffunknown", "michaelwolffredacted", "michaewolff", "wolff"],
    },
    "Noam and Valeria Chomsky": {
        "include": ["chomsky", "noam", "valeria"],
        "exclude": ["harry", "diana", "avi"],
        "prefer": ["noamchomsky", "valeriachomsky", "valeriachomskyunknown", "noamchomskyunknown"],
    },
    "Larry Summers": {
        "include": ["summers", "larry", "lawrence", "lhs"],
        "exclude": ["amy", "julie", "shample"],
        "prefer": ["larrysummers", "lawrencehsummers", "lawrencesummers", "larrysummersunknown", "lhsummers", "ihsummers"],
    },
    "Steve Bannon": {
        "include": ["bannon", "steve"],
        "exclude": ["sean"],
        "prefer": ["stevebannon", "stevebannonunknown", "stevebannonredacted", "stevbannon"],
    },
    "Reid Hoffman": {
        "include": ["hoffman", "reid", "reed", "rhoffman"],
        "exclude": ["moshe", "auren", "carol", "donald", "maja", "patrik", "mitch"],
        "prefer": ["reidhoffman", "reedhoffman", "reidhoffmanunknown", "rhoffman"],
    },
    "Bill Gates": {
        "include": ["gates", "bill", "billg"],
        "exclude": ["boris", "melinda", "rick", "gayle", "front", "sally", "richard", "jenna", "dale"],
        "prefer": ["billgates", "billgatesredacted"],
    },
    "Elon Musk": {
        "include": ["musk", "elon", "erm"],
        "exclude": ["kimbal", "kimbal", "maye", "talulah"],
        "prefer": ["elonmusk", "etonmusk", "elonmuskredacted", "elonmuskelonspaexcom"],
    },
}

role_is_recipient = pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"])
name_counts = addresses.group_by("name_key").len().filter(pl.col("name_key").is_not_null())
people = []

for target in targets.iter_rows(named=True):
    rules = search[target["name"]]
    include_match = pl.any_horizontal(*[pl.col("name_key").str.contains(token, literal=True) for token in rules["include"]])
    exclude_match = pl.any_horizontal(*[pl.col("name_key").str.contains(token, literal=True) for token in rules["exclude"]]) if rules["exclude"] else pl.lit(False)
    candidates = (
        name_counts.filter(include_match & ~exclude_match)
        .sort("len", descending=True)
        .get_column("name_key")
        .to_list()
    )
    candidates = [key for key in rules["prefer"] if key in candidates] + [key for key in candidates if key not in rules["prefer"]]
    candidates = candidates[:12]

    sender_ids_by_key = {
        key: set(addresses.filter((pl.col("address_role") == "sender") & (pl.col("name_key") == key)).get_column("id"))
        for key in candidates
    }
    recipient_ids_by_key = {
        key: set(addresses.filter(role_is_recipient & (pl.col("name_key") == key)).get_column("id"))
        for key in candidates
    }

    best_score = None
    best_keys = []
    best_sent = 0
    best_received = 0
    best_total = 0
    best_ratio = 0.0

    for width in range(1, min(len(candidates), 9) + 1):
        for picked in itertools.combinations(candidates, width):
            sent = len(set().union(*(sender_ids_by_key[key] for key in picked)) & jeff_recipient_ids)
            received = len(set().union(*(recipient_ids_by_key[key] for key in picked)) & jeff_sender_ids)
            if received == 0:
                continue
            ratio = sent / received
            total = sent + received
            score = abs(total - target["total_emails"]) / target["total_emails"] + abs(math.log((ratio + 1e-9) / target["ratio"]))
            if best_score is None or score < best_score:
                best_score = score
                best_keys = list(picked)
                best_sent = sent
                best_received = received
                best_total = total
                best_ratio = ratio

    people.append(
        {
            "name": target["name"],
            "target_ratio": target["ratio"],
            "matched_ratio": best_ratio,
            "ratio_log_error": abs(math.log((best_ratio + 1e-9) / target["ratio"])),
            "target_total": target["total_emails"],
            "matched_total": best_total,
            "delta_total": best_total - target["total_emails"],
            "total_error": abs(best_total - target["total_emails"]) / target["total_emails"],
            "person_error": best_score,
            "sent_to_jeff": best_sent,
            "received_from_jeff": best_received,
            "picked_keys": ", ".join(best_keys),
        }
    )

results = pl.DataFrame(people).sort("target_total", descending=True)
results.write_csv("data/famous_correspondents.matched.csv")

combined_error = results.get_column("person_error").sum()
total_abs_delta = results.get_column("delta_total").abs().sum()
ratio_log_error = results.get_column("ratio_log_error").sum()
worst_person_error = results.get_column("person_error").max()

print(f"METRIC combined_error={combined_error}")
print(f"METRIC total_abs_delta={total_abs_delta}")
print(f"METRIC ratio_log_error={ratio_log_error}")
print(f"METRIC worst_person_error={worst_person_error}")
print(f"METRIC matched_rows={results.height}")
print(results.select("name", "target_ratio", "matched_ratio", "target_total", "matched_total", "delta_total", "person_error", "picked_keys"))
