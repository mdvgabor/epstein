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
             "\u3010", "\u3011", "\ufffd"],
            [" ", "<", ">", '"', "'", "&",
             " ", " ", "'", "'", '"', '"',
             "<", "<", "<", "<",
             ">", ">", ">", ">",
             "[", "]", " "],
        )
        .str.replace_all(r"</?(?:u|s|change)>", "")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
        .replace("", None)
    )


def normalize_body_lines_expr(expr):
    return (
        expr.fill_null("")
        .str.replace_many(
            ["&nbsp;", "&lt;", "&gt;", "&quot;", "&#39;", "&amp;",
             "\u00a0", "\u200b", "\u2018", "\u2019", "\u201c", "\u201d",
             "\u2039", "\u276e", "\u3008", "\uff1c",
             "\u203a", "\u276f", "\u3009", "\uff1e",
             "\u3010", "\u3011", "\ufffd"],
            [" ", "<", ">", '"', "'", "&",
             " ", " ", "'", "'", '"', '"',
             "<", "<", "<", "<",
             ">", ">", ">", ">",
             "[", "]", " "],
        )
        .str.replace_all(r"</?(?:u|s|change)>", "")
        .str.replace_all(r"\r\n?", "\n")
        .str.replace_all(r"[ \t\f\v]+", " ")
        .str.replace_all(r"(?m)^[ \t]+|[ \t]+$", "")
        .str.replace_all(r"\n{3,}", "\n\n")
        .str.strip_chars()
        .replace("", None)
    )


def clean_quoted_printable_body_expr(expr):
    return (
        expr.str.replace_many(
            {
                "=C2=A0": " ",
                "=C2=AD": "",
                "=C2�": " ",
                "=C2": " ",
                "=E2=80=98": "'",
                "=E2=80=99": "'",
                "=E2=80=9A": "'",
                "=E2=80=9B": "'",
                "=E2=80=9C": '"',
                "=E2=80=9D": '"',
                "=E2=80=9E": '"',
                "=E2=80=9F": '"',
                "=E2=80=8B": "",
                "=E2=80=93": "-",
                "=E2=80=94": "-",
                "=E2=80=90": "-",
                "=E2=80=91": "-",
                "=E2=80=92": "-",
                "=E2=80=A6": "...",
                "=E2=82=AC": "EUR",
                "=A0": " ",
                "=AO": " ",
                "=AD": "",
                "=91": "'",
                "=92": "'",
                "=93": '"',
                "=94": '"',
                "=96": "-",
                "=97": "-",
                "=85": "...",
                "=20": " ",
                "=09": " ",
                "=0A": "\n",
                "=0D": "\n",
                "=3D": "=",
                "=2E": ".",
                "=2C": ",",
                "=3A": ":",
                "=3B": ";",
                "=21": "!",
                "=3F": "?",
                "=28": "(",
                "=29": ")",
                "=2F": "/",
                "=40": "@",
                "=5F": "_",
                "=2D": "-",
                "=nbsp;": " ",
            },
            ascii_case_insensitive=True,
        )
        .str.replace_all(r"(?i)([\p{L}])=E2\s+([st])\b", "${1}'${2}")
        .str.replace_all(r"(?i)=E2", " ")
        .str.replace_all(r"([—–-])=([\p{L}])", "${1}${2}")
        .str.replace_all(r"(?i)(^|\s)=([a-z])", "${1}${2}")
        .str.replace_all(r"(?i)([\p{L}])=([\p{L}])", "${1}${2}")
        .str.replace_all(r"(?i)([\p{L}\p{N}])=(?:\s+>?\s*|>\s*)([\p{L}\p{N}])", "${1}${2}")
        .str.replace_all(r"(?i)=\s*(?:>\s*)?(?:\r?\n|\r)\s*(?:>\s*)?", "")
        .str.replace_all(r"(?i)\bContent-Transfer-Encoding:\s*quoted-printable\b", " ")
        .str.replace_all(r"(?i)\bContent-Type:\s*text/(?:plain|html);\s*charset=[A-Za-z0-9_-]+\b", " ")
    )


