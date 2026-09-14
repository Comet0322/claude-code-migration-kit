---
name: migration-clarify
description: >
  Clarification and gap-analysis skill: called by the top-level orchestrator
  once migration/analysis/ artifacts are complete but the rulebook or
  manifest is still missing. Always stops at the end for human sign-off —
  never auto-proceeds to conversion.
---

# Clarification and Gap Analysis Skill

The heaviest human-collaboration step in the pipeline — mistakes here are
the most expensive. Show your reasoning after every section instead of
deciding silently.

## Decision points

Sections marked **[decision point]** share one shape: gather evidence,
compute a recommendation, ask the human once via `AskUserQuestion`
(recommendation + reasoning up front, never a bare option list), then
record the answer and reasoning at the named target — never a silent
default. Each section below states only its **evidence**, **options**, and
**record target**; the ask/record mechanics aren't repeated.

## 1. Load domain skill content

`migration` already decided `domain_skill` before calling you — read it
from the repo's root `CLAUDE.md` (line "Migration domain skill: `<name>`"),
don't re-decide it, and don't ask the human again. Missing? Stop and tell
the human to rerun `migration` first — you never pick a domain skill
yourself, and you never invent one.

Load: private package documentation, UI/scope conventions (if written),
template project, syntax-conversion/library-replacement rules,
target-language library docs, test/build method. Feeds every later section
and all three conversion-stage subagents.

`domain_skill` may itself be a `*-template` skill used directly (`migration`
offers this when no domain-* skill matched) — a template skill only has
template project/library docs/test-build method, never private package
documentation, app types, or UI/scope conventions. Treat every section this
domain skill doesn't have the same as "written but empty": every later
section already has a fallback for that (section 4 treats an empty seed
rules table as "everything's a gap, ask"; the UI decision point asks
plainly with no recommendation; the private-package check no-ops with
nothing to match against). Don't treat a missing section as an error.

- A section says "same as skill `<name>`" (bare skill name) → load that
  skill's content with the Skill tool; it's independently-maintained
  target-side shared knowledge, not something this domain skill forgot to
  fill in. Treat it as inline from here on.
- A section gives a relative path instead (has a `/`, usually `.md`) →
  content moved to a reference file in that domain skill's own folder
  (oversized content, see `domain-template`) — Read it directly, don't
  load it as a skill. Treat it the same way once read.

## 2. Gap inventory

Scan `migration/analysis/units.tsv` for places the target language forces
an explicit decision the source left implicit (ownership, nullability,
interface contracts); write `migration/clarify/inventory.tsv` — a lookup
table for agents, not something a human reads end to end.

## 3. Decide how to get ground truth (three tiers — human decides, not the agent)

The test-writer agent needs "what the old code actually does" as its
assertion basis, but this machine may lack the old runtime. **Settle this
here — never leave it for the test-writer to improvise**: installing
software or changing the environment is the human's call, not an agent's
(this has happened: a test-writer with no Delphi compiler ran `brew
install fpc` itself).

Check in order:

1. **Runtime environment exists**: use the domain skill's "source language
   runtime environment" section, or probe read-only (`which <compiler>`,
   never install). Found → record the invocation in `ground_truth_reason`,
   `ground_truth_tier: environment`.
2. **No environment, ask for mock data**: input/output examples, test
   cases, or production snapshots, stored under
   `migration/clarify/behavior-snapshots/`, `ground_truth_tier: snapshot`.
   Closer to most real migrations — many legacy systems can't be installed
   in a sandbox.
3. **Neither available, last resort**: explicitly confirm with the human
   that this batch accepts inferred behavior with no execution or
   human-provided data, `ground_truth_tier: inference`, record the agreed
   reasoning and date in `ground_truth_reason`.

Write the tier + reason into `RULEBOOK.md` frontmatter — **create the file
now if it doesn't exist yet** (frontmatter-only skeleton, e.g.
`---\nground_truth_tier: <tier>\n---\n\n# Rulebook\n`; body filled in by
section 4 below). The test-writer reads this file and never judges or
fixes the environment itself.

### Decide whether to add a parity check (optional) [decision point]

The current verification is a **one-sided assertion** — test-writer bakes
observed old behavior into a fixed assertion; verification never re-runs
the old system live to diff against it. Catches "new code fails its own
assertion," not "the assertion was wrong to begin with."

- Applies only if: `ground_truth_tier` is `environment` or `snapshot`.
  `inference` has no baseline to diff against — skip without asking.
- Ask: spend extra to build a validated referee — run old and new on the
  same real inputs post-conversion and mechanically diff, beyond each
  unit's own tests and the integration check?
- Record target: `RULEBOOK.md` frontmatter's `parity_check` field
  (`enabled`, or omit — default off); see `migration-convert`'s "Parity
  check" section for how it runs.

## 4. Draft the rulebook with the human [decision point, one ask per functionality group]

