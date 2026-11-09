# FairRank: logins and test checklist

App: http://localhost:5173  (API: http://localhost:8000)
Password for every demo user: `FairRank-demo-1`  (synthetic demo data only)

## Logins

| Role | Email | Name | Lands on |
|---|---|---|---|
| Recruiter | recruiter1@companya.example | Asha Verma | Requisitions |
| Recruiter | recruiter2@companya.example | Rohan Mehta | Requisitions |
| Delivery head | head@companya.example | Kavita Rao | Pipeline + AI vs recruiter report |
| Client (Northwind IT Services) | manager@northwind.example | Neel Kapoor | Phone-first shortlist |
| Client (Meridian Bank Operations) | manager@meridian.example | Sana Iqbal | Phone-first shortlist |

## Start / stop / reset

```bash
docker compose up -d                                  # start everything
docker compose restart worker                         # after ANY backend code change (worker does not auto-reload)
docker compose exec web python manage.py seed         # reset demo data
docker compose logs -f worker                         # watch CV scoring
docker compose down                                   # stop
```

## Automated tests

```bash
docker compose exec web python -m pytest -q           # backend, expect 279 passed, about 4 minutes (don't run two at once)
docker compose exec frontend npm test -- --run        # frontend, expect 32 passed
```

## Manual checklist

Recruiter (`recruiter1@companya.example`)
- [ ] Login lands on Requisitions
- [ ] New requisition: paste a JD, a scorecard is generated (criteria, weights, must-haves)
- [ ] Scorecard editor: change a weight, save, version goes up
- [ ] Upload CVs tab: tick consent, upload PDF/DOCX, per-file status updates live
- [ ] Renamed .txt as .pdf or file over 5 MB is rejected with a reason
- [ ] Same file twice is flagged duplicate
- [ ] Scanned PDF shows "Needs manual review" and has no score
- [ ] Ranked list: score, band, per-criterion evidence, next action visible
- [ ] Low scorers are labelled but still listed and searchable (no auto-reject)
- [ ] A criterion without a CV quote shows "No evidence found"
- [ ] Candidate detail: CV text with evidence highlighted
- [ ] Submit to client is blocked until the CV has been opened, then works
- [ ] Failed scoring shows "Scoring failed, retry" and the CV stays visible

Client isolation (`manager@northwind.example`, use a phone-width window)
- [ ] Only candidates submitted to Northwind are visible
- [ ] Email and phone are masked
- [ ] Reject with a reason works
- [ ] Propose an interview slot; contacts unmask at the interview stage
- [ ] "How we screen" panel opens
- [ ] Log in as `manager@meridian.example`: none of Northwind's candidates are visible
- [ ] Opening a Northwind candidate URL as Meridian gives 404

Delivery head (`head@companya.example`)
- [ ] Pipeline board shows sourced to joined
- [ ] AI vs recruiter agreement report loads

Deletion
- [ ] Delete a candidate on request: gone from lists and client portal, tombstone remains

## LLM

Configured in `.env` (never commit it): `LLM_PROVIDER=groq` (model `qwen/qwen3.8-27b`), fallback Gemini (`gemini-3.8-flash`).
Set `LLM_PROVIDER=offline` for key-free, repeatable rule-based scoring.
After editing `.env`: `docker compose up -d --force-recreate web worker`.
Scores can vary a little between runs because the model is not deterministic.

## Sample CVs

```bash
docker compose exec web python manage.py generate_cvs /tmp/cvs
docker compose cp web:/tmp/cvs ./sample_cvs      # 31 synthetic CVs (add sample_cvs/ to .gitignore)
```

Test JDs to paste into a new requisition: Python Backend Engineer, Data Analyst, Technical Recruiter, DevOps Engineer
(seeded already: Senior Java Developer, KYC Analyst, Retail Store Manager).
