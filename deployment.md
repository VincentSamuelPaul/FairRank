# deployment.md

Repo: https://github.com/VincentSamuelPaul/FairRank (keep it public until the review is finished).
Live app: https://fairrank.vincents.systems (synthetic data, demo logins in section 4). It currently runs the Docker development stack behind a Cloudflare Tunnel, not the production Caddy build; section 3 is the exact procedure for the production build, and section 1 reproduces everything a reviewer needs on one machine.

## 1. Run it locally (Docker, about 5 minutes)

Needs Docker with Compose. No API key is needed: with none configured, scoring uses a built-in rule-based scorer that the UI labels.

```bash
git clone https://github.com/VincentSamuelPaul/FairRank.git && cd FairRank
cp .env.example .env
# edit .env: set SECRET_KEY (any 32+ characters), POSTGRES_PASSWORD, DEBUG=true. Leave the rest blank.
docker compose up -d --build        # postgres, web (Django), worker, frontend (Vite dev server)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed
```

Open http://localhost:5173 and sign in with a demo login (section 4). Blank values in `.env` mean "use the default".

- Start over with the demo data exactly as a reviewer sees it: `docker compose exec web python manage.py seed --reset` (wipes the database and uploaded files first).
- Bulk-upload sample: `docker compose exec web python manage.py generate_cvs /tmp/cvs`, then `docker compose cp web:/tmp/cvs ./sample_cvs` and drop the files on a requisition's **Upload CVs** tab. All 31 CVs are synthetic (PDF and DOCX, mixed layouts, one scanned, one duplicate).
- The worker (`python manage.py run_worker`) parses and scores uploaded CVs in small batches and starts with `docker compose up`.
- Real AI scoring (optional): set `LLM_PROVIDER=groq` with `GROQ_API_KEY`, or `gemini` with `GEMINI_API_KEY`. If one fails the other is tried. Rate limits (429) back off exponentially. With keys set, a provider failure shows "Scoring failed, retry" (it is never replaced by fake scores). With no key at all the offline scorer runs; `FALLBACK_TO_OFFLINE=false` turns that off.

## 2. Tests (all run locally, no keys needed)

| What | Command | Result when last run |
|---|---|---|
| Backend (pytest), 279 tests | `docker compose exec web python -m pytest` | 279 passed |
| Frontend (Vitest), 32 tests | `docker compose exec frontend npx vitest run` | 32 passed |
| Types and lint | `docker compose exec frontend npx tsc -b` and `npm run lint` | 0 errors |
| Rendered UI, 82 checks | `scripts/qa.sh` | 82 passed |
| Login fits 13 screen sizes | `scripts/login-fit.sh` | 13 of 13 |
| Colour contrast | `python3 scripts/contrast.py` | 0 failures |
| Browser end-to-end, every role, 36 checks | see below | 36 passed |
| Production build smoke test, 34 checks | `BASE=http://localhost:8080 scripts/prod-smoke.sh` | 34 passed |

Browser end-to-end (uses the offline scorer so it is deterministic, then restores):

```bash
docker compose exec web python manage.py generate_cvs /tmp/cvs && mkdir -p .review/cvs && docker compose cp web:/tmp/cvs/. .review/cvs/
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.e2e.yml up -d web worker
scripts/e2e-ui.sh                  # removes its own "E2E ..." requisitions first; seed data is never touched
docker compose up -d web worker    # back to the configured LLM provider
```

The sign-in form is rate limited (10 a minute per client). When running the browser suites repeatedly, set `LOGIN_RATE=1000/min` in your local `.env` and recreate `web`, then set it back.

## 3. Deploy on my OptiPlex (about 20 minutes)

Assumes a Linux machine with Docker (Compose v2) and git, and a domain whose DNS you control. Only Caddy publishes ports; Postgres, Django and the worker are internal. Choose **A (Cloudflare Tunnel)** or **B (port forward)** in step 3.

1. **Get the code.**
   ```bash
   git clone https://github.com/VincentSamuelPaul/FairRank.git && cd FairRank
   ```
2. **Create `.env`** (names only are in `.env.example`; values stay on the server).
   ```bash
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"        # paste as SECRET_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"        # paste as POSTGRES_PASSWORD
   ```
   Set: `SECRET_KEY`, `POSTGRES_PASSWORD`, `ALLOWED_HOSTS=app.yourdomain.com`, `CSRF_TRUSTED_ORIGINS=https://app.yourdomain.com`, `SEED_PASSWORD` (a demo password you choose; do not reuse a real one), and optionally `LLM_PROVIDER` with `GROQ_API_KEY` or `GEMINI_API_KEY`. Leave `DEBUG` blank (production). The app refuses to start with a missing or short `SECRET_KEY`.
