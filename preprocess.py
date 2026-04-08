import difflib
import json
import re
from pathlib import Path

import polars as pl


def normalize_text(expr):
    return (
        expr.fill_null("")
        .str.replace_all("&nbsp;", " ")
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


def clean_body(expr):
    return (
        normalize_text(expr)
        .str.replace_all(r"(?i)https?://\S+", " ")
        .str.replace_all(r"(?i)www\.\S+", " ")
        .str.replace_all(r"(?i)\b(?:view in browser|download now|save now|click here)\b:?", " ")
        .str.replace_all(r"(?i)\b(?:unsubscribe|privacy policy|terms of service|manage preferences)\b", " ")
        .str.replace_all(r"(?i)\b(?:original message|forwarded by|begin forwarded message)\b", " ")
        .str.replace_all(r"(?i)<[^>]+>", " ")
        .str.replace_all(r"(?im)^(from|to|cc|bcc|sent|subject):[^\n]*$", " ")
        .str.replace_all(r"(?im)^[-_]{2,}.*forwarded message.*$", " ")
        .str.replace_all(r"(?im)^this email and any attachments.*$", " ")
        .str.replace_all(r"(?im)^please consider the environment.*$", " ")
        .str.replace_all(r"(?i)\b(?:do you yahoo!?|don'?t pick lemons|citrix sharefile|all rights reserved)\b", " ")
        .str.replace_all(r"[_=~-]{3,}", " ")
        .str.replace_all(r"[<>]{2,}", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def email_expr(column):
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
        .str.extract(
            r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})",
            1,
        )
        .str.replace_all(r"@grnail\.", "@gmail.")
        .str.replace_all(r"@gmall\.", "@gmail.")
        .str.replace_all(r"@smail\.", "@gmail.")
        .str.replace_all(r"@tmail\.", "@gmail.")
        .str.replace_all(r"\.(?:corn|cord)[a-z]?$", ".com")
        .str.replace_all(r"\.con$", ".com")
    )
    local_part = extracted.str.extract(r"^([^@]+)@", 1).str.replace_all(r"\.", "")
    domain_part = extracted.str.extract(r"@(.+)$", 1)
    return (
        pl.when(
            extracted.is_not_null()
            & (extracted.str.len_chars() <= 320)
            & (local_part.str.len_chars() <= 64)
            & (domain_part.str.len_chars() <= 255)
        )
        .then(local_part + pl.lit("@") + domain_part)
        .otherwise(None)
    )


def display_name_expr(column):
    cleaned = (
        pl.col(column)
        .fill_null("")
        .str.replace_all(
            r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})",
            " ",
        )
        .str.replace_all(r"[<>\[\]\(\)\"]", " ")
        .str.replace_all("'", " ")
        .str.replace_all(r"\s+", " ")
        .str.replace_all(r"^[,;:\-\s]+|[,;:\-\s]+$", "")
    )
    return pl.when(cleaned == "").then(None).otherwise(cleaned)


def repair_candidate(value):
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


def canonicalize_email(value):
    if value is None or "@" not in value:
        return None
    local_part, domain = value.rsplit("@", 1)
    domain = domain.lower()
    if domain == "googlemail.com":
        domain = "gmail.com"
    return f"{local_part.replace('.', '').lower()}@{domain}"


