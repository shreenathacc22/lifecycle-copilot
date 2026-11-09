"""Date parsing for lifecycle columns. Only unambiguous formats are accepted;
anything else is kept as the source text and reported, never guessed."""
from datetime import date, datetime

FORMATS = ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%d-%B-%Y", "%d %B %Y", "%B %d, %Y", "%m/%d/%Y")


def parse_date(value) -> tuple[date | None, bool]:
    """Returns (date or None, ok). ok is False only when there was text that
    could not be read as a date."""
    if value is None:
        return None, True
    if isinstance(value, datetime):
        return value.date(), True
    if isinstance(value, date):
        return value, True
    text = str(value).strip()
    if not text:
        return None, True
    if "T" in text or " 00:00:00" in text:
        text = text.replace("T", " ").split(" ")[0]
    for fmt in FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), True
        except ValueError:
            continue
    return None, False
