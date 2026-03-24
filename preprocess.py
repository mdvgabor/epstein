from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import polars as pl

from jmail import jmail

EMAIL_COLUMNS = [
    "sender",
    "to_recipients",
    "cc_recipients",
    "bcc_recipients",
    "account_email",
    "all_participants",
]
RECIPIENT_COLUMNS = ["to_recipients", "cc_recipients", "bcc_recipients"]
MASK_PATTERN = r"redacted|█"
OCR_TAG_PATTERN = r"<(/?u|/?s|change)>"
WHITESPACE_PATTERN = r"^\s|\s$|  +|\u00a0"
EMPTY_PATTERN = r"^\s*$"
EMPTY_LIST_PATTERN = r"^\s*\[\s*\]\s*$"
PLACEHOLDER_ONLY_PATTERN = r"^\s*(\[\]\s*)+$"


@dataclass(frozen=True)
class Issue:
    name: str
    count: int
    examples: tuple[str, ...] = ()


def example_strings(
    frame: pl.DataFrame,
    column: str,
    predicate: pl.Expr,
    *,
    limit: int = 3,
) -> tuple[str, ...]:
    values = (
        frame.filter(predicate)
        .select(pl.col(column))
        .drop_nulls()
        .head(limit)
        .to_series()
        .to_list()
    )
    return tuple(truncate(value) for value in values)


def truncate(value: str, limit: int = 100) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def nonzero(issues: Iterable[Issue]) -> list[Issue]:
    return [issue for issue in issues if issue.count > 0]


def print_issue(issue: Issue) -> None:
    print(f"- {issue.name}: {issue.count}")
    if issue.examples:
        print(f"  examples: {' | '.join(issue.examples)}")


def sender_issues(df: pl.DataFrame) -> list[Issue]:
    column = "sender"
    missing = pl.col(column).is_null() | pl.col(column).fill_null("").str.contains(
        EMPTY_PATTERN
    )
    no_email = (
        pl.col(column).fill_null("").str.contains("@").not_()
        & pl.col(column).fill_null("").str.contains(EMPTY_PATTERN).not_()
    )
    redacted = pl.col(column).fill_null("").str.to_lowercase().str.contains(MASK_PATTERN)
    ocr_tags = pl.col(column).fill_null("").str.contains(OCR_TAG_PATTERN)
    unmatched_angles = pl.col(column).fill_null("").str.count_matches("<") != pl.col(
        column
    ).fill_null("").str.count_matches(">")
    multiple_ats = pl.col(column).fill_null("").str.count_matches("@") > 1
    whitespace = pl.col(column).fill_null("").str.contains(WHITESPACE_PATTERN)

    variant_frame = (
        df.with_columns(
            pl.col(column)
            .fill_null("")
            .str.extract(r"([A-Za-z0-9._%+\-/=]+@[A-Za-z0-9.\-]+)")
            .str.to_lowercase()
            .alias("mailbox")
        )
        .filter(pl.col("mailbox").is_not_null() & pl.col("mailbox").ne(""))
        .group_by("mailbox")
        .agg(pl.col(column).n_unique().alias("variant_count"))
        .filter(pl.col("variant_count") > 1)
        .sort("variant_count", descending=True)
    )

    variant_examples = tuple(
        variant_frame.head(3).select("mailbox").to_series().to_list()
    )

    return nonzero(
        [
            Issue(
                "missing_or_blank",
                df.select(missing.sum()).item(),
                example_strings(df, column, missing),
            ),
            Issue(
                "no_email_address_present",
                df.select(no_email.sum()).item(),
                example_strings(
                    df,
                    column,
                    no_email
                    & pl.col(column)
                    .fill_null("")
                    .str.to_lowercase()
                    .str.contains(MASK_PATTERN)
                    .not_(),
                ),
            ),
            Issue(
                "redacted_or_masked",
                df.select(redacted.sum()).item(),
                example_strings(df, column, redacted),
            ),
            Issue(
                "ocr_markup_tags",
                df.select(ocr_tags.sum()).item(),
                example_strings(df, column, ocr_tags),
            ),
            Issue(
                "unmatched_angle_brackets",
                df.select(unmatched_angles.sum()).item(),
                example_strings(df, column, unmatched_angles),
            ),
            Issue(
                "multiple_at_signs_or_merged_addresses",
                df.select(multiple_ats.sum()).item(),
                example_strings(df, column, multiple_ats),
            ),
            Issue(
                "whitespace_artifacts",
                df.select(whitespace.sum()).item(),
                example_strings(df, column, whitespace),
            ),
            Issue(
                "same_mailbox_with_multiple_sender_variants",
                variant_frame.height,
                variant_examples,
            ),
        ]
    )


