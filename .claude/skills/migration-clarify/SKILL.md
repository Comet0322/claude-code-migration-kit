---
name: migration-clarify
description: >
  Clarification and gap-analysis skill: called by the top-level orchestrator
  once migration/analysis/ artifacts are complete but the rulebook or
  manifest is still missing. Always stops at the end for human sign-off —
  never auto-proceeds to conversion.
---

# Clarification and Gap Analysis Skill

This is the heaviest human-collaboration step in the whole pipeline — your
output decides where the conversion stage's rules come from. Mistakes here
are the most expensive, so make your reasoning visible after every section
instead of deciding silently and moving on.

## Headless test protocol (active when `migration/.headless-test` exists)

This skill normally uses `AskUserQuestion` to let a human decide at several
points. If the marker file `migration/.headless-test` exists, you're being
driven unattended by an automated test harness:

- Anywhere that would normally call `AskUserQuestion` (or otherwise stop and
  wait for a reply): instead, using the same evidence and reasoning you'd
  use to rank recommendations, **pick the option you judge most reasonable
  yourself**, append the full candidate comparison, reasoning, and
  confidence level to `migration/decision-log.md` (headed `## <section
  title>`), then proceed with that decision — don't stop. End the entry with
  `STATUS: decided`.
- Exception: if the evidence genuinely doesn't favor any option (e.g.
  candidate domain skills are indistinguishable, or the code gives no clue
  about target shape/UI scope), log the reasoning the same way but end with
  `STATUS: needs-human`, then **stop the whole skill call** — this isn't a
  failure, it's a case a human would need to weigh in on too; an honest
  record beats a forced guess.
- When the marker doesn't exist (the normal case), none of this applies —
  use the regular `AskUserQuestion` flow.

Domain-skill selection specifically also honors one more, narrower marker:
`migration/.headless-test-domain-skill` (only meaningful together with
`.headless-test`). If present, its contents force-select a specific domain
skill instead of running the normal self-decide/ambiguity logic — see
section 1. This exists purely to regression-test a domain skill's full
conversion pipeline through a fingerprint that's *deliberately* ambiguous by
design (e.g. the same source facts intentionally shared by two domain skills
targeting different languages, which would otherwise always stop at
`needs-human` and never get exercised past domain-skill selection). A real
migration run has no such marker available, since a real run has no way to
know the "correct" answer in advance — this is a test-only escape hatch, not
a general override mechanism for any other section's decisions.

Regardless of the marker, `migration/RULEBOOK.md` frontmatter's
`ground_truth_tier` field must be one of `environment` / `snapshot` /
`inference`, with `ground_truth_reason` holding the rationale — a format
requirement, not a change to the three-tier decision logic below.

## 1. Select domain skill (once per repo, not per unit)

- Check whether `migration/RULEBOOK.md` already exists with a `domain_skill`
  field in its frontmatter — if already selected earlier in this
  conversation (e.g. rerunning this skill in the same session), load it and
  don't ask again.
- If not: scan installed skills named `domain-*` (workspace and user level;
  `domain-template` itself never counts, skip it). None found → **stop and
  tell the human to prepare one first** — copying `domain-template` and
  filling it in works — never invent domain knowledge from nothing.
- Candidates found: read the actual code in this repo (import paths,
  config filenames, private-package references seen in
  `migration/analysis/units.tsv`), compare against each candidate's "app
  types this domain skill covers" and "private package documentation"
  sections, rank the best match as the recommendation. If
  `migration/.headless-test` doesn't exist, use `AskUserQuestion` to ask the
  human which one (candidates + recommendation + reasoning); if it exists,
  check `migration/.headless-test-domain-skill` first (see the Headless test
  protocol section above) before falling back to the normal
  self-decide/ambiguity logic:
  - Present and its content matches one of the candidates found above → use
    it directly, skip the self-decide/ambiguity comparison entirely (a
    forced test override, not a recommendation — no fingerprint match
    needed to justify it). Log the pick to `migration/decision-log.md`
    exactly as any other headless decision, explicitly noting it was a
    forced test override rather than a self-decided pick, `STATUS: decided`.
  - Present but its content names something that isn't one of the
    candidates found above → this is a fixture/test misconfiguration, not a
    real ambiguity. Log the mismatch to `migration/decision-log.md`,
    `STATUS: needs-human`, stop — don't silently ignore the override or
    silently fall back to self-deciding instead.
  - Not present → follow the Headless test protocol's normal
    self-decide/ambiguity logic.
