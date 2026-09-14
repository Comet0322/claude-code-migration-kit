# Pipeline stages: input → output

Reference only — each stage's own SKILL.md is authoritative. This just
answers "what does stage N need, what does it leave behind."

## 0. migration (domain skill selection)

**Input:** the legacy source repo (a direct, lightweight scan — no
`units.tsv` yet), installed `domain-*` skills, a human answer.

**Output:** a `Migration domain skill: <name>` line appended to the repo's
root `CLAUDE.md` — the single source of truth every later stage reads from
(never duplicated into `RULEBOOK.md`).

## 1. migration-analyze

**Input:** the legacy source repo (read-only scan); `domain_skill` is
already known (from root `CLAUDE.md`). Its dependency-ordering script and
`target_path` decision still don't use it — see its own "Why this step
can't decide target_path" section — but its unit-scanner subagent now does
(see below).

**Output:**
- `migration/analysis/depmap/edges.tsv` / `order.txt` / `cycles.txt` —
  dependency graph, topological order, cycle groups (script-computed).
- `migration/analysis/depmap/external-refs.tsv` — references that don't
  resolve to a local file (native + private-package calls, mixed,
  unclassified — classification is `migration-clarify`'s job).
- `migration/analysis/depmap/ambiguous-units.tsv` / `entry-points.tsv` —
  only when the source language's script can detect but not resolve an
  ambiguity.
- `migration/analysis/depmap/library-substitution-candidates.tsv` — local
  code that hand-rolls something the target library already provides
  (`unit_id`, source pointer, capability name, evidence); may be empty.
  Feeds `migration-clarify`'s rulebook-drafting decision point later,
  alongside `external-refs.tsv`.
- `migration/analysis/units.tsv` — `unit_id`/`source_path`/`cycle_group`/
  `order_index`/`risk_flag`/`risk_reason`, one row per unit (or per merged
  cycle group).
- `migration/analysis/ANALYSIS.md` — human-readable summary.

**Internal subagent:** `migration-unit-scanner`, one per chunk, dispatched
in parallel. Input: that chunk's `unit_id`/`source_path`(s)/`cycle_group`,
plus `domain_skill`'s target-language library docs. Output, from one read:
`risk_flag`/`risk_reason` + a one-line summary per unit, plus zero or more
library-substitution candidates — this is the one subagent that used to be
two (`migration-risk-scanner` and a clarify-stage
`migration-library-gap-scanner`), merged so the same source isn't read
twice for two different purposes.

## 2. migration-clarify

**Input:** `migration/analysis/units.tsv`, `.../external-refs.tsv`,
`.../library-substitution-candidates.tsv`, the selected domain skill's content,
human answers at each decision point.

**Output:**
- `migration/clarify/RULEBOOK.md` — frontmatter (`ground_truth_tier`,
  `ground_truth_reason`, `target_shape` if applicable, `parity_check` if
  enabled — `domain_skill` lives in root `CLAUDE.md`, not here) + body
  (repo-specific / domain-general rules).
- `migration/clarify/inventory.tsv` — explicit-decision-forcing gaps
  (ownership, nullability, interface contracts).
- `migration/clarify/manifest.tsv` — `units.tsv` renamed in place:
  `target_path` filled, `source_path` repointed at the local `legacy/`
  copy, plus `pilot` (`yes`/`no`) and `manual_work`
  (`trust-as-is`/`trust-verify`/`retranslate`, only on qualifying rows)
  columns added. `units.tsv` stops existing after this — `manifest.tsv` is
  its replacement, not a second copy.
- `legacy/` — local copies of every unit's source.
- `migration/clarify/behavior-snapshots/` — only if
  `ground_truth_tier: snapshot`.

No subagent of its own for rulebook-drafting evidence anymore — it reads
`library-substitution-candidates.tsv` rather than re-scanning source itself.

## 3. migration-convert

**Input:** `migration/clarify/manifest.tsv` + a stated scope (`pilot=yes`
rows, or all rows), `RULEBOOK.md`, `inventory.tsv`.

**Output:**
- `target/` — the converted project itself.
- `migration/convert/state/<unit_id>.json` — one per unit:
  `status`/`attempts`/`last_note`.
- `migration/convert/cost-log.tsv` — one line per agent call.
- `migration/convert/deviation-log.tsv` — one line per rule gap.
- `migration/convert/rulebook-amendments.md` — pending fixes for a human to
  merge into `RULEBOOK.md` between batches.
- `migration/convert/state/_integration.json` — once every unit is
  `pass`/`excluded` (gains `parity_status`/`parity_note` too, if the parity
  check ran).
- `migration/convert/pilot-signoff.txt` — written by the human (or you,
  with their explicit agreement) — never by you unprompted.

**Internal subagents,** one pass per unit:

| Agent | Input | Output |
|---|---|---|
| `migration-test-writer` | `unit_id`, `source_path`, inventory rows, `ground_truth_tier`/`ground_truth_reason`, domain skill's test conventions | test file + behavior-observation notes |
| `migration-translator` | `source_path`, `target_path`, rulebook, inventory rows, domain skill's conversion rules, test file (read-only) | translated code + translation notes |
| `migration-test-reviewer` | `source_path`, `target_path`, test file + notes, rulebook, domain skill's build/test method | structured review report |
