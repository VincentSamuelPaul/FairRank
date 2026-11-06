"""CV file validation, text extraction (PDF / DOCX) and rule-based profile parsing.

Extraction is local: no OCR (A3). A file with almost no text is reported as such so the
caller can mark it "Needs manual review" instead of inventing a score.
"""
import io
import re
import zipfile
from dataclasses import dataclass, field
from decimal import Decimal

from ai.vocab import find_city, find_skills

MAX_PDF_PAGES = 12
MAX_DOCX_XML_BYTES = 20 * 1024 * 1024


class UnsupportedFile(ValueError):
    """The upload is not a real PDF or DOCX (magic bytes), or is unreadable."""


def sniff_kind(data: bytes) -> str:
    """Decide the file type from its bytes, never from the extension or client-sent type."""
    if data[:1024].lstrip(b"\x00\r\n\t ").startswith(b"%PDF-"):
        return "pdf"
    if data[:4] == b"PK\x03\x04":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                info = zf.getinfo("word/document.xml")
                if info.file_size <= MAX_DOCX_XML_BYTES:
                    return "docx"
        except (zipfile.BadZipFile, KeyError):
            pass
    raise UnsupportedFile("Only real PDF or DOCX files are accepted.")


def extract_text(data: bytes, kind: str) -> str:
    try:
        return (_pdf_text(data) if kind == "pdf" else _docx_text(data)).strip()
    except UnsupportedFile:
        raise
    except Exception as exc:  # corrupt / encrypted files surface as many exception types
        raise UnsupportedFile(f"Could not read the file ({type(exc).__name__}).") from exc


# --- PDF ------------------------------------------------------------------------------------

def _pdf_text(data: bytes) -> str:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:MAX_PDF_PAGES]:
            pages.append(_page_text(page))
    return "\n\n".join(p for p in pages if p.strip())


def _group_lines(words: list[dict], tolerance: float = 3.0) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (round(w["top"]), w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= tolerance:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(line, key=lambda w: w["x0"]) for line in lines]


def _join(words: list[dict]) -> str:
    return " ".join(w["text"] for w in words)


def _find_gutter(lines: list[list[dict]], width: float) -> float | None:
    """x position of a vertical gutter that (almost) no line crosses, if the page has two columns.

    A real column layout has several lines with text on both sides AND a right column whose left
    edge is aligned. A centred heading that merely straddles the middle is not a column.
    """
    best: tuple[int, float] | None = None
    x = width * 0.30
    while x <= width * 0.70:
        crossing = sum(any(w["x0"] < x < w["x1"] for w in line) for line in lines)
        starts = [min(w["x0"] for w in line if w["x0"] >= x) for line in lines
                  if any(w["x1"] <= x for w in line) and any(w["x0"] >= x for w in line)]
        if len(starts) >= 5 and crossing <= 0.15 * len(lines) and _aligned(starts):
            if best is None or (crossing, abs(x - width / 2)) < (best[0], abs(best[1] - width / 2)):
                best = (crossing, x)
        x += 2
    return best[1] if best else None


def _aligned(starts: list[float], tolerance: float = 4.0, share: float = 0.8) -> bool:
    median = sorted(starts)[len(starts) // 2]
    return sum(abs(s - median) <= tolerance for s in starts) >= share * len(starts)


def _page_text(page) -> str:
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
    if not words:
        return ""
    lines = _group_lines(words)
    gutter = _find_gutter(lines, float(page.width))
    if gutter is None:
        return "\n".join(_join(line) for line in lines)
    out: list[str] = []
    left: list[str] = []
    right: list[str] = []

    def flush() -> None:
        out.extend(left)
        out.extend(right)
        left.clear()
        right.clear()

    for line in lines:
        if any(w["x0"] < gutter < w["x1"] for w in line):
            flush()
            out.append(_join(line))
            continue
        l_words = [w for w in line if w["x1"] <= gutter]
        r_words = [w for w in line if w["x0"] >= gutter]
        if l_words:
            left.append(_join(l_words))
        if r_words:
            right.append(_join(r_words))
    flush()
    return "\n".join(out)


# --- DOCX -----------------------------------------------------------------------------------

def _docx_text(data: bytes) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(io.BytesIO(data))
    lines: list[str] = []

    def walk_table(table: Table) -> None:
        for row in table.rows:
            cells, seen = [], set()
            for cell in row.cells:  # merged cells repeat; keep each once
                if id(cell._tc) in seen:
                    continue
                seen.add(id(cell._tc))
                cells.append(cell)
            texts = [c.text.strip() for c in cells if c.text.strip()]
            if len(texts) == 2 and all("\n" not in t for t in texts):
                lines.append(texts[0] + ("" if texts[0].endswith(":") else ":") + " " + texts[1])
            elif texts and all("\n" not in t for t in texts):
                lines.append(" | ".join(texts))
            else:
                lines.extend(texts)
            for cell in cells:
                for nested in cell.tables:
                    walk_table(nested)

    for child in doc.element.body.iterchildren():
        if child.tag.endswith("}p"):
            lines.append(Paragraph(child, doc).text)
        elif child.tag.endswith("}tbl"):
            walk_table(Table(child, doc))
    return "\n".join(lines)


# --- Profile (rule-based; the LLM is only used for scoring) ---------------------------------

@dataclass
class ParsedData:
    full_name: str = ""
    email: str = ""
    phone: str = ""
    current_role: str = ""
    experience_years: Decimal | None = None
    skills: list[str] = field(default_factory=list)
    notice_days: int | None = None
    location: str = ""
    current_ctc: Decimal | None = None
    expected_ctc: Decimal | None = None


_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\w.])(\+?\d[\d\s\-()]{8,16}\d)(?![\w])")
_NOT_NAME = re.compile(
    r"resume|curriculum|vitae|\bcv\b|profile|summary|objective|experience|education|skills|engineer|developer|"
    r"analyst|manager|officer|executive|consultant|contact|address|phone|email|mobile",
    re.I,
)
_ROLE_WORDS = re.compile(r"developer|engineer|analyst|manager|officer|executive|consultant|lead|architect|associate|supervisor", re.I)