def fuzzy_repair_emails(frame):
    known = (
        frame.filter(pl.col("email").is_not_null())
        .with_columns(
            pl.col("email").str.extract(r"^([^@]+)@", 1).alias("local_part"),
            pl.col("email").str.extract(r"@(.+)$", 1).alias("domain"),
        )
        .group_by("email", "local_part", "domain")
        .len()
        .filter(pl.col("len") >= 2)
    )
    candidates_by_domain = {}
    for row in known.iter_rows(named=True):
        domain = "gmail.com" if row["domain"] == "googlemail.com" else row["domain"]
        candidates_by_domain.setdefault(domain, []).append(
            (re.sub(r"[^a-z0-9]", "", row["local_part"]), row["email"], row["len"])
        )

    repaired_rows = []
    suspicious = frame.filter(
        pl.col("email").is_null()
        & pl.col("normalized_value").is_not_null()
        & pl.col("normalized_value")
        .str.to_lowercase()
        .str.contains(r"§|#|=|grnail|gmall|smail|tmail|corn|cord|\.con\b")
    )
    email_regex = re.compile(
        r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})"
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
        local_seed = re.sub(r"[^a-z0-9._%+\-/=]+", "", local_seed).rstrip(".@")
        compare_seed = re.sub(r"[^a-z0-9]", "", local_seed)
        if len(compare_seed) < 4:
            continue
        domain = "gmail.com" if domain == "googlemail.com" else domain
        best_email = None
        best_score = 0.0
        second_score = 0.0
        best_count = -1
        for known_local, known_email, known_count in candidates_by_domain.get(domain, []):
            if abs(len(known_local) - len(compare_seed)) > max(2, len(compare_seed) // 3):
                continue
            score = difflib.SequenceMatcher(None, compare_seed, known_local).ratio()
            if score > best_score or (score == best_score and known_count > best_count):
                second_score = best_score
                best_score = score
                best_email = known_email
                best_count = known_count
            elif score > second_score:
                second_score = score
        if best_email is None or best_score < 0.82:
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
        return frame

    return (
        frame.join(
            pl.DataFrame(repaired_rows).unique(
                subset=["id", "address_role", "address_index"], keep="first"
            ),
            on=["id", "address_role", "address_index"],
            how="left",
        )
        .with_columns(pl.coalesce("email_repaired", "email").alias("email"))
        .drop("email_repaired")
    )


def sample_values(frame, column, limit=5):
    if column not in frame.columns:
        return []
    values = frame.get_column(column).drop_nulls().head(limit).to_list()
    return [str(value)[:200] for value in values]


out_dir = Path("data")
out_dir.mkdir(exist_ok=True)

base = (
    pl.scan_parquet("data/emails.parquet")
    .with_row_index("row_nr")
    .with_columns(
        pl.col("is_promotional").fill_null(False).alias("is_promotional"),
        pl.col("sender").alias("sender_raw"),
        pl.col("account_email").alias("account_email_raw"),
        pl.col("to_recipients").alias("to_recipients_raw"),
        pl.col("cc_recipients").alias("cc_recipients_raw"),
        pl.col("bcc_recipients").alias("bcc_recipients_raw"),
        pl.col("content_markdown").alias("content_markdown_raw"),
        pl.col("subject").fill_null("").str.strip_chars().replace("", None).alias("subject_clean"),
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
        pl.col("to_recipients").fill_null("[]").str.json_decode(pl.List(pl.String)).alias("to_recipients_items"),
        pl.col("cc_recipients").fill_null("[]").str.json_decode(pl.List(pl.String)).alias("cc_recipients_items"),
        pl.col("bcc_recipients").fill_null("[]").str.json_decode(pl.List(pl.String)).alias("bcc_recipients_items"),
        clean_body(pl.col("content_markdown")).alias("body_clean"),
        pl.concat_str(
            [
                pl.col("subject").fill_null("").str.strip_chars(),
                pl.lit("\n"),
                clean_body(pl.col("content_markdown")).fill_null(""),
            ]
        )
        .str.strip_chars()
        .replace("", None)
        .alias("text_clean"),
        pl.coalesce(
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.fZ", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%d", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%m/%d/%Y %H:%M", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%m/%d/%Y", strict=False),
        ).alias("sent_at_parsed"),
    )
    .with_columns(
        pl.col("text_clean").str.len_chars().fill_null(0).alias("text_char_len"),
        pl.col("text_clean").str.count_matches(r"\b[\p{L}\p{N}']+\b").fill_null(0).alias("text_token_len"),
        pl.col("body_clean").str.contains(r"(?i)(http://|https://|www\.)").fill_null(False).alias("still_has_url"),
        pl.col("body_clean").str.contains(r"</?(?:u|s|change)>").fill_null(False).alias("still_has_ocr_markup"),
        pl.col("sender_raw")
        .fill_null("")
        .str.to_lowercase()
        .str.contains(r"redacted|█")
        .alias("sender_redacted"),
        pl.col("sent_at_parsed").dt.year().alias("year"),
    )
    .with_columns(
        pl.when(pl.col("year").is_between(1990, 2019, closed="both"))
        .then(pl.col("year"))
        .otherwise(None)
        .alias("year_valid"),
        pl.when(pl.col("sent_at_parsed").is_not_null() & pl.col("year").is_between(1990, 2019, closed="both"))
        .then(pl.col("sent_at_parsed"))
        .otherwise(None)
        .alias("sent_at_valid"),
        (
            pl.col("id").cast(pl.String).fill_null("")
            + pl.lit("||")
            + pl.col("sender_normalized").fill_null("")
            + pl.lit("||")
            + pl.col("subject_clean").fill_null("")
            + pl.lit("||")
            + pl.col("sent_at").fill_null("")
            + pl.lit("||")
            + pl.col("text_clean").fill_null("").str.slice(0, 500)
        ).alias("duplicate_signature"),
    )
)

