# DESIGN.md — FairRank design language

Reference: "Tidewell" (dark navy, streaked light bloom, frosted glass, cream accent, huge light headline). We copy its COMPOSITION and DETAIL, not just its colours. If a choice below conflicts with readability or the brief ("clean, minimal, nothing without a purpose"), readability wins.

## 1. Two surfaces, one system

| Surface | Where | Look |
|---|---|---|
| **Showcase** | Login, landing, empty hero moments | Full treatment: framed canvas, streaked gradient, light bloom, glass panels, huge light type |
| **Workspace** | Requisitions, scorecard, upload, ranked list, candidate detail, pipeline, delivery report | Calm solid navy (`--bg-ws`), NO blur, NO streaks, high contrast, dense but airy |
| **Portal (client, phone-first)** | Client shortlist, candidate view | Quiet, large tap targets, same tokens, solid surfaces, no decoration |

Rule: decoration lives only on Showcase. Workspace and Portal earn their look from type, spacing and alignment.

## 2. Tokens (single source: `frontend/src/styles/tokens.css`, mirrored in the Tailwind theme)

### Colour
```
--bg-base:        #0B1530   /* page base */
--bg-bloom:       #1E3A66   /* gradient mid */
--bg-highlight:   #2A4A7F   /* bloom core, showcase only */
--bg-ws:          #0A1429   /* page, darkest (round 2: see section 7) */
--surface-panel:  #0F1C3E   /* panels */
--surface-1:      #152550   /* cards */
--surface-2:      #1E3068   /* raised / hover */
--glass:          rgba(255,255,255,0.07)   /* showcase only */
--glass-strong:   rgba(255,255,255,0.11)
--border:         rgba(255,255,255,0.14)   /* 1px everywhere */
--border-strong:  rgba(255,255,255,0.24)

--text-1:         #F3EBDD   /* primary (cream) */
--text-2:         rgba(243,235,221,0.72)
--text-3:         rgba(243,235,221,0.62)   /* helper text, placeholders (>= 4.5:1 on all four workspace steps) */

--accent:         #F3EBDD   /* primary action colour: primary buttons */
--on-accent:      #0B1530

--ok:     #8FD3A8   --warn:  #E8C77A   --bad:  #E88F8F   --info: #9DB8E8
/* ok/warn/bad/info are for STATUS ONLY (score bands, chips). Never for decoration. */
```
Contrast: all text must be >= 4.5:1 on its background (large text 3:1). Check `--text-3` on `--surface-1` before use; if it fails, use `--text-2`.

### Type
- Family: **Inter Tight** (display and UI) via Fontsource, self-hosted. Fallback `ui-sans-serif, system-ui`. Numerals: `font-variant-numeric: tabular-nums` on every score, count and date.
- Scale (px / line-height / weight / tracking):
  - Display (showcase headline): `clamp(44px, 7vw, 112px)` / 0.95 / 300 / -0.03em
  - H1: 32 / 1.1 / 400 / -0.02em
  - H2: 22 / 1.2 / 500 / -0.01em
  - Body: 15 / 1.55 / 400
  - Small: 13 / 1.45 / 400
  - Micro (labels, chips): 11.5 / 1.3 / 500 / +0.04em uppercase
- Max 3 text sizes per screen. Evidence quotes: body size, italic OFF, left rule 2px `--border-strong`, quote text `--text-1`, source label micro.

### Space, radius, depth
- 4px base: 4 8 12 16 24 32 48 72 120. Page gutter 16 (phone) / 32 (desktop). Cards padded 16 to 24.
- Radius: frame 24, card 16, input 12, pill 999.
- Depth = border + blur (showcase) or border + surface step (workspace). No drop shadows heavier than `0 8px 30px rgba(0,0,0,0.25)` and only on floating panels (menus, dialogs).
- Motion: 150 to 220 ms ease-out. Fade/translate 4 to 8 px. Respect `prefers-reduced-motion`.

## 3. Showcase composition (login/landing) — match the reference's structure

1. Page has an outer margin (12 to 16 px) and a rounded 24px **frame** that holds everything.
2. Background inside the frame: base gradient + one radial **light bloom** (centre-left, `--bg-highlight` at ~35% to transparent) + a 1px **vertical streak** overlay at ~4% opacity (CSS repeating-linear-gradient). No images.
3. **Top bar**: product mark left; centre **pill nav** (glass, 1px border); right two small round glass buttons (theme/help placeholders must DO something or be removed, no dead buttons).
4. **Headline** bottom-left, Display size, cream, max 2 lines: "Hiring that shows its work."
5. Subcopy under it, Small size, `--text-2`, max 2 lines.
6. **Top-right glass panel** with REAL product proof: a sample candidate card = score ring (e.g. 82), role, 2 criterion rows each with a verified quote and a "Verified in CV" tag, and a hairline progress rule above it.
7. **Sign-in**: second glass card under the proof panel (email, password, cream pill button). On phone it stacks: headline, then sign-in, then proof panel.
8. **Bottom proof strip**: hairline rule (first 15% brighter, like the reference), then 5 columns of line icon + 2-line label: "Every score quotes the CV" / "Blind to name and gender" / "Nobody auto-rejected" / "Low scorers stay searchable" / "Consent and deletion logged". On phone: horizontal scroll or 2-column wrap.
9. Buttons: primary = cream filled pill with a small arrow icon; secondary = ghost text with arrow. Hover: arrow nudges 2px.

## 4. Core components (build these FIRST, as a small kit at `frontend/src/components/ui/`)

Each has loading, empty and error variants where relevant, and a story or demo route at `/dev/components`.

