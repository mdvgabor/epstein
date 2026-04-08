from pathlib import Path

import polars as pl

from address_processing import (
    build_address_table,
    canonicalize_email,
    clean_body,
    decoded_list_expr,
    fuzzy_repair_emails,
    normalize_text,
    normalized_list_expr,
)
out_dir = Path("data")
out_dir.mkdir(exist_ok=True)

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
        *[
            normalized_list_expr(role).alias(f"{role}_normalized")
            for role in ["to_recipients", "cc_recipients", "bcc_recipients"]
        ],
        *[
            decoded_list_expr(role).alias(f"{role}_items")
            for role in ["to_recipients", "cc_recipients", "bcc_recipients"]
        ],
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

addresses_before = build_address_table(processed)
addresses_after = fuzzy_repair_emails(addresses_before).with_columns(
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

clean_corpus.write_parquet(out_dir / "emails.cleaned.analysis_ready.parquet")
addresses_after.write_parquet(out_dir / "email_addresses.parquet")
print(f"Wrote full clean corpus with {clean_corpus.height:,} rows to data/emails.cleaned.analysis_ready.parquet")
print(f"Wrote parsed addresses with {addresses_after.height:,} rows to data/email_addresses.parquet")