- Once decided, write it into `migration/RULEBOOK.md` frontmatter
  (`domain_skill` field). If the file doesn't exist yet, create a
  frontmatter-only skeleton here with the body left blank (e.g.
  `---\ndomain_skill: <name>\n---\n\n# Rulebook\n`) — sections 3, 4, and 6
  below will progressively fill in the `ground_truth_tier`/
  `ground_truth_reason`/`target_shape` frontmatter fields and the rule body;
  you don't write the whole rulebook here.

Batch reminder: this record belongs to **this repo**, not shared across
repos. The same batch of "same kind" legacy apps (using the same
domain-skill/template) is usually split into many separate repos/checkouts,
each a brand-new `migration/` directory — ask again every time, don't
silently decide per-repo without confirmation. Because the code
characteristics within a batch tend to look alike, the human is usually just
confirming the recommendation, not starting from scratch.

## 2. Load domain skill content

Read in: private package documentation, UI/scope conventions (if written),
template project, syntax-conversion/library-replacement rules, target
language library docs, test/build method. These feed every later section
and the three conversion-stage subagents.

If the template-project / target-language-library-docs / test-build-method
sections say "same as skill `<name>`" instead of inline content, use the
Skill tool to load that skill's actual content — it's target-side shared
knowledge maintained independently, possibly useful outside migration too
(see `domain-template`), not something the selected domain skill forgot to
fill in. Once loaded, treat it as if it were inline in this domain skill, and
pass it along to every later section and the three subagents the same way.

If a section instead gives a relative path (e.g. "see
`references/private-package.md`" — has a `/`, usually a `.md` extension,
unlike the "same as skill `<name>`" pattern which is a bare skill name):
that means the content was too large and got moved to a reference file
inside that domain skill's own folder (see `domain-template`'s "when a
single domain skill's content is too large" section) — not another skill.
Read that relative path directly with the Read tool (relative to that domain
skill's own folder), don't try to load it as a skill name. Treat it the same
way once read in.

## 3. Decide how to get ground truth (three tiers — human decides, not the agent)

The conversion stage's test-writer agent needs "what the old code actually
does" as its assertion basis — but this machine may not have the old
language's runtime available. **This must be settled here, not left for the
test-writer agent to discover and improvise on its own**: it has actually
happened that a test-writer found no Delphi compiler and ran `brew install
fpc` to install one itself — unacceptable; installing software or changing
the environment is the human's call, not something an agent can act on.

Check in order which tier applies to this batch (or repo):

1. **A usable runtime environment exists**: check the domain skill's "source
   language runtime environment" section for how to invoke it; if unwritten,
   or the documented method fails on this machine, probe read-only (e.g.
   `which <compiler>`, query only, never install) to see if one's already
   present. Found → write the exact invocation into `RULEBOOK.md`
   frontmatter's `ground_truth_reason`, `ground_truth_tier` = `environment`.
2. **No environment: ask the human for mock data / snapshots**: request
   input/output examples, existing test cases, or production data snapshots
   for this code, store them under `migration/behavior-snapshots/`,
   `ground_truth_tier` = `snapshot`. Second choice, but closer to most real
   migrations — many legacy systems simply can't be installed in a migration
   sandbox.
3. **Neither available, last resort**: explicitly confirm with the human
   "this batch accepts behavior inferred from reading docs/code, with no
   real execution or human-provided data to verify it," `ground_truth_tier`
   = `inference`, and record the human's agreed reasoning and date in
   `ground_truth_reason` — a risk-acceptance decision that must leave a
   trace, never a silent default or an after-the-fact admission.

Write the chosen tier into `RULEBOOK.md` frontmatter's `ground_truth_tier`/
`ground_truth_reason` fields; the test-writer agent reads this file to decide
what to do — it never judges this itself, and never fixes the environment
itself.

In headless mode (`migration/.headless-test` exists), if tier 1 (runtime
environment) probing fails and `migration/behavior-snapshots/` has no usable
material, **default straight to `ground_truth_tier: inference`**, with
`ground_truth_reason` = "automated test environment, no source-side runtime
or behavior snapshot available," and don't stop — a deliberately relaxed test
default, different from the general rule that "neither available" is a last
resort requiring explicit human agreement; only applies when the marker file
exists.

### Decide whether to add a parity check (optional, only ask if `ground_truth_tier` isn't `inference`)

The current verification method is a **one-sided assertion**: the
test-writer observes old behavior once and bakes it into a fixed new-language
test assertion; verification later only checks the new code against that
assertion, never re-runs the old system live to diff against it. Good enough
for most batches, but it can't catch "is this assertion actually a correct
reflection of the old behavior."

When `ground_truth_tier` is `environment` or `snapshot` (real old behavior
exists as a baseline), ask the human once with `AskUserQuestion`: "Beyond
each unit's own tests and the final integration check, do you want to spend
extra to build a **validated** referee after all units are converted — run
old and new systems on the same real inputs and mechanically diff the
output, rather than just checking the new system is internally
consistent?" `inference` tier has no real old behavior to use as a baseline
— skip this without asking.

Record the answer in `migration/RULEBOOK.md` frontmatter's `parity_check`
field (`enabled`, or omit — default off). This is a cost/value decision, not
a default — see `migration-convert`'s "Parity check" section for how it runs
once all units are converted.

## 4. Draft the rulebook with the human

Start from the domain skill's "syntax conversion / library replacement
rules" as seed rules — already decided, no need to revisit. Only discuss
with the human the translation decisions **specific to this codebase and not
covered by the domain skill**: read out places in the codebase where "two
agents might make different choices" (backed by data, e.g. "this pattern
appears N times"), decide them one at a time with the human, and add them to
`migration/RULEBOOK.md`'s body (section 1 already created a frontmatter-only
skeleton; this is filling in the body after the frontmatter, not creating a
new file).