- **ScoreRing / ScoreBadge**: 0 to 100, tabular numerals centred, ring stroke colour by band (Strong >= 75 `--ok`, Possible 50 to 74 `--warn`, Weak < 50 `--bad`), band word beside it. Never colour alone: always the number plus the word. State "Needs manual review" (dashed ring, no number) and "Scoring failed".
- **EvidenceQuote**: quote text, criterion name (micro), tag "Verified in CV" (`--ok` dot) or "No evidence found" (`--text-3`, dashed). Click scrolls the CV text to the highlighted match.
- **CriterionRow**: criterion name, must-have/nice-to-have marker, per-criterion score bar, EvidenceQuote underneath. Collapsed shows 1 line; expand for full quote.
- **StatusChip**: pipeline stage or flag (Sourced, Screened, Submitted, Shortlisted, Interview, Offered, Joined, Duplicate, Needs review). Micro type, 1px border, small dot.
- **CandidateCard / CandidateRow**: rank number, masked-or-real name per role, current role and experience, notice period, ScoreBadge, top 2 evidence snippets, ONE clear next action button ("Open CV" first; "Submit to client" enabled only after viewed, with a tooltip explaining why when disabled).
- **GlassPanel** (showcase only), **Pill** nav, **Button** (primary, ghost, danger), **Field** (label above, 12px radius, visible focus ring in `--accent`), **EmptyState** (icon, one sentence, one action), **Skeleton**, **ErrorState** (what happened, retry), **Toast**, **Dialog**.
- **FairnessPanel** ("How we screen"): the 5 rules as a compact list with icons; used in the client portal and on the login page proof strip.

## 5. Screen rules

- **Ranked list (most important screen)**: left = rank + ScoreBadge; middle = name/role/meta + top 2 evidence snippets; right = next action. Sticky header with requisition title, counts by band, filter chips (All, Strong, Possible, Weak, Needs review, Duplicates) and search. Weak and Needs review are shown, never hidden. Row height compact but 44px+ tap targets.
- **Candidate detail**: two columns on desktop (CV text with highlighted evidence | criteria and actions), single column on phone with tabs.
- **Client portal (phone first, 375px)**: one candidate per card, masked contact, score band word (no raw AI internals), 2 evidence lines, three big buttons: Shortlist, Reject (opens reason sheet), Propose slot. Bottom-sheet dialogs, 48px targets. A visible "How we screen" link.
- **Upload**: drag area, then a per-file table with status chips (Queued, Parsing, Parsed, Needs review, Duplicate, Failed), overall progress bar, retry on failed.
- **Pipeline**: columns on desktop, stage dropdown on phone.

## 6. Quality checklist (run before calling any screen done)

- [ ] Uses only tokens; `grep` for stray hex codes finds none outside tokens.css
- [ ] Looks right at 375, 768, 1440 px; no horizontal scroll
- [ ] Loading (skeleton), empty, error states exist and were seen
- [ ] Keyboard: tab order, visible focus, Esc closes dialogs; icons-only buttons have aria-labels
- [ ] Contrast >= 4.5:1 checked for text-2 and text-3 on their surfaces
- [ ] No dead buttons; disabled buttons explain why
- [ ] Numbers use tabular figures and align in columns
- [ ] Nothing on screen without a purpose (remove decoration that carries no information)
- [ ] Playwright screenshots at 375 and 1440 saved under `docs/screens/` and compared to the reference
## 7. Round 2 additions (single source of truth: tokens in `frontend/src/styles/tokens.css`)

Owner feedback: the workspace was one flat navy, forms were dark-on-dark, login did not excite. Additions below extend sections 1 to 6; where they conflict, this section wins.

### 7.1 Depth ladder (workspace)
`page (--bg-ws #0A1429) < panel (--surface-panel #0F1C3E) < card (--surface-1 #152550) < raised (--surface-2 #1E3068)`. Each step is visibly lighter; use the next step up for anything that sits on a surface (inputs inside a card use raised; hover is raised).
- **Card treatment** (`surface-card` utility): 1px top edge `--highlight` (rgba(255,255,255,0.10)) and a vertical sheen, the top `--card-sheen` (4%) lighter than the bottom.
- **Page wash** (`page-wash` utility): a very subtle radial wash behind page headers so the page is not one flat slab.
- Contrast (checked by `scripts/contrast.py`): `--text-2` >= 6.25:1 and `--text-3` >= 5.05:1 on every step.

### 7.2 One cool interactive hue
`--signal #7FB2FF` for links, focus rings, the selected tab/nav underline and the input focus glow (>= 5.79:1 on every step). Cream (`--accent`) stays the primary action colour; do not use `--signal` for buttons.

### 7.3 Pipeline stage hues (stage chips only)
Each stage has a hue used as a 6px dot and a 12% tinted chip background with a 30% border; the label always names the stage (never colour alone), and Rejected is struck through.
| Stage | Token | Hue |
|---|---|---|
| Sourced | `--stage-sourced #94A3B8` | slate |
| Screened | `--stage-screened #7DD3FC` | sky |
| Submitted | `--stage-submitted #B4A0FF` | violet |
| Shortlisted | `--stage-shortlisted #5EEAD4` | teal |
| Interview | `--stage-interview #FBBF24` | amber |
| Offered | `--stage-offered #FB923C` | orange |
| Joined | `--stage-joined #86EFAC` | green |
| Rejected | `--stage-rejected #C48B9A` | muted rose |
Stage hues never colour text or anything but the dot, tint and border. `--ok/--warn/--bad/--info` remain for score bands and flags.

### 7.4 Score bands tint their context (ranked list)
Each row has a `--stripe` (3px) left edge in the band colour (Strong ok, Possible warn, Weak bad); Needs review rows use a dashed `--info` stripe because there is no score to colour by. The ScoreRing has a soft glow behind it in the band colour (12%, `--glow-blur` 24px).