def recipient_issues(df: pl.DataFrame, column: str) -> list[Issue]:
    empty_rows = pl.col(column).fill_null("").str.contains(EMPTY_LIST_PATTERN)
    null_rows = pl.col(column).is_null()
    empty_string_rows = pl.col(column).fill_null("").str.contains(r'\[\s*""\s*\]')

    items = (
        df.select(pl.col(column).str.json_decode(pl.List(pl.String)).alias("item"))
        .explode("item")
    )

    item_not_blank = pl.col("item").is_not_null() & pl.col("item").str.contains(
        EMPTY_PATTERN
    ).not_()
    item_no_email = item_not_blank & pl.col("item").str.contains("@").not_()
    item_redacted = (
        pl.col("item").fill_null("").str.to_lowercase().str.contains(MASK_PATTERN)
    )
    item_tags = pl.col("item").fill_null("").str.contains(OCR_TAG_PATTERN)
    item_unmatched_angles = pl.col("item").fill_null("").str.count_matches("<") != pl.col(
        "item"
    ).fill_null("").str.count_matches(">")
    item_multiple_ats = pl.col("item").fill_null("").str.count_matches("@") > 1
    item_whitespace = pl.col("item").fill_null("").str.contains(WHITESPACE_PATTERN)
    item_empty_string = pl.col("item").is_not_null() & pl.col("item").str.contains(
        EMPTY_PATTERN
    )

    return nonzero(
        [
            Issue(
                "null_rows",
                df.select(null_rows.sum()).item(),
                example_strings(df, column, null_rows),
            ),
            Issue(
                "empty_list_rows",
                df.select(empty_rows.sum()).item(),
                example_strings(df, column, empty_rows),
            ),
            Issue(
                "recipient_items_without_email_address",
                items.select(item_no_email.sum()).item(),
                example_strings(
                    items,
                    "item",
                    item_no_email & item_redacted.not_(),
                ),
            ),
            Issue(
                "redacted_or_masked_items",
                items.select(item_redacted.sum()).item(),
                example_strings(items, "item", item_redacted),
            ),
            Issue(
                "ocr_markup_tags",
                items.select(item_tags.sum()).item(),
                example_strings(items, "item", item_tags),
            ),
            Issue(
                "unmatched_angle_brackets",
                items.select(item_unmatched_angles.sum()).item(),
                example_strings(items, "item", item_unmatched_angles),
            ),
            Issue(
                "multiple_at_signs_or_merged_addresses",
                items.select(item_multiple_ats.sum()).item(),
                example_strings(items, "item", item_multiple_ats),
            ),
            Issue(
                "empty_string_items",
                items.select(item_empty_string.sum()).item(),
                example_strings(items, "item", item_empty_string),
            ),
            Issue(
                "whitespace_artifacts",
                items.select(item_whitespace.sum()).item(),
                example_strings(items, "item", item_whitespace),
            ),
            Issue(
                "rows_containing_empty_string_items",
                df.select(empty_string_rows.sum()).item(),
                example_strings(df, column, empty_string_rows),
            ),
        ]
    )


def account_email_issues(df: pl.DataFrame) -> list[Issue]:
    column = "account_email"
    missing = pl.col(column).is_null() | pl.col(column).fill_null("").str.contains(
        EMPTY_PATTERN
    )
    no_email = (
        pl.col(column).is_not_null()
        & pl.col(column).str.contains(EMPTY_PATTERN).not_()
        & pl.col(column).str.contains("@").not_()
    )

    return nonzero(
        [
            Issue(
                "missing_or_blank",
                df.select(missing.sum()).item(),
                example_strings(df, column, missing),
            ),
            Issue(
                "non_email_tokens",
                df.select(no_email.sum()).item(),
                example_strings(df, column, no_email),
            ),
            Issue(
                "distinct_non_null_values",
                df.select(pl.col(column).drop_nulls().n_unique()).item(),
                tuple(
                    df.select(pl.col(column))
                    .drop_nulls()
                    .unique()
                    .sort(column)
                    .head(5)
                    .to_series()
                    .to_list()
                ),
            ),
        ]
    )


def all_participants_issues(df: pl.DataFrame) -> list[Issue]:
    column = "all_participants"
    placeholder_only = pl.col(column).str.contains(PLACEHOLDER_ONLY_PATTERN)
    empty_list_tokens = pl.col(column).str.contains(r"\[\]")
    leading_or_trailing = pl.col(column).str.contains(r"^\s|\s$")
    whitespace = pl.col(column).str.contains(WHITESPACE_PATTERN)
    has_uppercase = pl.col(column).str.contains(r"[A-Z]")

    return nonzero(
        [
            Issue(
                "placeholder_only_rows",
                df.select(placeholder_only.sum()).item(),
                example_strings(df, column, placeholder_only),
            ),
            Issue(
                "contains_raw_empty_list_tokens",
                df.select(empty_list_tokens.sum()).item(),
                example_strings(df, column, empty_list_tokens),
            ),
            Issue(
                "leading_or_trailing_whitespace",
                df.select(leading_or_trailing.sum()).item(),
                example_strings(df, column, leading_or_trailing),
            ),
            Issue(
                "whitespace_artifacts",
                df.select(whitespace.sum()).item(),
                example_strings(df, column, whitespace),
            ),
            Issue(
                "lowercased_lossy_representation",
                df.height - df.select(has_uppercase.sum()).item(),
            ),
        ]
    )


def main() -> None:
    df = (
        pl.read_parquet(jmail("emails"), columns=EMAIL_COLUMNS + ["is_promotional"])
        .filter(pl.col("is_promotional") != True)
    )

    print(f"rows_after_promotional_filter: {df.height}")
    print()

    reports = {
        "sender": sender_issues(df),
        "to_recipients": recipient_issues(df, "to_recipients"),
        "cc_recipients": recipient_issues(df, "cc_recipients"),
        "bcc_recipients": recipient_issues(df, "bcc_recipients"),
        "account_email": account_email_issues(df),
        "all_participants": all_participants_issues(df),
    }

    for column, issues in reports.items():
        print(column)
        for issue in issues:
            print_issue(issue)
        print()


if __name__ == "__main__":
    main()
