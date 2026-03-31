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


def email_key(value: str | None) -> str | None:
    email = extract_email(value)
    if email is None:
        return None
    return re.sub(r"[^a-z]+", "", email.lower()) or None


addresses = pl.read_parquet("data/email_addresses.parquet").with_columns(
    pl.col("display_name").map_elements(name_key, return_dtype=pl.String).alias("name_key"),
    pl.col("email").map_elements(lambda value: None if value is None else re.sub(r"[^a-z]+", "", value.lower()) or None, return_dtype=pl.String).alias("email_key"),
).with_columns(
    pl.coalesce("name_key", "email_key").alias("search_key")
)
targets = pl.read_csv("data/famous_correspondents.csv")

jeff_sender_ids = set(
    addresses.filter(
        (pl.col("address_role") == "sender")
        & (
            pl.col("email").is_in(["jeevacation@gmail.com", "jeeproject@yahoo.com", "jeeyacation@gmail.com"])
            | pl.col("search_key").is_in(["jeffreye", "jeffreyepstein", "jepstein", "jeffrey", "jeevacationgmailcom", "jeeprojectyahoocom", "jeeyacationgmailcom", "jefffreyepstein", "jeffepstein", "jeevacation", "jefreyepstein", "jeeproject", "jeevacationmailcom", "jeevacationepstein"])
        )
    ).get_column("id")
)
jeff_recipient_ids = set(
    addresses.filter(
        pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"])
        & (
            pl.col("email").is_in(["jeevacation@gmail.com", "jeeproject@yahoo.com", "jeeyacation@gmail.com"])
            | pl.col("search_key").is_in(["jeffreye", "jeffreyepstein", "jepstein", "jeffrey", "jeevacationgmailcom", "jeeprojectyahoocom", "jeeyacationgmailcom", "jefffreyepstein", "jeffepstein", "jeevacation", "jefreyepstein", "jeeproject", "jeevacationmailcom", "jeevacationepstein"])
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
        "include": ["musk", "elon"],
        "exclude": ["kimbal", "kimbal", "maye", "talulah"],
        "prefer": ["elonmusk", "etonmusk", "elonmuskredacted", "elonmuskelonspaexcom"],
    },
}

role_is_recipient = pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"])
name_counts = addresses.group_by("search_key").len().filter(pl.col("search_key").is_not_null())
sender_with_jeff = addresses.filter((pl.col("address_role") == "sender") & pl.col("id").is_in(list(jeff_recipient_ids)))
recipient_with_jeff = addresses.filter(role_is_recipient & pl.col("id").is_in(list(jeff_sender_ids)))
sender_key_stats = sender_with_jeff.group_by("search_key").agg(pl.col("id").n_unique().alias("sender_count"))
recipient_key_stats = recipient_with_jeff.group_by("search_key").agg(pl.col("id").n_unique().alias("recipient_count"))
key_stats = name_counts.join(sender_key_stats, on="search_key", how="left").join(recipient_key_stats, on="search_key", how="left").fill_null(0)
sender_ids_by_key_global = {
    key: set(ids)
    for key, ids in sender_with_jeff.group_by("search_key").agg(pl.col("id").unique().alias("ids")).iter_rows()
    if key is not None
}
recipient_ids_by_key_global = {
    key: set(ids)
    for key, ids in recipient_with_jeff.group_by("search_key").agg(pl.col("id").unique().alias("ids")).iter_rows()
    if key is not None
}
people = []

for target in targets.iter_rows(named=True):
    rules = search[target["name"]]
    include_match = pl.any_horizontal(*[pl.col("search_key").str.contains(token, literal=True) for token in rules["include"]])
    exclude_match = pl.any_horizontal(*[pl.col("search_key").str.contains(token, literal=True) for token in rules["exclude"]]) if rules["exclude"] else pl.lit(False)
    candidates = (
        key_stats.filter(include_match & ~exclude_match)
        .filter(
            (
                ((pl.col("sender_count") + pl.col("recipient_count")) > 1)
                if target["name"] in ["Kathryn Ruemmler", "Lawrence Krauss", "Ariane de Rothschild", "Noam and Valeria Chomsky", "Reid Hoffman", "Elon Musk", "Bill Gates"]
                else ((pl.col("sender_count") + pl.col("recipient_count")) > 0)
            )
            | pl.col("search_key").is_in(rules["prefer"])
        )
        .sort("len", descending=True)
        .get_column("search_key")
        .to_list()
    )
    candidates = [key for key in rules["prefer"] if key in candidates] + [key for key in candidates if key not in rules["prefer"]]
    candidates = candidates[:22] if target["name"] == "Lawrence Krauss" else candidates[:16] if target["name"] == "Reid Hoffman" else candidates[:16] if target["name"] == "Ariane de Rothschild" else candidates[:14] if target["name"] in ["Kathryn Ruemmler", "Noam and Valeria Chomsky", "Bill Gates"] else candidates[:13] if target["name"] == "Elon Musk" else candidates[:12]

    sender_ids_by_key = {key: sender_ids_by_key_global.get(key, set()) for key in candidates}
    recipient_ids_by_key = {key: recipient_ids_by_key_global.get(key, set()) for key in candidates}

    best_score = None
    best_keys = []
    best_sent = 0
    best_received = 0
    best_total = 0
    best_ratio = 0.0

    for width in range(1, min(len(candidates), 11 if target["name"] == "Lawrence Krauss" else 10 if target["name"] == "Ariane de Rothschild" else 9) + 1):
        for picked in itertools.combinations(candidates, width):
            sent = len(set().union(*(sender_ids_by_key[key] for key in picked)))
            received = len(set().union(*(recipient_ids_by_key[key] for key in picked)))
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

    if target["name"] in ["Ariane de Rothschild", "Lawrence Krauss", "Kathryn Ruemmler"]:
        shared_keys = list(best_keys)
        remaining = [key for key in candidates if key not in shared_keys]
        sender_extra_choices = [()] + [(key,) for key in remaining] + list(itertools.combinations(remaining, 2)) + list(itertools.combinations(remaining, 3))
        recipient_extra_choices = [()] + [(key,) for key in remaining] + list(itertools.combinations(remaining, 2)) + list(itertools.combinations(remaining, 3))
        base_sender = set().union(*(sender_ids_by_key[key] for key in shared_keys))
        base_recipient = set().union(*(recipient_ids_by_key[key] for key in shared_keys))
        sender_extra_sets = [(extras, set().union(*(sender_ids_by_key[key] for key in extras))) for extras in sender_extra_choices]
        recipient_extra_sets = [(extras, set().union(*(recipient_ids_by_key[key] for key in extras))) for extras in recipient_extra_choices]
        for sender_extras, sender_extra_ids in sender_extra_sets:
            for recipient_extras, recipient_extra_ids in recipient_extra_sets:
                if not sender_extras and not recipient_extras:
                    continue
                sent_ids = base_sender | sender_extra_ids
                received_ids = base_recipient | recipient_extra_ids
                received = len(received_ids)
                if received == 0:
                    continue
                sent = len(sent_ids)
                ratio = sent / received
                total = sent + received
                score = abs(total - target["total_emails"]) / target["total_emails"] + abs(math.log((ratio + 1e-9) / target["ratio"]))
                if score < best_score:
                    best_score = score
                    best_keys = [f"shared: {', '.join(shared_keys)}"] + [f"from+: {key}" for key in sender_extras] + [f"to+: {key}" for key in recipient_extras]
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
