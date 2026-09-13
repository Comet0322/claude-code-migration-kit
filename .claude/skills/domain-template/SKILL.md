---
name: domain-template
description: >
  [Template, do not use directly] Skeleton for packaging domain knowledge.
  Copy this folder, rename it to domain-<your-app-type> (e.g.
  domain-legacy-billing), and replace every section below with real facts
  about this batch of legacy code. The migration-clarify skill scans
  .claude/skills/domain-* to list every packaged domain skill as a
  candidate. This template itself must never be selected — everything in it
  is a placeholder.
---

# Domain Skill Template

This document isn't meant to be executed — it's meant to be filled in. Once
filled in and renamed, it becomes a real domain skill that can show up in
migration-clarify's selection menu.

The eight content sections below run in "source → conversion rules → target"
order. Read/fill them in that order and you'll naturally understand what the
old code looks like, then how the two sides map, then what the target looks
like, without jumping back and forth. The two sections after that
("extracting shared knowledge into its own skill" and "when a single domain
skill's content is too large") are authoring notes for whoever fills this
in, not content itself — that's why they come last.

## App types this domain skill covers

[One sentence describing which batch of legacy code this knowledge applies
to. Write concrete, machine-comparable fingerprints where you can — common
private-package import paths, specific config filenames, specific framework
versions — migration-clarify matches these against the actual code to guess
"which domain skill probably applies here" as a recommendation.]

## Private package documentation

[Documentation for the private/internal library(ies) this batch of apps
shares. **Embed the actual content, or point to a file path inside the
repo — never an external URL.** Agents have no browser; in an air-gapped
environment a link that can't even be reached is worse than useless.

If this private package's own implementation ships as **source code**
alongside each app in the migrated repo (a common pattern for Delphi
private packages: `.pas` unit files travel with the application, not just a
compiled `.dll`/`.bpl`), **name those implementation files explicitly**
(e.g. "this private package's implementation is
`Dept200Data.pas`/`Dept200Log.pas`"). migration-clarify matches this against
`manifest.tsv` and marks the corresponding units `excluded` (the private
package's own implementation doesn't need line-by-line translation — the
target side already has a replacement library defined here, only the
calling code needs conversion). Without naming the files, this automation
doesn't happen and those units get translated like ordinary application
code — wasted conversion/test cost.

If this private package's source **isn't visible** in the migrated repo
(e.g. it's just an externally-provided compiled COM DLL pulled in via an
`Object=` reference), don't name any files — code that calls this package
already gets scanned by `migration-analyze` as part of the calling unit;
there's no separate "package itself" unit to exclude.]

## UI/scope conventions (optional)

[If this batch of apps typically has a UI layer (`.frm`/`.dfm`, or
`uses`/`import` clauses referencing UI framework units), record this
department's past convention on "should the UI migrate too" and why (e.g.
"past migrations of this batch always dropped the UI and kept only core
logic, because the new system standardizes on a different frontend").

This section records **convention, not a pre-made decision for you** — UI
keep/drop is ultimately a scope decision. `migration-clarify` still uses
`AskUserQuestion` to ask the human whenever it detects UI-layer units,
regardless of what's written here; the only difference is that a filled-in
convention gets attached to that question as the recommended option (the
human is confirming "match past convention?" instead of guessing from
scratch), while an empty section just asks plainly with no recommendation.

No UI layer, or you don't know the past convention — omit this section
entirely (heading included) rather than leaving an empty body; don't invent
a "convention" that never actually existed just to fill it.]

## Source language runtime environment (optional)

[If you know how to get a compiler/interpreter for this source language in
an ordinary environment, write the exact method (command, Docker image,
internal tool link). migration-clarify uses this to judge "is a usable
environment available"; if unsure, or this machine may not be able to
install it, leave it blank or write "unknown, confirm on the spot during
migration-clarify" — don't invent one just to fill the section. With no
usable environment, migration-clarify falls back to asking the human for
mock data/snapshots instead — no agent will install anything not written
here on its own.]

## Syntax conversion / library replacement rules

[Old library → new library mapping table. This is the rulebook's seed: any
translation decision where "two agents might choose differently" belongs
here — don't wait until rulebook drafting to decide it on the fly.

**This table is a living domain rulebook, not something you write once and
leave alone.** Every real migration using this domain skill will surface
codebase-specific rules during `migration-clarify`'s rulebook drafting that
this table didn't cover. Some of those are genuinely one-off (specific to
that one repo's quirks); others are really general facts about this
domain's private package/library that any app using it would hit — those
belong here, not stuck in a single repo's `migration/clarify/RULEBOOK.md` forever.
`migration-clarify` flags candidates for you at the end of its run (see its
"Done when" section) — periodically review that list and fold the ones that
generalize into this table, so the next migration using this domain skill
starts from a stronger seed instead of rediscovering the same pattern from
scratch. This is a human decision made between batches, same as any other
edit to this file — no agent updates this table on its own.]

## Template project

[The expected target project skeleton after conversion — directory
structure, entry point, what the build config files should look like.
migration-clarify uses this to decide each unit's `target_path`;
migration-convert uses it to actually build the scaffold in its own
pre-flight (mechanical execution of the shape decided here, not a judgment
call, so it doesn't happen in migration-clarify).

The entry point needs more than "where the file is" — also write **how to
run it and what counts as success**. Once every unit is converted,
migration-convert does a one-time integration check: build the whole target
project, run every test, and run the entry point described here once, to
confirm the assembled program actually works — not just each file passing
its own test. Example: "entry point `target/src/main.py`, run `python3
target/src/main.py --help`, printing usage text counts as success." If this
batch of apps has no natural single entry point (e.g. it's a pile of
independent library functions), say so explicitly — migration-convert will
skip "run the entry point" and only do "run every test together."

If the target language needs external packages (not pure standard library):
list them, the command for **the human to install manually beforehand**
(e.g. `npm install`, `pip install -r requirements.txt`), and how to
**confirm read-only** that they're already installed (e.g. `test -d
node_modules`, `pip show <pkg>`). migration-clarify's "confirm target-side
prerequisites" section and migration-convert's pre-flight check both use
this read-only method — not installed → stop and tell the human, no agent
ever runs the install command itself (a symmetric rule to "source language
runtime environment" above, just on the target-language side). Pure
standard library, no extra packages needed → say "none" explicitly.]

## New-language library docs

[A **summary** of how to use the target language's replacement libraries,
written directly here — **not an external URL**. Agents have no browser to
open a link, and an air-gapped environment can't reach one anyway — a bare
link is as good as no documentation to a conversion agent. Keep it short;
what matters is that it's self-contained enough to actually use, not a path
the agent has to go figure out on its own.]

## Test / build method

[Concrete commands for how this batch of apps runs tests and builds. Used
by migration-test-reviewer, and checked for existence by the conversion
skill's guardrails.]

## Extracting shared knowledge into its own skill (optional, target-side sharing only)

If a domain skill's "template project," "new-language library docs," or
"test/build method" section is **identical** across other domain skills,
don't copy-paste it into each one — extract it into its own skill, and
rewrite the corresponding section as one line: "same as skill `<skill
name>`."

The typical case is **target-side sharing**: different departments,
different source languages, but converting to the same target language
using the same internal library/conventions — e.g. `python-template`,
`java-template`.

Give the extracted skill a clear, triggerable `description` — this kind of
skill is usually useful outside migration too (anyone writing
company-compliant code in this language), not just for migration.

**Don't extract "app types this domain skill covers," "private package
documentation," "source language runtime environment," or "syntax
conversion/library replacement rules" into their own skill** — even when
the same source code is planned/already migrated to more than one target
language (e.g. both `domain-<app>-java` and `domain-<app>-python` exist),
these sections stay filled in directly in each domain skill, duplicated
across both: the same batch of source facts is usually small, and the
maintenance cost of an extra shared skill (one more indirection layer to
keep in sync) outweighs what duplication saves. "Syntax conversion/library
replacement rules" in particular can never be shared by nature (it's a
mapping from *this specific source* to *this specific target* — change the
target language and the right-hand column is completely different);
forcibly extracting the other sections would just scatter one domain
skill's content across two files, forcing the reader to open another skill
before they have the full source-side picture.

Avoid a name starting with `domain-` — this kind of skill isn't a candidate
for "which domain skill applies to this legacy codebase," and
`migration-clarify` shouldn't list it as an option when scanning `domain-*`.

When `migration-clarify`'s "load domain skill content" step sees "template
project," "new-language library docs," or "test/build method" written as
"same as skill `<name>`," it additionally uses the Skill tool to load that
skill's actual content, then feeds it along to rulebook drafting and the
three conversion-stage subagents — the subagents themselves have no Skill
tool access, so clarify/convert read it in and relay it, not the subagents
calling it directly.

### When the target side isn't a single convention: list multiple options in the "template project" section

The same target language may not have just one project convention
company-wide — e.g. target Python might have both a "FastAPI service" and a
"background ETL batch" shape. In that case **don't** split into multiple
skills — put them in different subsections of the same shared target-side
skill instead (e.g. under `python-template`: "using corplib" holds the
DB/logging usage genuinely shared across shapes, while "project shape:
FastAPI long-running service" and "project shape: background ETL batch"
each get their own section for skeleton/entry point/test-build method).
Keep the same target-side knowledge sectioned within one skill, not
scattered across several — so a reader doesn't need several skills open at
once to piece together the full target-side picture.

The domain skill's "template project" section then lists options instead of
a single "same as skill `<name>`," pointing at different sections of the
same skill, e.g.:

```
This batch's target Python project could be a FastAPI service or a
background ETL batch, pick one:
- Same as skill `python-template`'s "Project shape: FastAPI long-running
  service" section
- Same as skill `python-template`'s "Project shape: background ETL batch"
  section
```

When `migration-clarify` sees multiple options listed, it uses
`AskUserQuestion` to confirm with the human which one applies to this
migration (see `migration-clarify`'s "decide target project shape" section)
— **where that decision gets recorded and in what format is
migration-clarify's own implementation detail; the domain skill doesn't
need to know or hardcode a specific filename/field name**: that's a storage
mechanism owned by the migration side, and hardcoding it here would force
every already-written domain skill to be edited whenever migration-clarify
later changes how it stores that decision. Only one shape → write a single
"same as skill `<name>`" directly, don't list multiple options "just in
case."

## When a single domain skill's content is too large: split into reference files in the same folder (optional)

Different from "extracting shared knowledge into its own skill" above —
that section solves "other skills need this knowledge too, worth
maintaining independently"; this one is about "this knowledge is only used
by this one domain skill, it's just too much to fit into a single
`SKILL.md`." The criteria differ, don't conflate them: the former looks at
"is any other skill sharing this," the latter looks at "would the volume
make `SKILL.md` too bloated."

For a real department's domain skill, these sections are often much bigger
than this repo's simulated scenarios:

- **Private package documentation** — a real private library often has far
  more than one or two classes/methods; the full API listed out could run
  several pages.
- **Syntax conversion/library replacement rules** — this is the rulebook's
  seed, and a real legacy codebase's translation decisions are often far
  more than a handful — could be dozens.
- **New-language library docs** — if this domain skill has no shared
  target-side template skill and embeds full documentation itself, this can
  also get large.

When it's too large, move the actual content to
`references/<descriptive-filename>.md` inside this domain skill's own
folder (e.g.
`.claude/skills/domain-<app>/references/private-package.md`), and rewrite
the corresponding `SKILL.md` section as one line pointing at that relative
path plus a sentence on what's in it (e.g. "full private-package API in
`references/private-package.md` (all classes/method signatures and
examples)").

The difference from "same as skill `<name>`": that points at **another
skill**, loaded with the Skill tool; this points at **a file inside this
same skill's own folder** — a relative path (not a skill name), read
directly with the Read tool. Don't mistake it for another skill name and
try calling the Skill tool with it (it wouldn't resolve anyway — a path
like this was never a registered skill). When `migration-clarify`'s "load
domain skill content" step sees a section whose content is a relative path
(has a `/`, usually a `.md` extension — clearly different from the bare
skill-name pattern of "same as skill `<name>`"), it reads it directly with
the Read tool and treats it exactly as if it were inline content.

Don't split preemptively "just in case" when the content isn't actually
large — `SKILL.md` itself gets loaded in full whenever the skill triggers;
splitting exists to keep rarely-needed bulk content from padding out
something that loads every single time, not a formatting requirement. A
private-package doc that's one or two paragraphs, or a mapping table with
four or five rows, is fine staying right in `SKILL.md`.
