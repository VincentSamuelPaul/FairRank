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


# --- Evidence QUALITY (separate from rule 2's verbatim check) -------------------------------------------
# A verbatim quote can still be weak: a bare job title or a skills list shows a keyword, not work done.
_SKILLS_LABEL = re.compile(r"^\W*(?:technical\s+|key\s+|core\s+)?(?:skills?|technologies|tools|tech\s*stack|competenc\w+)\b", re.I)
_TITLE_HEADER = re.compile(r"^\W*[A-Z][\w&/ .+-]{2,70}[,|@\-–]\s*[\w&/ .+-]{2,60}\(?\s*(?:\d{4}|\w{3}\s+\d{4})\s*[-–to ]+\s*(?:\d{4}|present|current)\)?\W*$", re.I)
WEAK_POINTS_CAP = 50
TITLE_POINTS_CAP = 65
WEAK_CONFIDENCE_CAP = 0.5
_FACT_CRITERIA = re.compile(r"notice|location|based in|ctc|salary|relocat", re.I)


def evidence_kind(quote: str) -> str:
    """'work' (a sentence or bullet describing what was done), 'title' (a bare role/heading line),
    'skills_list' (a comma-separated list of keywords) or 'fact' (a labelled value such as 'Location: Noida')."""
    text = normalize_ws(quote or "").lstrip("-•*· ").strip()
    words = text.split()
    if _SKILLS_LABEL.match(text):
        return "skills_list"
    parts = [p for p in re.split(r"[,;|]", text) if p.strip()]
    if len(parts) >= 3 and sum(len(p.split()) for p in parts) / len(parts) <= 3:
        return "skills_list"
    if _TITLE_HEADER.match(text):
        return "title"
    if ":" in text and len(text.split(":", 1)[0].split()) <= 3:
        return "fact"
    if len(words) <= 6 and not re.search(r"[.;]", text):
        return "title"
    return "work"


def cap_weak_evidence(criterion_name: str, points: int, confidence: float, quote: str) -> tuple[int, float, str]:
    """Lower points and confidence when the only evidence is a title or a skills list. Returns (points, confidence, kind).
    Factual criteria (notice, location, CTC) are exempt: a labelled value IS the evidence."""
    kind = evidence_kind(quote)
    if _FACT_CRITERIA.search(criterion_name or ""):
        return points, confidence, kind
    if kind == "skills_list":
        return min(points, WEAK_POINTS_CAP), min(confidence, WEAK_CONFIDENCE_CAP), kind
    if kind == "title":
        return min(points, TITLE_POINTS_CAP), min(confidence, WEAK_CONFIDENCE_CAP), kind
    return points, confidence, kind
