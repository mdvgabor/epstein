import os
from pathlib import Path
import re
from time import perf_counter

import polars as pl

from address_processing import (
    build_address_table,
    canonicalize_email_expr,
    clean_body,
    decoded_list_expr,
    fuzzy_repair_emails,
    normalize_person_name_expr,
    normalize_text,
)

input_dir = Path("data")
out_dir = Path(os.environ.get("PREPROCESS_OUT_DIR", input_dir.as_posix()))
out_dir.mkdir(parents=True, exist_ok=True)
sample_rows = int(os.environ.get("PREPROCESS_SAMPLE_ROWS", "0") or "0")
profile_started_at = perf_counter()
profile_last_at = profile_started_at


def log_phase(label):
    global profile_last_at
    now = perf_counter()
    print(f"[profile] {label}: phase={now - profile_last_at:.2f}s total={now - profile_started_at:.2f}s", flush=True)
    profile_last_at = now


def person_name_key_exprs(expr):
    normalized = normalize_person_name_expr(expr)
    tokens = normalized.str.split(" ")
    first = tokens.list.first()
    last = tokens.list.last()
    return [
        normalized.alias("name_key_full"),
        normalized.str.replace_all(" ", "", literal=True).alias("name_key_compact"),
        pl.when(tokens.list.len() >= 2)
        .then(first + pl.lit(" ") + last.str.slice(0, 1))
        .otherwise(None)
        .alias("name_key_first_last_initial"),
        pl.when(tokens.list.len() >= 2)
        .then(first.str.slice(0, 1) + pl.lit(" ") + last)
        .otherwise(None)
        .alias("name_key_initial_last"),
        pl.when((tokens.list.len() >= 2) & (last.str.len_chars() >= 3))
        .then(first.str.slice(0, 1) + pl.lit(" ") + last.str.slice(0, 3))
        .otherwise(None)
        .alias("name_key_initial_last_prefix"),
    ]


def name_match_label_expr():
    return pl.col("name_key_type").replace(
        {
            "name_key_full": "display_name_full",
            "name_key_compact": "display_name_compact",
            "name_key_first_last_initial": "display_name_first_last_initial",
            "name_key_initial_last": "display_name_initial_last",
            "name_key_initial_last_prefix": "display_name_initial_last_prefix",
        }
    )


def name_match_priority_expr():
    return (
        pl.when(pl.col("match_source") == "display_name_full")
        .then(pl.lit(0, dtype=pl.UInt8))
        .when(pl.col("match_source") == "display_name_compact")
        .then(pl.lit(1, dtype=pl.UInt8))
        .when(pl.col("match_source") == "display_name_first_last_initial")
        .then(pl.lit(2, dtype=pl.UInt8))
        .when(pl.col("match_source") == "display_name_initial_last")
        .then(pl.lit(3, dtype=pl.UInt8))
        .when(pl.col("match_source") == "display_name_initial_last_prefix")
        .then(pl.lit(4, dtype=pl.UInt8))
        .otherwise(None)
    )


def long_name_keys(frame, index):
    return (
        frame.unpivot(
            index=index,
            on=[
                "name_key_full",
                "name_key_compact",
                "name_key_first_last_initial",
                "name_key_initial_last",
                "name_key_initial_last_prefix",
            ],
            variable_name="name_key_type",
            value_name="person_name_key",
        )
        .filter(pl.col("person_name_key").is_not_null())
        .with_columns(name_match_label_expr().alias("match_source"))
        .drop("name_key_type")
    )


def unique_person_name_matches(people_frame):
    keyed = people_frame.with_columns(*person_name_key_exprs(pl.col("person_name")))
    long = long_name_keys(keyed, ["person_id", "person_name"])
    return (
        long.join(
            long.group_by("match_source", "person_name_key").len().filter(pl.col("len") == 1).select(
                "match_source", "person_name_key"
            ),
            on=["match_source", "person_name_key"],
            how="inner",
        )
        .with_columns(name_match_priority_expr().alias("match_priority"))
        .select("match_source", "match_priority", "person_name_key", "person_id", "person_name")
    )


