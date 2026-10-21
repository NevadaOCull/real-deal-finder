import re

MONEY = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)")
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Words before an amount that make it a discount or a minimum spend, not the price.
NOT_A_PRICE_BEFORE = re.compile(r"\b(?:save|get|extra|spend|over)\s*$", re.I)


def parse_price(text: str | None) -> float | None:
    """The first dollar amount in a deal title that is the price (not "$10 off", "$50+" or "save $40")."""
    text = text or ""
    for match in MONEY.finditer(text):
        after = text[match.end():match.end() + 5]
        if after.lstrip().lower().startswith("off") or after.startswith("+"):
            continue
        if NOT_A_PRICE_BEFORE.search(text[max(0, match.start() - 8):match.start()]):
            continue
        price = float(match.group(1).replace(",", ""))
        if price > 0:
            return price
    return None


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
