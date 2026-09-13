---
name: migration-convert
description: >
  Conversion orchestrator skill: called by the top-level orchestrator once
  clarification and gap analysis are complete, given a manifest path. Do not
  use while migration/ prerequisites (rulebook, inventory, domain-skill
  selection, target project scaffold) are incomplete.
---

# Conversion Orchestrator Skill

You do exactly three things: **queue, dispatch to the right agent, record
results.** Understanding the old code, writing tests, translating code,
running and reviewing tests — all of that belongs to the three subagents
(`migration-test-writer` / `migration-translator` / `migration-test-reviewer`).
You don't read code details yourself, and you don't judge whether a
translation is correct — that's the reviewer's job.

## Calling convention

The caller (top-level orchestrator or a human) always passes
`migration/manifest.tsv`, and clearly states this call's **scope**: **only
rows where `pilot` is `yes`**, or **all rows** (`pilot` unrestricted). The
first round (before pilot sign-off) gets the pilot-only scope; calls after
sign-off get the full scope. **Either way, you only process units with
`status: pending`** — anything already `pass`/`fail-*`/`excluded` is always
skipped, so a "full scope" call in practice only touches units the pilot
never covered, it won't redo units already `pass`. Whether to widen from
pilot to full scope is the caller's sign-off decision, not your logic.

## Pre-flight checks (stop if incomplete — don't fill gaps yourself)

1. Manifest file exists, and every row has `unit_id` / `source_path` /
   `target_path` (`pilot`/`cycle_group`/`risk_flag`/`risk_reason` are
   leftovers from the analysis/clarification stages — extra columns don't
   affect this check).
2. `migration/RULEBOOK.md` (frontmatter must have `domain_skill`,
   `ground_truth_tier`, `ground_truth_reason`) and `migration/inventory.tsv`
   both exist.
3. If the selected domain skill's "template project" section lists more than
   one shape option (e.g. target Python has both a FastAPI-service and an
   ETL-batch template skill), `migration/RULEBOOK.md` frontmatter must have a
   `target_shape` field pointing at one — this decides which template
   knowledge to feed the three subagents. A domain skill with only one shape
   (no divergence) doesn't need this field. Missing it → stop, tell the
   human to run `migration-clarify` to decide, don't guess a shape yourself.
4. The domain skill's described template-project scaffold already exists at
   the target paths (you're not responsible for generating the scaffold).
5. If the domain skill declares target-side packages are needed (see the
   template-project section), confirm read-only they're already installed
   (e.g. `test -d node_modules`, `pip show <pkg>`) — **query only, never
   install**. Not installed → stop and tell the human what to install first
   — don't run the install command yourself (same red line as item 6, just
   checking a different thing).
6. `.claude/settings.json` already has deny rules for `git commit` / `git
   push` and package-install commands (`brew install`/`pip install`/`npm
   install`, etc). **Not there → stop, tell the human what rules to add
   (point them at `.claude/skills/migration/templates/settings.json` +
   `.claude/skills/migration/templates/settings.README.md`), don't edit
   settings.json yourself** — this red line can't be routed around for
   convenience. Even if the Claude Code platform's own self-modification
   guard happens to block your edit attempt, that's not license to try
   another way (e.g. writing the file indirectly via a script) — the only
   correct next step is to stop and let the human edit it, or run the
   blocked command themselves.

Any item incomplete → report what's missing, STOP, don't try to generate it
or skip it.

## Red Flags

When any of these thoughts show up, you're talking yourself into routing
around a red line — stop, follow the rule instead:

