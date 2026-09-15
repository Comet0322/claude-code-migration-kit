---
name: migration-convert
description: >
  Conversion orchestrator skill: called by the top-level orchestrator once
  clarification and gap analysis are complete, given a manifest path. Do not
  use while migration/ prerequisites (rulebook, inventory, domain-skill
  selection) are incomplete — building the target project scaffold itself is
  this skill's own pre-flight job, not a prerequisite it waits on.
---

# Conversion Orchestrator Skill

You do exactly three things: **queue, dispatch to the right agent, record
results.** Understanding the old code, writing tests, translating code,
running and reviewing tests all belong to the three subagents
(`migration-test-writer`/`migration-translator`/`migration-test-reviewer`).
You don't read code details yourself, and you don't judge whether a
translation is correct — that's the reviewer's job.

## Calling convention

The caller always passes `migration/clarify/manifest.tsv` and states this
call's **scope**: rows where `pilot` is `yes`, or all rows. First round
(before pilot sign-off) gets pilot-only; calls after sign-off get full scope
— widening is the caller's decision, not yours. Either way, **you only
process units with `status: pending`** — `pass`/`fail-*`/`excluded` are
always skipped, so a full-scope call in practice only touches units the
pilot never covered.

## Pre-flight checks (stop if incomplete — don't fill gaps yourself)

1. Manifest exists, every row has `unit_id`/`source_path`, and
   `target_path` unless it's blank (blank is a valid row, see "Unit state"
   below). Extra columns (`pilot`/`cycle_group`/`risk_flag`/`risk_reason`/
   `manual_work`) don't affect this check.
2. Repo's root `CLAUDE.md` has a "Migration domain skill: `<name>`" line
   (written by `migration` before analysis ever ran — not
   `RULEBOOK.md`'s job). `migration/clarify/RULEBOOK.md` (frontmatter must
   have `ground_truth_tier`, `ground_truth_reason`) and
   `migration/clarify/inventory.tsv` both exist.
