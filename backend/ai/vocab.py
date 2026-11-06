"""Small shared vocabulary used by the CV profile parser and the offline provider."""
import re

# canonical name -> regex alternatives (case-insensitive, word-bounded when matched)
SKILLS: dict[str, tuple[str, ...]] = {
    "Java": (r"java(?!\s*script)",),
    "Spring Boot": (r"spring\s*boot",),
    "Spring": (r"spring(?!\s*boot)",),
    "Hibernate": (r"hibernate",),
    "Microservices": (r"micro[\s\-]?services?",),
    "REST APIs": (r"rest(?:ful)?\s*apis?", r"restful", r"rest\s*services?"),
    "SQL": (r"sql",),
    "PostgreSQL": (r"postgres(?:ql)?",),
    "Kafka": (r"kafka",),
    "Docker": (r"docker",),
    "Kubernetes": (r"kubernetes|k8s",),
    "AWS": (r"aws|amazon\s*web\s*services",),
    "Maven": (r"maven",),
    "JUnit": (r"junit",),
    "Angular": (r"angular",),
    "React": (r"react(?:\.?js)?",),
    "Python": (r"python",),
    "KYC": (r"kyc|know\s*your\s*customer",),
    "AML": (r"aml|anti[\s\-]?money\s*laundering",),
    "Customer due diligence": (r"cdd|customer\s*due\s*diligence",),
    "Sanctions screening": (r"sanctions?\s*screening",),
    "Transaction monitoring": (r"transaction\s*monitoring",),
    "Excel": (r"(?:ms\s*|microsoft\s*)?excel",),
    "Compliance": (r"compliance",),
    "Store operations": (r"store\s*operations?",),
    "Inventory management": (r"inventory(?:\s*management)?",),
    "Visual merchandising": (r"visual\s*merchandising|merchandising",),
    "Team leadership": (r"team\s*(?:leadership|management)|led\s*a\s*team|managed\s*a\s*team",),
    "P&L management": (r"p\s*&\s*l|profit\s*(?:and|&)\s*loss",),
    "Customer service": (r"customer\s*(?:service|experience)",),
    "Sales targets": (r"sales\s*targets?",),
    "Loss prevention": (r"loss\s*prevention|shrinkage",),
    "Staff scheduling": (r"(?:staff|shift)\s*(?:scheduling|rostering)|rostering",),
}

CITIES = (
    "Noida", "Gurgaon", "Gurugram", "Delhi", "New Delhi", "Mumbai", "Pune", "Bengaluru", "Bangalore",
    "Hyderabad", "Chennai", "Kolkata", "Ghaziabad", "Faridabad", "Jaipur", "Lucknow", "Ahmedabad",
)


def skill_pattern(canonical: str) -> re.Pattern:
    alts = SKILLS.get(canonical)
    body = "|".join(alts) if alts else re.escape(canonical)
    return re.compile(rf"(?<![A-Za-z0-9])(?:{body})(?![A-Za-z0-9])", re.I)


def find_skills(text: str) -> list[str]:
    """Canonical skills mentioned in `text`, in order of first appearance."""
    hits: list[tuple[int, str]] = []
    for name in SKILLS:
        m = skill_pattern(name).search(text)
        if m:
            hits.append((m.start(), name))
    names = [n for _, n in sorted(hits)]
    if "Spring Boot" in names and "Spring" in names:  # "Spring Boot" implies the generic one
        names.remove("Spring")
    return names


def find_city(text: str) -> str:
    for city in CITIES:
        if re.search(rf"(?<![A-Za-z]){city}(?![A-Za-z])", text, re.I):
            return {"Gurugram": "Gurgaon", "Bangalore": "Bengaluru"}.get(city, city)
    return ""
