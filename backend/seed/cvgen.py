"""Synthetic CV generator (all people, companies and contacts are invented: A9, A14).

Produces PDF and DOCX files in several layouts so the parser is exercised on realistic variety:
single column, two column (sidebar), table-based, and one scanned (image-only) PDF.
CVs deliberately include gender, date of birth, marital status and a photo line so blind scoring has
something to redact.
"""
import io
import random
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

FIRST_F = ["Ananya", "Meera", "Kavya", "Ishita", "Nandini", "Sneha", "Tanvi", "Divya", "Riya", "Aditi", "Shruti", "Leela"]
FIRST_M = ["Vikram", "Aarav", "Kunal", "Manish", "Siddharth", "Harsh", "Yash", "Deepak", "Rahul", "Nikhil", "Tarun", "Varun"]
LAST = ["Khanna", "Sethi", "Malhotra", "Bhatt", "Chopra", "Joshi", "Menon", "Pillai", "Saxena", "Tiwari", "Kulkarni",
        "Desai", "Agarwal", "Bose", "Chandra", "Dutta", "Grover", "Iyer", "Kohli", "Rastogi", "Sood", "Trivedi"]
COMPANIES = ["Brightwave Systems", "Kestrel Software", "Lumina Technologies", "Orbit Digital", "Quillon Labs",
             "Zephyr Infotech", "Nimbus Solutions", "Cobalt Systems", "Harbor Analytics", "Saffron Retail Group",
             "Marigold Stores", "Pinecrest Financial Services", "Lakeview Credit Services", "Ashoka Trading Co"]
CITIES = ["Noida", "Gurgaon", "Delhi", "Pune", "Bengaluru", "Hyderabad", "Ghaziabad"]
MARITAL = ["Married", "Single", "Unmarried"]