3. Domain skill's "template project" section lists more than one shape
   (e.g. target Python's FastAPI-service vs. ETL-batch) → `RULEBOOK.md`
   frontmatter needs `target_shape` pointing at one; missing it, stop and
   tell the human to run `migration-clarify` — don't guess. Single-shape
   domain skills don't need this field.
4. Build the target scaffold (+ `target_shape` if set — formatted `<skill>:
   <shape name>`; the part after the colon matches that skill's own
   `## Project shape: <name>` heading verbatim) — unlike the other
   checks, you actually build this one: `migration-clarify` only
   confirms/decides, it never creates files under `target/`. Pure
   mechanical execution of already-decided facts (target shape + manifest's
   `target_path` values), no judgment call, so it belongs here.
   **If the template-project section points at a concrete reference
   implementation** (a real, runnable directory it names explicitly — e.g.
   `python-template`'s `vendor/boogie-sdk-python/examples/etl_demo/` — not
   just a prose directory-tree description), **copy that directory wholesale
   into the target path(s), unmodified** — don't read its design and
   hand-write your own matching structure from memory. Copying the working
   original is what step 6 below actually verifies; a hand-rebuilt
   look-alike would just be your own untested guess at the same layout.
   Only fall back to building the structure from the section's prose
   description when it has no such reference directory to copy (this is a
   lower-confidence scaffold — say so in the final report). **Idempotent —
   never overwrite or destroy an existing scaffold**, whether a prior call
   built it or a human did by hand.
5. Domain skill declares target-side packages needed → confirm read-only
   they're installed — query only, never install. For Python, **check by
   actually importing it** (e.g. `python -c "import boogie_sdk"`), not
   `pip show`/`uv pip show`: a workspace-member or editable/path install is
   genuinely usable but `pip show` reports it as "not found" anyway — a
   false negative that looks identical to a real missing dependency. For
   other ecosystems, `test -d node_modules` or the equivalent is fine.
   Missing → stop, tell the human what to run.
   `migration-clarify` already checked this once as an early heads-up —
   re-confirm anyway, since real time may have passed.
6. **If step 4 copied a concrete reference implementation, run it once,
   completely unmodified, before touching any unit** — its own documented
   entry point and its own test command (both from the "Test / build
   method" section), exactly as shipped. This is an infra smoke test, not a
   per-unit check: it confirms the DB connection, SDK config, and
   build/runtime wiring all work in *this* environment, using code that's
   already known-good, before spending any per-unit pipeline cost on top of
   a broken foundation. Record the result to
   `migration/convert/state/_scaffold.json` (`{"status": "pass"|"fail",
   "note": "..."}`) so a later call doesn't rerun it once it's passed.
   Fails → **STOP, report the failure to the human as an environment/infra
   problem** — don't route it through `migration-test-writer`/
   `migration-translator`/`migration-test-reviewer`; those diagnose
   translated code, not the unmodified reference template, and rerunning
   them against a broken environment would misattribute an infra failure to
   a translation bug. Nothing to run (step 4 fell back to a hand-built,
   prose-only scaffold, since no reference directory existed to copy) →
   skip this, note in the report that the scaffold itself is unverified.

Any item incomplete → report what's missing, STOP, don't generate or skip
it. Only once the scaffold exists **and**, where a concrete reference was
copied, step 6 has actually passed, does the per-unit pipeline below start.

Deliberately *not* on this checklist: whether `.claude/settings.json` blocks
`git commit`/`git push`/installs. It doesn't, on purpose — a repo-wide deny
rule would also block the human's own unrelated work in that same repo (see
`.claude/skills/migration/templates/settings.README.md`). This kit relies
entirely on the rule itself, never a technical block — nothing stops you
from running these commands here; the rule holds anyway.

## Red Flags

When any of these thoughts show up, you're talking yourself into routing
around a red line — stop, follow the rule instead:

| Thought | Reality |
|---|---|
| "This is just test/setup work, it doesn't count" / "Nothing's technically stopping me" | No exception, ever — this happened: someone created `.claude/settings.json` themselves just to get a test running. There's no deny rule backing this up on purpose; the absence of a technical block was never permission. |
| "We'll need to install it eventually" / "Prerequisites are probably fine, let's just try" | Installing, and judging "probably fine" vs. "confirmed," are both the human's call — stop for anything missing on the pre-flight checklist, no matter how minor it looks. |
| "This rule gap only came up once or twice, let's apply something reasonable and keep going" | 3+ occurrences is a threshold, not room to invent a rule under it either — you never fill a rulebook gap yourself, at any count. |
| "The reviewer's verdict looks too strict, I'll use my own judgment" | Not your call — the reviewer's verdict is final, full stop. |

## Unit state

Each unit's state lives in `migration/convert/state/<unit_id>.json`:

```json
{
  "status": "pending | pass | fail-conversion | fail-test | rule-gap | excluded",
  "attempts": { "test_writer": 0, "translator": 0, "reviewer": 0 },
  "last_note": ""
}
```

**Only process units with `status: pending`** (a missing state file counts
as pending) — with two exceptions you resolve yourself before the loop, no
agents involved, by writing the state file directly:
- Blank `target_path` → `status: excluded` (private package's own
  implementation, or dropped UI layer — only calling units need
  conversion).
- `manual_work: trust-as-is` → `status: pass` (human already confirmed the
  existing file needs no verification). **Report these separately in the
  final burndown** — different confidence than a real pipeline pass.

Both are `migration-clarify`'s decisions, already made when it produced the
manifest — you're executing them, never inventing either signal yourself.

`pass`/`fail-conversion`/`fail-test`/`rule-gap`/`excluded` are all
**terminal** — skip on every future call, only count them in the burndown.
Otherwise permanently-failed units would get rerun (another round of
three-agent cost) every time you're called, even with nothing fixed.

**A human retries a terminal unit** by resetting its state file to
`status: "pending"` with `attempts` zeroed, or deleting the file. **You
never decide "this looks fixed, retry"** yourself — no reset, no retry,
ever. After a 3+ rule-gap pause specifically: the human fixes
`RULEBOOK.md`, marks it resolved in `rulebook-amendments.md`, and resets
every paused unit — you never guess which units a fix resolves.

## Model selection

Always specify a model explicitly for the three subagents — never let it
inherit yours (an unspecified model silently inherits the caller's, usually
the priciest, defeating this section).

- **test-writer / translator, first attempt**: mid-tier is enough —
  mechanical work, and the rulebook already converged the places two agents
  might diverge.
- **reviewer**: always mid-tier or above — the only quality gate, don't
  downgrade to save money.
- **Retries** (attempt ≥ 2): bump to a stronger tier — surviving one retry
  and still failing usually means this model can't see its own problem, not
  that it needs another try at the same level.
- **Integration check / parity check**: always the highest tier available —
  a single judgment call affecting the whole batch, errors here are the
  most expensive.

## Per-unit pipeline

In manifest order (no cross-unit parallelism unless the caller explicitly
asks for it), for every unit with `status: pending`:

0. **Check this unit's manifest row for `manual_work` first** (a unit
   reaching this point already isn't `trust-as-is` — that's resolved before
   the loop, see "Unit state" above): `trust-verify` → this unit **skips
   step 2 (migration-translator)** — step 3's review target is the
   **existing file** at `target_path`, not anything newly produced by an
   agent. Blank or `retranslate` → run the normal three steps.

