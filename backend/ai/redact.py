"""Blind scoring (rule 3) and contact masking (rule 6).

`redact_for_scoring` strips name, gender, age/date of birth, photo mentions and marital
status (plus contact details and family-name lines) from the text before it reaches any
LLM. Images are never sent: only extracted text leaves this server.
"""
import re

PLACEHOLDER = "[REDACTED]"

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"(?:https?://|www\.|linkedin\.com/|github\.com/)\S+", re.I)
_PHONE = re.compile(r"(?<![\w.])(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,5}\)?[\s\-]?)?\d{3,5}[\s\-]?\d{4,6}(?![\w])")

# Whole-line fields: label then the rest of the line.
_LABELLED_LINE = re.compile(
    r"""(?imx)
    ^(?P<label>[ \t]*(?:[\-•*▪●][ \t]*)?
      (?:(?:candidate[ \t]+|full[ \t]+)?name
        |gender|sex
        |date[ \t]+of[ \t]+birth|d\.?o\.?b\.?|birth[ \t]*date|born(?:[ \t]+on)?
        |age
        |marital[ \t]+status|marital|civil[ \t]+status
        |father'?s?[ \t]+name|mother'?s?[ \t]+name|husband'?s?[ \t]+name|spouse(?:'s)?[ \t]+name
        |photo(?:graph)?|passport[ \t\-]size[ \t]+photo(?:graph)?|nationality|religion|caste)
      [ \t]*[:\-–][ \t]*)
    [^\n]*$
    """
)
_AGE_PHRASES = re.compile(
    r"\b(?:aged?\s*[:\-]?\s*\d{2}\b(?:\s*(?:years?|yrs?)(?:\s*old)?)?|\d{2}\s*[\-]?\s*(?:years?|yrs?)[\s\-]*old)",
    re.I,
)
_DOB_INLINE = re.compile(
    r"\b(?:\d{1,2}[\s/.\-](?:\d{1,2}|[A-Za-z]{3,9})[\s/.\-,]+(?:19|20)\d{2})\b"
)
_MARITAL_WORDS = re.compile(r"\b(?:unmarried|married|divorced|widowed|widower|bachelor|spinster)\b", re.I)
_GENDER_WORDS = re.compile(r"\b(?:male|female|transgender)\b", re.I)
_TITLES = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Shri|Smt|Sri|Kumari)\.?(?=\s)", re.I)
_PHOTO = re.compile(r"\[?\s*(?:passport[\s\-]size\s+)?photo(?:graph)?\s*(?:attached|here)?\s*\]?", re.I)
_PRONOUNS = {
    "he": "they", "she": "they", "his": "their", "hers": "theirs", "her": "their",
    "him": "them", "himself": "themselves", "herself": "themselves",
}
_PRONOUN_RE = re.compile(r"\b(" + "|".join(_PRONOUNS) + r")\b", re.I)


def _neutral_pronoun(match: re.Match) -> str:
    word = match.group(1)
    repl = _PRONOUNS[word.lower()]
    return repl.capitalize() if word[0].isupper() else repl


def _redact_name(text: str, full_name: str) -> str:
    parts = [p for p in re.split(r"[\s.,]+", full_name or "") if len(p) >= 2]
    for part in sorted(set(parts), key=len, reverse=True):
        text = re.sub(rf"(?i)(?<![A-Za-z]){re.escape(part)}(?![A-Za-z])", PLACEHOLDER, text)
    return text


def redact_for_scoring(text: str, full_name: str = "") -> str:
    """Return `text` with protected attributes and contact details removed."""
    out = _LABELLED_LINE.sub(lambda m: f"{m.group('label').rstrip()} {PLACEHOLDER}", text)
    out = _EMAIL.sub(PLACEHOLDER, out)
    out = _URL.sub(PLACEHOLDER, out)
    out = _AGE_PHRASES.sub(PLACEHOLDER, out)
    out = _DOB_INLINE.sub(PLACEHOLDER, out)
    out = _MARITAL_WORDS.sub(PLACEHOLDER, out)
    out = _GENDER_WORDS.sub(PLACEHOLDER, out)
    out = _PHOTO.sub(PLACEHOLDER, out)
    out = _TITLES.sub("", out)
    out = _PRONOUN_RE.sub(_neutral_pronoun, out)
    out = _PHONE.sub(lambda m: PLACEHOLDER if len(re.sub(r"\D", "", m.group()) ) >= 10 else m.group(), out)
    return _redact_name(out, full_name)


# --- Masking for client-facing payloads (rule 6, assumption A7) -----------------------

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    host, _, tld = domain.rpartition(".")
    return f"{local[:1]}•••@{host[:1]}•••.{tld}"


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return f"•••• ••• •{digits[-2:]}" if len(digits) >= 4 else ""


def mask_contacts_in_text(text: str) -> str:
    """Hide emails, phone numbers and profile URLs inside free text shown to clients."""
    out = _EMAIL.sub(lambda m: mask_email(m.group()), text)
    out = _URL.sub("•••", out)
    return _PHONE.sub(lambda m: mask_phone(m.group()) if len(re.sub(r"\D", "", m.group())) >= 10 else m.group(), out)
