# %% Cell 1

import difflib
import re
from pathlib import Path

import polars as pl

from jmail import jmail

email_pattern = (
    r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@"
    r"(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})"
)
email_regex = re.compile(email_pattern)


def normalize_text(expr: pl.Expr) -> pl.Expr:
    return (
        expr.str.replace_all("&nbsp;", " ")
        .str.replace_all("&lt;", "<")
        .str.replace_all("&gt;", ">")
        .str.replace_all("&quot;", '"')
        .str.replace_all("&#39;", "'")
        .str.replace_all("&amp;", "&")
        .str.replace_all("\u00a0", " ")
        .str.replace_all("\u200b", " ")
        .str.replace_all("\u2018|\u2019", "'")
        .str.replace_all('\u201c|\u201d', '"')
        .str.replace_all("\u2039|\u276e|\u3008|\uff1c", "<")
        .str.replace_all("\u203a|\u276f|\u3009|\uff1e", ">")
        .str.replace_all("\u3010", "[")
        .str.replace_all("\u3011", "]")
        .str.replace_all(r"</?(?:u|s|change)>", "")
        .str.replace_all(r"[\r\n\t]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def email_expr(column: str) -> pl.Expr:
    extracted = (
        pl.col(column)
        .str.to_lowercase()
        .str.replace_all(r"(?i)=40", "@")
        .str.replace_all(r"(?i)=2e", ".")
        .str.replace_all(r"(?i)=5f", "_")
        .str.replace_all(r"(?i)=2d", "-")
        .str.replace_all(r"(?i)=20|=09|=0a|=0d", "")
        .str.replace_all(
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)(gmail|googlemail|yahoo|hotmail|outlook|icloud|me|mac|msn|live|gmx|aol|protonmail|ymail|rocketmail)\.",
            "${1}${2}@${3}.",
        )
        .str.replace_all(
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)([a-z0-9-]+\.(?:com|net|org|edu|gov|mil|int|co|io|ai|me|tv|us|uk|ru|fr|de|ch|it|nl|se|no|es|br|ca|mx))\b",
            "${1}${2}@${3}",
        )
        .str.extract(email_pattern, 1)
        .str.replace_all(r"@grnail\.", "@gmail.")
        .str.replace_all(r"@gmall\.", "@gmail.")
        .str.replace_all(r"@smail\.", "@gmail.")
        .str.replace_all(r"@tmail\.", "@gmail.")
        .str.replace_all(r"\.(?:corn|cord)[a-z]?$", ".com")
        .str.replace_all(r"\.con$", ".com")
    )
    local_part = extracted.str.extract(r"^([^@]+)@", 1).str.replace_all(r"\.", "")
    domain_part = extracted.str.extract(r"@(.+)$", 1)
    extracted = pl.when(extracted.is_not_null()).then(local_part + pl.lit("@") + domain_part).otherwise(None)

    return (
        pl.when(
            extracted.is_not_null()
            & (extracted.str.len_chars() <= 320)
            & (local_part.str.len_chars() <= 64)
            & (domain_part.str.len_chars() <= 255)
        )
        .then(extracted)
        .otherwise(None)
    )


def display_name_expr(column: str) -> pl.Expr:
    cleaned = (
        pl.col(column)
        .fill_null("")
        .str.replace_all(email_pattern, " ")
        .str.replace_all(r"[<>\[\]\(\)\"]", " ")
        .str.replace_all("'", " ")
        .str.replace_all(r"\s+", " ")
        .str.replace_all(r"^[,;:\-\s]+|[,;:\-\s]+$", "")
    )
    return pl.when(cleaned == "").then(None).otherwise(cleaned)


