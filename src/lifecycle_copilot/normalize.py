"""Key normalisation for matching. Exact rules only: trim, upper-case, strip
zero-width characters, and treat known placeholder serials as blank."""

ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

# Serials that mean "no serial". TO CONFIRM with the ITAM team (spec §6 step 1).
PLACEHOLDER_SERIALS = frozenset(
    {
        "N/A",
        "NA",
        "0",
        "NONE",
        "NULL",
        "-",
        "UNKNOWN",
        "TO BE FILLED BY O.E.M.",
        "DEFAULT STRING",
        "SYSTEM SERIAL NUMBER",
        "0123456789",
    }
)


def norm_key(value) -> str:
    if value is None:
        return ""
    text = str(value).translate(ZERO_WIDTH).replace(" ", " ")
    return " ".join(text.split()).upper()


def norm_serial(value) -> tuple[str, bool]:
    """Returns (normalised serial, was_placeholder). Placeholders come back blank."""
    key = norm_key(value)
    if key in PLACEHOLDER_SERIALS:
        return "", True
    return key, False


def norm_hostname(value) -> str:
    return norm_key(value)