1. **Call `migration-test-writer`**: `unit_id`, `source_path`, relevant
   inventory rows, `RULEBOOK.md` frontmatter's `ground_truth_tier`/
   `ground_truth_reason` (required — it branches its whole method on this),
   the domain skill's test-framework conventions, test/build method, and
   where the template expects test files. Returns a test file path +
   behavior-observation notes.
2. **Call `migration-translator`** (skipped per step 0): `source_path`,
   `target_path`, the rulebook, relevant inventory rows, the domain skill's
   conversion rules, and the test file path (read-only — remind it not to
   edit tests). Returns translation notes.
3. **Call `migration-test-reviewer`**: `source_path`, `target_path`, the
   test file path + behavior-observation notes, the rulebook, the domain
   skill's build/test method. Returns a structured review report.

**Every agent call, pass or fail, appends one line to
`migration/convert/cost-log.tsv`** (`timestamp, unit_id, agent, attempt,
tokens, tool_uses, duration_ms, outcome` — tab-separated, `outcome` from the
same status vocabulary, e.g. `2026-09-12T18:20:00Z	user_sync
migration-translator	1	48213	9	62000	pass`). Reruns cost the same as
first attempts and must count too, or pilot cost estimates come in low —
this is what a human uses to decide whether to scale to the full batch in
an environment with no "just buy more compute" option.

4. Dispatch by review verdict:
   - **Pass** → `status: pass`, next unit.
   - **Fail, conversion's fault**:
     - `manual_work: trust-verify` unit → **no translator rerun** (nothing
       was ever produced to fix — the manually pre-completed version
       failed review). `status: fail-conversion`, `last_note`: "manually
       pre-completed version failed review, returned to the human," no
       retry.
     - Normal unit → `attempts.translator += 1`; under the cap (default 2),
       rerun step 2 with the review report attached; at the cap,
       `status: fail-conversion`, skip, log, move on.
   - **Fail, tests' fault** → `attempts.test_writer += 1`; under the cap,
     rerun step 1 with the review report (step 2 doesn't need rerunning
     after a test rewrite, go straight to step 3); at the cap,
     `status: fail-test`, skip, log.
   - **Rule gap** → `status: rule-gap`, append one line to
     `migration/convert/deviation-log.tsv` (`timestamp/unit_id/category/
     detail`), no retry, skip.

## Rule gap recurrence threshold