def repair_candidate(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.lower()
    value = re.sub(r"(?i)=40", "@", value)
    value = re.sub(r"(?i)=2e", ".", value)
    value = re.sub(r"(?i)=5f", "_", value)
    value = re.sub(r"(?i)=2d", "-", value)
    value = re.sub(r"(?i)=20|=09|=0a|=0d", "", value)
    value = re.sub(r"@grnail\.", "@gmail.", value)
    value = re.sub(r"@gmall\.", "@gmail.", value)
    value = re.sub(r"@smail\.", "@gmail.", value)
    value = re.sub(r"@tmail\.", "@gmail.", value)
    value = re.sub(r"\.(?:corn|cord)[a-z]?$", ".com", value)
    value = re.sub(r"\.con$", ".com", value)
    value = re.sub(
        r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)(gmail|googlemail|yahoo|hotmail|outlook|icloud|me|mac|msn|live|gmx|aol|protonmail|ymail|rocketmail)\.",
        r"\1\2@\3.",
        value,
    )
    value = re.sub(
        r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)([a-z0-9-]+\.(?:com|net|org|edu|gov|mil|int|co|io|ai|me|tv|us|uk|ru|fr|de|ch|it|nl|se|no|es|br|ca|mx))\b",
        r"\1\2@\3",
        value,
    )
    return value


def canonical_email_parts(local_part: str, domain: str) -> tuple[str, str]:
    domain = domain.lower()
    if domain == "googlemail.com":
        domain = "gmail.com"
    local_part = local_part.replace(".", "")
    return local_part, domain


def canonicalize_email(email: str | None) -> str | None:
    if email is None or "@" not in email:
        return None
    local_part, domain = email.rsplit("@", 1)
    local_part, domain = canonical_email_parts(local_part, domain)
    return f"{local_part}@{domain}"


