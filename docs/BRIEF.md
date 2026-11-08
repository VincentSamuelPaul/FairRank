# Client brief: Staffing firm's AI resume screening tool and client shortlist portal

*(Verbatim from the Isocode take-home. Task: build the product end to end with a great UI and UX. Due 9 Nov 2026, 11:59 pm IST. Work alone. Submit one ZIP with a TDD and a deployment.md.)*

## Client

Company A, Noida. Contract and permanent hiring for IT services, banking back-office and retail clients. 120 staff including 70 recruiters, revenue ₹40–50 crore a year.

## Today

Clients email job descriptions (JDs). Recruiters search job boards and an old internal database, download CVs and read each one. Shortlists go to clients as Excel sheets with CVs attached. Feedback comes by email or phone, and status lives in each recruiter's own sheet.

## The problem

Assumptions: 300 open requisitions a month, 120 CVs each, 3 minutes per CV. 300 × 120 × 3 = 1,08,000 minutes = 1,800 hours a month, 21,600 hours a year × ₹350 = ₹75.6 lakh. Shortlists take 5 days, and 5% of requisitions (180 of 3,600 a year) are lost to faster rivals at ₹45,000 average fee: ₹81 lakh. Total ₹1.57 crore a year.

## Users

Recruiters, client hiring managers, and the delivery head. The CEO signs the deal.

## The ask

My recruiters spend their day reading CVs that were never going to fit. I want them to upload a pile of CVs against a job and see the best first, with reasons. Clients should review shortlists in a portal, not by phone. I must be able to show clients that we treat candidates fairly.

## Must have

- JD intake: AI extracts must-have skills, experience, CTC and notice into an editable scorecard
- Bulk CV upload (PDF or DOCX, up to 500), parsed into profiles with duplicate detection
- AI score per CV with evidence lines quoted from the CV for each criterion
- Client portal with masked contacts, where clients shortlist, reject with a reason or propose an interview slot
- Pipeline per requisition from sourced to joined
- Candidate consent record and deletion on request

## Core build

Software Engineering candidates must ship this slice end to end, in about 6 to 8 screens: JD scorecard, bulk CV upload and parsing, ranked list with evidence, client shortlist portal, and pipeline. Roles: recruiter and client hiring manager. AI: CV scoring with evidence. Hard part: parsing varied CV formats in bulk. Mock payments, messages and outside systems, and seed from the sample data. The rest of MUST HAVE is optional depth.

## Out of scope

- Job board integrations or scraping
- Video interviews
- Background verification

## AI or automation

AI parses CVs and scores them against the scorecard. When it is wrong: it never rejects anyone automatically; every score shows its evidence; a recruiter must open a CV before submitting it; name, gender, age, photo and marital status are hidden from scoring; low scorers stay searchable. A weekly sample compares AI ranks with recruiter choices for the delivery head.

## Constraints

CVs are personal data under the DPDP Act 2023: consent, hiring use only, deletion on request, and a log of who viewed what. Each client sees only candidates submitted to them. Some CVs are scans; clients often review on phones.

## Design

The client values good, minimal design: clean layouts, white space, a restrained palette and clear type, with nothing on screen that lacks a purpose. Design counts as much as features. Recruiters scan many profiles: make the score, its evidence and the next action clear; the client portal should look clean and professional on a phone.

## Budget and time

₹7 lakh, 6 weeks. Success: screening time per requisition down 60%; shortlist within 48 hours for 80% of requisitions; client acceptance of candidates from 45% to 60%.

## Sample data

| Candidate ID | Name | Current Role | Experience yrs | Key Skills | Notice Days |
|---|---|---|---|---|---|
| CND-91022 | Ritika Bansal | Senior Java Developer | 6.5 | Java, Spring Boot, microservices | 60 |
| CND-91047 | Arjun Rawat | KYC Analyst | 3.0 | KYC, AML checks, Excel | 30 |
| CND-91088 | Pooja Nair | Java Developer | 4.0 | Java, Hibernate, REST APIs | 90 |

Example JD: Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days

---

# Submission rules (from the task page)

- ZIP (max 25 MB) with exactly two files: **TDD** (PDF or Word) and **deployment.md**
- TDD: GitHub URL at the very top (and live app link if deployed); architecture and why; data model, main flows, how the AI part works; UI and design decisions and key screens; what was cut and what next
- deployment.md: run locally step by step; how it is deployed + env var NAMES only; demo login details for the reviewer
- Use only information in the brief. **Label every assumption in the TDD**
- Keep the commit history. No secrets or real personal data in the repo. Keep the repo public until review is finished
- Must have: main flows work on realistic sample data (no dead buttons); frontend + backend + DB + sign-in with roles; AI part works including when wrong or unsure; polished UI (consistent design, phone layout, loading / empty / error states); tests for the most important logic; basic security (no secrets, validated inputs, access control)
- Scoring: Quality of work 50%, Problem solving 30%, Communication 20%

