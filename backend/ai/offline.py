"""Offline provider: a deterministic, rule-based stand-in for the LLM.

Used when LLM_PROVIDER=offline (tests, seed data, keyless demos, and as the honest last resort
documented in the TDD). Results are labelled with MODEL_NAME so nobody mistakes them for an LLM.
It produces the same schemas as the real providers, so everything downstream (evidence
verification, weighting, bands) is identical.
"""
import re

from ai.schemas import CriterionResult, CVScoring, ExtractedCriterion, JDExtraction
from ai.vocab import find_city, find_skills, skill_pattern

MODEL_NAME = "offline-heuristic-v1"
PLACEHOLDER = "[REDACTED]"
_WEAK_CONTEXT = re.compile(r"\b(familiar|exposure|basic|learning|beginner|theoretical)\b", re.I)
_SKILLS_LABEL = re.compile(r"^\s*(?:[-•*▪●]\s*)?(?:technical\s+|key\s+|core\s+)?(?:skills|competenc\w+|technologies|tools)\b", re.I)


# --- JD extraction ----------------------------------------------------------------------

def extract_jd(jd_text: str) -> JDExtraction:
    first = jd_text.strip().splitlines()[0] if jd_text.strip() else ""
    title = re.split(r"[,\n(]", first)[0].strip()[:200]
    exp = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*(?:years|yrs)", jd_text, re.I)
    exp_min = float(exp.group(1)) if exp else None
    exp_max = float(exp.group(2)) if exp else None
    notice = re.search(r"notice(?:\s*period)?\s*(?:of\s*)?(?:up\s*to|upto|max(?:imum)?|within|<=?)?\s*(\d+)\s*days", jd_text, re.I)
    notice_days = int(notice.group(1)) if notice else None
    ctc = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?)", jd_text, re.I)
    ctc_min = float(ctc.group(1)) * 100_000 if ctc else None
    ctc_max = float(ctc.group(2)) * 100_000 if ctc else None
    location = find_city(jd_text)

    criteria = _skill_criteria(jd_text, title)
    if exp_min is not None:
        label = f"{exp_min:g}-{exp_max:g} years of experience" if exp_max is not None else f"{exp_min:g}+ years of experience"
        criteria.append(ExtractedCriterion(name=label, description="Total relevant experience", is_must_have=True))
    if notice_days is not None:
        criteria.append(ExtractedCriterion(
            name=f"Notice period up to {notice_days} days", description="Can join within the notice limit", is_must_have=True))
    if location:
        criteria.append(ExtractedCriterion(
            name=f"Based in or willing to work in {location}", description="Location fit", is_must_have=False))
    if not criteria:  # nothing recognisable: keep the editor usable instead of failing
        criteria.append(ExtractedCriterion(name=title or "Relevant experience", description="Edit this criterion", is_must_have=True))
    return JDExtraction(
        title=title, location=location, exp_min_years=exp_min, exp_max_years=exp_max,
        notice_max_days=notice_days, ctc_min=ctc_min, ctc_max=ctc_max, criteria=criteria[:15],
    )


def _skill_criteria(jd_text: str, title: str) -> list[ExtractedCriterion]:
    """Skills found in the title/JD. Lines under 'nice to have' are optional; the rest are must-have."""
    seen: dict[str, bool] = {}
    nice_mode = False
    lines = jd_text.splitlines() or [jd_text]
    for idx, line in enumerate(lines):
        low = line.lower()
        if re.search(r"nice\s*to\s*have|good\s*to\s*have|preferred|plus\b|bonus", low):
            nice_mode = True
        elif re.search(r"must\s*have|required|mandatory|responsibilit", low):
            nice_mode = False
        for name in find_skills(line):
            seen.setdefault(name, not nice_mode)
    must_count = 0
    out: list[ExtractedCriterion] = []
    for name, is_must in seen.items():
        if is_must and must_count >= 6:  # keep the card focused: the rest become nice-to-have
            is_must = False
        must_count += is_must
        out.append(ExtractedCriterion(name=name, description=f"Hands-on {name}", is_must_have=is_must))
    return out


# --- CV scoring -------------------------------------------------------------------------