def add_display_name_matches(participants, name_matches):
    participant_columns = participants.columns
    keyed = participants.with_row_index("participant_row").with_columns(
        *person_name_key_exprs(pl.col("display_name"))
    )
    best_matches = (
        long_name_keys(keyed, "participant_row")
        .join(name_matches, on=["match_source", "person_name_key"], how="inner")
        .sort("participant_row", "match_priority")
        .unique(subset=["participant_row"], keep="first", maintain_order=True)
        .select(
            "participant_row",
            pl.col("person_id").alias("person_id_name"),
            pl.col("person_name").alias("person_name_name"),
            pl.col("match_source").alias("match_source_name"),
        )
    )
    return (
        keyed.select("participant_row", *participant_columns)
        .join(best_matches, on="participant_row", how="left")
        .drop("participant_row")
    )


def machine_email_expr(expr):
    return expr.fill_null("").str.to_lowercase().str.contains(
        r"^(?:no-?reply|noreply|donotreply|do-?not-?reply|news|newsletter|updates?|notifications?|hello|info|support|mailer|mail|admin|contact|marketing|sales|editor|alerts?|mailer-daemon|postmaster)@|^[a-z0-9._%+\-]*(?:batch|daemon|notification|newsletter|bounce|system)[a-z0-9._%+\-]*@|@list\.|@[^@]*\.list\.|@(?:lists|newsletter|notifications?)\."
    )


def human_display_name_expr(expr):
    name_key = normalize_person_name_expr(expr)
    return (
        expr.is_not_null()
        & expr.str.contains("@", literal=True).not_()
        & expr.str.contains("&", literal=True).not_()
        & name_key.is_not_null()
        & (name_key.str.split(" ").list.len() >= 2)
        & name_key.str.contains(
            r"\b(?:mail|mailto|mailer|delivery|subsystem|daemon|system|batch|list|newsletter|notification|updates?|support|admin|office|service|services|team|group|department|valuations|control|oversight|banking|middle|customer|client|alert|alerts|times|worldwide|reservation|reservations|online|university|college|school|etl|pwm|crm|derivatives|travel|bank|capital|fund|funds|llp|llc|inc|ltd|corp|corporation|company|clientservices|sharefile|nytimes|vacation|scanner|linkedin|jobs|dbgps|news|brief|breaking|digest|editorial|editor|feed|post|posts|press|daily|beast|flipboard|smartbrief|reuters|calendar|security|assurant|protect|mobile|alerts?|staff|branch)\b"
        ).not_()
        & name_key.str.contains(r"\b(?:from|subject|re|fw|fwd|forwarded|message|original)\b").not_()
        & name_key.str.contains(r"[0-9]").not_()
        & name_key.str.contains(r"&").not_()
    )


people = pl.read_csv(input_dir / "jmail_people.csv").select(
    pl.col("slug").alias("person_id"),
    pl.col("name").alias("person_name"),
    "description",
)
people_with_counts = pl.read_csv(input_dir / "jmail_people.csv").select(
    pl.col("slug").alias("person_id"),
    pl.col("name").alias("person_name"),
    "email_count",
)

seed_path = input_dir / "person_email_seed.csv"
if not seed_path.exists():
    pl.DataFrame(
        {
            "person_id": ["jeffrey-epstein", "jeffrey-epstein"],
            "email": ["jeeproject@yahoo.com", "jeevacation@gmail.com"],
        }
    ).write_csv(seed_path)

seed_emails = (
    pl.read_csv(seed_path)
    .select("person_id", canonicalize_email_expr(pl.col("email")).alias("email"))
    .filter(pl.col("person_id").is_not_null() & pl.col("email").is_not_null())
    .unique(subset=["person_id", "email"], keep="first")
    .join(people.select("person_id", "person_name"), on="person_id", how="inner")
    .with_columns(pl.lit("seed_email").alias("alias_source"))
)

missing_people = (
    pl.read_csv(seed_path)
    .select("person_id")
    .filter(pl.col("person_id").is_not_null())
    .unique()
    .join(people.select("person_id"), on="person_id", how="anti")
)
if missing_people.height > 0:
    raise ValueError(f"Unknown person_id values in {seed_path}: {missing_people['person_id'].to_list()}")

conflicting_seed_emails = (
    seed_emails.group_by("email")
    .agg(pl.col("person_id").n_unique().alias("person_count"))
    .filter(pl.col("person_count") > 1)
)
if conflicting_seed_emails.height > 0:
    conflicts = (
        seed_emails.join(conflicting_seed_emails.select("email"), on="email", how="inner")
        .sort("email", "person_id")
        .select("email", "person_id")
        .iter_rows()
    )
    raise ValueError(f"Conflicting email assignments in {seed_path}: {list(conflicts)}")

