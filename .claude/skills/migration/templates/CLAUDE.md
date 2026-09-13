<!--
This file is auto-maintained by the `migration` skill (see its "Keep
migration/CLAUDE.md current" section) — it's a convenience summary for
resuming work quickly, not a source of truth. If anything here disagrees
with what the skill actually reports by reading migration/'s real files,
trust the files, not this summary. Safe to read anytime; edits to anything
outside "Human notes" below get overwritten the next time the skill
refreshes this file.
-->

# Migration workspace: <app/repo name>

**Status**: <analyzing | clarifying | pilot running | converting | integration check | parity check | done>
**Last updated**: <ISO timestamp> — after `<skill name>` step <N>

## Resuming this migration

Just invoke the `migration` skill again — it re-derives what to do next
purely from what's actually in `migration/` (never from this file, never
from conversation memory). This file exists so a human (or a fresh session)
can get oriented in a few seconds instead of re-reading every artifact.

## Decisions made so far

- **Domain skill**: <name, or "not yet selected">
- **Ground truth tier**: <environment | snapshot | inference | "not yet decided"> — <one-line reason>
- **Target shape**: <template skill name, or "n/a — domain skill has only one shape">
- **Parity check**: <enabled | not enabled | "not yet decided">

## Key artifacts

| Path | What it is |
|---|---|
| `migration/analysis/ANALYSIS.md` | Human-readable analysis summary (unit count, cycles, risk highlights) |
| `migration/analysis/depmap/` | Machine-computed dependency graph (edges/order/cycles/external-refs) |
| `migration/clarify/RULEBOOK.md` | Decisions ledger — frontmatter + translation rules, read-only once drafted |
| `migration/clarify/manifest.tsv` | Unit list, target paths, pilot flags |
| `migration/clarify/inventory.tsv` | Gap inventory (ownership/nullability/interface decisions) |
| `migration/convert/state/<unit_id>.json` | Per-unit conversion status |
| `migration/convert/cost-log.tsv` | Token/time cost per subagent call |
| `migration/convert/deviation-log.tsv`, `migration/convert/rulebook-amendments.md` | Rule gaps found mid-conversion, pending human merge |
| `migration/clarify/behavior-snapshots/` | Human-provided ground truth (only if tier is `snapshot`) |

## Open items / reminders

<list anything a human still needs to do — install a package, sign off a
pilot, resolve a rulebook amendment, etc. Empty list if nothing's pending.>

## Batch context (optional)

<If this repo is one of several similar legacy apps being migrated as a
batch, note the others here and whether their domain-skill/rulebook
decisions were reused or diverged. Delete this section if there's no batch —
don't leave it as a placeholder that looks unfinished.>

## Human notes

<Free text. This section is never overwritten by the skill — anything below
this heading is yours.>