def _line_window(text: str, pos: int, max_len: int = 200) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    end = len(text) if end == -1 else end
    if end - start > max_len:
        start, end = max(start, pos - max_len // 2), min(end, pos + max_len // 2)
    return text[start:end].strip()


def _result(cid: int, points: int, conf: float, quote: str, why: str) -> CriterionResult:
    if PLACEHOLDER in quote:
        quote = ""
    return CriterionResult(criterion_id=cid, points=max(0, min(100, points)), confidence=conf, quote=quote, rationale=why)


def _score_experience(cid: int, name: str, cv: str) -> CriterionResult:
    rng = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)", name)
    plus = re.search(r"(\d+(?:\.\d+)?)\s*\+", name)
    lo = float(rng.group(1)) if rng else float(plus.group(1)) if plus else 0.0
    hi = float(rng.group(2)) if rng else None
    best = None
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", cv, re.I):
        line = _line_window(cv, m.start())
        if re.search(r"experience|exp\b", line, re.I):
            best = m
            break
    if best is None:
        return _result(cid, 0, 0.5, "", "No total experience stated in the CV")
    years = float(best.group(1))
    quote = _line_window(cv, best.start())
    if years < lo:
        pts, why = int(100 - (lo - years) * 30), f"{years:g} years is below the {lo:g} year minimum"
    elif hi is not None and years > hi:
        pts, why = 85, f"{years:g} years is above the {hi:g} year range"
    else:
        pts, why = 100, f"{years:g} years fits the requested range"
    return _result(cid, pts, 0.9, quote, why)


def _score_notice(cid: int, name: str, cv: str) -> CriterionResult:
    limit_m = re.search(r"(\d+)\s*days", name)
    limit = int(limit_m.group(1)) if limit_m else 60
    m = re.search(r"notice(?:\s*period)?\s*[:\-–]?\s*(?:of\s*)?(\d+)\s*(day|week|month)s?", cv, re.I)
    if m:
        n = int(m.group(1)) * {"day": 1, "week": 7, "month": 30}[m.group(2).lower()]
        pts = 100 if n <= limit else max(0, 100 - 2 * (n - limit))
        return _result(cid, pts, 0.95, _line_window(cv, m.start()), f"Notice of {n} days against a {limit} day limit")
    imm = re.search(r"immediate(?:ly)?\s*(?:joiner|joining|available)?|serving\s*notice", cv, re.I)
    if imm:
        return _result(cid, 100, 0.8, _line_window(cv, imm.start()), "Available immediately")
    return _result(cid, 0, 0.4, "", "Notice period not stated in the CV")


def _score_location(cid: int, name: str, cv: str) -> CriterionResult:
    city = find_city(name)
    if not city:
        return _result(cid, 0, 0.3, "", "No location named in the criterion")
    m = re.search(rf"(?<![A-Za-z]){city}(?![A-Za-z])", cv, re.I)
    if m:
        return _result(cid, 100, 0.9, _line_window(cv, m.start()), f"CV places the candidate in {city}")
    reloc = re.search(r"open\s*to\s*relocat\w*|willing\s*to\s*relocat\w*", cv, re.I)
    if reloc:
        return _result(cid, 55, 0.7, _line_window(cv, reloc.start()), "Willing to relocate")
    return _result(cid, 0, 0.6, "", f"No sign of {city} or relocation in the CV")


def _score_skill(cid: int, name: str, cv: str) -> CriterionResult:
    pattern = skill_pattern(name)
    body_hit = list_hit = None
    body_count = 0
    for m in pattern.finditer(cv):
        line = _line_window(cv, m.start())
        if _SKILLS_LABEL.match(line):
            list_hit = list_hit or m
        else:
            body_count += 1
            body_hit = body_hit or m
    if body_hit is not None:
        quote = _line_window(cv, body_hit.start())
        if _WEAK_CONTEXT.search(quote):
            return _result(cid, 35, 0.45, quote, f"{name} mentioned only as familiarity")
        pts = min(100, 70 + 10 * (body_count - 1))
        return _result(cid, pts, 0.85, quote, f"{name} used in the work history ({body_count} mention{'s' if body_count > 1 else ''})")
    if list_hit is not None:
        return _result(cid, 50, 0.6, _line_window(cv, list_hit.start()), f"{name} listed under skills but not shown in the work history")
    return _result(cid, 0, 0.7, "", f"No mention of {name}")


def score_cv(cv_text: str, criteria: list[dict]) -> CVScoring:
    results = []
    for c in criteria:
        low = c["name"].lower()
        if "notice" in low:
            results.append(_score_notice(c["id"], c["name"], cv_text))
        elif "experience" in low or re.search(r"\d\s*(?:-|–|to|\+)\s*\d*\s*years", low):
            results.append(_score_experience(c["id"], c["name"], cv_text))
        elif "based in" in low or "location" in low or find_city(c["name"]):
            results.append(_score_location(c["id"], c["name"], cv_text))
        else:
            results.append(_score_skill(c["id"], c["name"], cv_text))
    return CVScoring(results=results)
