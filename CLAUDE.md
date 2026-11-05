# CLAUDE.md — Staffing AI screening + client shortlist portal

Read `docs/BRIEF.md` first. It is the source of truth. Use ONLY information in the brief; anything else is an assumption and must be listed in the assumptions table in `docs/BRIEF.md` (and later the TDD).

Deadline: 9 Nov 2026, 11:59 pm IST. Solo project. A working, polished slice beats a broad broken one.

## Stack (decided)

- Backend: Python 3.12, Django 5 + Django REST Framework
- Validation: DRF serializers for API input; Pydantic for LLM JSON output
- DB: PostgreSQL (docker compose). Use SQLite only for quick local tests if needed
- Auth: Django session auth (httpOnly cookie, CSRF on). Custom User with `role` in {recruiter, client, delivery_head}; clients also belong to a `ClientOrg`
- Jobs: `Job` table + worker (`python manage.py run_worker`). No Celery or Redis
- Parsing: `pdfplumber` (PDF), `python-docx` (DOCX), `rapidfuzz` (dedupe)
- LLM: one function `ai/llm.py::call_llm(prompt, schema)`; Gemini Flash primary, Groq fallback, chosen by env. Cache by (cv_hash, scorecard_version)
- Frontend: React + Vite + TypeScript, React Router, TanStack Query, Tailwind + shadcn/ui, React Hook Form + Zod
- Tests: pytest-django; a few frontend tests (Vitest) for key components
- Deploy: Docker Compose (postgres, web/gunicorn, worker, caddy). Caddy serves the Vite build and proxies `/api` to Django (same origin, so session cookies and CSRF just work)

## Repo layout

```
backend/
  config/            # settings (env-driven), urls
  accounts/          # User, ClientOrg, roles, permissions
  requisitions/      # Requisition, Scorecard, ScorecardCriterion (versioned)
  candidates/        # Candidate, CVFile, ParsedProfile, Consent, Tombstone
  screening/         # Score, CriterionScore (evidence), ai pipeline
  portal/            # Submission, ClientDecision, InterviewSlot
  audit/             # ViewLog, Job, Notification (mock)
  ai/                # llm.py, prompts.py, schemas.py (pydantic), redact.py, evidence.py
  seed/              # management command + synthetic CV generator
frontend/
docs/                # BRIEF.md, PLAN.md, TDD notes
docker-compose.yml  Caddyfile  .env.example  README.md
```

## NON-NEGOTIABLE rules (these come from the brief; each needs a test)

1. **Never auto-reject.** Low scorers are labelled, never hidden or removed. Low scorers stay searchable. No code path changes a candidate's status based on score alone.
2. **Every score shows evidence.** Each criterion score stores a quote from the CV. Before saving, verify the quote is an exact substring of the extracted CV text (normalise whitespace only). If not, DROP the quote and mark the criterion "No evidence found". Never display an unverified quote.
3. **Blind scoring.** Name, gender, age/DOB, photo and marital status are redacted from the text sent to the LLM for scoring. Redaction happens in `ai/redact.py` and is tested.
4. **Open before submit.** A recruiter can submit a candidate to a client only if a `ViewLog` row exists for that recruiter and candidate (they opened the CV). Enforced server-side, not just in the UI.
5. **Client isolation.** Clients only ever see candidates with a `Submission` to their org. Enforce via a custom manager/queryset (`Candidate.objects.visible_to(user)`), used by every client-facing view. Test that client A cannot fetch client B's candidate by ID (expect 404).
6. **Masked contacts.** Client serializers mask email/phone until the candidate is at the interview stage (assumption A7). Raw values never leave the server for clients.
7. **View log.** Every open of a candidate profile or CV writes a `ViewLog` (who, what, when). One helper, used everywhere.
8. **Consent and deletion.** Candidates have a consent record. Deletion on request wipes file, text and parsed fields and leaves a tombstone (id, date). Deleted candidates disappear from all lists and from client portals.
9. **Honest unsure states.** Scanned/empty-text PDF → "Needs manual review" (no fake score). LLM error or invalid JSON after one retry → "Scoring failed, retry" with the CV still visible. Low-confidence criteria show as "Unverified".
10. **No secrets in the repo.** Everything via env; `.env.example` has names only. Only synthetic data in the repo.

## Coding rules

- Small, frequent commits with clear messages (reviewers read the history). Conventional style: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Validate all inputs (serializers). File upload: allow only PDF/DOCX, check size (e.g. 5 MB per file) and magic bytes, never trust the extension.
- Permissions via DRF permission classes per role; default deny.
- LLM output always parsed through a Pydantic schema; on failure retry once, then fail gracefully.
- Rate-limit aware: queue CV processing, batch of N at a time, exponential backoff on 429.
- Every UI list/page needs loading, empty and error states. Mobile-first for the client portal.
- Design: minimal. White space, one accent colour, clear type, nothing without a purpose. Score + evidence + next action must be obvious on the ranked list.
- Keep functions small and typed. Business logic in services, not views.

## Tests that must exist (pytest)

- `test_evidence_substring`: invented quote is dropped; real quote kept; whitespace-normalised match works
- `test_redaction`: name/gender/age/photo/marital status stripped from LLM input
- `test_client_isolation`: client A gets 404 for client B's candidate and requisition
- `test_open_before_submit`: submit without view → 403
- `test_no_auto_reject`: low score leaves status unchanged and candidate still searchable
- `test_masking`: client payload has masked contacts before interview stage
- `test_dedupe`: same email / near-identical name+phone flagged as duplicate
- `test_deletion`: deletion wipes data, leaves tombstone, removes from client view
- `test_scan_flagged`: empty-text PDF marked needs manual review
- `test_scoring_weights`: weighted total and band thresholds

## Screens (core build, 6 to 8)

1. Login (role-aware redirect)
2. Requisitions list + JD intake (paste JD → AI scorecard)
3. Scorecard editor (criteria, weights, must-have flags, versioned)
4. Bulk CV upload with progress, per-file status (parsed / needs review / duplicate / failed)
5. Ranked list with score, per-criterion evidence, next action; search/filter incl. low scorers
6. Candidate detail (CV text view, evidence highlighted, consent, "Submit to client")
7. Client portal (phone-first): shortlist, reject with reason, propose interview slot, masked contacts, "How we screen" panel
8. Pipeline board (sourced → screened → submitted → shortlisted → interview → offered → joined) + delivery head's AI-vs-recruiter agreement report

## Seed data (must exist so the app never looks empty)

- Users: 2 recruiters, 1 delivery head, 2 client orgs each with 1 hiring manager (demo creds go in deployment.md)
- The 3 sample candidates from the brief (Ritika Bansal, Arjun Rawat, Pooja Nair) and the example JD (Senior Java Developer, 5-8 yrs, Spring Boot, Noida, notice up to 60 days)
- About 30 synthetic CVs in mixed PDF/DOCX layouts (single column, two column, table-based, one scanned image PDF, one duplicate), plus 2 more JDs (KYC Analyst, retail store manager)
- Pre-computed scores cached for seed CVs so the demo works even if the LLM quota is exhausted

## Working agreement

- Update the checklist in `docs/PLAN.md` as items finish.
- When a decision is unclear, pick the simplest option, note it as an assumption, and keep going.
- Never claim something works without running it. Run tests before committing.