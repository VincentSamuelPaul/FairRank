import pytest

from candidates.parsing import UnsupportedFile, extract_text, parse_profile, sniff_kind
from conftest import SAMPLE_CV, make_docx, make_pdf


def test_pdf_and_docx_extract_and_parse():
    for data, kind in ((make_pdf(SAMPLE_CV.splitlines()), "pdf"), (make_docx(SAMPLE_CV.splitlines()), "docx")):
        assert sniff_kind(data) == kind
        parsed = parse_profile(extract_text(data, kind))
        assert parsed.full_name == "Jane Doe" and parsed.email == "jane.doe@example.com"
        assert float(parsed.experience_years) == 6 and parsed.notice_days == 30 and parsed.location == "Noida"
        assert {"Java", "Spring Boot", "Hibernate"} <= set(parsed.skills)


def test_magic_bytes_beat_the_extension():
    with pytest.raises(UnsupportedFile):
        sniff_kind(b"MZ\x90\x00 an executable renamed to cv.pdf")
    with pytest.raises(UnsupportedFile):
        sniff_kind(b"PK\x03\x04 a zip that is not a docx")


def test_corrupt_pdf_is_reported_not_crashed():
    with pytest.raises(UnsupportedFile):
        extract_text(b"%PDF-1.4 garbage", "pdf")


@pytest.mark.parametrize("layout", ["pdf_single", "pdf_table", "pdf_two_column", "docx_single", "docx_table"])
@pytest.mark.parametrize("domain,level", [("java", "strong"), ("kyc", "medium"), ("retail", "weak")])
def test_every_layout_parses_the_same_facts(layout, domain, level):
    """The hard part of the brief: varied CV formats. Same person, five layouts, same parsed profile."""
    import random

    from seed.cvgen import build_persona, render

    persona = build_persona(random.Random(5), domain, level, layout, years=4.5, notice=45, city="Noida")
    _, data = render(persona)
    parsed = parse_profile(extract_text(data, sniff_kind(data)))
    assert parsed.full_name == persona.name
    assert parsed.email == persona.email and parsed.phone == persona.phone
    assert float(parsed.experience_years) == 4.5 and parsed.notice_days == 45 and parsed.location == "Noida"
    assert persona.skills[0] in parsed.skills


def test_scanned_pdf_has_no_extractable_text():
    import random

    from seed.cvgen import build_persona, render

    _, data = render(build_persona(random.Random(5), "kyc", "weak", "pdf_scanned"))
    assert extract_text(data, "pdf") == ""
