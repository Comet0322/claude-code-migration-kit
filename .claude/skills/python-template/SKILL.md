---
name: python-template
description: >
  Company-internal Python target-side knowledge base — usage rules for the
  corplib all-in-one package (DB access + structured logging) and both
  project-shape templates the company currently supports (FastAPI
  long-running service / background ETL batch) live here, so the same
  target-side knowledge doesn't fragment across several skills. Use when
  writing or reviewing any company-internal Python code that talks to the
  DB, needs logging, or builds one of these two project shapes — not
  limited to legacy migration. In the legacy-to-Python migration context,
  domain-200-delphi-python's and domain-300-vb-python's target-side
  knowledge (library docs, project-shape templates, test/build method) all
  point here — don't duplicate it. A different-language binding of the same
  company DB/logging convention as `java-template` — same backend MS SQL
  Server, same log-collection format, just the Python-side implementation.
---

# python-template: Company-Internal Python Target-Side Knowledge (Library + Project-Shape Templates)

This skill is the single entry point for company-internal Python
target-side knowledge, covering two things:

1. **How to use corplib** (DB + Logging) — applies no matter which project
   shape you're installing it into, stated once, not repeated per shape.
2. **Project-shape templates** — the company currently supports two:
   **FastAPI long-running service** and **background ETL batch**. First
   confirm which shape this batch of apps is (confirmed with the human by
   `migration-clarify`, see its "decide target project shape" section), then
   follow that shape's own directory structure/entry point/test-build
   method — don't apply both.

In the legacy migration context, both `domain-200-delphi-python` and
`domain-300-vb-python` point their target-side knowledge (template project,
library docs, test/build method) here — don't duplicate it.

The `vendor/corplib-python/` subfolder holds a real, installable, runnable
minimal implementation of `corplib` (backed by SQLite, not the real MS SQL
Server this document describes — purely so the harness test infrastructure
can verify the whole pipeline actually imports, runs, and passes/fails
tests; it's not the company's real production package, nor a substitute for
the behavior this document describes) — maintained inside this same skill
folder alongside this `SKILL.md`, not a separate thing.

## Using corplib (DB + Logging)

Conversion rules reference these interfaces directly — no need to pick your
own DB/logging solution, and don't bypass this to wire up `sqlite3`/`logging`
from the standard library yourself.

### `corplib.db`

```python
from corplib.db import Database

db = Database.from_env()  # reads the CORPLIB_DB_DSN env var; internally
                           # uses a pyodbc connection pool pointing at the
                           # same MS SQL Server as the old system

# Query
with db.session() as conn:
    rows = conn.fetch_all(
        "SELECT id, name FROM users WHERE dept = :dept", {"dept": "200"}
    )
    row = conn.fetch_one("SELECT * FROM users WHERE id = :id", {"id": 1})

# Write / transaction
with db.transaction() as tx:
    tx.execute(
        "UPDATE users SET name = :name WHERE id = :id",
        {"name": "foo", "id": 1},
    )
    # commits only if the with-block exits normally; an exception rolls back
    # automatically
```

- Parameters always use named `:name` placeholders — `conn`/`tx` handle
  escaping themselves; never build SQL by string concatenation.
- Connection pooling, retries, and timeouts are all built into
  `Database.from_env()` — conversion rules don't need to reimplement any of
  this.

### `corplib.logging`

```python
from corplib.logging import get_logger

logger = get_logger(__name__)
logger.info("fetched user", extra={"unit_id": "u123", "user_id": 1})
logger.error("db timeout", extra={"unit_id": "u123"}, exc_info=True)
```

- Output is always one JSON object per line (timestamp, level, logger name,
  message, extra fields) written to stdout, handled by an external log
  collector — no handler/formatter configuration needed.
- The package must be installed manually by a human beforehand (not on
  public PyPI; in an air-gapped environment a human needs to install it
  from the internal package repo/a vendored wheel first). Read-only
  confirmation method: this machine uses a project-level `.venv` (built
  with `uv venv`) — check `.venv/bin/python -m pip show corplib` or `uv pip
  show --python .venv/bin/python corplib` — **don't use a bare
  system-level `pip show corplib`**; this machine's Homebrew Python
  disallows system-level installs by default (PEP 668), so a bare command
  coming up empty doesn't mean it's not installed, it means you checked the
  wrong place. Coming up empty → stop and tell the human to install it
  first, don't run the install command yourself.