BULLETS = {
    "java": {
        "strong": [
            "Built and maintained {n} Spring Boot microservices for payment and order workflows",
            "Designed REST APIs with Spring Boot and documented them with OpenAPI",
            "Tuned Hibernate queries and PostgreSQL indexes, cutting report latency by {pct}%",
            "Introduced Kafka based event processing for order status updates",
            "Wrote JUnit tests and set up Jenkins pipelines for every service",
            "Containerised services with Docker and deployed them on AWS",
            "Led a team of {k} developers through two production releases",
        ],
        "medium": [
            "Developed Java services using Spring MVC and Hibernate for an insurance platform",
            "Built REST APIs consumed by the web and mobile front ends",
            "Worked on a Spring Boot migration of one legacy module",
            "Wrote SQL queries and stored procedures for reporting",
            "Supported releases and fixed production defects",
        ],
        "weak": [
            "Developed Core Java modules for an in-house ERP using JSP and Servlets",
            "Maintained batch jobs and wrote SQL reports on Oracle",
            "Fixed defects and supported user acceptance testing",
            "Familiar with Spring Boot through internal training; basic exposure only",
        ],
    },
    "kyc": {
        "strong": [
            "Completed KYC and customer due diligence reviews for {n} high risk accounts a month",
            "Ran AML transaction monitoring alerts and escalated suspicious activity reports",
            "Performed sanctions screening on onboarding and periodic reviews",
            "Built Excel trackers and pivot reports to cut review turnaround by {pct}%",
            "Trained {k} new analysts on KYC policy and audit readiness",
        ],
        "medium": [
            "Verified customer documents and completed KYC checks for retail accounts",
            "Handled AML alert reviews under supervision",
            "Maintained Excel trackers for pending documents",
            "Coordinated with relationship managers to close KYC gaps",
        ],
        "weak": [
            "Performed data entry for account opening forms",
            "Basic exposure to KYC document checks; learning AML concepts",
            "Prepared Excel sheets for the operations team",
        ],
    },
    "retail": {
        "strong": [
            "Ran store operations for a {n} person team, owning the store P&L management and monthly targets",
            "Improved inventory management accuracy to 98% through weekly stock audits",
            "Led visual merchandising refreshes for every season and campaign",
            "Cut shrinkage by {pct}% with a loss prevention programme",
            "Built staff scheduling that raised sales per labour hour",
            "Developed {k} team leads into store managers through team leadership coaching",
        ],
        "medium": [
            "Managed daily store operations and cash handling",
            "Tracked inventory management and raised replenishment orders",
            "Supported visual merchandising changes sent from head office",
            "Handled customer service escalations",
        ],
        "weak": [
            "Worked as a sales associate on the shop floor",
            "Helped with stock counting and basic inventory tasks",
            "Familiar with visual merchandising guidelines; exposure only",
        ],
    },
}
SKILLS = {
    "java": {
        "strong": ["Java", "Spring Boot", "Microservices", "REST APIs", "Hibernate", "PostgreSQL", "Kafka", "Docker", "AWS", "JUnit"],
        "medium": ["Java", "Spring", "Hibernate", "REST APIs", "SQL", "Maven"],
        "weak": ["Core Java", "JSP", "Servlets", "SQL", "Oracle"],
    },
    "kyc": {
        "strong": ["KYC", "AML", "Customer due diligence", "Sanctions screening", "Transaction monitoring", "Excel"],
        "medium": ["KYC", "AML", "Excel", "Document verification"],
        "weak": ["Data entry", "Excel", "Customer service"],
    },
    "retail": {
        "strong": ["Store operations", "Inventory management", "Visual merchandising", "Team leadership", "P&L management", "Loss prevention", "Staff scheduling"],
        "medium": ["Store operations", "Inventory management", "Customer service", "Cash handling"],
        "weak": ["Sales", "Customer service", "Stock counting"],
    },
}
ROLES = {
    "java": {"strong": "Senior Java Developer", "medium": "Java Developer", "weak": "Software Engineer"},
    "kyc": {"strong": "Senior KYC Analyst", "medium": "KYC Analyst", "weak": "Operations Associate"},
    "retail": {"strong": "Store Manager", "medium": "Assistant Store Manager", "weak": "Sales Associate"},
}
YEARS = {
    "java": {"strong": (5.5, 8.0), "medium": (3.0, 4.5), "weak": (1.0, 2.5)},
    "kyc": {"strong": (3.5, 5.0), "medium": (2.0, 3.0), "weak": (0.5, 1.5)},
    "retail": {"strong": (5.0, 8.0), "medium": (3.0, 4.5), "weak": (1.0, 2.0)},
}
NOTICE = {"strong": [15, 30, 45, 60], "medium": [30, 60, 90], "weak": [60, 90]}
EDUCATION = {
    "java": ["B.Tech, Computer Science", "MCA"], "kyc": ["B.Com", "MBA, Finance"], "retail": ["B.A.", "BBA, Retail Management"],
}


@dataclass
class Persona:
    name: str
    gender: str
    dob: str
    marital: str
    email: str
    phone: str
    city: str
    role: str
    years: float
    notice: int
    current_ctc: int
    expected_ctc: int
    skills: list[str]
    summary: str
    jobs: list[tuple[str, str, str, list[str]]]  # period, title, company, bullets
    education: list[str]
    domain: str = "java"
    level: str = "medium"
    layout: str = "pdf_single"
    extra: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")