After every `deviation-log.tsv` write, check whether the same `category`
has hit 3+ occurrences. If so: stop processing the rest of that category
(others keep running unaffected), write it as a pending decision to
`migration/convert/rulebook-amendments.md` (never edit `RULEBOOK.md`
directly — read-only inside the loop, amendments merge between batches),
and list the paused units explicitly in the final report.

## Integration check, once all units pass

After each call, check whether **every row in `manifest.tsv`** (not just
this call's scope) is `pass` or `excluded` — `excluded` units never produce
a `target_path` file so they never become `pass`, but shouldn't permanently
block this from triggering either. Not everything done yet → skip to "Done
when."

Once everything's `pass`/`excluded`, run once (check whether
`migration/convert/state/_integration.json` exists to know if already run;
redo if any unit resets to `pending`/failure afterward):

1. Run the domain skill's build method once across all of `target/`, not
   per-unit.
2. Run every test under `target/` once, combined (not each unit's test file
   separately) — catches "fine alone, breaks together" problems (naming
   collisions, circular imports).
3. Domain skill documents an entry point → run it once to confirm the
   assembled program works. Undocumented → skip, don't invent one.

Log usage to `cost-log.tsv` (`unit_id` = `_integration`). Write
`_integration.json`: `{"status": "pass"|"fail", "note": "..."}`. **No
auto-retry on failure** — the problem could span multiple units; list
concrete symptoms in the final report, let the human pick which unit to
send back.

## Parity check (optional — only if `RULEBOOK.md` frontmatter has `parity_check: enabled`)

A separate check, run once, after everything's already `pass`/`excluded` —
not part of the per-unit loop.

Run only if `_integration.json` has `status: pass` and
`parity_check: enabled`; otherwise record `parity_status: skipped`. Already
run (`parity_status` is `pass`/`fail`) → don't redo unless a human resets
it.

1. **Get a baseline**: `ground_truth_tier: snapshot` → use
   `migration/clarify/behavior-snapshots/`; `tier: environment` → run a few
   representative inputs against the old system live, using the invocation
   method in `ground_truth_reason`.
2. **Validate the comparison mechanism itself** (`tier: environment` only —
   `snapshot` has no live old code to mutate, skip this step):
   deliberately break a copy of the old code (flip a conditional, drop
   error handling, change output format), confirm the comparison actually
   catches it. Doesn't catch it → the mechanism's broken, stop and report,
   don't use it further.
3. Run `target/`'s entry point on the same inputs, diff against the
   baseline. No entry point → skip, say so plainly, don't invent one.
4. Merge into `_integration.json` (don't open a new file):
   `parity_status: pass|fail|skipped`, `parity_note`.
5. **No auto-retry on failure** — list the differences, let the human
   decide which unit to send back, same handling as an integration-check
   failure.

Log usage to `cost-log.tsv` (`unit_id` = `_parity`).

## Done when

Manifest finished (or paused on a rule gap) → stop, report a burndown:
totals / `pass` / `fail-conversion` / `fail-test` / `rule-gap` / `excluded`,
plus `_scaffold.json`'s result (whether the scaffold came from a copied
reference and, if so, whether its unmodified smoke run passed — or that the
scaffold is unverified prose-only if there was nothing to copy), the
integration-check result (if it ran) and `parity_status` (if it ran), plus
the list of pending rulebook-amendment items. List `excluded` as
its own line, never folded into failure counts, never omitted — it's not a
failure, it's "this unit never needed conversion." Within `pass`, break out
`manual_work: trust-as-is` units as their own line too — different
confidence than a real pipeline pass.

Attach `cost-log.tsv`'s totals (total tokens, total time, subtotals per
agent role) — what the human uses to estimate full-batch cost from pilot
cost. Remind explicitly that terminal-state units need their status reset
to `pending` to retry — don't assume the human remembers. **Never decide
yourself whether to scale the pilot to the full batch, or move to the next
stage** — that's the caller's call after reading this report.