## Project shape: FastAPI long-running service

This shape assumes this batch of apps needs to run as a resident HTTP
service, not a batch job that runs to completion and exits. See "using
corplib" above for DB/logging usage, not repeated here.

```
target/<unit-group-or-app-name>/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point: builds the FastAPI app,
│   │                             # mounts routes, mounts corplib's
│   │                             # logging middleware
│   ├── api/
│   │   └── routes_<unit_id>.py  # One router file per migrated unit
│   ├── core/
│   │   └── config.py            # pydantic BaseSettings, reads env vars
│   │                             # (DB DSN, log level, etc.)
│   └── models/
│       └── <unit_id>.py         # pydantic schema for this unit
├── tests/
│   └── test_<unit_id>.py
└── requirements.txt
```

Entry point: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Success
criterion: it starts and `GET /healthz` returns 200 (`main.py` mounts its
own `/healthz` route returning `{"status": "ok"}` — this doesn't correspond
to any one legacy unit, it's purely an entry-point health check).

External packages (not pure standard library):
- `fastapi`, `uvicorn`, `pydantic` (public packages).
- `corplib` (see "using corplib" above).

The human must run manually first: `.venv/bin/python -m pip install -r
requirements.txt`. Read-only confirmation: `.venv/bin/python -m pip show
fastapi`, `.venv/bin/python -m pip show uvicorn` (same venv/PEP-668 caveat
as "using corplib" above — don't use a bare system-level `pip show`). Coming
up empty → stop and tell the human to install it first, don't run the
install command yourself.

`main.py` must mount `from corplib.logging import RequestLoggingMiddleware`
and call `app.add_middleware(RequestLoggingMiddleware)` — every request
then automatically logs one line with a trace_id, so conversion rules don't
need to log request-level detail in every router themselves.

### Test / build method (FastAPI)

- Run tests: `.venv/bin/python -m pytest tests/ -q`
- Confirm the whole app imports (no real DB connection involved):
  `.venv/bin/python -c "from app.main import app"`
- Integration check (run once after migration-convert has every unit
  passing): start `.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0
  --port 8000`, `curl -sf http://localhost:8000/healthz` returning 200
  counts as the entry-point check passing, then run the full
  `.venv/bin/python -m pytest tests/ -q` once more.

## Project shape: background ETL batch

This shape assumes this batch of apps is scheduled/manually triggered, runs
to completion once, and exits — not a resident HTTP service. See "using
corplib" above for DB/logging usage, not repeated here.

```
target/<unit-group-or-app-name>/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point: runs each job in sequence,
│   │                             # then exits — not resident
│   ├── jobs/
│   │   └── job_<unit_id>.py     # One batch-job module per migrated unit,
│   │                             # exposing a run() function
│   └── core/
│       └── config.py            # reads env vars (DB DSN, log level, etc.)
├── tests/
│   └── test_<unit_id>.py
└── requirements.txt
```

Entry point: `python -m app.main`. Success criterion: the process runs to
completion and exits naturally with exit code 0, and the log shows each
job's own completion message (e.g. `logger.info("job done", extra={"job":
"<unit_id>"})`) — **no HTTP health check**, since this isn't a resident
service; any job in `main.py` that raises an uncaught exception must let
the whole process exit with a non-zero code — don't swallow the error and
let the process look like it finished normally.

External packages (not pure standard library):
- `corplib` (see "using corplib" above).
- Generally nothing else beyond the standard library is needed; if these
  jobs need scheduled triggering, the scheduling itself (cron/an internal
  scheduling system) is a deployment concern, not part of this template.

The human must run manually first: `.venv/bin/python -m pip install -r
requirements.txt`. Read-only confirmation: same method as "using corplib"
above (`pip show corplib`, project-level `.venv`, never a bare system-level
check). Coming up empty → stop and tell the human to install it first,
don't run the install command yourself.

### Test / build method (ETL batch)

- Run tests: `.venv/bin/python -m pytest tests/ -q`
- Confirm the whole app imports (no real DB connection involved):
  `.venv/bin/python -c "from app.main import main"`
- Integration check (run once after migration-convert has every unit
  passing): run `.venv/bin/python -m app.main`, confirm the process exits
  with code 0 and the log shows every job's completion message, then run
  the full `.venv/bin/python -m pytest tests/ -q` once more.