person_name_matches = unique_person_name_matches(people)
people_last_names = (
    people.with_columns(normalize_person_name_expr(pl.col("person_name")).str.split(" ").list.last().alias("last_name"))
    .filter(pl.col("last_name").is_not_null() & (pl.col("last_name").str.len_chars() >= 5))
)
unique_last_names = (
    people_last_names.group_by("last_name")
    .agg(pl.col("person_id").n_unique().alias("person_count"))
    .filter(pl.col("person_count") == 1)
    .join(people_last_names.select("person_id", "person_name", "last_name"), on="last_name", how="inner")
    .select("person_id", "person_name", "last_name")
)
log_phase("load people metadata")

email_scan = pl.scan_parquet(input_dir / "emails.parquet").filter(pl.col("is_promotional").fill_null(False).not_())
if sample_rows > 0:
    email_scan = email_scan.head(sample_rows)
    print(f"[profile] sample mode: reading first {sample_rows:,} non-promotional emails", flush=True)

base = (
    email_scan
    .with_columns(
        pl.col("is_promotional").fill_null(False).alias("is_promotional"),
        pl.col("sender").alias("sender_raw"),
        pl.col("account_email").alias("account_email_raw"),
        *[pl.col(role).alias(f"{role}_raw") for role in ["to_recipients", "cc_recipients", "bcc_recipients"]],
        pl.col("content_markdown").alias("content_markdown_raw"),
        pl.col("subject").fill_null("").str.strip_chars().replace("", None).alias("subject_clean"),
        normalize_text(pl.col("sender")).alias("sender_normalized"),
        normalize_text(pl.col("account_email")).alias("account_email_normalized"),
        *[decoded_list_expr(role).alias(f"{role}_items") for role in ["to_recipients", "cc_recipients", "bcc_recipients"]],
        clean_body(pl.col("content_markdown")).alias("body_clean"),
        pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.fZ", strict=False).alias("sent_at"),
    )
    .with_columns(
        *[
            pl.col(f"{role}_items").list.eval(normalize_text(pl.element())).alias(f"{role}_normalized")
            for role in ["to_recipients", "cc_recipients", "bcc_recipients"]
        ],
        pl.concat_str(
            [
                pl.col("subject").fill_null("").str.strip_chars(),
                pl.lit("\n"),
                pl.col("body_clean").fill_null(""),
            ]
        )
        .str.strip_chars()
        .replace("", None)
        .alias("text_clean"),
    )
    .with_columns(
        pl.col("text_clean").str.len_chars().fill_null(0).alias("text_char_len"),
        pl.col("text_clean").str.count_matches(r"\b[\p{L}\p{N}']+\b").fill_null(0).alias("text_token_len"),
        pl.col("sender_raw")
        .fill_null("")
        .str.to_lowercase()
        .str.contains(r"redacted|█")
        .alias("sender_redacted"),
        pl.col("sent_at").dt.year().alias("year"),
    )
    .with_columns(
        pl.when(pl.col("year").is_between(1990, 2019, closed="both"))
        .then(pl.col("year"))
        .otherwise(None)
        .alias("year"),
        (
            pl.col("id").cast(pl.String).fill_null("")
            + pl.lit("||")
            + pl.col("sender_normalized").fill_null("")
            + pl.lit("||")
            + pl.col("subject_clean").fill_null("")
            + pl.lit("||")
            + pl.col("sent_at").cast(pl.String).fill_null("")
            + pl.lit("||")
            + pl.col("text_clean").fill_null("").str.slice(0, 500)
        ).alias("duplicate_signature"),
    )
)

processed = base.collect()
log_phase("base collect")

fact_emails = (
    processed.with_columns(
        pl.col("duplicate_signature").is_duplicated().alias("duplicate_signature_flag"),
        pl.col("id").is_duplicated().alias("duplicate_id_flag"),
        pl.col("subject_clean")
        .fill_null("")
        .str.replace_all(r"(?i)^\s*(?:re|fw|fwd)\s*:\s*", "")
        .str.strip_chars()
        .replace("", None)
        .alias("subject_base"),
    )
    .select(
        pl.col("id").alias("email_id"),
        "doc_id",
        "message_index",
        pl.col("subject_clean").alias("subject"),
        "subject_base",
        "sent_at",
        "year",
        "folder_path",
        "release_batch",
        "body_clean",
        "text_clean",
        "text_char_len",
        "text_token_len",
        "duplicate_id_flag",
        "duplicate_signature_flag",
        "sender_redacted",
    )
)
log_phase("build fact emails")

