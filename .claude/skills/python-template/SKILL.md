---
name: python-template
description: >
  Company-internal Python target-side knowledge base — usage rules for the
  boogie-sdk all-in-one package (config, crypto, infra/DB, device I/O,
  observability, governance) and both project-shape templates the company
  currently supports (FastAPI long-running service / background ETL batch)
  live here, so the same target-side knowledge doesn't fragment across
  several skills. Use when writing or reviewing any company-internal Python
  code that talks to the DB, does crypto/masking, needs logging, or builds
  one of these two project shapes — not limited to legacy migration. In the
  legacy-to-Python migration context, a domain-* skill's target-side
  knowledge (library docs, project-shape templates, test/build method)
  points here — don't duplicate it (also the direct target when no domain-*
  skill is installed and the migration orchestrator picks this template on
  its own). A different-language binding of the same company boogie-sdk convention as
  `java-template` — same backend MS SQL Server, same log-collection format,
  just the Python-side implementation.
---

# python-template: Company-Internal Python Target-Side Knowledge (Library + Project-Shape Templates)

This skill is the single entry point for company-internal Python
target-side knowledge, covering two things:

1. **How to use boogie-sdk** — applies no matter which project shape you're
   installing it into, stated once, not repeated per shape. Full API
   reference: [`boogie-sdk-api.md`](boogie-sdk-api.md) (facade pattern in
   section 3, per-module API in section 5, and a "migration cheat sheet" in
   section 7 mapping common legacy Delphi/VB6 patterns onto `boogie-sdk`
   calls — that mapping is the actual purpose of this library).
2. **Project-shape templates** — the company currently supports two:
   **FastAPI long-running service** and **background ETL batch**. First
   confirm which shape this batch of apps is (confirmed with the human by
   `migration-clarify`, see its "decide target project shape" section), then
   follow that shape's own directory structure/entry point/test-build
   method — don't apply both.

In the legacy migration context, a matching `domain-*` skill points its
target-side knowledge (template project, library docs, test/build method)
here — don't duplicate it. When no domain-* skill matches a batch, the
`migration` orchestrator can also point a migration straight at this skill
as `domain_skill`, no domain-* skill involved at all.

The `vendor/boogie-sdk-python/` subfolder holds a real, installable,
runnable implementation of `boogie-sdk` — a single `uv` package
(`boogie_sdk`, `src/` layout, Python >= 3.11). It's a training/simulation
SDK: infra connectivity (DB, cache, queue, object storage, service
discovery, HTTP, scheduler/locking, device protocols) is all in-memory
fakes or SQLite, not the real company infrastructure this document
describes; but where the operation itself is the point rather than the
infra behind it, the implementation is real (AES-256-GCM, SHA-256/512,
Ed25519, real SQL via SQLite, real Excel/PDF generation via
openpyxl/fpdf2) — enough to actually exercise the harness test
infrastructure end to end (imports, runs, tests pass/fail for real). It's
maintained inside this same skill folder alongside this `SKILL.md`, not a
separate thing, and is registered as a member of this repo's root `uv`
workspace.

## Using boogie-sdk

Conversion rules reference these interfaces directly — no need to pick your
own DB/crypto/logging solution, and don't bypass this to wire up
`sqlite3`/`logging`/`cryptography` from the standard library yourself. Full
signatures for every client below: [`boogie-sdk-api.md`](boogie-sdk-api.md)
section 5.

```python
from boogie_sdk import BoogieSdk

sdk = BoogieSdk.init()

# DB (infra) -- named `:param` placeholders, never string concatenation.
# `sdk.db` is a DbClient: `.query`/`.execute` run standalone, no session
# wrapper. `.transaction` takes a callable (not a context manager) — it
# receives a DbSession with the same `.query`/`.execute` and commits if the
# callable returns normally, rolls back on any exception raised inside it.
rows = sdk.db.query("SELECT id, name FROM users WHERE dept = :dept", {"dept": "200"})

def _rename(session):
    session.execute("UPDATE users SET name = :name WHERE id = :id", {"name": "foo", "id": 1})

sdk.db.transaction(_rename)

# Logging (observability) -- one JSON object per line to stdout.
# `.error` takes the exception object itself as `exc=`, not `exc_info=True`.
sdk.logger.info("fetched user", unit_id="u123", user_id=1)
sdk.logger.error("db timeout", exc=some_exception, unit_id="u123")

# Crypto -- real AES-256-GCM/SHA/Ed25519, in-memory key management
ciphertext = sdk.crypto.encrypt_aes(plaintext, key_id="key-1")

# Masking is NOT on sdk.crypto -- it's module-level functions, imported
# directly, the one deliberate exception to the "everything is a
# Xxx*Client on sdk.*" convention.
from boogie_sdk.crypto import mask_util
masked_phone = mask_util.mask_phone(phone)

sdk.close()
```

