import difflib
import re

import polars as pl


def normalize_text(expr):
    return (
        expr.fill_null("")
        .str.replace_many(
            ["&nbsp;", "&lt;", "&gt;", "&quot;", "&#39;", "&amp;",
             "\u00a0", "\u200b", "\u2018", "\u2019", "\u201c", "\u201d",
             "\u2039", "\u276e", "\u3008", "\uff1c",
             "\u203a", "\u276f", "\u3009", "\uff1e",
             "\u3010", "\u3011"],
            [" ", "<", ">", '"', "'", "&",
             " ", " ", "'", "'", '"', '"',
             "<", "<", "<", "<",
             ">", ">", ">", ">",
             "[", "]"],
        )
        .str.replace_all(r"</?(?:u|s|change)>", "")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def clean_body(expr):
    return (
        normalize_text(
            expr.fill_null("")
            .str.replace_all(r"(?im)^(?:from|to|cc|bcc|sent|subject):[^\n]*$", " ")
            .str.replace_all(
                r"(?im)^[-_]{2,}.*forwarded message.*$|^this email and any attachments.*$|^please consider the environment.*$",
                " ",
            )
        )
        .str.replace_all(r"(?i)https?://\S+|www\.\S+", " ")
        .str.replace_many(
            {
                "view in browser": " ",
                "download now": " ",
                "save now": " ",
                "click here": " ",
                "unsubscribe": " ",
                "privacy policy": " ",
                "terms of service": " ",
                "manage preferences": " ",
                "original message": " ",
                "forwarded by": " ",
                "begin forwarded message": " ",
                "do you yahoo!?": " ",
                "don't pick lemons": " ",
                "citrix sharefile": " ",
                "all rights reserved": " ",
            },
            ascii_case_insensitive=True,
        )
        .str.replace_all(r"(?i)<[^>]+>", " ")
        .str.replace_all(r"[_=~-]{3,}|[<>]{2,}", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def decoded_list_expr(column):
    return pl.col(column).fill_null("[]").str.json_decode(pl.List(pl.String))


def normalized_list_expr(column):
    return decoded_list_expr(column).list.eval(normalize_text(pl.element()))


def email_expr(column):
    extracted = (
        pl.col(column)
        .str.to_lowercase()
        .str.replace_many(["=40", "=2e", "=5f", "=2d", "=20", "=09", "=0a", "=0d"], ["@", ".", "_", "-", "", "", "", ""])
    )
    for pattern, replacement in [
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
    extracted = extracted.str.replace_many(
        ["@grnail.", "@gmall.", "@smail.", "@tmail."],
        ["@gmail.", "@gmail.", "@gmail.", "@gmail."],
    )
    for pattern, replacement in [
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
        .str.replace_all("'", " ", literal=True)
        .str.replace_all(r"\s+", " ")
        .str.replace_all(r"^[,;:\-\s]+|[,;:\-\s]+$", "")
    )
    return pl.when(cleaned == "").then(None).otherwise(cleaned)


def canonicalize_email(value):
    if value is None or "@" not in value:
        return None
    local_part, domain = value.rsplit("@", 1)
    domain = domain.lower()
    if domain == "googlemail.com":
        domain = "gmail.com"
    return f"{local_part.replace('.', '').lower()}@{domain}"


def canonicalize_email_expr(expr):
    local = expr.str.extract(r"^(.*)@[^@]*$", 1)
    domain = expr.str.extract(r"@([^@]*)$", 1).str.to_lowercase()
    domain = pl.when(domain == "googlemail.com").then(pl.lit("gmail.com")).otherwise(domain)
    return (
        pl.when(expr.is_not_null() & expr.str.contains("@", literal=True))
        .then(local.str.to_lowercase().str.replace_all(".", "", literal=True) + pl.lit("@") + domain)
        .otherwise(None)
    )


def normalize_person_name_expr(expr):
    return (
        expr.fill_null("")
        .str.to_lowercase()
        .str.replace_many(["&nbsp;", "&#39;", "&quot;", "&amp;"], [" ", " ", " ", " "])
        .str.replace_all("[\u2019']", "")
        .str.replace_all(r"[^a-z0-9]+", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def repair_candidate_expr(expr):
    return (
        expr.str.to_lowercase()
        .str.replace_many(
            ["=40", "=2e", "=5f", "=2d", "=20", "=09", "=0a", "=0d"],
            ["@", ".", "_", "-", "", "", "", ""],
        )
        .str.replace_all(
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)(gmail|googlemail|yahoo|hotmail|outlook|icloud|me|mac|msn|live|gmx|aol|protonmail|ymail|rocketmail)\.",
            "${1}${2}@${3}.",
        )
        .str.replace_all(
            r"(^|[<\"'\[(])([a-z0-9._%+\-/=]+)(?:§|#)([a-z0-9-]+\.(?:com|net|org|edu|gov|mil|int|co|io|ai|me|tv|us|uk|ru|fr|de|ch|it|nl|se|no|es|br|ca|mx))\b",
            "${1}${2}@${3}",
        )
        .str.replace_all(r"@(?:grnail|gmall|smail|tmail)\.", "@gmail.")
        .str.replace_all(r"\.(?:corn|cord)[a-z]?$|\.con$", ".com")
    )


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
        .filter(pl.col("normalized_value").is_not_null())
        .with_columns(
            email_expr("normalized_value").alias("email"),
            display_name_expr("normalized_value").alias("display_name"),
        )
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

    suspicious = frame.filter(
        pl.col("email").is_null()
        & pl.col("normalized_value").is_not_null()
        & pl.col("normalized_value")
        .str.to_lowercase()
        .str.contains(r"§|#|=|grnail|gmall|smail|tmail|corn|cord|\.con\b")
    )

    if suspicious.height == 0:
        return frame

    with_candidate = suspicious.with_columns(
        repair_candidate_expr(pl.col("normalized_value")).alias("candidate")
    )
    direct = with_candidate.with_columns(
        canonicalize_email_expr(
            pl.col("candidate").str.extract(
                r"""(?:^|[<"'(\[ \t])([A-Za-z0-9](?:[A-Za-z0-9._%+\-/=]*[A-Za-z0-9])?@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})(?:$|[>"')\] \t,;])""",
                1,
            )
        ).alias("email_repaired")
    )

    direct_repairs = (
        direct.filter(pl.col("email_repaired").is_not_null())
        .select("id", "address_role", "address_index", "email_repaired")
    )

    needs_fuzzy = direct.filter(pl.col("email_repaired").is_null())

    candidates_by_domain = {}
    for row in known.iter_rows(named=True):
        domain = "gmail.com" if row["domain"] == "googlemail.com" else row["domain"]
        candidates_by_domain.setdefault(domain, []).append(
            (re.sub(r"[^a-z0-9]", "", row["local_part"]), row["email"], row["len"])
        )

    fuzzy_rows = []
    for row in needs_fuzzy.iter_rows(named=True):
        candidate = row["candidate"]
        if candidate is None:
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
        fuzzy_rows.append(
            {
                "id": row["id"],
                "address_role": row["address_role"],
                "address_index": row["address_index"],
                "email_repaired": canonicalize_email(best_email),
            }
        )

    if fuzzy_rows:
        repaired_rows = pl.concat(
            [direct_repairs, pl.DataFrame(fuzzy_rows)],
            how="diagonal_relaxed",
        )
    elif direct_repairs.height > 0:
        repaired_rows = direct_repairs
    else:
        return frame

    return (
        frame.join(
            repaired_rows.unique(subset=["id", "address_role", "address_index"], keep="first"),
            on=["id", "address_role", "address_index"],
            how="left",
        )
        .with_columns(pl.coalesce("email_repaired", "email").alias("email"))
        .drop("email_repaired")
    )