| Thought | Reality |
|---|---|
| "This is just test/setup work, it doesn't really count as routing around it" | No "this time is just a test so it doesn't count" exception — this exact rule exists because it really happened: someone created `.claude/settings.json` themselves just to get a test running. Never install packages, never edit `settings.json`, in any situation. |
| "It's blocked, so I'll just route around it another way (a script, writing the file indirectly)" | A deny block is the design working, not a puzzle to solve around it — even the platform's own self-modification guard blocking an edit attempt isn't license to route around it; the correct response is always to stop and let the human decide, not find another path. |
| "We'll need to install it eventually, might as well now" | Deciding what to install and when is the human's call, not an efficiency question — you're saving yourself trouble, not making a decision that's yours to make. |
| "The prerequisites are probably fine, let's just try running it" | Stop for whatever's missing on the pre-flight checklist regardless — "probably fine" doesn't substitute for "confirmed." |
| "This unit looks like it's already fixed by a recent rule change, let's retry" | Without a human explicitly resetting the status to `pending`, this unit stays failed forever — it never retries itself. |
| "The domain skill didn't document an entry point, let's just pick some file and try running it" | No documented entry point → skip the "run the entry point" step in the integration check, don't invent one. |
| "This rule gap only came up once or twice, let's just apply a rule that looks reasonable and keep going" | Pausing at 3+ occurrences is a threshold, not room for "apply something efficient first" — under 3 in the same category, keep running, but that never means you get to invent a rule on your own to fill a gap the domain skill/rulebook didn't cover. |
| "The reviewer's verdict looks too strict/unreasonable, I'll use my own judgment" | You don't judge whether a translation is correct — the reviewer's verdict is final, accept it fully, don't second-guess it. |

## Unit state

Each unit's state lives in `migration/state/<unit_id>.json`:

```json
{
  "status": "pending | pass | fail-conversion | fail-test | rule-gap | excluded",
  "attempts": { "test_writer": 0, "translator": 0, "reviewer": 0 },
  "last_note": ""
}
```

**Only process units with `status: pending` (a missing state file also
counts as `pending`).** `pass`, `fail-conversion`, `fail-test`, `rule-gap`,
`excluded` are all **terminal states** — skip them, never rerun, only count
them in the final burndown. This is deliberate: otherwise every time you're
called again, permanently-failed units would get rerun (spending another
round of three-agent cost) even though the human hasn't fixed anything.

`excluded` is the only terminal state **not produced by you** — `migration-clarify`
writes it directly while completing the manifest (this unit is the private
package's own implementation, already replaced by a target-side library;
only the units calling it need conversion). You don't decide which units
should be `excluded`, and you never mark one yourself — treat it like any
other terminal state and skip it.

**For a human to retry a terminal-state unit**, they explicitly reset its
state file to `status: "pending"` with `attempts` zeroed (a fresh full retry
budget under the fixed rules), or just delete that unit's state file
(equivalent to `pending`). **You never decide "this looks fixed, let's
retry"** yourself — without an explicit human reset to `pending`, a unit
stays failed forever in the burndown, waiting on the human. This especially
applies after a "3+ rule-gap occurrences" pause: once the human fixes
`RULEBOOK.md`, they need to mark that item resolved in
`rulebook-amendments.md` and reset every unit paused by it back to
`pending` before you'll reprocess them on the next call — you never
cross-reference "which units does this fix resolve" yourself, that's the
human's job.

## Model selection