Seed rules: the domain skill's "syntax conversion / library replacement
rules" — already decided, don't revisit.

- Evidence, two sources — a functionality group can come from either, and
  counts the same way once grouped:
  - `migration/analysis/depmap/external-refs.tsv` (refs unresolved to a
    local file — native + private-package calls mixed, unclassified; see
    `migration-analyze`).
  - `migration/analysis/depmap/library-substitution-candidates.tsv` — local
    code that reimplements a target-library capability by hand (a hand-rolled DB
    connection instead of the library's DB-access function, ad-hoc hashing
    instead of its crypto function, print/file logging instead of its
    structured logging — whatever the target library's own docs actually
    name as a capability), invisible to `external-refs.tsv` since it's not
    an external reference at all. This is a high-level "which library
    realizes this" question just like the external-ref case, so it gets the
    same treatment here, not left for the translator to notice
    mid-conversion. Already computed by `migration-analyze`'s
    `migration-unit-scanner` dispatches (one read of the source doing both
    risk assessment and this at once) — just read the file, don't re-scan
    the code yourself.
  Group by **functionality performed**, not literal call text — two
  different-looking things doing the same thing share a group. Drop groups
  that are clearly unambiguous (string/date formatting, collection ops) —
  any translator would do them the same way regardless of library.
- Options (per remaining group): a library call from section 1's loaded
  knowledge that realizes it, or "custom logic, no library, plain syntax."
  Already covered by the domain skill's seed rules (anywhere, not just the
  rules table) → not a gap, already decided.
- Ask: once per group, never per occurrence, never left to the translator
  — this is a high-level call (which library realizes this capability),
  and a different guess per unit would translate the same functionality
  inconsistently across the batch. Recommend your proposed mapping with
  the group's occurrence count as evidence.
- Record target: add the mapping to `RULEBOOK.md`'s body, tagged
  `[repo-specific]` (only makes sense for this codebase) or
  `[domain-general]` (really belongs in the domain skill, this repo just
  surfaced it first — feeds "Done when"'s candidate list).

Rulebook is read-only from here on — none of the three conversion-stage
agents may edit it; amendments come from a human between batches.

## 5. Decide target project shape (optional) [decision point]

Some target languages have more than one project-template convention (e.g.
Python's "FastAPI service" vs "background ETL batch" shapes, each its own
directory structure/entry point/integration check, under the same template
skill's different sections).

- Applies only if: the domain skill's "template project" section lists more
  than one option. A single "same as skill `<name>`" → no divergence, skip
  entirely, don't write `target_shape`.
- Evidence / options: the domain skill's listed shapes.
- Ask: which shape applies to this migration (one manifest, one shape,
  never per unit). If the human says the manifest genuinely mixes two
  shapes, that means splitting into two migration instances, not mixing
  shapes in one manifest.
- Record target: `RULEBOOK.md` frontmatter's `target_shape`, formatted
  `<template skill name>: <shape name>` (the shape name copied verbatim
  from that skill's own `## Project shape: <name>` heading, e.g.
  `python-template: background ETL batch`) — the skill name alone doesn't
  disambiguate which shape, and this holds whether `domain_skill` points at
  the template indirectly ("same as skill `<name>`") or *is* the template
  directly. This value decides which skeleton `migration-convert` scaffolds
  from.

## 6. Confirm target-side prerequisites

Decides/confirms, doesn't build — scaffolding (`target/` directory
structure, build config) is `migration-convert`'s job, pure mechanical
execution of what's already decided. Don't create files under `target/`
here.

If the template project declares external target-side packages, confirm
read-only whether they're installed. For Python, **check by actually
importing it** (e.g. `python -c "import boogie_sdk"`), not `pip show`/`uv
pip show` — a workspace-member or editable/path install is genuinely
usable but reports as "not found" there anyway, a false negative
indistinguishable from a real missing dependency. Other ecosystems: `test
-d node_modules` or the equivalent is fine. Missing → **stop, tell the
human the install command** — same red line as ground truth: don't install
it yourself. Rerun once installed; `migration-convert` re-confirms in its
own pre-flight anyway since time may
pass. Nothing declared → nothing to do.

## 7. Copy source locally, fill in target_path, produce the full manifest

`units.tsv`'s `source_path` may sit outside this migration's own root
(external repo, read-only mount) — **copy each unit's source into this
migration's own `legacy/` directory** (preserve relative paths; flattening
to `legacy/<filename>` is fine if nothing collides). Keeps `migration/`
self-contained and trustworthy independent of the source repo's later fate.

Decide `target_path` per row using the template's naming convention
(`target_shape`'s template if set, else the domain skill's template-project
section directly). **Fill `target_path` in on `units.tsv`, rewrite
`source_path` to the local `legacy/...` copy, then rename the file to
`migration/clarify/manifest.tsv`** — one file, not two kept in sync;
`units.tsv` shouldn't exist after this step. Keep the existing
`cycle_group`/`order_index`/`risk_flag`/`risk_reason` columns — section 8
reads `risk_flag` to pick the pilot, and all four stay for human
traceability (why a unit was flagged) even where nothing downstream reads
them; `migration-convert` doesn't mind extra columns either way.

