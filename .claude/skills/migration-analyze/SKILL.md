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

## Risk assessment: split across parallel migration-risk-scanner subagents

Once the script's output gives you the unit list (one row per file, or per
merged cycle-group), reading every unit's actual source to judge
`risk_flag`/`risk_reason` yourself in one context doesn't scale — a real
batch can be dozens to hundreds of files, and holding all of it in one
context defeats the point of chunking the work at all. Instead:

1. **Chunk the unit list, never splitting a `cycle_group` across chunks** —
   a cycle group's units are already treated as one atomic thing downstream
   (converted/tested/reviewed together), so they need to be read together
   here too, not split across two scanners that each only see half the
   picture. Size chunks so each one is comfortably readable in one pass — a
   rough guideline is "a handful of files," not a fixed count; a small batch
   might be one chunk, a large one might be a dozen.
2. **Dispatch one `migration-risk-scanner` subagent per chunk, in parallel**
   — send all the Task calls together, not one at a time waiting for each
   to finish before starting the next. Give each one only its own chunk's
   `unit_id`/`source_path`(s)/`cycle_group` — it doesn't need the rest of
   the batch.
3. Specify a model explicitly for every dispatch (mid-tier is enough — this
   is mechanical read-and-summarize work, not a judgment call requiring the
   strongest available model) — same "never let it inherit the caller's
   model" discipline as `migration-convert`'s subagent dispatches.
4. Merge every scanner's returned rows into `units.tsv`'s `risk_flag`/
   `risk_reason` columns, and keep the one-line summaries for
   `migration/analysis/ANALYSIS.md` below. If a scanner reports a source
   file it couldn't read, don't guess a risk assessment for that unit
   yourself — carry the "couldn't read" note into both outputs so a human
   sees it, same as any other gap.

## Output

Two artifacts, both under `migration/analysis/`:

- **`migration/analysis/units.tsv`** — columns `unit_id, source_path,
  cycle_group, order_index, risk_flag, risk_reason`, in topological order
  (`order_index` can be left blank and inferred from row order; writing it
  out just makes the number visible without anyone having to count rows).
  The three column groups map to script-computed facts plus the scanners'
  risk judgment — not three unrelated artifacts bolted together:
  `unit_id`/`source_path`/`cycle_group`/`order_index` come directly from
  `edges.tsv`/`order.txt`/`cycles.txt`; `risk_flag` (`high`/`normal`) and
  `risk_reason` come from the `migration-risk-scanner` dispatches above, not
  from you eyeballing the code yourself. `risk_flag` later drives
  `migration-clarify`'s pilot-subset selection (prioritize `high`-flagged
  units for the pilot).
- **`migration/analysis/ANALYSIS.md`** — a human-readable summary, for
  someone orienting themselves without wanting to parse four `.tsv`/`.txt`
  files: total unit count, cycle-group count and which units are in each
  cycle, high-risk units with their `risk_reason` up front, the most
  frequently occurring `external-refs.tsv` entries (a preview of what
  `migration-clarify` will need to classify, not a classification itself —
  that's still not this step's call), and every unit's one-line summary
  from its `migration-risk-scanner` (grouped by risk level, high first, so
  the parts most worth a human's attention aren't buried at the bottom).

## Boundaries

Read-only. Don't touch the rulebook, inventory, or domain-skill selection;
don't write any unit's code; don't produce the final `migration/clarify/manifest.tsv`
(that needs `target_path`, which is `migration-clarify`'s job).

## Done when

Stop once the three `migration/analysis/depmap/` intermediate files,
`units.tsv`, and `migration/analysis/ANALYSIS.md` all exist; report a
summary (unit count, cycle-group count, high-risk unit count). Read-only and
rerunnable — the top-level orchestrator can go straight to
`migration-clarify` without human sign-off, unless the scale or complexity
of cycles is unusual enough that you judge a human should look first.