def build_persona(rng: random.Random, domain: str, level: str, layout: str, *, name: str | None = None,
                  email: str | None = None, phone: str | None = None, years: float | None = None,
                  notice: int | None = None, city: str | None = None, role: str | None = None,
                  skills: list[str] | None = None, gender: str | None = None, idx: int = 0) -> Persona:
    gender = gender or rng.choice(["Female", "Male"])
    first = rng.choice(FIRST_F if gender == "Female" else FIRST_M)
    name = name or f"{first} {rng.choice(LAST)}"
    lo, hi = YEARS[domain][level]
    years = years if years is not None else round(rng.uniform(lo, hi) * 2) / 2
    pool = list(BULLETS[domain][level])
    rng.shuffle(pool)
    fmt = {"n": rng.choice([3, 4, 6, 8, 12]), "pct": rng.choice([20, 30, 35, 40]), "k": rng.choice([3, 4, 5])}
    picked = [b.format(**fmt) for b in pool]
    cut = max(2, len(picked) // 2)
    jobs = [
        (f"{2026 - int(years) + 1 if years >= 2 else 2025} - Present", role or ROLES[domain][level],
         rng.choice(COMPANIES), picked[:cut]),
        (f"{max(2016, 2026 - int(years) - 2)} - {2026 - int(years)}" if years >= 2 else "2024 - 2025",
         "Associate " + (role or ROLES[domain][level]).split()[-1], rng.choice(COMPANIES), picked[cut:] or picked[:2]),
    ]
    day, month, year = rng.randint(1, 28), rng.choice(["January", "March", "May", "July", "September", "November"]), rng.randint(1986, 2001)
    slug = name.lower().replace(" ", ".")
    ctc = int(4 + years * 2.2)
    return Persona(
        name=name, gender=gender, dob=f"{day} {month} {year}", marital=rng.choice(MARITAL),
        email=email or f"{slug}@example.com", phone=phone or f"+91 90000 {10000 + idx * 37 + rng.randint(0, 36):05d}",
        city=city or rng.choice(CITIES), role=role or ROLES[domain][level], years=years,
        notice=notice if notice is not None else rng.choice(NOTICE[level]), current_ctc=ctc, expected_ctc=ctc + 3,
        skills=skills or SKILLS[domain][level],
        summary=f"{role or ROLES[domain][level]} with {years:g} years of experience. " + picked[0] + ".",
        jobs=jobs, education=[rng.choice(EDUCATION[domain]) + ", " + rng.choice(["Delhi University", "Pune University", "Anna University", "Mumbai University"])],
        domain=domain, level=level, layout=layout,
    )


# --- text blocks shared by all layouts -------------------------------------------------------

def contact_lines(p: Persona) -> list[str]:
    return [f"Email: {p.email}", f"Phone: {p.phone}", f"Location: {p.city}"]


def profile_lines(p: Persona) -> list[str]:
    return [f"Total Experience: {p.years:g} years", f"Notice Period: {p.notice} days",
            f"Current CTC: {p.current_ctc} LPA", f"Expected CTC: {p.expected_ctc} LPA"]


def personal_lines(p: Persona) -> list[str]:
    return [f"Gender: {p.gender}", f"Date of Birth: {p.dob}", f"Marital Status: {p.marital}", "Photo: attached"]


def flat_lines(p: Persona) -> list[tuple[str, str]]:
    """(kind, text) lines for single-column renderers. kinds: name, role, h, p, b"""
    out = [("name", p.name), ("role", p.role)]
    out += [("p", t) for t in contact_lines(p) + profile_lines(p)]
    out += [("h", "Summary"), ("p", p.summary), ("h", "Skills"), ("p", "Technical Skills: " + ", ".join(p.skills))]
    out.append(("h", "Experience"))
    for period, title, company, bullets in p.jobs:
        out.append(("p", f"{title}, {company} ({period})"))
        out += [("b", b) for b in bullets]
    out += [("h", "Education")] + [("p", e) for e in p.education]
    out += [("h", "Personal Details")] + [("p", t) for t in personal_lines(p)]
    return out


# --- PDF renderers ----------------------------------------------------------------------------

def _pdf_single(p: Persona, table: bool = False) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=10, leading=13)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
    story: list = []
    for kind, text in flat_lines(p):
        if kind == "name":
            story.append(Paragraph(escape(text), ss["Title"]))
        elif kind == "role":
            story.append(Paragraph(escape(text), ss["Heading3"]))
        elif kind == "h":
            story += [Spacer(1, 4), Paragraph(escape(text.upper()), ss["Heading4"])]
        elif kind == "b":
            story.append(Paragraph(escape(text), body, bulletText="-"))
        else:
            story.append(Paragraph(escape(text), body))
    if table:  # replace the flat experience with a table: period | role + bullets
        story = [s for s in story]
        rows = []
        for period, title, company, bullets in p.jobs:
            cell = [Paragraph(f"<b>{escape(title)}</b>, {escape(company)}", body)] + [Paragraph("- " + escape(b), body) for b in bullets]
            rows.append([Paragraph(escape(period), body), cell])
        t = Table(rows, colWidths=[35 * mm, 135 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey)]))
        story.append(Spacer(1, 6))
        story.append(Paragraph("WORK HISTORY", ss["Heading4"]))
        story.append(t)
    doc.build(story)
    return buf.getvalue()


