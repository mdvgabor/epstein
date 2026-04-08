import os
from pathlib import Path

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

out_dir = Path("data")
out_dir.mkdir(exist_ok=True)


def unique_person_key_table(keyed, key_column):
    table = keyed.filter(pl.col(key_column).is_not_null())
    return (
        table.join(
            table.group_by(key_column).len().filter(pl.col("len") == 1).select(key_column),
            on=key_column,
            how="inner",
        )
        .select(key_column, "person_id", "person_name")
    )


base = (
    pl.scan_parquet("data/emails.parquet")
    .with_row_index("row_nr")
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
        pl.coalesce(
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S%.fZ", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%Y-%m-%d", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%m/%d/%Y %H:%M", strict=False),
            pl.col("sent_at").str.strptime(pl.Datetime, "%m/%d/%Y", strict=False),
        ).alias("sent_at_parsed"),
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

processed = (
    base.filter(pl.col("is_promotional").not_())
    .with_columns(
        pl.col("text_char_len").lt(80).alias("too_short"),
        pl.col("sent_at_valid").is_null().alias("invalid_date"),
        pl.col("duplicate_signature").is_duplicated().alias("duplicate_signature_flag"),
        pl.col("id").is_duplicated().alias("duplicate_id_flag"),
    )
    .collect(engine=os.getenv("POLARS_ENGINE_AFFINITY", "auto"))
)

person_emails = (
    pl.read_csv(out_dir / "jmail_person_emails.csv")
    .select(
        pl.col("slug").alias("person_id"),
        pl.col("name").alias("person_name"),
        pl.col("email").alias("matched_alias_email"),
        canonicalize_email_expr(pl.col("email")).alias("email"),
    )
    .filter(pl.col("email").is_not_null())
    .unique(subset=["person_id", "email"], keep="first")
)
person_emails = person_emails.join(
    person_emails.group_by("email").len().filter(pl.col("len") == 1).select("email"),
    on="email",
    how="inner",
)

people = pl.read_csv(out_dir / "jmail_people.csv").select(
    pl.col("slug").alias("person_id"),
    pl.col("name").alias("person_name"),
)

# Pre-compute all name keys on the people table
_name_norm = normalize_person_name_expr(pl.col("person_name"))
_name_tokens = _name_norm.str.split(" ")
_first_tok = _name_tokens.list.first()
_last_tok = _name_tokens.list.last()

people_keyed = people.with_columns(
    _name_norm.alias("person_name_full_key"),
    _name_norm.str.replace_all(" ", "", literal=True).alias("person_name_compact_key"),
    pl.when(_name_tokens.list.len() >= 2)
    .then(_first_tok + pl.lit(" ") + _last_tok.str.slice(0, 1))
    .otherwise(None)
    .alias("person_name_first_last_initial_key"),
    pl.when(_name_tokens.list.len() >= 2)
    .then(_first_tok.str.slice(0, 1) + pl.lit(" ") + _last_tok)
    .otherwise(None)
    .alias("person_name_initial_last_key"),
    pl.when((_name_tokens.list.len() >= 2) & (_last_tok.str.len_chars() >= 3))
    .then(_first_tok.str.slice(0, 1) + pl.lit(" ") + _last_tok.str.slice(0, 3))
    .otherwise(None)
    .alias("person_name_initial_last_prefix_key"),
)

person_names_full = unique_person_key_table(people_keyed, "person_name_full_key")
person_names_compact = unique_person_key_table(people_keyed, "person_name_compact_key")
person_names_first_last_initial = unique_person_key_table(people_keyed, "person_name_first_last_initial_key")
person_names_initial_last = unique_person_key_table(people_keyed, "person_name_initial_last_key")
person_names_initial_last_prefix = unique_person_key_table(people_keyed, "person_name_initial_last_prefix_key")

addresses_before = build_address_table(processed)

# Compute name keys on addresses: normalize once, tokenize once, derive all keys
_addr_name_norm = normalize_person_name_expr(pl.col("display_name"))
_addr_tokens = _addr_name_norm.str.split(" ")
_addr_first = _addr_tokens.list.first()
_addr_last = _addr_tokens.list.last()

addresses_after = (
    fuzzy_repair_emails(addresses_before)
    .with_columns(
        canonicalize_email_expr(pl.col("email")),
        _addr_name_norm.alias("person_name_full_key"),
    )
    .with_columns(
        pl.col("person_name_full_key").str.replace_all(" ", "", literal=True).alias("person_name_compact_key"),
        pl.col("person_name_full_key").str.split(" ").alias("_name_tokens"),
    )
    .with_columns(
        pl.when(pl.col("_name_tokens").list.len() >= 2)
        .then(pl.col("_name_tokens").list.first() + pl.lit(" ") + pl.col("_name_tokens").list.last().str.slice(0, 1))
        .otherwise(None)
        .alias("person_name_first_last_initial_key"),
        pl.when(pl.col("_name_tokens").list.len() >= 2)
        .then(pl.col("_name_tokens").list.first().str.slice(0, 1) + pl.lit(" ") + pl.col("_name_tokens").list.last())
        .otherwise(None)
        .alias("person_name_initial_last_key"),
        pl.when((pl.col("_name_tokens").list.len() >= 2) & (pl.col("_name_tokens").list.last().str.len_chars() >= 3))
        .then(pl.col("_name_tokens").list.first().str.slice(0, 1) + pl.lit(" ") + pl.col("_name_tokens").list.last().str.slice(0, 3))
        .otherwise(None)
        .alias("person_name_initial_last_prefix_key"),
    )
    .drop("_name_tokens")
    .join(
        person_emails.rename(
            {
                "person_id": "person_id_email",
                "person_name": "person_name_email",
            }
        ),
        on="email",
        how="left",
    )
    .join(
        person_names_full.rename(
            {
                "person_id": "person_id_name_full",
                "person_name": "person_name_name_full",
            }
        ),
        on="person_name_full_key",
        how="left",
    )
    .join(
        person_names_compact.rename(
            {
                "person_id": "person_id_name_compact",
                "person_name": "person_name_name_compact",
            }
        ),
        on="person_name_compact_key",
        how="left",
    )
    .join(
        person_names_first_last_initial.rename(
            {
                "person_id": "person_id_name_first_last_initial",
                "person_name": "person_name_name_first_last_initial",
            }
        ),
        on="person_name_first_last_initial_key",
        how="left",
    )
    .join(
        person_names_initial_last.rename(
            {
                "person_id": "person_id_name_initial_last",
                "person_name": "person_name_name_initial_last",
            }
        ),
        on="person_name_initial_last_key",
        how="left",
    )
    .join(
        person_names_initial_last_prefix.rename(
            {
                "person_id": "person_id_name_initial_last_prefix",
                "person_name": "person_name_name_initial_last_prefix",
            }
        ),
        on="person_name_initial_last_prefix_key",
        how="left",
    )
    .with_columns(
        pl.coalesce(
            "person_id_email",
            "person_id_name_full",
            "person_id_name_compact",
            "person_id_name_first_last_initial",
            "person_id_name_initial_last",
            "person_id_name_initial_last_prefix",
        ).alias("person_id"),
        pl.coalesce(
            "person_name_email",
            "person_name_name_full",
            "person_name_name_compact",
            "person_name_name_first_last_initial",
            "person_name_name_initial_last",
            "person_name_name_initial_last_prefix",
        ).alias("person_name"),
        pl.when(pl.col("person_id_email").is_not_null())
        .then(pl.lit("email_exact"))
        .when(pl.col("person_id_name_full").is_not_null())
        .then(pl.lit("display_name_full"))
        .when(pl.col("person_id_name_compact").is_not_null())
        .then(pl.lit("display_name_compact"))
        .when(pl.col("person_id_name_first_last_initial").is_not_null())
        .then(pl.lit("display_name_first_last_initial"))
        .when(pl.col("person_id_name_initial_last").is_not_null())
        .then(pl.lit("display_name_initial_last"))
        .when(pl.col("person_id_name_initial_last_prefix").is_not_null())
        .then(pl.lit("display_name_initial_last_prefix"))
        .otherwise(None)
        .alias("match_source"),
    )
    .drop(
        "person_id_email",
        "person_name_email",
        "person_id_name_full",
        "person_name_name_full",
        "person_id_name_compact",
        "person_name_name_compact",
        "person_id_name_first_last_initial",
        "person_name_name_first_last_initial",
        "person_id_name_initial_last",
        "person_name_name_initial_last",
        "person_id_name_initial_last_prefix",
        "person_name_name_initial_last_prefix",
        "person_name_full_key",
        "person_name_compact_key",
        "person_name_first_last_initial_key",
        "person_name_initial_last_key",
        "person_name_initial_last_prefix_key",
    )
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

clean_corpus.write_parquet(out_dir / "emails.cleaned.analysis_ready.parquet")
addresses_after.write_parquet(out_dir / "email_addresses.parquet")
print(f"Wrote full clean corpus with {clean_corpus.height:,} rows to data/emails.cleaned.analysis_ready.parquet")
print(f"Wrote parsed addresses with {addresses_after.height:,} rows to data/email_addresses.parquet")
print(
    "Matched "
    f"{addresses_after.filter(pl.col('person_id').is_not_null()).height:,} address rows to "
    f"{addresses_after.select(pl.col('person_id').drop_nulls().n_unique()).item():,} people"
)
