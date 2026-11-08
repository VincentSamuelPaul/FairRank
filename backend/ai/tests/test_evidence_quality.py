"""Evidence QUALITY: a verbatim quote that is only a job title or a skills list must not earn full marks."""
import pytest

from ai import offline
from ai.evidence import cap_weak_evidence, evidence_kind
from ai.schemas import CriterionResult
from screening.services import resolve_criterion

WORK = "- Designed REST APIs with Spring Boot and documented them with OpenAPI"


@pytest.mark.parametrize("quote,kind", [
    ("Senior Java Developer", "title"),
    ("Senior Java Developer, Cobalt Systems (2021 - Present)", "title"),
    ("Technical Skills: Java, Spring Boot, Microservices, REST APIs, Hibernate", "skills_list"),
    ("Java, Spring Boot, Kafka, Docker, Kubernetes", "skills_list"),
    (WORK, "work"),
    ("Led a team of 5 developers through two production releases", "work"),
    ("Total Experience: 6.5 years", "fact"),
    ("Location: Noida", "fact"),
])
def test_evidence_kind(quote, kind):
    assert evidence_kind(quote) == kind


def test_title_or_skills_list_is_capped_but_a_work_sentence_is_not():
    assert cap_weak_evidence("Java", 95, 0.9, "Senior Java Developer") == (65, 0.5, "title")
    assert cap_weak_evidence("Java", 95, 0.9, "Technical Skills: Java, Spring, Kafka")[:2] == (50, 0.5)
    assert cap_weak_evidence("Spring Boot", 95, 0.9, WORK)[:2] == (95, 0.9)


def test_factual_criteria_are_exempt():
    assert cap_weak_evidence("Notice period up to 60 days", 100, 0.95, "Notice Period: 60 days")[:2] == (100, 0.95)
    assert cap_weak_evidence("Based in or willing to work in Noida", 100, 0.9, "Location: Noida")[:2] == (100, 0.9)


def test_cap_applies_to_any_provider_output_and_keeps_the_quote_verbatim():
    cv = "Asha\nSenior Java Developer\nSkills: Java, Spring"
    res = CriterionResult(criterion_id=1, points=95, confidence=0.9, quote="Senior Java Developer", rationale="Strong Java")
    points, conf, quote, status, why = resolve_criterion(res, cv, "Java")
    assert (points, conf, quote, status) == (65, 0.5, "Senior Java Developer", "verified")
    assert "Capped" in why and "job title" in why


def test_invented_quote_is_still_dropped_before_any_quality_logic():
    res = CriterionResult(criterion_id=1, points=95, confidence=0.9, quote="Led a team of 40 engineers", rationale="x")
    points, _, quote, status, _ = resolve_criterion(res, "Senior Java Developer", "Java")
    assert (points, quote, status) == (0, "", "no_evidence")


def test_offline_scorer_prefers_a_sentence_describing_work_over_title_and_skills_list():
    cv = ("Asha Verma\nSenior Java Developer\nTechnical Skills: Java, Spring Boot, Kafka\n"
          "EXPERIENCE\n- Built payment services in Java handling 2M requests a day\n")
    r = offline.score_cv(cv, [{"id": 1, "name": "Java"}]).results[0]
    assert "Built payment services" in r.quote and r.points >= 70


def test_offline_scorer_lowers_the_score_when_only_a_title_supports_it():
    cv = "Asha Verma\nSenior Java Developer\nEXPERIENCE\n- Managed vendor contracts\n"
    r = offline.score_cv(cv, [{"id": 1, "name": "Java"}]).results[0]
    assert r.quote == "Senior Java Developer" and r.points <= 65 and r.confidence <= 0.5