raw_stats = (
    base.select(
        pl.len().alias("raw_rows"),
        pl.col("is_promotional").sum().alias("promotional_rows"),
        pl.col("sender").is_null().sum().alias("sender_nulls_raw"),
        pl.col("subject").is_null().sum().alias("subject_nulls_raw"),
        pl.col("content_markdown").is_null().sum().alias("content_nulls_raw"),
        pl.col("sent_at").is_null().sum().alias("sent_at_nulls_raw"),
    )
    .collect()
    .row(0, named=True)
)

processed = (
    base.filter(pl.col("is_promotional").not_())
    .with_columns(
        pl.col("text_char_len").lt(80).alias("too_short"),
        pl.col("sent_at_valid").is_null().alias("invalid_date"),
        pl.col("duplicate_signature").is_duplicated().alias("duplicate_signature_flag"),
        pl.col("id").is_duplicated().alias("duplicate_id_flag"),
    )
    .collect()
)

scalar_addresses = pl.concat(
    [
        processed.select(
            "id",
            pl.lit("sender").alias("address_role"),
            pl.lit(None, dtype=pl.Int64).alias("address_index"),
            pl.col("sender_raw").alias("raw_value"),
            pl.col("sender_normalized").alias("normalized_value"),
        ),
        processed.select(
            "id",
            pl.lit("account_email").alias("address_role"),
            pl.lit(None, dtype=pl.Int64).alias("address_index"),
            pl.col("account_email_raw").alias("raw_value"),
            pl.col("account_email_normalized").alias("normalized_value"),
        ),
    ],
    how="diagonal_relaxed",
)