address_rows = build_address_table(processed)
log_phase("build address table")

participant_rows = fuzzy_repair_emails(address_rows).with_columns(
    pl.col("id").alias("email_id"),
    pl.col("address_role")
    .replace(
        {
            "to_recipients": "to",
            "cc_recipients": "cc",
            "bcc_recipients": "bcc",
        }
    )
    .alias("involvement_role"),
    pl.col("address_index").fill_null(0).cast(pl.Int64).alias("role_index"),
)
log_phase("repair participant rows")


def resolve_people(participants, aliases):
    participant_columns = [
        column
        for column in participants.columns
        if column not in {"person_id_name", "person_name_name", "match_source_name"}
    ]
    return (
        participants.join(
            aliases.rename(
                {
                    "person_id": "person_id_alias",
                    "person_name": "person_name_alias",
                    "alias_source": "match_source_alias",
                }
            ),
            on="email",
            how="left",
        )
        .with_columns(
            pl.coalesce("person_id_alias", "person_id_name").alias("person_id"),
            pl.coalesce("person_name_alias", "person_name_name").alias("person_name"),
            pl.when(pl.col("person_id_alias").is_not_null())
            .then(pl.col("match_source_alias"))
            .otherwise(pl.col("match_source_name"))
            .alias("match_source"),
        )
        .select(*participant_columns, "person_id", "person_name", "match_source")
    )


def infer_aliases(resolved_people, known_aliases):
    candidates = (
        resolved_people.filter(
            pl.col("person_id").is_not_null()
            & pl.col("email").is_not_null()
            & pl.col("match_source").is_in(["display_name_full", "display_name_compact", "display_name_first_last_initial"])
            & machine_email_expr(pl.col("email")).not_()
        )
        .group_by("email", "person_id", "person_name")
        .agg(
            pl.col("email_id").n_unique().alias("email_count"),
            pl.col("match_source").filter(pl.col("match_source") == "display_name_full").len().alias("full_name_rows"),
        )
    )
    unambiguous = (
        candidates.group_by("email")
        .agg(
            pl.col("person_id").n_unique().alias("person_count"),
            pl.col("email_count").max().alias("best_email_count"),
            pl.col("full_name_rows").max().alias("best_full_name_rows"),
        )
        .filter(
            (pl.col("person_count") == 1)
            & ((pl.col("best_full_name_rows") >= 2) | (pl.col("best_email_count") >= 5))
        )
    )
    return (
        candidates.join(unambiguous.select("email"), on="email", how="inner")
        .select("person_id", "person_name", "email")
        .join(known_aliases.select("email"), on="email", how="anti")
        .unique(subset=["person_id", "email"], keep="first")
        .with_columns(pl.lit("inferred_email").alias("alias_source"))
    )


participant_name_matches = add_display_name_matches(participant_rows, person_name_matches)
log_phase("static display-name matches")

alias_map = seed_emails
resolved_people = resolve_people(participant_name_matches, alias_map)
log_phase("alias resolve pass 0")
for _ in range(3):
    new_aliases = infer_aliases(resolved_people, alias_map)
    if new_aliases.height == 0:
        break
    alias_map = pl.concat([alias_map, new_aliases], how="diagonal_relaxed").unique(
        subset=["person_id", "email"], keep="first"
    )
    conflicts = alias_map.group_by("email").agg(pl.col("person_id").n_unique().alias("person_count")).filter(
        pl.col("person_count") > 1
    )
    if conflicts.height > 0:
        alias_map = alias_map.join(conflicts.select("email"), on="email", how="anti")
    resolved_people = resolve_people(participant_name_matches, alias_map)
    log_phase("alias resolve iteration")

