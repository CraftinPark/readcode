# Messy code: where should Tier 1 problems' code come from?

*Experiment, 2026-10-27, branch danny-v0. Tier 1 = practice without AI; we want code that reads like a real person wrote it: bad names, stale comments, half-finished error handling, bugs nobody noticed.*

## The question

Can we produce realistic "human" code cheaply, or do we have to collect it? Four sources, two samples each, judged blind.

| Source | How | Where |
|---|---|---|
| **Real low-star repos** | Small MIT-licensed Flask booking apps last pushed **before ChatGPT (Nov 2022)**, so a person wrote them. Found with GitHub search `language:python license:mit stars:0..8 pushed:2017-01-01..2022-10-31`. | `raw/real/` (licenses alongside) |
| **Contest wrong answers** | Real incorrect Python submissions to Codeforces from DeepMind's CodeContests dataset (CC BY 4.0), fetched a few rows at a time. A different domain (algorithm puzzles), included as a human-written control. | `raw/contest/` |
| **AI guided by real novice mistakes** | One prompt per model: "write this as a 2019 second-year student would", with a catalogue of real novice mistakes from the literature (KASER, EDM 2026). Sonnet and Haiku. | `raw/guided/` |
| **Old-way vibe coding** | Danny's idea: a student builds the app through six chat messages, each answered by a **fresh** model that never sees the whole file; only what the student pastes. `tools/vibe_assemble.py` pastes each answer in mechanically (whole new app replaces the file, same-named functions are replaced, new ones appended, missing imports added; nothing cleaned up). Sonnet and Haiku chains. | `raw/vibe-*/step1..6.md`, `raw/vibe-*/app.py` |

The six student messages: (1) Flask app with register/login on SQLite; (2) add booking (pastes only `init_db`); (3) "no such table: bookings, don't want to lose users"; (4) add a cancel page by booking id; (5) a table of busy rooms per hour; (6) pastes the real error the assembled file produced (Sonnet: a SyntaxError; Haiku: `no such column: status`).

## Run the blind test

1. Open `blind/sample-A.py` ... `sample-H.py` (don't open the key).
2. For each sample write down: **(a)** human or AI, **(b)** which source (real repo / contest / AI-guided / vibe-coded), **(c)** how real it feels, 1-5, **(d)** what gave it away.
3. Then open `KEY-dont-open-before-guessing.md`.

**Known giveaways to discount:** length (contest samples are 25-171 lines, vibe-coded ones 335-385) and domain (contest samples aren't booking apps). The interesting comparison is real repo vs AI-guided vs vibe-coded, all the same booking app.

## What we already see (before anyone guesses)

- **Modern models answer like good teachers.** Every step-1 reply was clean and secure (hashed passwords, `?` placeholders, open-redirect checks). Even in fragments, both models put an ownership check on "cancel by booking id". So the mess does not come from bad answers.
- **Fragmented context does create real mess,** the kind that builds up in real codebases:
  - both files create `app = Flask(__name__)` twice, because partial answers re-declared it; routes registered before the second one belong to a discarded app and would 404;
  - Haiku's cancel code uses a `status` column its own schema never created (schema drift between chats);
  - Haiku answered "add booking" with helper functions but no booking page; its occupancy page arrived as a new `index()`, which replaced the student's home page;
  - Sonnet labelled a bare SQL statement and an HTML template as `python`.
- **AI-guided mess is plausible but tidy.** It does exactly the listed mistakes ("TODO: check overlap", a comment "only the owner can cancel" with no check, `current_user.id != 1` as admin). Real code has stranger, unlisted things: `print("idhar")` ("here" in Hindi), `[False]*14` for a 10-hour day, a query with a hard-coded `roomID = 1` whose result is never used, routes copied from a tutorial that reference a `Post` model this app never defines.

## Honest notes on method

- Manual steps on the vibe-coded files, all recorded here: skipped blocks the model itself said were HTML templates to save elsewhere; deleted top-level SQL the step-6 answer told the student to move into `init_db`; un-escaped triple quotes that came from our own prompt's escaping, not the model.
- An early version of the assembler swept prose into the file (a closing fence was read as an opening one); fixed before these results.
- Claude 3 Haiku was retired in April 2026, so "use an old model" isn't really available; the models here are today's Sonnet and Haiku.
- Two samples per source is a pilot: enough to see whether people can tell, not to measure how well.