**Also read `migration/analysis/depmap/external-refs.tsv` as a second
evidence source**: these are references the analysis stage recorded that
don't resolve to a local file, native standard-library calls and private
packages mixed together with no classification (see `migration-analyze` —
that classification is a judgment call, not something the analysis stage
should do). After deduping and counting occurrences, **use your own
knowledge of the source language to filter first**: skip anything whose
translation is clearly unambiguous (string/date formatting, collection
operations — anything any conversion agent would translate the same way).

For what's left, check whether the domain skill already covers it — **check
both the "private package documentation" section and the "syntax
conversion / library replacement rules" table, not just one**:
- "Private package documentation" names the **package itself** (a DLL
  filename, a COM component name, e.g. `Dept200Common.dll`) — this is the
  case where an externally-provided private package with no source in the
  repo shows up in `external-refs.tsv` (a private package whose source IS in
  the repo, like `Dept200Data.pas`, resolves to a local file and never
  appears in this list — it's handled by the existing "identify private
  package itself" mechanism below, unrelated to this check).
- The "syntax conversion / library replacement rules" table's left column
  holds **specific API call snippets** (e.g. `Conn.Query(sql,
  Array(...))`), not package names — matching an `external-refs.tsv` name
  string against this table usually won't hit, so it alone can't tell you
  "is this covered."

Checking only the rules table misses one case: the package name was already
named in "private package documentation," and the target side already has a
matching `corplib` to use directly — the rules table just never repeated the
package name in its own row. That's not a real gap; checking only the rules
table would misjudge it as "domain skill doesn't cover this" and raise a
false alarm. Only when **both** sections miss it is it a real candidate —
native or private, as long as it meets both "domain skill mentions it in
neither section" and "not obviously safe to translate" — raise it as a
candidate with its occurrence count as evidence, decided the same way as
every other rulebook item (it might be "domain skill missed a rule," or it
might be "this batch really does have an undocumented private package") — no
separate report or sign-off needed for this list.

**Tag each new rule you add to the body as `[repo-specific]` or
`[domain-general]`** — this is a judgment call you make alongside the human
when deciding the rule, not extra process: `[repo-specific]` means it only
makes sense because of something particular to this one codebase (a naming
quirk, a one-off legacy workaround); `[domain-general]` means it's really a
fact about the domain skill's own private package/library that any app using
it would hit the same way, this repo just happened to be the first to
surface it. This tag is what feeds the "Done when" section's list of
domain-skill-worthy candidates — it isn't just bookkeeping.

The rulebook is read-only for the rest of this session once done — none of
the three conversion-stage agents may edit it; amendments after this point
are made by a human between batches.

## 5. Gap inventory

Scan `migration/analysis/units.tsv`, list the places where the target
language forces an explicit decision that the source language could leave
implicit (ownership, nullability, interface contracts), write
`migration/inventory.tsv`. A table for agents to look things up in, not
something a human is meant to read end to end.

## 6. Decide target project shape (optional, only if the domain skill's template section lists more than one option)

Some target languages don't have a single project-template convention — e.g.
target Python might internally have both a "FastAPI service" shape and a
"background ETL batch" shape, each with its own directory structure, entry
point, and integration-check method, mapped to different sections under the
same template skill (e.g. `python-template`'s "Project shape: FastAPI
long-running service" / "Project shape: background ETL batch" sections).

If the selected domain skill's "template project" section lists more than
one option, use `AskUserQuestion` to confirm with the human which shape
applies to **this migration (this `migration/` directory, this
manifest)** — same as domain-skill selection, one manifest is always one
shape, never decided per unit. (If `migration/.headless-test` exists, follow
the Headless test protocol instead of calling `AskUserQuestion`.) If the
human tells you this migration's manifest genuinely mixes two shapes, report
that back: it means this repo should split into two separate migration
instances (each its own `migration/` directory), not mix shapes in one
manifest.

Once decided, write it into `migration/RULEBOOK.md` frontmatter's
`target_shape` field (value: template skill name). This field decides which
template skeleton `migration-convert` scaffolds the target project from and
which template knowledge it feeds the three subagents.

If the domain skill's "template project" section only has a single "same as
skill `<name>`" (no listed options), this target language has no shape
divergence in this batch — skip this section, don't ask the human, don't
write `target_shape`.

## 7. Copy source locally, fill in target_path, produce the full manifest

Read `migration/analysis/units.tsv` — its `source_path` is wherever
`migration-analyze` saw it during scanning, not guaranteed to sit under this
migration's own working root (could be a source repo kept elsewhere, even a
read-only mount). **Copy each unit's source file into this migration's own
`legacy/` directory** (preserving `units.tsv`'s relative path structure;
when sources are scattered across many unrelated directories, flattening to
`legacy/<filename>` is fine too, as long as nothing collides across the
whole batch).

Reasoning: this migration's whole working directory (`migration/`,
`legacy/`, `target/`) needs to be self-contained — movable, archivable, and
comparable against other migration runs as a unit, without depending on the
external source repo staying put at the same relative paths. If that repo
later gets updated, moved, or even deleted, this migration's completed
analysis and decisions stay fully trustworthy — no risk of missing files or
(worse) silently matching against a different version.