Always specify a model explicitly when calling the three subagents — never
let it inherit your own model (an unspecified model silently inherits the
caller's, usually the most expensive one, defeating this section entirely).

- **test-writer / translator, first attempt**: a mid-tier model is enough —
  both steps are mechanical work ("translate per rulebook/domain-skill
  rules"), and the rulebook has already converged the places where two
  agents might choose differently, so the strongest model isn't needed.
- **reviewer**: always mid-tier or above — it's the only quality gate,
  judgment matters more than cost here, don't downgrade to save money.
- **Retries (`attempts.translator` or `attempts.test_writer` ≥ 1, i.e. the
  2nd+ attempt)**: bump to a stronger tier, don't hit the same tier against
  it twice — surviving one retry and still failing usually means this model
  can't see its own problem this round; a stronger model beats giving the
  same one another try.
- **Integration check and parity check** (see the two sections below):
  always use the highest-tier model available — both make a single judgment
  affecting the whole batch or all units, and errors here are the most
  expensive.

## Per-unit pipeline

In manifest order (no cross-unit parallelism unless the caller explicitly
asks for it), for every unit with `status: pending`:

0. **Check this unit's `last_note` first**: if `migration-clarify`'s
   "identify units with pre-existing manual work" section marked it
   "manually pre-completed, pending verification, skip conversion step,"
   this unit **skips step 2 (migration-translator)** — step 3's review target
   is the **existing file** at `target_path`, not anything newly produced by
   an agent. No such marker → run the normal three steps.

1. **Call `migration-test-writer`**, giving it `unit_id`, `source_path`, the
   relevant inventory rows, and the domain skill's test-framework
   conventions. Get back a test file path plus behavior-observation notes.
2. **Call `migration-translator`** (skipped for units flagged in step 0),
   giving it `source_path`, `target_path`, the rulebook, relevant inventory
   rows, the domain skill's conversion rules, and the test file path
   (read-only, remind it not to edit the tests). Get back translation notes.
3. **Call `migration-test-reviewer`**, giving it `source_path`,
   `target_path`, the test file path plus behavior-observation notes, the
   rulebook, and the domain skill's build/test method. Get back a
   structured review report.

**Every time you call any of the above agents, whether it passed or needs a
rerun, append its usage stats as one line to `migration/cost-log.tsv`**
(columns: `timestamp, unit_id, agent, attempt, tokens, tool_uses,
duration_ms, outcome`, e.g.:
`2026-09-12T18:20:00Z	user_sync	migration-translator	1	48213	9	62000	pass`
— tab-separated, all eight columns filled, `outcome` matching the unit-state
vocabulary — `pass`/`fail-conversion`/`fail-test`/`rule-gap` — don't invent
other terms). This isn't just for successes — reruns cost the same
resources and need to count toward the budget, or "how much did this pilot
actually cost" gets underestimated. This log is for human capacity
planning (air-gapped, fixed-compute environments have no "just buy more
compute" option — whether to scale a pilot to the full batch relies on this
number, not a feeling).

4. Dispatch by review verdict:
   - **Pass** → status `pass`, move to the next unit.
   - **Fail, blamed on conversion**:
     - A unit flagged "skip conversion step" **can't have
       migration-translator rerun** — no agent ever produced anything to fix,
       meaning the manually pre-completed version failed review. Status goes
       straight to `fail-conversion`, `last_note` becomes "manually
       pre-completed version failed review, returned to the human to decide
       whether to hand it to the kit for a fresh translation," no retry,
       leave it for the human to decide in the final report.
     - Normal units → `attempts.translator += 1`; under the retry cap
       (default 2) rerun step 2 with the review report attached; at the cap,
       status `fail-conversion`, skip this unit, log it, move on (don't
       block the queue).
   - **Fail, blamed on tests** → `attempts.test_writer += 1`; under the cap,
     rerun step 1 with the review report attached (after the test rewrite,
     step 2's conversion doesn't need rerunning, go straight back to step 3
     for re-review); at the cap, status `fail-test`, skip, log.
   - **Review reports "rule gap"** → status `rule-gap`, append one line to
     `migration/deviation-log.tsv` (`timestamp / unit_id / category /
     detail`), no retry, skip this unit.

## Rule gap recurrence threshold: pause, don't keep force-translating

After every write to `deviation-log.tsv`, check whether the same `category`
has now hit 3+ occurrences. If so:

- **Stop processing the rest of the manifest's units in that same
  category** (other categories keep running unaffected).
- Write this category, with its known cases, as a pending human decision
  appended to `migration/rulebook-amendments.md` (**never edit `RULEBOOK.md`
  directly** — the rulebook is read-only inside the loop; amendments are
  merged by the human between batches).
- List explicitly in the final report which units paused due to rule gaps.

## Integration check, once all units pass

After each call's scope finishes (whether pilot-only or all rows), check
whether every single row in `migration/manifest.tsv` (**not just this
call's scope**) is already `pass` or `excluded` — `excluded` units have no
target file and never become `pass`, so their non-`pass` state must never
permanently block the integration check from triggering. Skip this section
and go straight to "done when" if not everything is `pass`/`excluded` yet.

Only once everything is `pass`/`excluded`, and only once (use whether
`migration/state/_integration.json` exists to know if it's already run;
redo this section if any unit's state gets reset to `pending` or a failure
state afterward):

Call `migration-test-reviewer` once more, but this time its review scope
shifts from "one unit" to "the whole `target/` project":

1. Run the domain skill's build method once across **everything** under
   `target/`, not unit by unit.
2. Run **every** test under `target/` once, as one combined test run (not
   each unit's test file separately) — this catches "fine alone, breaks once
   combined" problems (e.g. naming collisions between two units, circular
   imports that only blow up once integrated).
3. If the domain skill's "template project" section describes how to run the
   entry point, run it once to confirm the assembled program actually
   works — not just each file passing its own tests. Skip this item if
   undescribed (or explicitly says there's no entry point) — don't invent
   one.

Append this call's usage stats to `migration/cost-log.tsv` too (`unit_id`
column = `_integration`).

Write `migration/state/_integration.json`: `{"status": "pass"|"fail", "note":
"..."}`. **A failure doesn't auto-retry** — the problem could span multiple
units, unlike a single unit's failure where the responsible agent is clear;
list concrete symptoms in the final report and let the human decide which
unit to send back.

This section's scope corresponds to the original code-migration-kit's Step 4
(compile) + Step 5 (run it), replaced here with a one-time check instead of
that kit's full error-queue-plus-dedicated-fixer machinery — this batch size
doesn't need that much weight.

## Parity check (optional, only if `RULEBOOK.md` frontmatter has `parity_check: enabled`)

The caller's stated task this time is "parity check" — not the
manifest-scanning loop, a separate check run once against a batch that's
already all `pass`/`excluded`.

Only run this if the integration check's
`migration/state/_integration.json` has `status: pass`, and `RULEBOOK.md`
frontmatter has `parity_check: enabled` — otherwise just record
`parity_status` as `skipped`. Already done (`_integration.json`'s
`parity_status` is already `pass` or `fail`) → don't redo it, unless a human
resets it to unset.

1. **Get the input/output baseline for comparison**: `ground_truth_tier:
   snapshot` → use existing cases under `migration/behavior-snapshots/`;
   `tier: environment` → use the invocation method recorded in `RULEBOOK.md`
   frontmatter's `ground_truth_reason`, run a few representative inputs
   against the old system live, and record the outputs as the baseline.
2. **Validate the comparison mechanism itself — this step can't be
   skipped**: only possible with `tier: environment` — deliberately mutate a
   few behaviors in a copy of the old code (flip a conditional, drop an
   error-handling block, change an output format), confirm the comparison
   mechanism actually catches the difference; if it doesn't, the mechanism
   itself is broken — stop and report, don't use it further. `tier:
   snapshot` has no live old code to mutate, skip this step — the snapshot
   itself is real data the human provided; its trustworthiness is on the
   human who supplied it, not something to validate here.
3. Run the new system (`target/`'s entry point) on the same inputs,
   mechanically diff the output against the baseline — no documented entry
   point → skip this section and say plainly in the report "no entry point,
   parity check not possible," don't invent one.
4. Merge the result into `migration/state/_integration.json` (don't open a
   new file), adding two fields: `parity_status: pass|fail|skipped`,
   `parity_note`.
5. **A failure doesn't auto-retry** — list the differences and let the human
   decide which unit to send back, same handling as an integration-check
   failure.

Append this call's usage stats to `migration/cost-log.tsv` too (`unit_id`
column = `_parity`).

This section's scope corresponds to the original code-migration-kit's Step 6
(match behavior), minus its existing-test census (our source batches never
have existing tests to inherit as a referee) and minus the `06-post-parity`
marker-burndown machinery. It's optional because for many batches the
one-time integration check above is already enough, and this section's cost
(needing to rerun the old system, plus validating the comparison mechanism
itself) is clearly higher — worth doing is the human's cost/value call when
deciding `parity_check` in `migration-clarify`.

## Done when

Manifest finished (or paused on a rule gap) → stop, report a burndown:
totals / pass / fail-conversion / fail-test / rule-gap / excluded, plus the
integration-check result (if it ran) and `parity_status` (`pass`/`fail`/
`skipped`, if it ran), plus the list of pending rulebook-amendment items.
List `excluded` as its own line, never folded into failure counts, and never
omitted — it's not a failure, it's "this unit never needed conversion,"
and the human needs to see it was explicitly accounted for, not lost.
Attach `migration/cost-log.tsv`'s totals too (total tokens, total time,
subtotals per agent role) — this is what the human uses to decide "given
what this pilot cost, roughly how much would the full batch cost." Remind
explicitly that terminal-state units need their status reset to `pending`
to retry — don't assume the human remembers. **Never decide yourself
whether to scale the pilot to the full batch, or move to the next stage** —
that's the caller's call after reading this report.