Every accessor on `sdk` is a **property**, not a method call (`sdk.db`,
`sdk.crypto`, `sdk.logger`), except `deviceio` clients which are grouped one
level deeper as methods, e.g. `sdk.deviceio.report_generator()`. Module
summary (full detail in [`boogie-sdk-api.md`](boogie-sdk-api.md) section 5):

| Module | Covers | Example call |
|---|---|---|
| `config` | `.ini`/env-based app configuration | `sdk.config.get("some_key")` |
| `crypto` | Encryption, secrets, tokens, certs, masking (real AES/SHA/Ed25519) | `sdk.crypto.encrypt_aes(data, key_id="k1")` |
| `infra` | DB, cache, queue, object storage, service discovery, HTTP, scheduler/locking | `sdk.db.query("SELECT * FROM t")` |
| `deviceio` | Device protocols, file polling, flat-file parsing, Excel/PDF reports, batch/shift tracking, SPC | `sdk.deviceio.report_generator().generate_excel(...)` |
| `observability` | Structured logging, metrics, tracing | `sdk.logger.info("done", batch_id=id)` |
| `governance` | ID generation, feature flags, rate limiting, notifications, health checks, audit trail | `sdk.audit.record(actor=..., action=..., resource=..., result=...)` |

- DB parameters always use named `:name` placeholders — `conn`/`tx` handle
  escaping themselves.
- Connection pooling/retries/timeouts, log formatting, and crypto key
  management are all built into `BoogieSdk.init()` — conversion rules don't
  need to reimplement any of this.
- Output is always one JSON object per line (timestamp, level, logger name,
  message, extra fields) written to stdout — the same format as
  `java-template`'s logger; no need to configure a handler/formatter
  yourself.
- The package must be installed manually by a human beforehand in a real
  (non-vendored) target project (not on public PyPI; in an air-gapped
  environment a human needs to install it from the internal package
  repo/a vendored wheel first). **Read-only confirmation method: actually
  import it** (`.venv/bin/python -c "import boogie_sdk"`) — don't use `pip
  show`/`uv pip show`, they report a false "not found" for a
  workspace-member or editable/path install even when it's genuinely
  usable, and this machine's `.venv` (built with `uv venv`) may not even
  have a `pip` module to run that command with in the first place. Import
  fails → stop and tell the human to install it first, don't run the
  install command yourself. Within this repo, `boogie-sdk` is already a
  member of the root `uv` workspace (`uv sync --all-packages` from the
  repo root), so this
  check only matters for a project built *outside* this repo.

## Project shape: FastAPI long-running service

This shape assumes this batch of apps needs to run as a resident HTTP
service, not a batch job that runs to completion and exits. See "using
boogie-sdk" above for DB/crypto/logging usage, not repeated here.

```
target/<unit-group-or-app-name>/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point: builds the FastAPI app,
│   │                             # mounts routes
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
- `boogie-sdk` (see "using boogie-sdk" above).

The human must run manually first: `.venv/bin/python -m pip install -r
requirements.txt`. Read-only confirmation: `.venv/bin/python -m pip show
fastapi`, `.venv/bin/python -m pip show uvicorn` (same venv/PEP-668 caveat
as "using boogie-sdk" above — don't use a bare system-level `pip show`).
Coming up empty → stop and tell the human to install it first, don't run
the install command yourself.

boogie-sdk doesn't ship an ASGI request-logging middleware (that's outside
what this training SDK models) — call `sdk.logger.info(...)` directly in
whichever routes/dependencies need per-request logging, rather than
expecting one bundled middleware to cover every route automatically.

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

The reference implementation of this shape is
[`vendor/boogie-sdk-python/examples/etl_demo/`](vendor/boogie-sdk-python/examples/etl_demo/)
— treat it as the concrete template, not just the description below. Every
boogie-sdk ETL example, regardless of language, uses this same fixed
4-file shape (Extract/Transform/Load plus an orchestrator):