After copying, decide `target_path` for each row per the template project's
naming convention (if "decide target project shape" set one, follow the
template skill it names via `RULEBOOK.md` frontmatter's `target_shape`
field; otherwise follow the domain skill's template-project section
directly). **Fill in the `target_path` column in place on
`migration/analysis/units.tsv` itself, change `source_path` to the copied
local `legacy/...` path, then rename/move this file to
`migration/manifest.tsv`** — don't write a fresh file and leave `units.tsv`
sitting untouched under `migration/analysis/` — that would turn one set of
content into two files that need to stay in sync; `units.tsv` shouldn't
exist anymore once this step is done. Keep `units.tsv`'s existing
`cycle_group`/`order_index`/`risk_flag`/`risk_reason` columns in
`manifest.tsv` — the three subsections below and section 9's pilot selection
still need them; `migration-convert` only looks at the
`unit_id`/`source_path`/`target_path` columns it needs, and the extra
columns don't affect it.

### Identify "private package itself" units — mark `excluded`, keep out of the conversion queue

If the domain skill (or a source-side shared skill it references) names
specific implementation files in its "private package documentation"
section, match each unit's `source_path` filename in `migration/manifest.tsv`
against them (`units.tsv` has already been renamed into `manifest.tsv` by
now — `cycle_group` and the other columns are still in the same file, no
need to open another one). An exact match means this unit **is** the private
package's own source, not application logic to translate — the target side
already has a matching `corplib` replacement, so translating it line by line
is pointless; only the calling units need their calls rewritten to use
`corplib` instead.

