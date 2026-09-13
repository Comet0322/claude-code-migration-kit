#!/bin/bash
# SubagentStop hook for migration-translator and migration-test-writer (see
# ../settings.json's "hooks" key) — both write real target-language code
# (converted source / new-language tests) and can produce plain syntax
# errors just as easily. Runs a cheap, mechanical syntax check on the target
# project right before either subagent is allowed to finish and hand its
# result back — catches a plain syntax error before it ever reaches
# migration-test-reviewer, instead of only being caught later in that
# separate, more expensive step.
#
# Checks the whole target/ project, not just whatever file this turn
# touched: the hook gets no reliable list of which files changed this turn
# (see settings.README.md), and `mvn compile`/`ruff check` already scan a
# whole project anyway — narrowing the scope would add complexity for no
# benefit.
#
# Exit 2 blocks SubagentStop (Claude Code re-shows stderr to the subagent
# and makes it keep going instead of finishing). Exit 0 lets it stop
# normally. This is a bonus check, not a hard gate: if the relevant tool
# (mvn/ruff) isn't installed, skip silently rather than blocking a subagent
# over missing tooling it has no way to install itself (same "don't install
# things automatically" rule as everywhere else in this kit).
set -u

POM=$(find target -maxdepth 2 -name pom.xml 2>/dev/null | head -n1)
REQ=$(find target -maxdepth 2 -name requirements.txt 2>/dev/null | head -n1)

if [ -n "$POM" ]; then
  PROJECT_DIR=$(dirname "$POM")
  if ! command -v mvn >/dev/null 2>&1; then
    exit 0
  fi
  OUTPUT=$(cd "$PROJECT_DIR" && mvn -q compile 2>&1)
  STATUS=$?
elif [ -n "$REQ" ]; then
  PROJECT_DIR=$(dirname "$REQ")
  if ! command -v ruff >/dev/null 2>&1; then
    exit 0
  fi
  OUTPUT=$(cd "$PROJECT_DIR" && ruff check . 2>&1)
  STATUS=$?
else
  # No target project scaffolded yet, or neither pom.xml nor
  # requirements.txt found (e.g. a target-side template this hook doesn't
  # know about yet) — nothing this script knows how to check, don't block.
  exit 0
fi

if [ "$STATUS" -ne 0 ]; then
  echo "Syntax check failed in $PROJECT_DIR — fix these before finishing:" >&2
  echo "$OUTPUT" >&2
  exit 2
fi

exit 0