```
target/<unit-group-or-app-name>/
├── main.py                # Orchestrator: wires up BoogieSdk, batch/shift
│                           # tracking, logger/tracer/metrics, calls
│                           # download -> process -> upload in order, prints
│                           # the final summary. Owns the DB connection
│                           # (sdk.db) and hands it to download() -- download
│                           # never reaches back into the wider sdk facade
│                           # itself.
├── download.py             # Extract: seeds/reads the source data. This is
│                            # the only stage that touches the database, so
│                            # its SQL lives as separate files under sql/
│                            # (loaded from disk) rather than being embedded
│                            # as string literals. If a real migrated job's
│                            # process/upload stages don't touch the DB
│                            # either (transform is pure in-memory, load is
│                            # object storage/queue), don't force SQL into
│                            # them just to have three files with SQL.
├── process.py               # Transform: masks a PII field via mask_util,
│                            # encrypts one via sdk.crypto, validates each
│                            # row, isolates a
│                            # bad row (audit + notification) without
│                            # crashing the batch.
├── upload.py                # Load: writes to sdk.object_storage/sdk.queue,
│                            # produces the Excel/PDF summary report via
│                            # sdk.deviceio.report_generator().
├── sql/                    # download.py's externalized SQL, one .sql file
│                           # per statement (only present if this stage is
│                           # SQL-driven).
├── tests/                  # pytest suite — see "Test / build method" below.
└── requirements.txt
```

Don't mix these four *application* files' responsibilities (e.g. don't put
transform logic in `main.py`), and don't split the application logic into a
5th file to make it feel more granular — exactly 4 files there,
responsibilities as above; `tests/`/`requirements.txt` are separate from
that count, not exceptions to it.

Entry point: `python main.py` (or, for the vendored reference demo itself,
`uv run --package boogie-sdk python
vendor/boogie-sdk-python/examples/etl_demo/main.py`). Success criterion:
the process runs to completion and exits naturally with exit code 0, and
the log shows each stage's own completion message — **no HTTP health
check**, since this isn't a resident service; any stage that raises an
uncaught exception outside the per-row isolation in `process.py` must let
the whole process exit with a non-zero code — don't swallow the error and
let the process look like it finished normally.

External packages (not pure standard library):
- `boogie-sdk` (see "using boogie-sdk" above).
- Generally nothing else beyond the standard library is needed; if these
  jobs need scheduled triggering, the scheduling itself (cron/an internal
  scheduling system) is a deployment concern, not part of this template.

The human must run manually first: `.venv/bin/python -m pip install -r
requirements.txt`. Read-only confirmation: same method as "using
boogie-sdk" above (actually import each package, not `pip show`). Import
fails → stop and tell the human to install it first, don't run the install
command yourself.

### Test / build method (ETL batch)

- Run tests: `.venv/bin/python -m pytest tests/ -q` (for the vendored
  reference SDK itself: `uv run --package boogie-sdk pytest
  vendor/boogie-sdk-python/tests -q`, 266 tests as of this writing, all
  against the observable behavior of the in-memory fakes/real libraries —
  no external services or Docker required).
- Confirm the whole app imports (no real DB connection involved):
  `.venv/bin/python -c "from main import main"`
- Integration check (run once after migration-convert has every unit
  passing): run `.venv/bin/python main.py`, confirm the process exits with
  code 0 and the log shows every stage's completion message, then run the
  full `.venv/bin/python -m pytest tests/ -q` once more.
  - **If the legacy source never creates its own tables** (a normal case,
    not an edge case — most production DB code assumes the schema already
    exists externally): a bare `python main.py` will fail with
    `sqlite3.OperationalError: no such table`, since `boogie-sdk`'s
    `DbClient` is an in-memory-only fake that starts genuinely empty every
    process launch, with no way to represent "the real DB already has
    these tables." This is **not** a translation defect — don't treat it
    as an integration-check failure. Instead, seed the same schema the
    test suite's own fixtures already create (reuse it, don't invent a
    second copy) via a throwaway setup script before running `main.py`, so
    the check exercises the assembled program against a DB shaped the way
    production actually is. Record in the integration-check note that the
    schema was pre-seeded and why — a human reading the result later needs
    to know this wasn't a zero-setup run.
