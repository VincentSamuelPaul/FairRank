"""Evidence verification (rule 2).

A quote may be stored and shown only if it is an exact substring of the extracted CV
text. Only whitespace is normalised; case, punctuation and wording must match.
"""
import re

_WS = re.compile(r"\s+")
MIN_QUOTE_CHARS = 3


def normalize_ws(text: str) -> str:
    return _WS.sub(" ", text).strip()


def verify_quote(cv_text: str, quote: str) -> str | None:
    """Return the whitespace-normalised quote if it appears in the CV text, else None."""
    wanted = normalize_ws(quote or "")
    if len(wanted) < MIN_QUOTE_CHARS:
        return None
    return wanted if wanted in normalize_ws(cv_text) else None


def locate_quote(cv_text: str, quote: str) -> tuple[int, int] | None:
    """Character span of the quote in the ORIGINAL text (whitespace-insensitive), for highlighting."""
    tokens = normalize_ws(quote or "").split(" ")
    if not tokens or not tokens[0]:
        return None
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    match = re.search(pattern, cv_text)
    return (match.start(), match.end()) if match else None