display_name_counts = (
    resolved_people.filter(
        pl.col("person_id").is_null()
        & pl.col("email").is_not_null()
        & pl.col("display_name").is_not_null()
        & machine_email_expr(pl.col("email")).not_()
        & human_display_name_expr(pl.col("display_name"))
    )
    .group_by("email", "display_name")
    .len()
    .sort("email", "len", descending=[False, True])
    .unique(subset=["email"], keep="first")
    .select("email", "display_name")
)
discovered_people = (
    resolved_people.filter(
        pl.col("person_id").is_null()
        & pl.col("email").is_not_null()
        & machine_email_expr(pl.col("email")).not_()
        & human_display_name_expr(pl.col("display_name"))
    )
    .group_by("email")
    .agg(
        pl.col("email_id").n_unique().alias("email_count"),
        pl.len().alias("participant_row_count"),
    )
    .filter(pl.col("email_count") >= 2)
    .join(display_name_counts, on="email", how="left")
    .with_columns(
        (
            pl.lit("discovered-email-")
            + pl.col("email").str.replace_all(r"[^a-z0-9]+", "-").str.strip_chars("-")
        ).alias("person_id"),
        pl.coalesce("display_name", "email").alias("person_name"),
        (pl.lit("Discovered from participant email ") + pl.col("email")).alias("description"),
    )
    .select("person_id", "person_name", "description", "email")
)
log_phase("discover unmatched people")

if discovered_people.height > 0:
    people = pl.concat(
        [
            people,
            discovered_people.select("person_id", "person_name", "description"),
        ],
        how="diagonal_relaxed",
    ).unique(subset=["person_id"], keep="first")
    discovered_aliases = (
        discovered_people.select("person_id", "person_name", "email")
        .with_columns(pl.lit("discovered_email").alias("alias_source"))
        .rename(
            {
                "person_id": "person_id_discovered",
                "person_name": "person_name_discovered",
                "alias_source": "match_source_discovered",
            }
        )
    )
    resolved_people = pl.concat(
        [
            resolved_people.filter(pl.col("person_id").is_not_null()),
            resolved_people.filter(pl.col("person_id").is_null())
            .join(discovered_aliases, on="email", how="left")
            .with_columns(
                pl.coalesce("person_id", "person_id_discovered").alias("person_id"),
                pl.coalesce("person_name", "person_name_discovered").alias("person_name"),
                pl.coalesce("match_source", "match_source_discovered").alias("match_source"),
            )
            .drop(
                "person_id_discovered",
                "person_name_discovered",
                "match_source_discovered",
            ),
        ],
        how="diagonal_relaxed",
    )
    log_phase("apply discovered people")

bridge_email_people = (
    resolved_people.filter(pl.col("person_id").is_not_null())
    .sort("email_id", "involvement_role", "role_index")
    .unique(subset=["email_id", "person_id", "involvement_role"], keep="first")
    .select(
        "email_id",
        "person_id",
        "person_name",
        "involvement_role",
        "role_index",
        "match_source",
        "display_name",
        "raw_value",
    )
)
log_phase("build bridge rows")