def strip_email_footer(value):
    if value is None:
        return None

    lines = value.splitlines()
    cleaned = [line.strip(" \t>") for line in lines]
    cut = len(lines)
    for index, line in enumerate(cleaned):
        lowered = line.lower()
        if re.fullmatch(r"[-_ ]*(?:original|forwarded) message[-_ :]*", lowered):
            cut = index
            break
        if re.fullmatch(r"begin forwarded message:?", lowered):
            cut = index
            break
        if re.fullmatch(r"(?:on .{1,260}\s+)?[^:\n]{1,220}\s+wrote:", lowered) or re.fullmatch(r"wrote:", lowered):
            cut = index - 1 if index > 0 and re.search(r"^[-_ ]{2,}|@", cleaned[index - 1]) else index
            break
        if re.search(
            r"\b(?:notice of confidentiality|confidentiality notice|legal notice|disclaimer|"
            r"attorney client privileged document|do not forward without permission|"
            r"pursuant to treasury department circular 230|irs circular 230)\b",
            lowered,
        ):
            cut = index
            break
        if re.search(
            r"\b(?:the information (?:contained|in)|this (?:e-?mail|email|message|communication)|"
            r"if you (?:are not|have received)|you are hereby notified)\b.{0,180}"
            r"\b(?:confidential|privileged|intended|recipient|error|unauthorized|prohibited)\b",
            lowered,
        ):
            cut = index
            break
        if re.search(
            r"^(?:the information (?:contained|in)|this (?:e-?mail|email|message|communication) "
            r"(?:and any|may contain|contains|is intended)|if you (?:are not|have received)|"
            r"you are hereby notified|.*unauthorized use,?\s+disclosure or copying of this communication)\b",
            lowered,
        ):
            cut = index
            break

    if cut == len(lines):
        for index, line in enumerate(cleaned[max(0, len(cleaned) - 11):], max(0, len(cleaned) - 11)):
            lowered = line.lower()
            if re.fullmatch(
                r"(?:\*?sent\*? (?:from|via) (?:my |the )?.{0,60}\b(?:iphone|ipad|android|blackberry|bb|mobile|wireless)\b.*\*?|"
                r"sent from mailbox for iphone|enviado desde mi .+|from my sent iphone)[,.! ]*",
                lowered,
            ):
                cut = index
                break

    if cut == len(lines):
        for index, line in enumerate(cleaned[max(0, len(cleaned) - 11):], max(0, len(cleaned) - 11)):
            lowered = line.lower()
            if not re.fullmatch(r"(?:--+|-|_+)", lowered):
                continue
            cut = index
            break

    if cut == len(lines):
        tail = cleaned[max(0, len(cleaned) - 11):]
        contact_seen = any(
            re.search(
                r"@|https?://|www\.|\b(?:tel|fax|phone|mobile|cell|office|direct|founder|president|"
                r"manager|director|esq|llc|ltd|inc|llp|p\.a\.|group|productions|management)\b|"
                r"(?:\+?\d[\d(). -]{6,}\d)",
                line.lower(),
            )
            for line in tail
        )
        if contact_seen:
            for index, line in enumerate(tail, max(0, len(cleaned) - 11)):
                if re.fullmatch(
                    r"(?:best|best regards|kind regards|regards|sincerely|thanks|thank you|"
                    r"cheers|warmly|yours truly)[,.! ]*",
                    line.lower(),
                ):
                    cut = index
                    break

    stripped = "\n".join(lines[:cut]).strip()
    return stripped or None


def remove_attachment_payloads_expr(expr):
    return (
        expr.str.replace_all(r"(?s)(?:^|\r?\n)begin [0-7]{3} .+?(?:\r?\n)end(?:\r?\n|$)", " ")
        .str.replace_all(r"(?:^|\r?\n)M[ -~]{50,}(?:\r?\n|$)", " ")
        .str.replace_all(r"(?:^|\r?\n)[A-Za-z0-9+/]{80,}={0,2}(?:\r?\n|$)", " ")
        .str.replace_all(r"(?i)--[A-Za-z0-9_./+=\-]{10,}-*", " ")
        .str.replace_all(
            r"(?im)^Content-(?:Type|Transfer-Encoding|Disposition|ID|Description):[^\n]*(?:\n[ \t]+[^\n]*)*",
            " ",
        )
    )