def fuzzy_repair_emails(parsed_addresses: pl.DataFrame) -> pl.DataFrame:
    known = (
        parsed_addresses.filter(pl.col("email").is_not_null())
        .with_columns(
            pl.col("email").str.extract(r"^([^@]+)@", 1).alias("local_part"),
            pl.col("email").str.extract(r"@(.+)$", 1).alias("domain"),
        )
        .group_by("email", "local_part", "domain")
        .len()
        .filter(pl.col("len") >= 2)
    )

    candidates_by_domain: dict[str, list[tuple[str, str, int]]] = {}
    for row in known.iter_rows(named=True):
        canonical_local, canonical_domain = canonical_email_parts(
            row["local_part"], row["domain"]
        )
        candidates_by_domain.setdefault(canonical_domain, []).append(
            (canonical_local, row["email"], row["len"])
        )

    repaired_rows: list[dict[str, str | int | None]] = []
    suspicious = parsed_addresses.filter(
        pl.col("email").is_null()
        & pl.col("normalized_value").is_not_null()
        & pl.col("normalized_value")
        .str.to_lowercase()
        .str.contains(r"§|#|=|grnail|gmall|smail|tmail|corn|cord|\.con\b")
    )

    for row in suspicious.iter_rows(named=True):
        candidate = repair_candidate(row["normalized_value"])
        if candidate is None:
            continue

        match = email_regex.search(candidate)
        if match is not None:
            repaired = canonicalize_email(match.group(1))
            start, end = match.span(1)
            left_ok = start == 0 or candidate[start - 1] in {'<', '"', "'", "(", "[", " ", "\t"}
            right_ok = end == len(candidate) or candidate[end] in {'>', '"', "'", ")", "]", " ", "\t", ",", ";"}
            if repaired is not None and left_ok and right_ok:
                repaired_rows.append(
                    {
                        "id": row["id"],
                        "address_role": row["address_role"],
                        "address_index": row["address_index"],
                        "email_repaired": repaired,
                    }
                )
                continue

        domain_match = re.search(
            r"(gmail\.com|googlemail\.com|yahoo\.com|hotmail\.com|outlook\.com|icloud\.com|me\.com|mac\.com|msn\.com|live\.com|gmx\.com|aol\.com|protonmail\.com|ymail\.com|rocketmail\.com)",
            candidate,
        )
        if domain_match is None:
            continue

        domain = domain_match.group(1)
        local_seed = candidate.split(domain, 1)[0]
        local_seed = re.sub(r"^[^a-z0-9]+", "", local_seed)
        local_seed = re.sub(r"[^a-z0-9._%+\-/=]+", "", local_seed)
        local_seed = local_seed.rstrip(".@")
        if len(local_seed) < 4:
            continue

        local_seed, domain = canonical_email_parts(local_seed, domain)
        domain_candidates = candidates_by_domain.get(domain, [])
        if not domain_candidates:
            continue

        compare_seed = re.sub(r"[^a-z0-9]", "", local_seed)
        if len(compare_seed) < 4:
            continue

        best_email = None
        best_score = 0.0
        second_score = 0.0
        best_count = -1
        for known_local, known_email, known_count in domain_candidates:
            compare_known = re.sub(r"[^a-z0-9]", "", known_local)
            if abs(len(compare_known) - len(compare_seed)) > max(2, len(compare_seed) // 3):
                continue
            score = difflib.SequenceMatcher(None, compare_seed, compare_known).ratio()
            if score > best_score or (score == best_score and known_count > best_count):
                second_score = best_score
                best_score = score
                best_email = known_email
                best_count = known_count
            elif score > second_score:
                second_score = score

        if best_email is None:
            continue
        if best_score < 0.82:
            continue
        if best_score < 0.995 and best_score - second_score < 0.08:
            continue

        repaired_rows.append(
            {
                "id": row["id"],
                "address_role": row["address_role"],
                "address_index": row["address_index"],
                "email_repaired": canonicalize_email(best_email),
            }
        )

    if not repaired_rows:
        return parsed_addresses

    repaired = pl.DataFrame(repaired_rows).unique(
        subset=["id", "address_role", "address_index"], keep="first"
    )
    return (
        parsed_addresses.join(
            repaired, on=["id", "address_role", "address_index"], how="left"
        )
        .with_columns(pl.coalesce("email_repaired", "email").alias("email"))
        .drop("email_repaired")
    )


base = (
    pl.scan_parquet(jmail("emails"))
    .select(
        "id",
        "sender",
        "to_recipients",
        "cc_recipients",
        "bcc_recipients",
        "account_email",
        "is_promotional",
    )
    .filter(pl.col("is_promotional") != True)
    .drop("is_promotional")
    .with_columns(
        normalize_text(pl.col("sender")).alias("sender_normalized"),
        normalize_text(pl.col("account_email")).alias("account_email_normalized"),
        pl.col("to_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .list.eval(normalize_text(pl.element()))
        .alias("to_recipients_normalized"),
        pl.col("cc_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .list.eval(normalize_text(pl.element()))
        .alias("cc_recipients_normalized"),
        pl.col("bcc_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .list.eval(normalize_text(pl.element()))
        .alias("bcc_recipients_normalized"),
        pl.col("to_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .alias("to_recipients_items"),
        pl.col("cc_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .alias("cc_recipients_items"),
        pl.col("bcc_recipients")
        .fill_null("[]")
        .str.json_decode(pl.List(pl.String))
        .alias("bcc_recipients_items"),
    )
)

normalized = base.select(
    "id",
    "sender",
    "sender_normalized",
    "to_recipients",
    "to_recipients_normalized",
    "cc_recipients",
    "cc_recipients_normalized",
    "bcc_recipients",
    "bcc_recipients_normalized",
    "account_email",
    "account_email_normalized",
)

scalar_addresses = pl.concat(
    [
        base.select(
            "id",
            pl.lit("sender").alias("address_role"),
            pl.lit(None, dtype=pl.Int64).alias("address_index"),
            pl.col("sender").alias("raw_value"),
            pl.col("sender_normalized").alias("normalized_value"),
        ),
        base.select(
            "id",
            pl.lit("account_email").alias("address_role"),
            pl.lit(None, dtype=pl.Int64).alias("address_index"),
            pl.col("account_email").alias("raw_value"),
            pl.col("account_email_normalized").alias("normalized_value"),
        ),
    ],
    how="diagonal_relaxed",
)

recipient_addresses = pl.concat(
    [
        base.with_columns(
            pl.int_ranges(0, pl.col("to_recipients_normalized").list.len()).alias("address_index")
        )
        .select(
            "id",
            pl.lit("to_recipients").alias("address_role"),
            "address_index",
            pl.col("to_recipients_items").alias("raw_value"),
            pl.col("to_recipients_normalized").alias("normalized_value"),
        )
        .explode("address_index", "raw_value", "normalized_value"),
        base.with_columns(
            pl.int_ranges(0, pl.col("cc_recipients_normalized").list.len()).alias("address_index")
        )
        .select(
            "id",
            pl.lit("cc_recipients").alias("address_role"),
            "address_index",
            pl.col("cc_recipients_items").alias("raw_value"),
            pl.col("cc_recipients_normalized").alias("normalized_value"),
        )
        .explode("address_index", "raw_value", "normalized_value"),
        base.with_columns(
            pl.int_ranges(0, pl.col("bcc_recipients_normalized").list.len()).alias("address_index")
        )
        .select(
            "id",
            pl.lit("bcc_recipients").alias("address_role"),
            "address_index",
            pl.col("bcc_recipients_items").alias("raw_value"),
            pl.col("bcc_recipients_normalized").alias("normalized_value"),
        )
        .explode("address_index", "raw_value", "normalized_value"),
    ],
    how="diagonal_relaxed",
)

parsed = (
    pl.concat([scalar_addresses, recipient_addresses], how="diagonal_relaxed")
    .with_columns(
        normalize_text(pl.col("raw_value")).alias("raw_value"),
        email_expr("normalized_value").alias("email"),
        display_name_expr("normalized_value").alias("display_name"),
    )
    .filter(pl.col("normalized_value").is_not_null())
    .select(
        "id",
        "address_role",
        "address_index",
        "raw_value",
        "normalized_value",
        "display_name",
        "email",
    )
)

emails_out = (
    parsed.select("email")
    .drop_nulls()
    .filter(pl.col("email") != "")
    .unique()
    .sort("email")
)

sender_domains = (
    parsed.filter(pl.col("address_role") == "sender")
    .select(pl.col("email").str.extract(r"@(.+)$", 1).alias("domain"))
    .drop_nulls()
    .filter(pl.col("domain") != "")
    .unique()
    .sort("domain")
)

normalized_emails, parsed_addresses, all_emails, sender_domains_out = pl.collect_all(
    [normalized, parsed, emails_out, sender_domains]
)

parsed_addresses = fuzzy_repair_emails(parsed_addresses)
all_emails = (
    parsed_addresses.select("email")
    .drop_nulls()
    .filter(pl.col("email") != "")
    .unique()
    .sort("email")
)
sender_domains_out = (
    parsed_addresses.filter(pl.col("address_role") == "sender")
    .select(pl.col("email").str.extract(r"@(.+)$", 1).alias("domain"))
    .drop_nulls()
    .filter(pl.col("domain") != "")
    .unique()
    .sort("domain")
)

Path("data").mkdir(parents=True, exist_ok=True)
normalized_emails.write_parquet("data/emails.normalized.parquet")
parsed_addresses.write_parquet("data/email_addresses.parquet")
all_emails.write_csv("data/all_emails.csv")
sender_domains_out.write_csv("data/sender_domains.csv")

print("Collected lazy outputs with polars.collect_all() on the Polars thread pool")
print(f"Wrote {normalized_emails.height} normalized rows to data/emails.normalized.parquet")
print(normalized_emails.select("id", "sender_normalized").head())
print(f"Wrote {parsed_addresses.height} parsed addresses to data/email_addresses.parquet")
print(parsed_addresses.head())
print(f"Wrote {all_emails.height} unique email addresses to data/all_emails.csv")
print(all_emails.head())
print(f"Wrote {sender_domains_out.height} sender domains to data/sender_domains.csv")
print(sender_domains_out.head())