### Identify "private package itself" units — mark `excluded`, keep out of the conversion queue

If the domain skill names specific implementation files in its "private
package documentation" section, match unit `source_path` filenames in
`manifest.tsv` against them exactly. A match **is** the package's own
source, not application logic — the target already has a `corplib`
replacement, translating it line by line is pointless; only calling units
need their calls rewritten.

**Leave `target_path` blank** — that alone is the signal `migration-convert`
reads to mark `excluded` itself; you never touch
`migration/convert/state/`. Log which skill replaced it in `RULEBOOK.md`
instead, for the human-facing trail. Only exact-named files qualify — don't
expand scope on your own judgment.

Nothing to do if the domain skill doesn't name the package down to file
level (e.g. a compiled COM DLL with no matching source) — its calls just
appear inline, never as a separate unit.

### Identify UI/presentation-layer units — ask the human whether to keep them [decision point]

UI layer (VB6 `.frm`, Delphi `.dfm`/form units, `Vcl.Forms`/`Vcl.Controls`
etc.) is a **scope decision**, not a technical fact — the domain skill
can't decide it for you.

- Applies only if: `manifest.tsv` has units that look like UI layer (skip
  otherwise — e.g. pure batch/CLI batches).
- Evidence / recommendation: the domain skill's "UI/scope conventions"
  section, if written — sharpens the question, **never replaces the human
  confirmation**; ask plainly if unwritten.
- Ask (once for the whole batch, never per unit): keep the UI (needs
  matching target-side UI framework knowledge — report back if the domain
  skill lacks it) or drop it (core logic only)?
- Record target — drop: leave `target_path` blank (same mechanism as
  private-package exclusion — `migration-convert` marks it `excluded`
  itself), log the reason in `RULEBOOK.md`. **A unit whose UI handler mixes
  in business logic can't be excluded wholesale** — log it so the
  conversion agent extracts only the business-logic part.

### Identify units with pre-existing manual work — ask the human whether to keep them [decision point]

After filling `target_path`, check: the path **already has a non-empty
file**, and `migration/convert/state/<unit_id>.json` **doesn't exist yet**
— someone put something there before this kit ran. (Different from
`migration-convert`'s scaffold idempotency, which only protects directory
structure/build config, not per-unit code.)

- Applies only if: qualifying units exist.
- Evidence: list `unit_id` + `target_path` + `source_path` so the human
  sees the scope.
- Ask: trust it? Whole batch or per unit, three options:
  1. **Trust as-is** — `migration-convert` will run none of the three
     agents and mark it `pass` directly, listed separately from real
     passes in the final burndown.
  2. **Trust but verify** — test-writer runs normally, translator is
     skipped, test-reviewer reviews the existing file directly; only asks
     about retranslating if review fails.
  3. **Retranslate** — normal processing, will overwrite. **Explicitly
     warn the human it'll overwrite the existing file and get
     commit/backup confirmation first.**
- Record target: a `manual_work` column on `manifest.tsv` for these units
  (`trust-as-is` / `trust-verify` / `retranslate`) — the single field
  `migration-convert` branches on. Don't write anything under
  `migration/convert/state/`; that's `migration-convert`'s own working
  area, not yours to touch.

## 8. Mark the pilot subset

Add a `pilot` column to `manifest.tsv` (`yes`/`no`), mark 2-3 units `yes`
— prioritize `risk_flag: high`, pair with one ordinary unit. This runs
first so a systematic rulebook error gets caught before it's spent on
every unit. One column on `manifest.tsv`, not a separate file —
`migration-convert` filters by it.

## Done when

All eight sections done → **always stop**, report the full artifact list:
the domain skill in use (from the root `CLAUDE.md`), `RULEBOOK.md`
(frontmatter's `ground_truth_tier`/`ground_truth_reason`/`target_shape` if
applicable/`parity_check` if enabled), inventory, manifest (with `pilot`),
target-side prerequisite status, and any pre-existing-manual-work units
with their decisions.

List every `[domain-general]`-tagged rule from section 4, naming the domain
skill file it's a candidate for — only surfaced in this report, not written
to any file, since folding it in is a human call between batches. **Never
edit the domain skill file yourself**, however confident the tag.

Don't auto-proceed — only after human review does the orchestrator run
`migration-convert` on `pilot=yes` rows.

Reminder if this is the first run on this repo: `.claude/settings.json` +
`.claude/hooks/` should be copied over now (see `migration`'s "before you
start") so the syntax-check hook is active from the first pilot unit — not
a hard blocker, just better done early. Not your job to create these.
