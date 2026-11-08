# deployment.md

Repo: https://github.com/VincentSamuelPaul/FairRank (keep it public until review is finished). Live app: not deployed from the build machine; the "Deploy" section below is the exact procedure, and the local run below reproduces everything the reviewer needs.

## Run locally (Docker, about 5 minutes)

Needs Docker with Compose.

```bash
cp .env.example .env
# edit .env: set SECRET_KEY (long random string), POSTGRES_PASSWORD, DEBUG=true, LLM_PROVIDER=offline
docker compose up -d --build        # postgres, web (Django), worker, frontend (Vite dev server)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed
```

Open http://localhost:5173 and sign in with a demo login below.

- Tests (all run locally, no keys needed):
  - Backend, 252 tests: `docker compose exec web python -m pytest`
  - Frontend, 32 tests: `docker compose exec frontend npx vitest run` (or `npm test` in `frontend/`)
  - Rendered UI checks: `scripts/qa.sh`; login fits 13 screen sizes: `scripts/login-fit.sh`; contrast: `python3 scripts/contrast.py`
  - Browser end-to-end for every role (36 checks): use the offline scorer so it is deterministic, then restore:
    ```bash
    docker compose exec web python manage.py generate_cvs /tmp/cvs && mkdir -p .review/cvs && docker compose cp web:/tmp/cvs/. .review/cvs/
    docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.e2e.yml up -d web worker
    scripts/e2e-ui.sh            # removes its own "E2E ..." requisitions first; seed data is never touched
    docker compose up -d web worker   # back to the configured LLM provider
    ```
- Bulk-upload sample: `docker compose exec web python manage.py generate_cvs /tmp/cvs` writes the 31 synthetic CVs (PDF and DOCX, mixed layouts, one scanned, one duplicate); copy them out with `docker compose cp web:/tmp/cvs ./sample_cvs` and drop them on a requisition's **Upload CVs** tab.
- The worker (`python manage.py run_worker`) parses and scores uploaded CVs in small batches. It starts with `docker compose up`.

### LLM
`LLM_PROVIDER=offline` needs no key and uses a rule-based stand-in (labelled in the UI and database). For real scoring set `LLM_PROVIDER=gemini` with `GEMINI_API_KEY`, or `groq` with `GROQ_API_KEY`. If one fails, the other is used as a fallback when its key is set. Rate limits (429) back off exponentially, then the job queue retries.

## Deploy (Docker Compose + Caddy)

```bash
cd frontend && npm ci && npm run build && cd ..     # produces frontend/dist, served by Caddy
cp .env.example .env                                  # fill in the names below; DEBUG=false, SECURE_COOKIES=true
docker compose -f docker-compose.yml --profile deploy up -d --build
docker compose exec web python manage.py seed
```

Caddy serves the Vite build and proxies `/api` and `/admin` to Django on the same origin, so session cookies and CSRF work without CORS. Set `SITE_ADDRESS` to the public hostname (Caddy then gets a certificate) or `:80` behind a tunnel, and put that origin in `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

### Environment variable names (values are never committed)
`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_COOKIES`, `DATABASE_URL`, `MEDIA_ROOT`, `STATIC_ROOT`, `MAX_UPLOAD_BYTES`, `MAX_FILES_PER_BATCH`, `LOGIN_RATE`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL`, `WORKER_BATCH_SIZE`, `WORKER_POLL_SECONDS`, `WORKER_BACKOFF_SECONDS`, `SEED_PASSWORD`, `SITE_ADDRESS`, `VITE_PROXY_TARGET` (dev only).

## Demo logins (synthetic; password `FairRank-demo-1` unless `SEED_PASSWORD` is set)

| Role | Email | Lands on |
|---|---|---|
| Recruiter | recruiter1@companya.example | Requisitions |
| Recruiter | recruiter2@companya.example | Requisitions |
| Delivery head | head@companya.example | Delivery: pipeline and AI vs recruiter report |
| Client hiring manager (Northwind IT Services) | manager@northwind.example | Phone-first shortlist |
| Client hiring manager (Meridian Bank Operations) | manager@meridian.example | Phone-first shortlist |

Things to try: open a candidate (this logs a view and unlocks Submit); try the Kafka-less CVs for "No evidence found"; open the scanned KYC CV ("Needs manual review"); sign in as the other client and confirm you see none of the first client's candidates; propose an interview slot and watch contacts unmask.
