---
name: migration
description: >
  Top-level orchestrator skill for the migration pipeline. For migrating a
  batch of similar legacy applications to a new language using pre-packaged
  domain knowledge (domain-* skills). Use when the user wants to
  migrate/port/rewrite a legacy application to a new language using the
  pre-packaged domain knowledge (domain-* skills).
---

# Migration Orchestrator

You do exactly one thing: **look at what's in `migration/` right now and decide
who to call next.** Never analyze, decide, or translate yourself — that's
migration-analyze / migration-clarify / migration-convert's job. After each
sub-skill call, respect its own gate rules on whether to stop.

## Before you start (one-time human repo setup)

Copy `.claude/skills/migration/templates/settings.json` into the repo's
`.claude/settings.json` **and** copy
`.claude/skills/migration/templates/hooks/` into the repo's `.claude/hooks/`
(the settings.json's `SubagentStop` hook entry points at that path — a
cheap `mvn compile`/`ruff check` gate that runs right before
`migration-translator`/`migration-test-writer` hands its result back) — or
merge the `hooks` content into an existing settings.json — see
`.claude/skills/migration/templates/settings.README.md` for details. Not a
hard prerequisite (nothing checks for it and stops if it's missing — the
hook is a bonus, not a red line), but do it while the human is signing off
the rulebook after `migration-clarify`, before `migration-convert` starts,
so the check is in place from the first pilot unit rather than partway
through.

Git commit/push and target-side package installs are **never** something
any agent in this pipeline does on its own — that's enforced entirely at
the prompt level (each subagent's own instructions, plus
`migration-convert`'s Red Flags table), not by a `.claude/settings.json`
deny rule. An earlier version of this kit used a blanket
`permissions.deny` for this, but a repo-wide deny also blocks anything else
in that repo the human asks Claude to do — including totally unrelated
commit/install requests, indefinitely, until someone remembers to remove
it — which caused more confusion than it prevented. See
`.claude/skills/migration/templates/settings.README.md` for the full
reasoning.

## Keep `migration/CLAUDE.md` current

First call on this repo (`migration/CLAUDE.md` doesn't exist yet): create it
from `.claude/skills/migration/templates/CLAUDE.md`. It's a human-readable
resume/orientation summary, not a source of truth — every routing decision
in this skill still comes from reading the real files, never from this
summary. Also check the repo's root `CLAUDE.md`: if missing, create one with
just a pointer line ("An in-progress migration lives in `migration/` — see
`migration/CLAUDE.md`."); if it already exists for unrelated reasons, append
that same pointer line if it isn't already there — **never overwrite an
existing root `CLAUDE.md`**, that file may already serve this repo's own
purposes.

Refresh `migration/CLAUDE.md`'s Status/Decisions/Open-items sections (never
touch the "Human notes" section — that's the human's, not yours) right
before every STOP point below, using whatever you already read to make the
routing decision — this is a summary of information you already gathered,
not a reason to re-read anything extra.

## Scope

Ends at "conversion done, every unit's tests pass, plus one lightweight
integration build/run check" (integration-check details live in
`migration-convert`, auto-triggered once all units pass). **Excludes** the
original kit's standalone global build phase (error queue, dedicated fixer
agents, rerun to clean) and its Step 6 behavior-matching machinery (inherited
test-suite burndown / parity referee) — both are heavy machinery for
large-scale batches; a deliberate opt-in extension if a human wants it, never
assume it's already included.

## Routing

1. **`migration/analysis/depmap/order.txt` or
   `migration/analysis/ANALYSIS.md` doesn't exist**: call `migration-analyze`
   (rerunning it is safe/idempotent even if the depmap files already exist —
   it won't redo the script, just resume from wherever it left off). Read-only
   and rerunnable — proceed to step 2 without waiting for sign-off, unless it
   flags unusual cycle complexity itself. (Check both files, not
   `migration/analysis/units.tsv` — `units.tsv` gets renamed and moved to
   `migration/clarify/manifest.tsv` once `migration-clarify` fills in
   `target_path`, so it stops existing after that step, and can also briefly
   not exist yet mid-`migration-analyze` now that its risk assessment is
   split across parallel `migration-risk-scanner` subagents: the depmap
   script's output can land before those subagent calls finish. `order.txt`
   and `ANALYSIS.md` are the two artifacts nothing downstream ever renames,
   consumes, or produces earlier than the other — checking both is what
   makes "has analysis fully finished" unambiguous.)

2. **Analysis artifacts complete, but `migration/clarify/RULEBOOK.md` (or its
   frontmatter is missing `domain_skill`/`ground_truth_tier`/
   `ground_truth_reason`) or `migration/clarify/manifest.tsv` is missing**:
   call `migration-clarify`. It always stops at the end — **STOP, wait for
   human confirmation**, don't decide "looks fine" and continue to step 3
   yourself.

3. **`migration/clarify/manifest.tsv` has rows marked `pilot=yes`, but
   `migration/convert/pilot-signoff.txt` doesn't exist**: call
   `migration-convert` with `migration/clarify/manifest.tsv`, telling it to
   **process only `pilot=yes` rows**. Present its burndown report, **STOP,
   human reviews it**. Only the human (or you, with their explicit
   agreement) writes `migration/convert/pilot-signoff.txt` as the sign-off
   marker — **even if the pilot is 100% clean with zero rule-gaps, never
   write this file yourself to skip confirmation**: a clean pilot isn't the
   same as human sign-off.

4. **Pilot signed off, `migration/clarify/manifest.tsv` still has units not
   `pass`/`excluded`**: call `migration-convert` with
   `migration/clarify/manifest.tsv`, telling it to **process all rows (not
   limited to `pilot`)**. Pilot units are already `pass` and get skipped
   automatically; `excluded` units (private-package implementations
   replaced by target-side library) never needed conversion and get skipped
   too. Present the final burndown, STOP.

5. **manifest all `pass`/`excluded`, but
   `migration/convert/state/_integration.json` doesn't exist or `status`
   isn't `pass`**: call `migration-convert` again (full manifest) — it
   detects every unit is done and triggers the one-time integration
   build/run check. A failed check doesn't count as "done" — STOP, list the
   symptoms for the human to decide which unit to send back.

6. **Integration check `pass`, `RULEBOOK.md` frontmatter has
   `parity_check: enabled`, but `_integration.json`'s `parity_status` is
   missing or not `pass`/`skipped`**: call `migration-convert`, telling it
   the task this time is "parity check" (not the manifest-scanning loop).
   `parity_status: fail` → STOP, list symptoms for the human to decide which
   unit to send back; `pass` → proceed to step 7. No `parity_check:
   enabled` → treat `parity_status` as `skipped` without actually calling
   this step, proceed to step 7.

7. **manifest all `pass`/`excluded`, integration check `pass`, and
   `parity_status` is `pass` or `skipped`**: report done. If
   `migration/convert/rulebook-amendments.md` still has open items, list
   them for the human — those are logged rule gaps, not auto-applied.

## Batch usage

The same batch of legacy apps is usually many separate repos/checkouts, not
multiple instances crammed into one repo. Rerunning this skill for the next
instance starts fresh at step 1 with a brand-new `migration/` directory —
only the domain-skill selection in `migration-clarify` tends to confirm fast
since the fingerprint match usually guesses right, not a from-scratch
decision each time.

## What not to do

- Don't do a step yourself just because it "looks simple" — call the right
  sub-skill instead.
- Don't judge "probably fine" and continue past a STOP point — every gate
  exists because errors here are the most expensive; stopping buys certainty.
