"""Rule 3: name, gender, age/DOB, photo and marital status never reach the LLM."""
from ai.redact import PLACEHOLDER, mask_contacts_in_text, mask_email, mask_phone, redact_for_scoring
from conftest import SAMPLE_CV


def test_protected_attributes_are_stripped():
    out = redact_for_scoring(SAMPLE_CV, full_name="Jane Doe")
    for leaked in ("Jane", "Doe", "Female", "12 March 1991", "Married", "Photo: attached", "jane.doe@example.com",
                   "98765 43210", "She is"):
        assert leaked not in out, leaked
    assert PLACEHOLDER in out


def test_job_relevant_content_survives():
    out = redact_for_scoring(SAMPLE_CV, full_name="Jane Doe")
    for kept in ("Spring Boot microservices", "Notice Period: 30 days", "Location: Noida", "6 years of experience"):
        assert kept in out


def test_age_phrases_and_inline_dob():
    out = redact_for_scoring("Age: 34 years\nI am 29 years old and born 03/04/1995. Java expert.", "")
    assert "34" not in out and "29" not in out and "1995" not in out
    assert "Java expert" in out


def test_gender_marital_words_inline():
    out = redact_for_scoring("Mr. Rahul is a married male engineer. He leads Java teams; his team ships weekly.", "Rahul")
    for w in ("Mr.", "Rahul", "married", "male", "He ", "his "):
        assert w not in out
    assert "Java teams" in out


def test_name_is_redacted_case_insensitively_in_any_position():
    out = redact_for_scoring("RITIKA BANSAL\nWorked with Ritika's team. Bansal Corp is unrelated text.", "Ritika Bansal")
    assert "RITIKA" not in out and "BANSAL" not in out.upper().replace("[REDACTED]", "")


def test_masking_helpers_hide_contacts():
    assert mask_email("ritika.bansal@example.com") == "r•••@e•••.com"
    assert "9000" not in mask_phone("+91 90000 00001") and mask_phone("+91 90000 00001").endswith("01")
    text = mask_contacts_in_text("Mail ritika@example.com or call +91 90000 00001, linkedin.com/in/ritika")
    assert "ritika@example.com" not in text and "90000 00001" not in text and "linkedin" not in text