3. **Pick how traffic arrives.**
   - **A. Cloudflare Tunnel (no router changes).** In Cloudflare Zero Trust create a tunnel, add a public hostname `app.yourdomain.com` with service `http://caddy:80`, and copy its token. In `.env` set `TUNNEL_TOKEN=<token>`, `SITE_ADDRESS=:80`, `CADDY_BIND=127.0.0.1`, `NUM_PROXIES=2`. Then `scripts/deploy.sh --tunnel`.
   - **B. Port forward.** Point an A record for `app.yourdomain.com` at your public IP and forward TCP 80 and 443 on the router to the OptiPlex. In `.env` set `SITE_ADDRESS=app.yourdomain.com` (Caddy gets a certificate automatically) and `NUM_PROXIES=1`. Then `scripts/deploy.sh`.
4. **Deploy.** `scripts/deploy.sh` pulls, builds the frontend, builds the images, starts everything (the web container runs migrations and collects static files), waits for the health check and fails loudly if any service is down.
5. **Load the demo data** (skip for a real, empty system):
   ```bash
   docker compose -f docker-compose.yml exec web python manage.py seed
   ```
6. **Back up** (cron-friendly): `scripts/backup.sh` writes a Postgres dump and the uploaded CVs to `./backups` (old backups are not deleted automatically).
7. **Update later:** `scripts/deploy.sh` again.

### Verify it works
- Health: `curl -s https://app.yourdomain.com/api/health/` returns `{"status":"ok"}`.
- Containers: `docker compose -f docker-compose.yml ps` shows db, web and worker `healthy` and caddy `running`.
- Sign in with each demo login below on your phone; the client login lands on the phone-first shortlist. Open a candidate, then confirm **Submit to client** is enabled only after opening the CV.
- Browser dev tools: no red errors; the session cookie is `Secure`, `HttpOnly`, `SameSite=Lax`.
- Rotate the demo passwords or reseed without demo users before sharing the link publicly.

Not verified: the Cloudflare Tunnel was used for the live demo with the development stack, so options A and B for the production build were checked only up to the Caddy container (production settings, health, headers, cookies and CSRF were tested end to end on the Docker stack at `http://localhost:8080`). Option A's `NUM_PROXIES=2` is the documented expectation for tunnel plus Caddy, not something measured here.

## 4. Demo logins (synthetic; password `FairRank-demo-1` unless `SEED_PASSWORD` is set)

| Role | Email | Lands on |
|---|---|---|
| Recruiter | recruiter1@companya.example | Requisitions |
| Recruiter | recruiter2@companya.example | Requisitions |
| Delivery head | head@companya.example | Pipeline and the AI vs recruiter report |
| Client hiring manager (Northwind IT Services) | manager@northwind.example | Phone-first shortlist |
| Client hiring manager (Meridian Bank Operations) | manager@meridian.example | Phone-first shortlist |

All five were signed in from a fresh clone. Things to try: open a candidate (this logs a view and unlocks Submit); look for a criterion that reads "No evidence found"; open the scanned KYC CV ("Needs manual review"); sign in as the other client and confirm none of the first client's candidates are visible; propose an interview slot and watch contacts unmask.

## 5. Environment variable names (values are never committed)

Identical to `.env.example`.

| Group | Names |
|---|---|
| Django | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_COOKIES`, `DATABASE_URL`, `MEDIA_ROOT`, `STATIC_ROOT`, `MAX_UPLOAD_BYTES`, `MAX_FILES_PER_BATCH`, `LOGIN_RATE`, `HSTS_SECONDS`, `NUM_PROXIES`, `CACHE_DIR` |
| Postgres | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| LLM | `LLM_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GROQ_API_KEY`, `GROQ_MODEL` |
| Seed | `SEED_PASSWORD`, `FALLBACK_TO_OFFLINE` |
| Caddy and tunnel | `SITE_ADDRESS`, `CADDY_BIND`, `TUNNEL_TOKEN` |
| Dev only | `VITE_PROXY_TARGET`, `VITE_DEMO_MODE` |
| Worker | `WORKER_BATCH_SIZE`, `WORKER_POLL_SECONDS`, `WORKER_BACKOFF_SECONDS` |

## 6. Known limits

- The live site runs the development stack (Django DEBUG on, demo-login chips visible). The production build was tested on localhost only; section 3 says what was and was not verified.
- Scanned or image-only PDFs are not OCR'd; they are flagged "Needs manual review".
- Email and SMS are mocked (a notifications log).
- Free-tier LLM quotas cap batch speed; the queue batches and backs off on 429.
- Containers run as the image's default user; Postgres is not exposed, but there is no read-only filesystem hardening.
- The login rate limit is per client address and relies on `NUM_PROXIES` matching how traffic arrives.
- Backups are written locally and not pruned or copied off the machine.
- The "Drafting scorecard" steps in the New requisition dialog are an estimated sequence (the create call is synchronous).