keyword_path = input_dir / "jmail_person_keywords.csv"
if keyword_path.exists():
    keyword_source = (
        pl.read_csv(keyword_path)
        .filter(pl.col("person_id").is_not_null() & pl.col("keyword").is_not_null())
        .join(people_with_counts.select("person_id", "person_name", "email_count"), on="person_id", how="inner")
        .with_columns(
            pl.col("keyword").str.to_lowercase().str.strip_chars().alias("keyword"),
            normalize_person_name_expr(pl.col("person_name")).alias("person_name_key"),
        )
    )
    current_counts = bridge_email_people.group_by("person_id").agg(pl.col("email_id").n_unique().alias("matched_email_count"))
    undercounted = (
        people_with_counts.join(current_counts, on="person_id", how="left")
        .with_columns((pl.col("email_count") - pl.col("matched_email_count").fill_null(0)).alias("gap"))
        .filter(pl.col("gap") > 500)
        .select("person_id", "gap")
    )
    keyword_source = keyword_source.join(undercounted, on="person_id", how="inner")
    keyword_groups = []
    for row in keyword_source.iter_rows(named=True):
        compact = re.sub(r"[^a-z0-9@. ]+", "", row["keyword"] or "").strip()
        name_parts = set((row["person_name_key"] or "").split())
        compact_joined = compact.replace(" ", "")
        if len(compact_joined) < 5:
            continue
        if compact in name_parts or compact_joined in name_parts:
            continue
        if not (
            " " in compact
            or "@" in compact
            or "." in compact
            or any(ch.isdigit() for ch in compact)
            or len(compact_joined) >= 8
            or compact.endswith("jet")
        ):
            continue
        keyword_groups.append((row["person_id"], row["person_name"], compact))
    surname_keywords = (
        unique_last_names.join(undercounted.select("person_id"), on="person_id", how="inner")
        .select("person_id", "person_name", pl.col("last_name").alias("keyword"))
        .iter_rows(named=True)
    )
    for row in surname_keywords:
        keyword_groups.append((row["person_id"], row["person_name"], row["keyword"]))
    log_phase("prepare keyword groups")

    keyword_frame = (
        pl.DataFrame(keyword_groups, schema=["person_id", "person_name", "keyword"], orient="row")
        .unique(subset=["person_id", "keyword"], keep="first")
        .sort("keyword")
    )
    if keyword_frame.height > 0:
        keywords = keyword_frame.select("keyword").unique().get_column("keyword").to_list()
        keyword_hits = (
            processed.select(
                pl.col("id").alias("email_id"),
                pl.concat_str(
                    [
                        pl.col("sender_raw").fill_null(""),
                        pl.lit("\n"),
                        pl.col("account_email_raw").fill_null(""),
                        pl.lit("\n"),
                        pl.col("to_recipients_raw").fill_null(""),
                        pl.lit("\n"),
                        pl.col("cc_recipients_raw").fill_null(""),
                        pl.lit("\n"),
                        pl.col("bcc_recipients_raw").fill_null(""),
                        pl.lit("\n"),
                        pl.col("subject_clean").fill_null(""),
                        pl.lit("\n"),
                        pl.col("content_markdown_raw").fill_null(""),
                    ]
                )
                .str.to_lowercase()
                .str.extract_many(keywords, overlapping=True)
                .alias("keyword"),
            )
            .with_row_index("email_order")
            .explode("keyword")
            .filter(pl.col("keyword").is_not_null())
            .join(keyword_frame, on="keyword", how="inner")
            .join(bridge_email_people.select("email_id", "person_id").unique(), on=["email_id", "person_id"], how="anti")
            .sort("person_id", "email_order")
            .unique(subset=["email_id", "person_id"], keep="first", maintain_order=True)
            .join(undercounted, on="person_id", how="inner")
            .with_columns(pl.col("email_id").cum_count().over("person_id").alias("person_hit_nr"))
            .filter(pl.col("person_hit_nr") <= pl.col("gap"))
            .select(
                "email_id",
                "person_id",
                "person_name",
                pl.lit("mentioned").alias("involvement_role"),
                pl.lit(0, dtype=pl.Int64).alias("role_index"),
                pl.lit("jmail_keyword").alias("match_source"),
                pl.lit(None, dtype=pl.String).alias("display_name"),
                pl.lit(None, dtype=pl.String).alias("raw_value"),
            )
        )
        if keyword_hits.height > 0:
            bridge_email_people = pl.concat([bridge_email_people, keyword_hits], how="diagonal_relaxed").unique(
                subset=["email_id", "person_id", "involvement_role"], keep="first"
            )
        log_phase("keyword extraction")

fact_path = out_dir / "fact_emails.parquet"
people_path = out_dir / "dim_people.parquet"
bridge_path = out_dir / "bridge_email_people.parquet"

fact_emails.write_parquet(fact_path)
people.write_parquet(people_path)
bridge_email_people.write_parquet(bridge_path)
log_phase("write parquet outputs")

for stale_path in [out_dir / "emails.cleaned.analysis_ready.parquet", out_dir / "email_addresses.parquet"]:
    if stale_path.exists():
        stale_path.unlink()

(out_dir / "duckdb_views.sql").write_text(
    "\n".join(
        [
            f"create or replace view fact_emails as select * from parquet_scan('{fact_path.as_posix()}');",
            f"create or replace view dim_people as select * from parquet_scan('{people_path.as_posix()}');",
            f"create or replace view bridge_email_people as select * from parquet_scan('{bridge_path.as_posix()}');",
        ]
    )
    + "\n"
)

print(f"Wrote {fact_emails.height:,} rows to {fact_path}")
print(f"Wrote {people.height:,} rows to {people_path}")
print(f"Wrote {bridge_email_people.height:,} rows to {bridge_path}")
