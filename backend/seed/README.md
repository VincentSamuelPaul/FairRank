# Seed data

Every CV, name, email and phone number produced here is **synthetic**. Emails use `example.com` / `.example`
domains and phones use the `+91 90000 xxxxx` placeholder range. No real person's data is in this repository.

- `data.py` defines the personas, JDs and scorecards. `cvgen.py` renders them to PDF/DOCX **in memory** (nothing is stored in git).
- `python manage.py seed` creates users, two client orgs, three requisitions and about 31 CVs, scored with the offline
  provider, so the demo needs no API key and no LLM quota.
- `python manage.py seed --reset` wipes the database and uploaded files first (demo/dev only).
- `python manage.py generate_cvs ./sample_cvs` writes the same CVs to a folder for bulk-upload testing.