recipient_addresses = pl.concat(
    [
        processed.with_columns(
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
        processed.with_columns(
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
        processed.with_columns(
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

addresses = (
    pl.concat([scalar_addresses, recipient_addresses], how="diagonal_relaxed")
    .with_columns(
        normalize_text(pl.col("raw_value")).alias("raw_value"),
        email_expr("normalized_value").alias("email"),
        display_name_expr("normalized_value").alias("display_name"),
    )
    .filter(pl.col("normalized_value").is_not_null())
    .select("id", "address_role", "address_index", "raw_value", "normalized_value", "display_name", "email")
)

addresses_before = addresses
addresses_after = fuzzy_repair_emails(addresses).with_columns(
    pl.col("email").map_elements(canonicalize_email, return_dtype=pl.String)
)

sender_fields = (
    addresses_after.filter(pl.col("address_role") == "sender")
    .group_by("id")
    .agg(
        pl.col("email").drop_nulls().first().alias("sender_email"),
        pl.col("display_name").drop_nulls().first().alias("sender_display_name"),
    )
)

account_fields = (
    addresses_after.filter(pl.col("address_role") == "account_email")
    .group_by("id")
    .agg(pl.col("email").drop_nulls().first().alias("account_email_clean"))
)

recipient_fields = (
    addresses_after.filter(pl.col("address_role").is_in(["to_recipients", "cc_recipients", "bcc_recipients"]))
    .group_by("id", "address_role")
    .agg(
        pl.col("email").drop_nulls().n_unique().alias("unique_email_count"),
        pl.col("display_name").drop_nulls().n_unique().alias("unique_display_name_count"),
    )
    .pivot(on="address_role", index="id", values=["unique_email_count", "unique_display_name_count"])
    .fill_null(0)
)

clean_corpus = (
    processed.filter(
        pl.col("too_short").not_()
        & pl.col("invalid_date").not_()
    )
    .with_columns(
        pl.col("to_recipients_normalized").list.len().alias("to_recipient_count"),
        pl.col("cc_recipients_normalized").list.len().alias("cc_recipient_count"),
        pl.col("bcc_recipients_normalized").list.len().alias("bcc_recipient_count"),
        pl.col("subject_clean")
        .fill_null("")
        .str.replace_all(r"(?i)^\s*(?:re|fw|fwd)\s*:\s*", "")
        .str.strip_chars()
        .replace("", None)
        .alias("subject_base"),
    )
    .join(sender_fields, on="id", how="left")
    .join(account_fields, on="id", how="left")
    .join(recipient_fields, on="id", how="left")
    .select(
        "id",
        "doc_id",
        "message_index",
        "sender_raw",
        "sender_normalized",
        "sender_email",
        "sender_display_name",
        "subject_clean",
        "subject_base",
        "sent_at_valid",
        "year_valid",
        "folder_path",
        "release_batch",
        "epstein_is_sender",
        "account_email_raw",
        "account_email_normalized",
        "account_email_clean",
        "to_recipients_raw",
        "cc_recipients_raw",
        "bcc_recipients_raw",
        "to_recipient_count",
        "cc_recipient_count",
        "bcc_recipient_count",
        "unique_email_count_to_recipients",
        "unique_email_count_cc_recipients",
        "unique_email_count_bcc_recipients",
        "unique_display_name_count_to_recipients",
        "unique_display_name_count_cc_recipients",
        "unique_display_name_count_bcc_recipients",
        "body_clean",
        "text_clean",
        "text_char_len",
        "text_token_len",
        "duplicate_id_flag",
        "duplicate_signature_flag",
        "sender_redacted",
    )
    .rename(
        {
            "sender_raw": "sender",
            "subject_clean": "subject",
            "sent_at_valid": "sent_at",
            "year_valid": "year",
            "account_email_raw": "account_email",
            "to_recipients_raw": "to_recipients",
            "cc_recipients_raw": "cc_recipients",
            "bcc_recipients_raw": "bcc_recipients",
            "unique_email_count_to_recipients": "to_unique_email_count",
            "unique_email_count_cc_recipients": "cc_unique_email_count",
            "unique_email_count_bcc_recipients": "bcc_unique_email_count",
            "unique_display_name_count_to_recipients": "to_unique_display_name_count",
            "unique_display_name_count_cc_recipients": "cc_unique_display_name_count",
            "unique_display_name_count_bcc_recipients": "bcc_unique_display_name_count",
        }
    )
    .with_columns(
        pl.col("to_unique_email_count").fill_null(0),
        pl.col("cc_unique_email_count").fill_null(0),
        pl.col("bcc_unique_email_count").fill_null(0),
        pl.col("to_unique_display_name_count").fill_null(0),
        pl.col("cc_unique_display_name_count").fill_null(0),
        pl.col("bcc_unique_display_name_count").fill_null(0),
        pl.coalesce("sender_email", "account_email_clean", "sender_normalized", "sender").alias("sender_best"),
        pl.coalesce("sender_display_name", "sender").alias("sender_name_best"),
    )
)

sample = clean_corpus.sample(n=min(25000, clean_corpus.height), seed=7).sort("sent_at", descending=False)
sample_csv = sample

normalized_emails = processed.select(
    "id",
    "sender_raw",
    "sender_normalized",
    "to_recipients_raw",
    "to_recipients_normalized",
    "cc_recipients_raw",
    "cc_recipients_normalized",
    "bcc_recipients_raw",
    "bcc_recipients_normalized",
    "account_email_raw",
    "account_email_normalized",
).rename(
    {
        "sender_raw": "sender",
        "to_recipients_raw": "to_recipients",
        "cc_recipients_raw": "cc_recipients",
        "bcc_recipients_raw": "bcc_recipients",
        "account_email_raw": "account_email",
    }
)

summary = pl.DataFrame(
    [
        {"metric": "raw_rows", "value": raw_stats["raw_rows"]},
        {"metric": "promotional_rows_removed", "value": raw_stats["promotional_rows"]},
        {"metric": "rows_after_promotional_filter", "value": processed.height},
        {"metric": "rows_with_invalid_or_out_of_scope_dates", "value": int(processed.get_column("invalid_date").sum())},
        {"metric": "rows_too_short_under_80_chars", "value": int(processed.get_column("too_short").sum())},
        {"metric": "clean_rows_ready_for_analysis", "value": clean_corpus.height},
        {"metric": "duplicate_id_rows_flagged", "value": int(processed.get_column("duplicate_id_flag").sum())},
        {"metric": "duplicate_signature_rows_flagged", "value": int(processed.get_column("duplicate_signature_flag").sum())},
        {"metric": "parsed_address_rows", "value": addresses_after.height},
        {"metric": "addresses_with_email_before_repair", "value": int(addresses_before.get_column("email").is_not_null().sum())},
        {"metric": "addresses_with_email_after_repair", "value": int(addresses_after.get_column("email").is_not_null().sum())},
        {
            "metric": "addresses_recovered_by_repair",
            "value": int(addresses_after.get_column("email").is_not_null().sum())
            - int(addresses_before.get_column("email").is_not_null().sum()),
        },
        {"metric": "clean_rows_with_sender_email", "value": int(clean_corpus.get_column("sender_email").is_not_null().sum())},
        {"metric": "clean_rows_with_account_email_clean", "value": int(clean_corpus.get_column("account_email_clean").is_not_null().sum())},
        {"metric": "clean_rows_with_sender_best", "value": int(clean_corpus.get_column("sender_best").is_not_null().sum())},
    ]
)

missingness = pl.DataFrame(
    [
        {
            "column": column,
            "null_count": int(clean_corpus.get_column(column).null_count()),
            "null_pct": round(clean_corpus.get_column(column).null_count() * 100 / max(clean_corpus.height, 1), 3),
        }
        for column in [
            "sender",
            "sender_normalized",
            "sender_email",
            "sender_best",
            "subject",
            "subject_base",
            "sent_at",
            "folder_path",
            "account_email",
            "account_email_clean",
            "body_clean",
            "text_clean",
        ]
    ]
)

address_role_summary = (
    addresses_after.group_by("address_role")
    .agg(
        pl.len().alias("rows"),
        pl.col("email").is_not_null().sum().alias("rows_with_email"),
        pl.col("display_name").is_not_null().sum().alias("rows_with_display_name"),
        pl.col("normalized_value").n_unique().alias("unique_normalized_values"),
        pl.col("email").n_unique().alias("unique_emails"),
    )
    .with_columns(
        ((pl.col("rows_with_email") / pl.col("rows")) * 100).round(2).alias("email_recovery_pct")
    )
    .sort("rows", descending=True)
)

date_quality = processed.select(
    pl.len().alias("rows_after_promotional_filter"),
    pl.col("sent_at").is_null().sum().alias("sent_at_missing"),
    pl.col("sent_at_parsed").is_null().sum().alias("sent_at_unparseable"),
    pl.col("sent_at_valid").is_null().sum().alias("sent_at_invalid_or_out_of_scope"),
    pl.col("sent_at_valid").min().alias("min_valid_sent_at"),
    pl.col("sent_at_valid").max().alias("max_valid_sent_at"),
)

examples = processed.select(
    "subject_clean",
    "sender_raw",
    "content_markdown_raw",
    "body_clean",
    "text_clean",
).filter(
    pl.col("content_markdown_raw").is_not_null()
    & pl.col("body_clean").is_not_null()
    & pl.col("content_markdown_raw").str.slice(0, 500).ne(pl.col("body_clean").str.slice(0, 500))
).head(5)

example_rows = []
for row in examples.iter_rows(named=True):
    example_rows.append(
        {
            "subject": row["subject_clean"] or "(no subject)",
            "sender": row["sender_raw"],
            "before": (row["content_markdown_raw"] or "")[:700].replace("\n", " ").strip(),
            "after_body_clean": (row["body_clean"] or "")[:700],
            "after_text_clean": (row["text_clean"] or "")[:700],
        }
    )

schema = pl.DataFrame(
    [
        {
            "column": name,
            "dtype": str(dtype),
            "null_count": int(sample_csv.get_column(name).null_count()),
            "null_pct": round(sample_csv.get_column(name).null_count() * 100 / max(sample_csv.height, 1), 3),
            "example": json.dumps(sample_values(sample_csv, name, 1)[0] if sample_values(sample_csv, name, 1) else None),
        }
        for name, dtype in sample_csv.schema.items()
    ]
)

analysis_ready_schema = pl.DataFrame(
    [
        {
            "column": name,
            "dtype": str(dtype),
            "null_count": int(clean_corpus.get_column(name).null_count()),
            "null_pct": round(clean_corpus.get_column(name).null_count() * 100 / max(clean_corpus.height, 1), 3),
            "example": json.dumps(sample_values(clean_corpus, name, 1)[0] if sample_values(clean_corpus, name, 1) else None),
        }
        for name, dtype in clean_corpus.schema.items()
    ]
)

summary.write_csv(out_dir / "preprocessing_summary.csv")
missingness.write_csv(out_dir / "preprocessing_missingness.csv")
address_role_summary.write_csv(out_dir / "preprocessing_address_role_summary.csv")
date_quality.write_csv(out_dir / "preprocessing_date_quality.csv")
pl.DataFrame(example_rows).write_csv(out_dir / "preprocessing_examples.csv")
schema.write_csv(out_dir / "emails.cleaned.preprocessed.schema.csv")
analysis_ready_schema.write_csv(out_dir / "emails.cleaned.analysis_ready.schema.csv")
sample_csv.write_csv(out_dir / "emails.cleaned.preprocessed.sample.csv")
clean_corpus.write_parquet(out_dir / "emails.cleaned.analysis_ready.parquet")
normalized_emails.write_parquet(out_dir / "emails.normalized.parquet")
addresses_after.write_parquet(out_dir / "email_addresses.parquet")

report = f"""# Preprocessing Report

## Scope

This deliverable keeps only the preprocessing layer of the project. The raw source corpus is `data/emails.parquet`, containing {raw_stats["raw_rows"]:,} rows. The preprocessing pipeline removes promotional messages, normalizes noisy headers and body text, repairs recoverable email-address artifacts, parses and validates timestamps, flags duplicate risk, and writes an analysis-ready sample plus documentation.

## What The Pipeline Does

1. Remove rows where `is_promotional == True`.
2. Normalize sender, account, and recipient header strings by stripping OCR tags, HTML entities, odd whitespace, and Unicode punctuation variants.
3. Parse recipient JSON arrays and normalize each individual address item.
4. Extract canonical email addresses from sender, account, to, cc, and bcc fields.
5. Repair recoverable malformed addresses such as quoted-printable artifacts (`=40`), OCR substitutions, and domain typos like `gmall` or `corn`.
6. Clean body text by removing URLs, header echoes, forward banners, and boilerplate disclaimer lines.
7. Build `text_clean` from cleaned subject plus cleaned body.
8. Parse `sent_at` and keep only dates that are both parseable and within the project scope `1990-2019`.
9. Flag duplicate risk using duplicated `id` values and duplicated signature hashes.

## Outcome Summary

- Raw rows: {raw_stats["raw_rows"]:,}
- Promotional rows removed: {raw_stats["promotional_rows"]:,}
- Rows after promotional filtering: {processed.height:,}
- Rows with invalid or out-of-scope dates: {int(processed.get_column("invalid_date").sum()):,}
- Rows shorter than 80 cleaned characters: {int(processed.get_column("too_short").sum()):,}
- Final clean analysis-ready rows: {clean_corpus.height:,}
- Duplicate `id` rows flagged: {int(processed.get_column("duplicate_id_flag").sum()):,}
- Duplicate signature rows flagged: {int(processed.get_column("duplicate_signature_flag").sum()):,}
- Parsed address rows: {addresses_after.height:,}
- Address rows with extracted email before repair: {int(addresses_before.get_column("email").is_not_null().sum()):,}
- Address rows with extracted email after repair: {int(addresses_after.get_column("email").is_not_null().sum()):,}
- Additional addresses recovered by repair: {int(addresses_after.get_column("email").is_not_null().sum()) - int(addresses_before.get_column("email").is_not_null().sum()):,}

## Quality Notes

- Minimum valid timestamp in scope: {date_quality.item(0, "min_valid_sent_at")}
- Maximum valid timestamp in scope: {date_quality.item(0, "max_valid_sent_at")}
- Sender fields marked as redacted or masked: {int(processed.get_column("sender_redacted").sum()):,}
- Body rows still containing OCR tag remnants after cleaning: {int(processed.get_column("still_has_ocr_markup").sum()):,}
- Body rows still containing URL strings after cleaning: {int(processed.get_column("still_has_url").sum()):,}

## Before / After Examples

"""

for i, row in enumerate(example_rows, start=1):
    report += f"""### Example {i}

- Subject: {row["subject"]}
- Sender: {row["sender"]}
- Before: `{row["before"]}`
- After body clean: `{row["after_body_clean"]}`
- Final text_clean: `{row["after_text_clean"]}`

"""

report += """## Output Files

- `data/emails.cleaned.preprocessed.sample.csv`: ready-to-use cleaned sample for analysis
- `data/emails.cleaned.analysis_ready.parquet`: full cleaned analysis-ready corpus
- `data/emails.cleaned.analysis_ready.schema.csv`: schema and missingness for the full cleaned corpus
- `data/emails.cleaned.preprocessed.schema.csv`: schema and missingness for the cleaned sample
- `data/preprocessing_summary.csv`: high-level preprocessing counts
- `data/preprocessing_missingness.csv`: missingness after preprocessing
- `data/preprocessing_address_role_summary.csv`: address extraction and recovery by role
- `data/preprocessing_date_quality.csv`: timestamp parsing and validity summary
- `data/preprocessing_examples.csv`: before/after cleaning examples
- `data/emails.normalized.parquet`: normalized header fields
- `data/email_addresses.parquet`: parsed canonicalized address table

## Remaining Caveats

- Duplicate flags are conservative quality indicators, not a full deduplication decision.
- Recipient arrays depend on source JSON being parseable; rows with badly malformed JSON cannot be reconstructed beyond what survives decoding.
- Email repair is intentionally conservative, so some damaged addresses remain unresolved instead of being guessed aggressively.
- Date validation is scoped to the research period `1990-2019`; parseable rows outside that window are excluded from the clean analysis-ready corpus.
"""

(out_dir / "preprocessing_report.md").write_text(report)

print(f"Wrote cleaned sample with {sample_csv.height:,} rows to data/emails.cleaned.preprocessed.sample.csv")
print(f"Wrote full clean corpus with {clean_corpus.height:,} rows to data/emails.cleaned.analysis_ready.parquet")
print(f"Wrote normalized headers to data/emails.normalized.parquet")
print(f"Wrote parsed addresses with {addresses_after.height:,} rows to data/email_addresses.parquet")
print("Wrote preprocessing report to data/preprocessing_report.md")