Leave `target_path` blank for such units (or write `(excluded — replaced by
<skill name>)`), and immediately write `migration/state/<unit_id>.json`
with `status` set directly to `excluded` (not `pending`), `last_note`
stating which skill replaced it. Log this decision in `RULEBOOK.md` (same
as any other batch-specific decision — visible reasoning), don't do it
silently, and don't invent judgment beyond the rule — only files the domain
skill explicitly names can be marked this way, don't expand the scope on
your own judgment.

No such units exist if the domain skill doesn't name the private package
down to file level (e.g. it only describes an externally-provided compiled
COM DLL with no matching source file in the repo) — the private package's
calls just appear directly in application code, `migration-analyze` never
scans it as a separate unit, nothing special to do.

### Identify UI/presentation-layer units — ask the human whether to keep them

Some legacy apps have a UI layer (VB6 `.frm`, Delphi `.dfm`/form units, or
`uses`/`import` clauses referencing UI framework units like
`Vcl.Forms`/`Vcl.Controls`/`Forms`/`Controls`) — different from private-package
exclusion: whether to keep the UI layer is a **scope decision**, not a
technical fact like "the target side already has an equivalent," the domain
skill can't decide this for you, always ask the human.

If `migration/manifest.tsv` has units that look like UI layer, use
`AskUserQuestion` to ask the human whether this whole migration should
"keep the UI (convert it along with everything else — meaning the selected
domain skill needs matching target-side UI framework knowledge, covered in
its template-project/target-language-library-docs sections; if it doesn't,
report that back — this domain skill needs more UI framework knowledge, or
the wrong one was picked)" or "drop the UI, convert only the core logic."
Same as "decide target project shape" — ask once for the whole batch, never
per unit. If the selected domain skill has a "UI/scope conventions" section,
read it in and present its recorded convention and reasoning as the
recommended option (e.g. "the domain skill records that this department's
convention is to drop the UI, for this reason — apply the same here?") —
this section only sharpens the question, **it can never replace this human
confirmation step**; if unwritten, ask plainly with no recommendation. (If
`migration/.headless-test` exists, follow the Headless test protocol instead
of calling `AskUserQuestion` — in that case, the "UI/scope conventions"
section content is exactly the evidence used to rank the recommendation, use
it directly.)

**Drop the UI**: mark these units `excluded` (same mechanism as
private-package exclusion, `last_note` = "UI layer, human decided not to
migrate, see RULEBOOK.md"), and log this decision in `RULEBOOK.md` (with
date and reasoning) — a scope-reduction decision that needs a paper trail
just like a rule decision, never a default, never your own call. **A unit
whose UI event handler mixes in business logic (e.g. a `ButtonClick` event
that both updates the screen and writes to the DB) can't just be marked
`excluded` wholesale** — log this case in `RULEBOOK.md` so the conversion
agent knows to extract only the business-logic part and drop only the
UI-triggered part, not an all-or-nothing choice per unit.

Skip this section without asking if no UI-layer units are detected (e.g.
this batch is pure batch/CLI tooling, like the department 200/300 simulated
scenarios).

### Identify units with pre-existing manual work — ask the human whether to keep them

After filling in `target_path` for every row, additionally check: this
`target_path` **already has a non-empty file**, and `migration/state/<unit_id>.json`
**doesn't exist yet** (meaning this kit's own pipeline never touched this
unit) — a signal that someone put something there manually (or otherwise)
before this kit ever got involved. Different from what `migration-convert`'s
scaffold-building idempotency protects (that protects directory
structure/build config files, not per-unit code files).

Whether to trust this existing work is a scope decision neither the domain
skill nor this skill can make for you — always ask the human. List the full
set (`unit_id` + `target_path` + matching `source_path`) so the human sees
the scope clearly, then ask with `AskUserQuestion` — they can answer for the
whole batch at once, or per unit if they prefer:

1. **Keep it, trust it as-is** — write `status: pass` directly into
   `migration/state/<unit_id>.json`, `last_note` = "manually pre-completed,
   human confirmed keep, never went through this kit's tests/review." The
   final burndown report must **list these separately from normal pipeline
   passes** — their confidence level differs from a pass that actually went
   through test-writer/reviewer, and the human needs to see that
   distinction.