def _pdf_two_column(p: Persona) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import simpleSplit
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, h - 50, p.name)
    c.setFont("Helvetica", 12)
    c.drawString(40, h - 68, p.role)

    def column(x: int, width: int, blocks: list[tuple[str, list[str]]]) -> None:
        y = h - 110
        for heading, lines in blocks:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, heading.upper())
            y -= 14
            c.setFont("Helvetica", 9)
            for line in lines:
                for part in simpleSplit(line, "Helvetica", 9, width):
                    c.drawString(x, y, part)
                    y -= 12
                y -= 2
            y -= 8

    left = [("Contact", contact_lines(p)), ("Profile", profile_lines(p)), ("Skills", ["Technical Skills: " + ", ".join(p.skills)]),
            ("Education", p.education), ("Personal Details", personal_lines(p))]
    right: list[tuple[str, list[str]]] = [("Summary", [p.summary])]
    exp: list[str] = []
    for period, title, company, bullets in p.jobs:
        exp.append(f"{title}, {company} ({period})")
        exp += ["- " + b for b in bullets]
    right.append(("Experience", exp))
    column(40, 150, left)
    column(235, 320, right)
    c.save()
    return buf.getvalue()


def _pdf_scanned(p: Persona) -> bytes:
    """Image-only PDF: the text is pixels, so extraction finds none (A3)."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    img = Image.new("L", (827, 1169), 255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=15)
    y = 40
    for kind, text in flat_lines(p):
        draw.text((50, y), text.upper() if kind in ("h",) else text, fill=30, font=font)
        y += 30 if kind in ("name", "h") else 22
    img = img.rotate(0.6, fillcolor=255)  # a slightly skewed "scan"
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawImage(ImageReader(img), 0, 0, width=A4[0], height=A4[1])
    c.save()
    return buf.getvalue()


# --- DOCX renderers ---------------------------------------------------------------------------

def _docx_single(p: Persona) -> bytes:
    from docx import Document

    doc = Document()
    for kind, text in flat_lines(p):
        if kind == "name":
            doc.add_heading(text, 0)
        elif kind == "role":
            doc.add_paragraph(text)
        elif kind == "h":
            doc.add_heading(text, 2)
        elif kind == "b":
            doc.add_paragraph(text, style="List Bullet")
        else:
            doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _docx_table(p: Persona) -> bytes:
    """Table-based layout: a sidebar cell and a main cell side by side, plus a label/value table."""
    from docx import Document

    doc = Document()
    doc.add_heading(p.name, 0)
    doc.add_paragraph(p.role)
    side = doc.add_table(rows=1, cols=2)
    left, right = side.rows[0].cells
    left.text = ""
    for heading, lines in [("CONTACT", contact_lines(p)), ("SKILLS", ["Technical Skills: " + ", ".join(p.skills)]),
                           ("EDUCATION", p.education), ("PERSONAL DETAILS", personal_lines(p))]:
        left.add_paragraph(heading)
        for line in lines:
            left.add_paragraph(line)
    right.text = ""
    right.add_paragraph("SUMMARY")
    right.add_paragraph(p.summary)
    right.add_paragraph("EXPERIENCE")
    for period, title, company, bullets in p.jobs:
        right.add_paragraph(f"{title}, {company} ({period})")
        for b in bullets:
            right.add_paragraph("- " + b)
    facts = doc.add_table(rows=0, cols=2)
    for line in profile_lines(p):
        label, _, value = line.partition(": ")
        row = facts.add_row().cells
        row[0].text, row[1].text = label, value
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


RENDERERS = {
    "pdf_single": lambda p: _pdf_single(p),
    "pdf_table": lambda p: _pdf_single(p, table=True),
    "pdf_two_column": _pdf_two_column,
    "pdf_scanned": _pdf_scanned,
    "docx_single": _docx_single,
    "docx_table": _docx_table,
}


def render(p: Persona) -> tuple[str, bytes]:
    ext = "docx" if p.layout.startswith("docx") else "pdf"
    return f"{p.slug}_{p.layout}.{ext}", RENDERERS[p.layout](p)
