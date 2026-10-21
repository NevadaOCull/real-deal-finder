import re

MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def parse_price(text: str | None) -> float | None:
    """The first dollar amount in a piece of text, e.g. a deal title."""
    match = MONEY.search(text or "")
    return float(match.group(1).replace(",", "")) if match else None


def to_number(value) -> float | None:
    """A positive number from a number or numeric string; anything else is None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and (match := NUMBER.search(value)):
        number = float(match.group(0).replace(",", ""))
    else:
        return None
    return number if number > 0 else None