def remove_legal_disclaimers_expr(expr):
    return (
        expr.str.replace_all(r"(?:^|\s)>+\s*", " ")
        .str.replace_all(r"\|+", " ")
        .str.replace_all(
            r"(?is)(?:\*{10,}\s*)?(?:please not[e]?\s*)?\bthe(?:\s|=)*information contain\w* in this\s*(?:communication|message|e-?mail|email)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bplease not[e]?.*?\bthe(?:\s|=)*information contain\w* in this\s*(?:communication|message|e-?mail|email)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bplease\s+not[e]?.{0,120}?\binformat\w* contain\w* in this\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bplease\s+not[e]?.{0,120}?\bth?e?\s*informat\w* contain\w* in this\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\b[a-z']{3,5}\s+information contain\w* in this\s*(?:communication|message|e-?mail|email)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthe(?:\s|=)*information contain\w* in this\s+\w{8,16}\s+is confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis (?:e-?mail|email|message) and any attachments\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis e-?mail and any files transmitted with it\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis (?:e-?mail|email) contains legally privileged\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis message is directed to and is for the use\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis (?:e-?mail|email) message, including any attached files\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bif you are not (?:the )?(?:intended|designated|named) recipient\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bif you are not an intended recipient\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bif the reader of this (?:e-?mail|email|message|e-?mail message) is not the intended recipient\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bif (?:you have )?received this (?:communication|message|e-?mail|email) in error\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bif you have received this communication and are not identified above\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\byou are hereby notified that any\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis message is a private communication\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis message and any attachments.*?may contain confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bconfidentiality notice\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis communication may contain confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis communication and any attachments contain information\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthe information contained in this electronic message\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthe information in this electronic mail message\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bdisclaimer\s*(?:important!?\s*)?this (?:email|message)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis (?:email|message) and any files transmitted with it are confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis message is intended for the above named person\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\byou, the recipient, are obligated to maintain it\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bunauthorized use,?\s+disclosure or copying of this communication\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\b\w?authorized use[,.]?\s+disclosure or copying of this communication\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bother use of this communication is strictly prohibited\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bany other use of the information therein is strictly prohibited\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis transmission may contain information that is confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bintended recipient\(s\) and may contain information that is confidential\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bany unauthorized review, use, duplication, disclosure or distribution is strictly prohibited\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bit is the property of jeffrey epstein\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bproperty\s+o?f?\s*(?:jeffrey epstein|jee)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthe\s*property\s+o?f?\s*(?:jeffrey epstein|jee|darren k\.? indyke)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bany review, reliance or distribution by others\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthis document and the information contained herein are intended only\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bthe information contained in this email is intended only\b.*$",
            " ",
        )
    )


def clean_body(expr):
    return (
        remove_legal_disclaimers_expr(
            normalize_body_lines_expr(
                clean_quoted_printable_body_expr(remove_attachment_payloads_expr(expr.fill_null("")))
                .str.replace_all(r"(?im)^(?:from|to|cc|bcc|sent|date|subject):[^\n]*$", " ")
                .str.replace_all(
                    r"(?im)^[-_]{2,}.*forwarded message.*$|^\*{0,2}\[?forwarded message\]?\*{0,2}.*$|^this email and any attachments.*$|^please consider the environment.*$",
                    " ",
                )
            )
            .map_elements(strip_email_footer, return_dtype=pl.String)
        )
        .str.replace_all(
            r"(?is)(?:^|\s)On\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b.{1,220}\bwrote:.*$",
            " ",
        )
        .str.replace_all(
            r"(?s)(?:^|\s)(?:\"[^\"\n]{1,160}\"(?:\s+<[^>\n]{1,200}>)?|[A-Z][A-Za-z0-9 .,_'@<>\-]{0,220})\s+wrote:.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)\bemail header \(partially visible\):\s*\"[^\"]{0,260}\bwrote:\"",
            " ",
        )
        .str.replace_all(
            r"(?is)^\s*wrote:\s+.*$",
            " ",
        )
        .str.replace_all(
            r"(?is)(?:^|[\s.>*_]+)\*?sent\*? (?:from|via) (?:my |the )?.{0,60}\b(?:iphone|ipad|android|blackberry|bb|mobile|wireless)\b.*$",
            " ",
        )
        .str.replace_all(
            r"(?i)\b(?:confidential|privileged|intended|unauthorized|prohibited|disclosure|copying|attachments?|thereof|addressee|recipient|notify|destroy|return|error|unlawful)\b(?:\s+\b(?:confidential|privileged|intended|unauthorized|prohibited|disclosure|copying|attachments?|thereof|addressee|recipient|notify|destroy|return|error|unlawful)\b){5,}",
            " ",
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
                "[forwarded message]": " ",
                "**forwarded message**": " ",
                "forwarded message from": " ",
                "note: forwarded message attached.": " ",
                "be a better friend, newshound, and know-it-all with yahoo! mobile. try it now.": " ",
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