def _first(pattern: str, text: str, flags: int = re.I) -> re.Match | None:
    return re.search(pattern, text, flags)


def _ctc(label: str, text: str) -> Decimal | None:
    m = _first(rf"{label}\s*(?:ctc)?\s*[:\-–]?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(lpa|lakhs?|l\b)", text)
    return Decimal(m.group(1)) * 100_000 if m else None


def _guess_name(lines: list[str]) -> str:
    labelled = _first(r"^\s*(?:candidate\s+|full\s+)?name\s*[:\-–]\s*(.+)$", "\n".join(lines), re.I | re.M)
    if labelled:
        return labelled.group(1).strip()[:200]
    for line in lines[:6]:
        words = line.split()
        if 2 <= len(words) <= 4 and not _NOT_NAME.search(line) and all(re.fullmatch(r"[A-Za-z.'\-]+", w) for w in words):
            return line.strip()
    return ""


def _guess_role(lines: list[str], name: str) -> str:
    labelled = _first(r"^\s*(?:current\s+)?(?:role|designation|position|title)\s*[:\-–]\s*(.+)$", "\n".join(lines), re.I | re.M)
    if labelled:
        return labelled.group(1).strip()[:200]
    for line in lines[:8]:
        if line.strip() != name and _ROLE_WORDS.search(line) and len(line.split()) <= 8 and "@" not in line:
            return line.strip()[:200]
    return ""


def _skills(text: str) -> list[str]:
    label = r"^\s*(?:technical\s+|key\s+|core\s+)?(?:skills|competencies|technologies)\b"
    inline = _first(label + r"\s*[:\-–]\s*(\S.*)$", text, re.I | re.M)  # "Technical Skills: a, b, c"
    tail = ""
    if inline:
        tail = inline.group(1).strip()
        end = inline.end()
        follow = text[end:].lstrip("\n").splitlines()  # a wrapped list continues until a heading or blank line
        for extra in follow[:3]:
            if not extra.strip() or extra.strip().isupper() or ":" in extra:
                break
            tail += " " + extra.strip()
    else:
        heading = _first(label + r"\s*[:\-–]?\s*$", text, re.I | re.M)  # list on the next line
        if heading:
            rest = text[heading.end():].lstrip("\n").splitlines()
            tail = rest[0] if rest else ""
    explicit = [s.strip(" •-*▪●") for s in re.split(r"[,|;•▪●]", tail) if 1 < len(s.strip(" •-*▪●")) <= 40]
    merged = list(dict.fromkeys(explicit + find_skills(text)))
    return merged[:25]


def parse_profile(text: str) -> ParsedData:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    data = ParsedData()
    email = _EMAIL.search(text)
    data.email = email.group().lower() if email else ""
    for m in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 10 <= len(digits) <= 13:
            data.phone = m.group().strip()
            break
    data.full_name = _guess_name(lines)
    data.current_role = _guess_role(lines, data.full_name)
    exp = None
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", text, re.I):
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.start())
        if re.search(r"experience|exp\b", text[line_start: line_end if line_end != -1 else len(text)], re.I):
            exp = Decimal(m.group(1))
            break
    data.experience_years = exp
    data.skills = _skills(text)
    notice = _first(r"notice(?:\s*period)?\s*[:\-–]?\s*(?:of\s*)?(\d+)\s*(day|week|month)s?", text)
    if notice:
        data.notice_days = int(notice.group(1)) * {"day": 1, "week": 7, "month": 30}[notice.group(2).lower()]
    elif _first(r"notice(?:\s*period)?\s*[:\-–]?\s*immediate|immediate(?:ly)?\s*joiner", text):
        data.notice_days = 0
    loc = _first(r"^\s*(?:current\s+)?(?:location|city)\s*[:\-–]\s*(.+)$", text, re.I | re.M)
    data.location = (loc.group(1).strip()[:120] if loc else "") or find_city(text)
    data.current_ctc = _ctc("current", text)
    data.expected_ctc = _ctc("expected", text)
    return data
