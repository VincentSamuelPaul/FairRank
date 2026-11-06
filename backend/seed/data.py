"""What the seed creates: three JDs and about 31 synthetic CVs (A9, A14). Deterministic."""
import random
from dataclasses import dataclass

from seed.cvgen import Persona, build_persona

JD_JAVA = "Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days"  # the brief's example JD

JD_KYC = """KYC Analyst, 2-5 years
Location: Gurgaon. Notice period up to 45 days.
Must have: KYC, AML, customer due diligence, sanctions screening, Excel.
Nice to have: transaction monitoring."""

JD_RETAIL = """Retail Store Manager, 4-8 years
Location: Delhi. Notice period up to 30 days.
Must have: store operations, inventory management, visual merchandising, team leadership, P&L management.
Nice to have: loss prevention, staff scheduling."""

# The brief's explicit v1 scorecard for the example JD (A1: must-have weight 3, nice-to-have 1)
JAVA_SCORECARD = [
    ("Java", "Hands-on Java development", 3, True),
    ("Spring Boot", "Builds services with Spring Boot", 3, True),
    ("5-8 years of experience", "Total experience between 5 and 8 years", 3, True),
    ("Notice period up to 60 days", "Can join within 60 days", 3, True),
    ("Based in or willing to work in Noida", "Location fit", 1, False),
]

LAYOUTS = ["pdf_single", "pdf_two_column", "docx_single", "docx_table", "pdf_table"]


@dataclass
class Spec:
    key: str
    title: str
    org_index: int
    jd: str
    location: str
    exp: tuple[float, float]
    notice: int
    scorecard: list | None  # None = extract with the offline provider
    people: list[tuple[Persona, str]]  # (persona, external id)


def _unique(rng: random.Random, domain: str, level: str, layout: str, taken: set[str], idx: int, **kw) -> Persona:
    while True:
        p = build_persona(rng, domain, level, layout, idx=idx, **kw)
        if p.name not in taken:
            taken.add(p.name)
            return p


def build_specs() -> list[Spec]:
    rng = random.Random(2026)
    taken: set[str] = {"Ritika Bansal", "Arjun Rawat", "Pooja Nair"}
    counter = [0]

    def phone() -> str:
        counter[0] += 1
        return f"+91 90000 {20000 + counter[0]:05d}"

    def layout(i: int) -> str:
        return LAYOUTS[i % len(LAYOUTS)]

    # --- Java: the brief's three sample candidates + 13 generated
    java: list[tuple[Persona, str]] = [
        (build_persona(rng, "java", "strong", "pdf_single", name="Ritika Bansal", gender="Female", years=6.5, notice=60,
                       city="Noida", role="Senior Java Developer", email="ritika.bansal@example.com",
                       phone="+91 90000 00001", skills=["Java", "Spring Boot", "Microservices", "REST APIs", "Hibernate"]),
         "CND-91022"),
        (build_persona(rng, "kyc", "medium", "docx_single", name="Arjun Rawat", gender="Male", years=3.0, notice=30,
                       city="Delhi", role="KYC Analyst", email="arjun.rawat@example.com", phone="+91 90000 00002",
                       skills=["KYC", "AML checks", "Excel"]), "CND-91047"),
        (build_persona(rng, "java", "medium", "pdf_two_column", name="Pooja Nair", gender="Female", years=4.0, notice=90,
                       city="Gurgaon", role="Java Developer", email="pooja.nair@example.com", phone="+91 90000 00003",
                       skills=["Java", "Hibernate", "REST APIs"]), "CND-91088"),
    ]
    levels = ["strong"] * 4 + ["medium"] * 5 + ["weak"] * 4
    for i, lvl in enumerate(levels):
        java.append((_unique(rng, "java", lvl, layout(i), taken, i, phone=phone(),
                             city=rng.choice(["Noida", "Noida", "Gurgaon", "Delhi", "Pune", "Bengaluru"])), f"CND-920{i + 1:02d}"))

    kyc: list[tuple[Persona, str]] = []
    for i, lvl in enumerate(["strong"] * 3 + ["medium"] * 3 + ["weak"] * 2):
        lay = "pdf_scanned" if i == 7 else layout(i + 1)  # the last one is the scanned, image-only CV
        kyc.append((_unique(rng, "kyc", lvl, lay, taken, 20 + i, phone=phone(),
                            city=rng.choice(["Gurgaon", "Gurgaon", "Delhi", "Noida"])), f"CND-930{i + 1:02d}"))

    retail: list[tuple[Persona, str]] = []
    for i, lvl in enumerate(["strong"] * 2 + ["medium"] * 3 + ["weak"]):
        retail.append((_unique(rng, "retail", lvl, layout(i + 2), taken, 40 + i, phone=phone(),
                               city=rng.choice(["Delhi", "Delhi", "Noida", "Ghaziabad"])), f"CND-940{i + 1:02d}"))
    # A duplicate: the same person re-uploaded in another format (same email and phone)
    original = retail[2][0]
    dup = build_persona(random.Random(7), "retail", "medium", "docx_table", name=original.name, gender=original.gender,
                        email=original.email, phone=original.phone, city=original.city, years=original.years,
                        notice=original.notice, role=original.role, skills=original.skills)
    retail.append((dup, "CND-94007"))

    return [
        Spec("java", "Senior Java Developer", 0, JD_JAVA, "Noida", (5, 8), 60, JAVA_SCORECARD, java),
        Spec("kyc", "KYC Analyst", 1, JD_KYC, "Gurgaon", (2, 5), 45, None, kyc),
        Spec("retail", "Retail Store Manager", 0, JD_RETAIL, "Delhi", (4, 8), 30, None, retail),
    ]
