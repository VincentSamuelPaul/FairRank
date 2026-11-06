# FairRank: Technical Design Document

GitHub: https://github.com/vincentsamuelpaul/FairRank (confirm URL) · Live app: add link once deployed

*Draft in Markdown: export to PDF or Word for submission. Every assumption is labelled A1–A19 in `docs/BRIEF.md` and referenced below.*

## 1. What it is
AI resume screening for recruiters and a phone-first shortlist portal for clients. Recruiters upload CVs against a job, see the best first with evidence quoted from each CV, and submit candidates. Clients shortlist, reject with a reason, or propose an interview slot. The delivery head sees the pipeline and an AI-vs-recruiter agreement report.

## 2. Architecture and why
React + Vite + TypeScript SPA → Caddy (same origin) → Django 5 + DRF → PostgreSQL. A DB-backed job table and a `run_worker` process handle parsing and scoring (no Celery or Redis: one fewer moving part for a solo build; the queue is rate-limit friendly with batches and exponential backoff). Same-origin via Caddy means httpOnly session cookies and CSRF work with no CORS. Business logic sits in `services.py` per app; views are thin; DRF serializers validate input; Pydantic validates every LLM output.

## 3. Data model
`User(role, client_org)` · `ClientOrg` · `Requisition` → versioned `Scorecard` → `ScorecardCriterion(weight, must-have)` · `Candidate(requisition, stage)` (A11) → `CVFile`, `ParsedProfile`, `Consent`, `StageEvent`, `ViewLog` · `Score` → `CriterionScore(points, confidence, evidence_quote, evidence_status)` · `Submission` → `ClientDecision`, `InterviewSlot` · `Tombstone` · `Job` · `Notification` (mock, A10). DB constraints back the rules: a score number exists only when status is "scored"; a quote exists only when marked verified; a rejection needs a reason; a client user belongs to exactly one org.

## 4. How the AI part works
1. **JD intake**: one LLM call → `JDExtraction` (skills, experience, CTC, notice, location) → editable scorecard v1. Must-have weight 3, nice-to-have 1 (A1). If the AI is down, the requisition is still created and the recruiter builds the scorecard by hand.
2. **Parsing** is rule-based (A18): pdfplumber with column detection for two-column PDFs, python-docx including tables, rapidfuzz for duplicates. Layout test matrix: 5 layouts × 3 domains.
3. **Blind scoring**: `ai/redact.py` strips name, gender, age/DOB, photo lines, marital status, family names, contacts and gendered pronouns before text reaches the LLM. Only text leaves the server, never images.
4. **Scoring**: one call per CV → per-criterion points 0–100, confidence, quote. **Every quote is checked as an exact substring of the CV text (whitespace-normalised) before saving; otherwise it is dropped, the criterion reads "No evidence found" and earns 0 (A15).** Total is the weighted mean; bands Strong ≥ 75, Possible 50–74, Weak < 50 (A2).
5. **When it is wrong or unsure**: scanned PDFs → "Needs manual review", no number (A3); invalid JSON retried once then "Scoring failed, retry" with the CV still readable; 429 backs off then the job queue retries, then fails honestly; confidence < 0.5 shows "Unverified"; results are cached by (CV hash, scorecard version); an `offline` provider (A16) keeps the demo working without quota and is labelled as such.
6. **No auto-reject**: no code path sets a stage from a score. Low scorers are labelled, listed and searchable. Rejection is a client's human decision (A13).

## 5. Main flows
Login (role-aware) → New requisition (paste JD → scorecard) → Upload (type, size, magic-byte checks; consent confirmed; queued; per-file status) → Ranked list (score, evidence, next action; search and filters) → Candidate (CV text with highlighted evidence; opening logs a view) → Submit (server refuses without a ViewLog, 403) → Client portal (masked contacts, shortlist, reject with reason, propose slot) → Pipeline board → Delivery report. Deletion on request wipes file, text, parsed fields and scores and leaves a tombstone (A6).

## 6. Security and privacy
Default-deny DRF permissions by role; session auth with CSRF; login throttled; client isolation via `Candidate.objects.visible_to(user)` (other orgs get 404); contacts masked in serializers until interview (A7), including inside CV text and quotes; every profile/CV open logged by one helper; no secrets in the repo; synthetic data only (A9, A14).

## 7. UI and design decisions
One accent colour, neutral surfaces, Geist type. Score, evidence chips and the next action are on every ranked row. Bands use accent strength, not red/green. Every list has loading, empty and error states. The client portal is single-column with 44 px targets and a sticky action bar. Verified at 390 px and 1280 px.

## 8. Tests
98 backend (pytest) and 15 frontend (Vitest). The ten required tests exist (evidence substring, redaction, client isolation, open-before-submit, no auto-reject, masking, dedupe, deletion, scan flagged, scoring weights), plus LLM retry/backoff/fallback, worker backoff, parsing layout matrix, upload validation and an end-to-end flow.

## 9. Cut and next
Cut: OCR for scans, drag-and-drop on the board (dropdown instead), real email/SMS, candidate-facing consent channel. Next: OCR, a candidate consent link, calibration of scoring against recruiter outcomes, per-client branding, audit export.
