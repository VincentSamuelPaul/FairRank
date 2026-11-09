# Interview notes (not part of the submission ZIP)

Short answers to say aloud. Each is under 80 words. Numbers were measured on the final run; see the last answer.

## Why Django plus React, and not Next.js?
The hard part of this product is rules on the server: who may see which candidate, what counts as evidence, what a score may change. Django and DRF give me default-deny permissions, serializers, migrations and a mature test runner out of the box. React is only the interface, so one same-origin Caddy in front gives session cookies and CSRF with no CORS. Next.js would have put those rules in two places.

## How does evidence verification work, and why a substring check?
The model returns a quote for each criterion. Before saving, I normalise whitespace in both texts and check the quote is an exact substring of the CV text. If it isn't, I drop the quote, mark "No evidence found" and score that criterion zero. A substring check is deliberately dumb: it cannot be argued with, so a model cannot buy points with an invented sentence.

## How is blind scoring implemented and tested?
`ai/redact.py` strips name, gender, age and date of birth, marital status, photo markers, family names, addresses, reference lines, emails, phones and gendered pronouns before text goes to any scorer. Images never leave the server. Dedicated redaction tests cover it, and the candidate page has a Blind view. It is minimisation, not anonymisation: work history, employers, city and CTC still go. Recruiters still see the original CV.

## How is client isolation enforced?
One queryset method, `Candidate.objects.visible_to(user)`, is the only way client-facing views fetch candidates. For a client it returns only candidates with a submission to their org. Anything else is not "forbidden", it simply doesn't exist, so another org's candidate is a 404. A permission matrix test calls every endpoint as five kinds of caller, and a separate test checks client A against client B's candidate.

## How is "open before submit" enforced server-side?
Every open of a profile or CV writes a `ViewLog` row through one helper. The submit service checks that a row exists for that recruiter and that candidate; if not, it returns 403. The UI also disables the button, but that is only a mirror. A second recruiter's view doesn't count, which a test pins down.

## What happens when the LLM is down, slow or wrong?
Wrong: invalid JSON gets one retry, then "Scoring failed, retry" with the CV still readable; invented quotes are dropped. Slow or rate-limited: a database job queue works in small batches with exponential backoff on 429. Down: the other provider is tried. With no key at all, a labelled rule-based scorer runs. A configured provider that fails is never hidden behind fake scores.

## How are duplicates detected?
Same email or same phone is flagged straight away. Otherwise a fuzzy name match (rapidfuzz, 90 or above) combined with a near-identical phone, one digit off, is flagged. Matches are flagged and shown, never merged or deleted, because a wrong merge loses a real person. The same person on two requisitions is two records by design (A11).

## What does the scanned-CV path do?
If a PDF has almost no extractable text, I don't guess and I don't OCR (A3). The candidate gets "Needs manual review", no score number, and stays visible and searchable so a recruiter can read the file. A fake score from empty text would be worse than no score, so the database also refuses a number on that status.

## DPDP: consent, view log and deletion design?
Consent is recorded per candidate on upload: source, time, purpose "hiring use only" (A5). Every open of a profile or CV is logged: who, what, when. On a deletion request the file, extracted text, parsed fields and scores are wiped, contacts are blanked, and a tombstone keeps only the id, date and requester (A6). The candidate disappears from every list and portal.

## The three biggest bugs found in testing, and the fixes
One: clients could read gender, date of birth and marital status inside the CV text; now hidden for clients (A20). Two: a client could shortlist the same candidate twice, creating a second decision row; now a conflict. Three: a blank value in `.env.example` crashed a fresh clone and broke Caddy, so settings now treat blank as unset (found by cloning into an empty folder, pinned by a settings test).

## What did you cut, and why?
OCR for scanned CVs: out of the time budget, so scans are flagged for a person. Drag and drop on the pipeline: a "Move to" menu is accessible and less code. Real email and SMS: mocked, as the brief allows. A candidate-facing consent link: no candidate channel was in scope. I chose a working, tested slice over a broad broken one.

## What would you build next?
OCR for scans. A candidate-facing consent and deletion link. Calibrating scores against recruiter and client outcomes, using the agreement report as the data source. Then audit export, per-client branding, and recruiter teams with scoped access. The first thing I'd measure is whether clients accept Strong candidates more often than Possible ones.

## The numbers
282 backend tests (155 of them end-to-end API tests), 32 frontend tests, 82 rendered-UI checks, 13 login-fit sizes, 36 browser end-to-end checks, a 34-check production smoke test, and 24 assumptions labelled A1 to A24. The ten rules the brief demands each have a named test, plus a permission matrix over every endpoint for five caller types.
