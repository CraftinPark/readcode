# Prompt: mine fixed bugs from a repository

Paste everything below the line into a fresh agent session (one with shell and
GitHub access, ideally an authenticated `gh`). Fill in the three values at the top.

---

You are mining **real, already-fixed bugs** from one open-source repository, to
turn the best of them into code-reading exercises. The exercises will recreate
each bug's *mechanism* in different code, so what matters most is understanding
**why** each bug happened, not the project's specifics.

**Repository:** `OWNER/REPO`
**Focus (optional):** e.g. payments, orders, webhooks, permissions, scheduling, caching
**Target:** 15 accepted bugs (look at roughly 60 candidates)

## 1. Find candidates

- Closed issues labelled as bugs that have a **merged** fix PR:
  `gh search issues --repo OWNER/REPO --state closed --label bug --json number,title,closedAt --limit 200`
  then for each, the linked PR (issue timeline or "Fixes #N" in PR bodies).
- Also merged PRs whose title starts with "fix" and that reference an issue.
- Prefer the last 3-4 years. Skip anything still open or reverted.

## 2. Keep only bugs that pass every filter

- The fix changes **at most ~30 lines of non-test code, in at most 3 files**.
- The issue describes a **symptom a user or operator saw** (wrong number, wrong state,
  missing event, wrong access), not just "refactor" or "error in logs".
- The cause is **logic**: state, money, time, ordering, retries, idempotency,
  permissions, caching, counters, pagination, units, defaults.
- Not: dependency bumps, typos, docs, pure UI styling, performance-only, flaky tests,
  build/CI, or framework upgrade breakage.
- Not famous: skip bugs with a CVE, a blog post, a conference talk or a named
  postmortem. If a quick web search for the symptom finds this exact bug, skip it.
- The repository's license is permissive (MIT, BSD, Apache-2.0). Record it.

## 3. Understand each kept bug (read the code, don't guess)

For each one, read the issue thread, the full PR diff, and any test the PR added.
Open the files at the **PR's base commit** (the buggy version) and answer:

1. **Symptom:** what someone actually saw, in their words.
2. **Root cause:** one sentence. Two bugs are "the same pattern" only if this one
   sentence explains both.
3. **Trigger:** the exact conditions needed (an ordering of events, a time/date,
   a retry, a specific amount, a cancellation path...).
4. **Distance:** how far the cause is from the symptom (same function / same file /
   another file / another service).
5. **Why it's easy to miss:** what makes the buggy line look correct.
6. **The fix:** one line, plus whether the PR's fix is the only reasonable one.

## 4. Rate it

- **Elusiveness (1-5):** given only the symptom and the code, how long would a strong
  engineer take? 1 = obvious from reading the function; 5 = needs reproducing,
  plus knowledge of outside behaviour (time zones, provider event order, isolation levels).
- **Distillable (yes/no):** can the mechanism be rebuilt in under ~60 lines without
  this project's framework, and still fail a test?
- **Reproduction needs:** what a playground would need to show it (clock control,
  event ordering, fault injection, concurrency, two accounts, a background job).

## 5. Output

Write two files.

**`bugs.jsonl`**: one JSON object per **accepted** bug:

```json
{
  "repo": "OWNER/REPO",
  "license": "BSD-3-Clause",
  "issue": 1234,
  "pr": 1240,
  "base_commit": "<PR base sha>",
  "merge_commit": "<merge sha>",
  "title": "short, in your own words",
  "symptom": "what the user saw",
  "root_cause": "one sentence",
  "trigger": "exact conditions",
  "distance": "same function | same file | other file | other service",
  "why_missed": "what makes the buggy code look right",
  "fix_summary": "one line",
  "fix_unique": true,
  "skills": ["idempotency"],
  "pattern": "domain-free name, e.g. 'default-off flag drops records from a total'",
  "elusiveness": 4,
  "distillable": true,
  "reproduction_needs": ["event ordering"],
  "files": [{"path": "src/x.py", "ranges": [[120, 180]]}],
  "buggy": "exact text from the base commit that the fix replaced",
  "fixed": "exact replacement text from the merge commit",
  "regression_test": "path::name of the test the PR added, or null",
  "notes": "anything uncertain, marked as such"
}
```

`skills` must come from this list only: `idempotency`, `tenant-isolation`,
`pagination`, `money-invariants`, `state-machine`, `retries-timeouts`,
`race-condition`, `caching`, `input-validation`, `backward-compat`,
`memory-safety`, `resource-management`, `integer-arithmetic`.

**`report.md`**:
- a table of accepted bugs: title, pattern, skills, elusiveness, distance;
- **clusters:** groups of bugs that share one root-cause sentence (these are the
  most valuable; say so if a cluster also matches a pattern you know from
  other projects);
- **rejected candidates:** one line each with the filter they failed;
- the 3 bugs you would turn into exercises first, and why.

## Rules

- Never invent line numbers, commits or file contents. Copy `buggy` and `fixed`
  exactly from the fetched files; if you could not fetch something, say so.
- Mark anything you are not sure about as unverified in `notes`.
- Quote only what the exercise needs (the changed lines and their function), not
  whole files; keep the license and attribution with every entry.
- Only already-public, already-fixed issues. Do not open issues, comment, or
  contact maintainers.