---

# Assumptions (label each of these in the TDD)

| # | Assumption | Reason |
|---|---|---|
| A1 | Scoring weights are per criterion on the scorecard, default must-have = 3, nice-to-have = 1, editable by the recruiter | Brief gives no weighting |
| A2 | Score bands: Strong ≥ 75, Possible 50–74, Weak < 50 (of weighted total) | Needed for a ranked list; tunable |
| A3 | Scanned or image-only PDFs are NOT OCR'd; they are marked "Needs manual review" | OCR is out of the time budget; honest "unsure" state |
| A4 | Bulk upload limit is 500 files per batch as in the brief; practical demo uses about 30 synthetic CVs | Free-tier LLM rate limits |
| A5 | Consent is captured as a recorded consent entry (source, timestamp, purpose = hiring use only) per candidate; in the demo it is recorded on upload by the recruiter on the candidate's behalf | No candidate-facing channel in scope |
| A6 | Deletion keeps a tombstone (candidate ID, date, requester) and wipes the file, text and parsed fields | Audit trail without personal data |
| A7 | "Masked contacts" = email/phone replaced with masked values for clients until a candidate reaches the interview stage | Brief says masked, does not say when to unmask |
| A8 | The weekly AI-vs-recruiter comparison is a report computed on demand and by a weekly job, shown to the delivery head | Brief says "weekly sample" |
| A9 | All CVs in the repo are synthetic; the LLM only ever sees synthetic or consented data | Task rules ban real personal data |
| A10 | Email/SMS notifications are mocked (written to a notifications log) | Brief allows mocking outside systems || A11 | A candidate record is one CV screened against one requisition (Candidate has a `requisition`; a Submission is one-to-one with it). The same person on two jobs is two records, with duplicates flagged | Simplest model that gives per-requisition stage, score and client isolation |
| A12 | JD CTC is stored as INR per year (`ctc_min`, `ctc_max`), nullable because the example JD has none | Brief names CTC but gives no unit |
| A13 | Pipeline stages are the seven in the brief plus a terminal `rejected` set only by a client's human decision, never from a score | Clients can reject with a reason, so a board needs somewhere to put them |
| A14 | Demo users, client orgs and phone numbers are synthetic (`@example.com` addresses, placeholder numbers). The brief's sample table has no email or phone, so these are invented to exercise masking | Needed to demo masked contacts and dedupe; covered by A9 |
| A15 | A criterion with no verified quote earns 0 points and reads "No evidence found" | A score must never rest on a claim the user cannot see checked against the CV |
| A16 | An `offline` rule-based provider (labelled `offline-heuristic-v1`) implements the same schemas as the LLM, used for tests, seed data and keyless demos. Seed scores are pre-computed with it | Free-tier quota can run out; the demo must still work. It is never presented as an LLM |
| A17 | A candidate moves sourced to screened when scoring completes (regardless of the score value). A client proposing an interview slot moves them to interview, which unmasks contacts (A7). Recruiters can only move interview/offered/joined and sourced/screened by hand | "Never auto-reject" forbids score-driven moves, not processing-driven ones |
| A18 | CV parsing (name, contacts, experience, skills, notice, CTC) is rule-based; the LLM is used only for JD intake and scoring | Saves quota; parsing is deterministic and testable |
| A19 | The Retail Store Manager JD is attached to the first synthetic client org (Northwind) because the brief asks for only 2 client orgs | Synthetic seed (A9) |
| A20 | The CV text a client reads has the value on gender, age, date of birth, marital status, photo, nationality, religion, caste and family-name lines replaced by "[hidden]". The candidate's name line stays. The stored CV is untouched | The brief hides these from scoring; showing them to the client would undercut "we treat candidates fairly" |
| A21 | The parser treats an experience above 60 years or a notice period above 365 days as "not stated" rather than storing it | Found by input testing: absurd numbers in a CV must never become facts or break a save |

| A22 | With no LLM API key configured, scoring falls back to the offline rule-based scorer (A16), labelled in the UI; a configured provider that fails is shown as "Scoring failed, retry", never replaced silently | A keyless demo must work; a real outage must not be hidden |
| A23 | Evidence that is only a bare job title or a skills list is capped (title 65, skills list 50 points, confidence 0.5) and the scoring prompt asks for a sentence describing work done | A keyword is not proof of work done |
