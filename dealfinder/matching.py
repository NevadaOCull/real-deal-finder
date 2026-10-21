import re


def matches(term: str, text: str) -> bool:
    """True if the search term appears in the text as a phrase of whole words (a plural counts)."""
    words = term.lower().split()
    if not words:
        return False
    pattern = r"(?<!\w)" + r"\s+".join(re.escape(word) for word in words) + r"(?:e?s)?(?!\w)"
    return re.search(pattern, text.lower()) is not None