2. **Keep it, but require verification** — test-writer runs as normal
   (getting real behavior per `ground_truth_tier`), **skip
   migration-translator**, go straight to test-reviewer reviewing the
   existing code; only if it fails do you ask the human whether to hand it
   to the kit for a fresh translation. The safest option: neither blind
   trust nor destroy-first. Record this decision in
   `migration/state/<unit_id>.json`'s `last_note` (e.g. "manually
   pre-completed, pending verification, skip conversion step") —
   `migration-convert` uses this note to decide whether to skip the
   conversion step.
3. **Don't trust it, let the kit retranslate** — proceed as normal
   `pending`, `migration-convert` will overwrite the existing file.
   **Explicitly tell the human this will overwrite the existing file, and
   they must confirm it's committed/backed up first** — don't assume this
   on the human's behalf; say so plainly in your report and let them confirm
   before continuing.

Skip this section without asking if no qualifying units are detected.

## 8. Confirm target-side prerequisites

This section decides/confirms, it doesn't build — actually constructing the
target project's scaffold (directory structure, build config files) is
`migration-convert`'s job now (its pre-flight checklist), since that's pure
mechanical execution of what's already decided here, not a judgment call
that needs your involvement. Don't create any files under `target/` in this
section.

What you do here: if the selected template project (same as "copy source
locally, fill in target_path, produce the full manifest" — if `RULEBOOK.md`
frontmatter has a `target_shape` field, use the template skill it points to)
declares external packages needed on the target side, confirm read-only
(e.g. `test -d node_modules`, `pip show <pkg>`) whether they're already
installed. If not, **stop and tell the human which install command to run
manually** — don't install anything yourself — same red line as "how to get
ground truth"'s "can't install things yourself," just on the target-language
side. Rerun this section to confirm once the human has installed it. This is
an early heads-up for the human, not the last check — `migration-convert`
re-confirms the same thing in its own pre-flight before it actually runs,
since real time may pass between this step and that call.

Nothing to confirm (purely standard-library target) → nothing to do here,
move on.

## 9. Mark the pilot subset

Add a `pilot` column to `migration/manifest.tsv` (values `yes`/`no`), mark
2-3 units `yes` from it — prioritize units with `risk_flag` = `high`, pair
with one typical/ordinary unit — mark everything else `no`. This subset is
what the conversion stage runs first: the rulebook hasn't been validated
against the whole batch yet, and if a rule has a systematic error, running
the pilot first contains the cost before it's spent on every unit.

Don't open a separate `pilot-manifest.tsv` file — that would turn the same
`unit_id`/`source_path`/`target_path` content into two records that need to
stay in sync. The `pilot` column is just one more column on `manifest.tsv`;
`migration-convert` filters its scope by this column, not by a separate file.

## Done when

Once all nine sections above are done, **you must always stop**, report the
full artifact list (`RULEBOOK.md` — including its frontmatter's
`domain_skill`/`ground_truth_tier`/`ground_truth_reason`/`target_shape` (if
that section applied)/`parity_check` (if enabled) fields, inventory, mismatch
report if any, manifest (with its `pilot` column), target-side prerequisite
status (packages confirmed installed, or what the human still needs to
install), and the list of any detected "pre-existing manual work" units with
their decisions).

List every `[domain-general]`-tagged rule from section 4 as its own item,
naming the domain skill file it's a candidate for (`.claude/skills/<domain
skill name>/SKILL.md`'s "syntax conversion / library replacement rules"
table). This is the only place this list surfaces — it isn't written to any
file, just called out in this report, since deciding whether to actually
fold a rule into the domain skill is a human judgment made between batches,
not something this run's artifacts need to track. **You never edit the
domain skill file yourself, regardless of how confident the tag is** — same
boundary as the rulebook itself, just on department-owned content instead of
this repo's own.

Don't auto-proceed to conversion — only after a human reviews these
decisions does the top-level orchestrator take `manifest.tsv`'s `pilot=yes`
rows to run `migration-convert`.

Add one reminder to your report: if this is the first run on this repo,
`.claude/settings.json` + `.claude/hooks/` should be copied over now (see
`migration`'s "before you start" section) so the syntax-check hook is in
place from the first pilot unit — not a hard prerequisite `migration-convert`
blocks on, but better done now than partway through. You don't check for or
create these files yourself — this is just a reminder, not your job.
