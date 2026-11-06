# Plan to deadline (Thu 5 Nov evening → Mon 9 Nov, 11:59 pm IST)

Rule: by end of each day something demoable works. Commit throughout.

## Thu 5 Nov (evening, about 3 h): foundation
- [~] Public GitHub repo, first commit with BRIEF.md, CLAUDE.md, PLAN.md (committed locally; remote `origin` is set, not pushed yet)
- [x] Django project, custom User with roles, ClientOrg, Postgres via docker compose
- [x] Session login/logout API + React shell with login page and role redirect
- [x] Models + migrations: Requisition, Scorecard/Criterion, Candidate, CVFile, ParsedProfile, Score/CriterionScore, Submission, ViewLog, Consent, Job
- [x] Seed command v0 (users, 3 sample candidates, example JD)

## Fri 6 Nov: JD → scorecard, upload, parsing
- [x] `call_llm` wrapper (Gemini + Groq fallback, cache, retry, Pydantic validation)
- [x] JD intake → AI scorecard → editable scorecard UI (versioned)
- [x] Bulk upload endpoint (type/size/magic-byte checks), Job queue + worker, progress UI
- [x] Text extraction (PDF, DOCX), scan detection → "Needs manual review"
- [x] Dedupe (email/phone exact, rapidfuzz on name)
- [x] Tests: scan flagged, dedupe

## Sat 7 Nov: scoring + ranked list
- [x] Redaction module + tests
- [x] Scoring prompt: per-criterion score + quote; evidence substring verifier + tests
- [x] Weighted total, bands, ranked list UI with evidence, filters, low scorers searchable
- [x] Candidate detail with CV text and highlighted evidence; ViewLog on open
- [x] Seed about 30 synthetic CVs (script) and cached scores

## Sun 8 Nov: client portal, pipeline, compliance
- [x] Submit to client (open-before-submit enforced), custom manager for client isolation + tests
- [x] Client portal (phone-first): masked contacts, shortlist, reject with reason, propose slot, "How we screen" panel
- [x] Pipeline board by requisition; stage changes logged
- [x] Consent record, deletion + tombstone + tests
- [x] Delivery head report: AI rank vs recruiter choice agreement

## Mon 9 Nov: polish, deploy, docs (buffer in the evening)
- [ ] Loading / empty / error states everywhere; check at 375 px width; keyboard + contrast pass
- [ ] Full test run green; fix bugs; secrets scan (`git grep` for keys); `.env.example`
- [ ] Deploy on the OptiPlex (compose + Caddy + Cloudflare Tunnel); smoke test the live URL from your phone on mobile data
- [ ] deployment.md (run locally, deploy, env var names, demo logins)
- [ ] TDD (PDF/Word): GitHub URL + live link at the top; architecture and why; data model; flows; AI design and failure handling; UI decisions with screenshots; assumptions table; what was cut; next steps
- [ ] ZIP with exactly two files; upload; **submit by about 6 pm, not 11:59 pm**

## Cut list if time runs short (in this order)
1. AI-vs-recruiter report (show a static computed table)
2. Pipeline drag and drop (use a dropdown)
3. Interview slot proposal (keep shortlist/reject)
4. Dedupe fuzzy matching (keep exact email/phone)

Never cut: evidence verification, blind scoring, client isolation, open-before-submit, tests for these, deployment.md, TDD.
