---
name: migration-analyze
description: >
  Analysis skill: called by the top-level orchestrator when
  migration/analysis/ artifacts don't exist yet. Read-only scan of legacy
  code to decide unit migration order. Do not use outside this context —
  rule decisions, domain-skill selection, and target paths are not this
  skill's job.
---

# Analysis Skill

You produce **facts**, not **decisions**. The dependency graph — who depends
on whom — is objective; whether/how to translate in that order is not your
call.

## Why this step can't decide target_path

Target-path naming conventions come from the domain skill's template-project
section, and the domain skill isn't selected until `migration-clarify` (analysis
runs first, domain-skill selection comes later). So this step only orders
things — it doesn't fill in "where it goes." That's left for
`migration-clarify` to complete on the manifest draft.

## Dependency graph: use a script, not judgment

Dependency order and cycle detection are exactly computable by script — don't
have the agent eyeball code and order it by feel.

1. Check whether `.claude/skills/migration/scripts/depmap_<source
   language>.*` exists first — this is pre-written and validated, shipped
   with the `migration` skill itself (currently `depmap_vb6.py`,
   `depmap_delphi.py`), not something this migration run generates on the
   fly. If it exists, **run it directly from that path — don't copy it into
   `migration/scripts/` first.** Copying just adds a file to keep in sync;
   this script isn't owned by this migration run, it's owned by the
   `migration` skill itself. If you spot inaccurate parsing, log it in
   `units.tsv`'s `risk_reason` column for a human to decide whether to fix
   the script later — don't patch it yourself, and don't save an edited copy
   under `migration/scripts/` (the next call still looks at
   `.claude/skills/migration/scripts/` first, so that copy would never be
   used anyway).
2. Only if no packaged script exists for this source language, check whether
   `migration/scripts/depmap_<source language>.*` already exists — if an
   earlier instance in this batch already wrote a dependency-analysis
   script for the same language, reuse it, don't rewrite it.
3. Only if neither exists, write one for the source language (parse
   import/require/include statements, produce file-level edges), save it to
   `migration/scripts/depmap_<source language>.*` for later instances in
   this batch to reuse. Note in your report that this language has no
   packaged version yet — worth promoting into
   `.claude/skills/migration/scripts/` if the batch will hit this language
   again, but that's a human/skill-maintainer decision, not yours to act on.
4. Run the script. Output:
   - `migration/analysis/depmap/edges.tsv` (from, to)
   - `migration/analysis/depmap/order.txt` (topologically sorted file order)
   - `migration/analysis/depmap/cycles.txt` (cyclic-dependency groups, if any)
   - `migration/analysis/depmap/external-refs.tsv` (source_path, reference —
     references that don't resolve to a local file, native standard-library
     calls and private packages listed together without distinction; that
     classification is a judgment call, not a fact, and belongs to
     `migration-clarify`'s rulebook-drafting step, not here)

## Handling cyclic dependencies

Don't try to break cycles yourself. Merge every file in the same cycle into
one `unit_id` in `units.tsv` (converted, tested, and reviewed together),
tagged with the same `cycle_group` value — the only way topological order
still holds when cycles exist.

## Output

One table: `migration/analysis/units.tsv` — columns `unit_id, source_path,
cycle_group, order_index, risk_flag, risk_reason`, in topological order
(`order_index` can be left blank and inferred from row order; writing it out
just makes the number visible without anyone having to count rows).

The three column groups map to script-computed facts plus your own risk
judgment — not three unrelated artifacts bolted together:
`unit_id`/`source_path`/`cycle_group`/`order_index` come directly from
`edges.tsv`/`order.txt`/`cycles.txt`; `risk_flag` (`high`/`normal`) and
`risk_reason` are your own judgment (basis: abnormal file size/complexity,
abnormally high fan-out, syntax the analysis script couldn't fully parse),
not script output. `risk_flag` later drives `migration-clarify`'s pilot-subset
selection (prioritize `high`-flagged units for the pilot).

## Boundaries

Read-only. Don't touch the rulebook, inventory, or domain-skill selection;
don't write any unit's code; don't produce the final `migration/manifest.tsv`
(that needs `target_path`, which is `migration-clarify`'s job).

## Done when

Stop once the three `migration/analysis/depmap/` intermediate files and
`units.tsv` all exist; report a summary (unit count, cycle-group count,
high-risk unit count). Read-only and rerunnable — the top-level orchestrator
can go straight to `migration-clarify` without human sign-off, unless the
scale or complexity of cycles is unusual enough that you judge a human should
look first.
