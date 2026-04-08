import difflib
import re

import polars as pl


def normalize_text(expr):
    expr = expr.fill_null("")
    for pattern, replacement in [
        ("&nbsp;", " "),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
        ("&amp;", "&"),
        ("\u00a0", " "),
        ("\u200b", " "),
        ("\u2018|\u2019", "'"),
        ('\u201c|\u201d', '"'),
        ("\u2039|\u276e|\u3008|\uff1c", "<"),
        ("\u203a|\u276f|\u3009|\uff1e", ">"),
        ("\u3010", "["),
        ("\u3011", "]"),
        (r"</?(?:u|s|change)>", ""),
        (r"[\r\n\t]+", " "),
        (r"\s+", " "),
    ]:
        expr = expr.str.replace_all(pattern, replacement)
    return expr.str.strip_chars().replace("", None)


def clean_body(expr):
    expr = normalize_text(expr)
    for pattern, replacement in [
        (r"(?i)https?://\S+", " "),
        (r"(?i)www\.\S+", " "),
        (r"(?i)\b(?:view in browser|download now|save now|click here)\b:?", " "),
        (r"(?i)\b(?:unsubscribe|privacy policy|terms of service|manage preferences)\b", " "),
        (r"(?i)\b(?:original message|forwarded by|begin forwarded message)\b", " "),
        (r"(?i)<[^>]+>", " "),
        (r"(?im)^(from|to|cc|bcc|sent|subject):[^\n]*$", " "),
        (r"(?im)^[-_]{2,}.*forwarded message.*$", " "),
        (r"(?im)^this email and any attachments.*$", " "),
        (r"(?im)^please consider the environment.*$", " "),
        (r"(?i)\b(?:do you yahoo!?|don'?t pick lemons|citrix sharefile|all rights reserved)\b", " "),
        (r"[_=~-]{3,}", " "),
        (r"[<>]{2,}", " "),
        (r"\s+", " "),
    ]:
        expr = expr.str.replace_all(pattern, replacement)
    return expr.str.strip_chars().replace("", None)


def decoded_list_expr(column):
    return pl.col(column).fill_null("[]").str.json_decode(pl.List(pl.String))


def normalized_list_expr(column):
    return decoded_list_expr(column).list.eval(normalize_text(pl.element()))


def email_expr(column):
    extracted = pl.col(column).str.to_lowercase()
    for pattern, replacement in [
        (r"(?i)=40", "@"),
        (r"(?i)=2e", "."),
        (r"(?i)=5f", "_"),
        (r"(?i)=2d", "-"),
        (r"(?i)=20|=09|=0a|=0d", ""),
        (
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)(gmail|googlemail|yahoo|hotmail|outlook|icloud|me|mac|msn|live|gmx|aol|protonmail|ymail|rocketmail)\.",
            "${1}${2}@${3}.",
        ),
        (
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)([a-z0-9-]+\.(?:com|net|org|edu|gov|mil|int|co|io|ai|me|tv|us|uk|ru|fr|de|ch|it|nl|se|no|es|br|ca|mx))\b",
            "${1}${2}@${3}",
        ),
    ]:
        extracted = extracted.str.replace_all(pattern, replacement)
    extracted = extracted.str.extract(
        r"([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})",
        1,
    )
    for pattern, replacement in [
        (r"@grnail\.", "@gmail."),
        (r"@gmall\.", "@gmail."),
        (r"@smail\.", "@gmail."),
        (r"@tmail\.", "@gmail."),
        (r"\.(?:corn|cord)[a-z]?$", ".com"),
        (r"\.con$", ".com"),
    ]:
        extracted = extracted.str.replace_all(pattern, replacement)
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
    for pattern, replacement in [
        (r"(?i)=40", "@"),
        (r"(?i)=2e", "."),
        (r"(?i)=5f", "_"),
        (r"(?i)=2d", "-"),
        (r"(?i)=20|=09|=0a|=0d", ""),
        (r"@grnail\.", "@gmail."),
        (r"@gmall\.", "@gmail."),
        (r"@smail\.", "@gmail."),
        (r"@tmail\.", "@gmail."),
        (r"\.(?:corn|cord)[a-z]?$", ".com"),
        (r"\.con$", ".com"),
        (
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)(gmail|googlemail|yahoo|hotmail|outlook|icloud|me|mac|msn|live|gmx|aol|protonmail|ymail|rocketmail)\.",
            r"\1\2@\3.",
        ),
        (
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)([a-z0-9-]+\.(?:com|net|org|edu|gov|mil|int|co|io|ai|me|tv|us|uk|ru|fr|de|ch|it|nl|se|no|es|br|ca|mx))\b",
            r"\1\2@\3",
        ),
    ]:
        value = re.sub(pattern, replacement, value)
    return value


def canonicalize_email(value):
    if value is None or "@" not in value:
        return None
    local_part, domain = value.rsplit("@", 1)
    domain = domain.lower()
    if domain == "googlemail.com":
        domain = "gmail.com"
    return f"{local_part.replace('.', '').lower()}@{domain}"


def scalar_address_rows(frame):
    return pl.concat(
        [
            frame.select(
                "id",
                pl.lit(role).alias("address_role"),
                pl.lit(None, dtype=pl.Int64).alias("address_index"),
                pl.col(f"{role}_raw").alias("raw_value"),
                pl.col(f"{role}_normalized").alias("normalized_value"),
            )
            for role in ["sender", "account_email"]
        ],
        how="diagonal_relaxed",
    )


def recipient_address_rows(frame):
    return pl.concat(
        [
            frame.with_columns(
                pl.int_ranges(0, pl.col(f"{role}_normalized").list.len()).alias("address_index")
            )
            .select(
                "id",
                pl.lit(role).alias("address_role"),
                "address_index",
                pl.col(f"{role}_items").alias("raw_value"),
                pl.col(f"{role}_normalized").alias("normalized_value"),
            )
            .explode("address_index", "raw_value", "normalized_value")
            for role in ["to_recipients", "cc_recipients", "bcc_recipients"]
        ],
        how="diagonal_relaxed",
    )


def build_address_table(frame):
    return (
        pl.concat([scalar_address_rows(frame), recipient_address_rows(frame)], how="diagonal_relaxed")
        .with_columns(
            normalize_text(pl.col("raw_value")).alias("raw_value"),
            email_expr("normalized_value").alias("email"),
            display_name_expr("normalized_value").alias("display_name"),
        )
        .filter(pl.col("normalized_value").is_not_null())
        .select("id", "address_role", "address_index", "raw_value", "normalized_value", "display_name", "email")
    )


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
        domain = "gmail.com" if domain_match.group(1) == "googlemail.com" else domain_match.group(1)
        local_seed = candidate.split(domain_match.group(1), 1)[0]
        local_seed = re.sub(r"^[^a-z0-9]+", "", local_seed)
        local_seed = re.sub(r"[^a-z0-9._%+\-/=]+", "", local_seed).rstrip(".@")
        compare_seed = re.sub(r"[^a-z0-9]", "", local_seed)
        if len(compare_seed) < 4:
            continue
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
