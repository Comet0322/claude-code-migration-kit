# boogie-sdk (Python)

`boogie-sdk` is a simulated internal-platform library used for training and
onboarding: it stands in for the kind of all-in-one corporate SDK a large
org builds around its infra (DB, cache, queue, object storage, device
protocols, observability, governance, ...). Backends that would normally
mean standing up real infrastructure -- databases, message queues, object
storage, device connections -- are **in-memory fakes**, so the whole thing
runs with zero external services. Where the operation itself is the point
rather than the infra behind it, the implementation is real: AES-256-GCM
encryption, SHA-256/512 hashing, Ed25519 signing, SQL execution (SQLite
under the hood), and Excel/PDF report generation all do genuine work. Every
module is reached through a single facade, `BoogieSdk`, mirroring how a real
internal platform SDK is usually consumed.

See [`boogie-sdk-api.md`](../../boogie-sdk-api.md) for the full
design doc and API reference, including the facade pattern (section 3) and
a "migration cheat sheet" (section 7) mapping common legacy Delphi/VB6
patterns onto `boogie-sdk` calls -- that mapping is the actual purpose of
this library: helping migrate old internal tools to Python.

## Install / setup

This package is vendored inside the `python-template` skill (as a member of
the repo's `uv` workspace, not a standalone project) so
`migration-clarify`/`migration-convert` can find it without any extra
setup. From the **repo root**:

```
uv sync --all-packages
```

Only resync this way (or `uv add <pkg>` from inside
`.claude/skills/python-template/vendor/boogie-sdk-python/` to add a
dependency for this package specifically) -- avoid a bare `uv sync`.

## Running tests

From the repo root:

```
uv run --package boogie-sdk pytest .claude/skills/python-template/vendor/boogie-sdk-python/tests -q
```

266 tests as of this writing, all against the observable behavior of the
in-memory fakes (no external services or Docker required).

## Quickstart

```python
from boogie_sdk import BoogieSdk

sdk = BoogieSdk.init()

ciphertext = sdk.crypto.encrypt_aes(b"secret payload", key_id="key-1")
sdk.db.execute("CREATE TABLE widgets (id INTEGER PRIMARY KEY, name TEXT)")
sdk.db.execute("INSERT INTO widgets (name) VALUES (:name)", {"name": "gadget"})
sdk.logger.info("widget inserted", table="widgets")

sdk.close()
```

## Modules

Every module is reached off the `sdk` facade returned by `BoogieSdk.init()`
(see [`boogie-sdk-api.md` section 5](../../boogie-sdk-api.md#5-模組-api-參考)
for the complete API of each). `deviceio` clients are grouped one level
deeper, e.g. `sdk.deviceio.report_generator()`.

| Module | Simulates | Example call |
|---|---|---|
| `config` | `.ini`/env-based app configuration | `sdk.config.get("some_key")` |
| `crypto` | KMS-backed encryption, secrets, tokens, certs (real AES/SHA/Ed25519) | `sdk.crypto.encrypt_aes(data, key_id="k1")` |
| `infra` | DB, cache, queue, object storage, service discovery, HTTP, scheduler/locking | `sdk.db.query("SELECT * FROM t")` |
| `deviceio` | Device protocols, file polling, flat-file parsing, Excel/PDF reports, batch/shift tracking, SPC | `sdk.deviceio.report_generator().generate_excel(...)` |
| `observability` | Structured logging, metrics, tracing | `sdk.logger.info("done", batch_id=id)` |
| `governance` | ID generation, feature flags, rate limiting, notifications, health checks, audit trail | `sdk.audit.record(actor=..., action=..., resource=..., result=...)` |

## Example: a full migrated batch job

[`examples/etl_demo/`](examples/etl_demo/) is the reference template for
what a full migrated legacy batch job looks like end to end -- extract from
`sdk.db`, mask/encrypt a PII field, load to `sdk.object_storage` and
`sdk.queue`, track the run with `sdk.deviceio.batch_tracker()`/
`shift_calendar()`, observe it with `sdk.logger`/`sdk.metrics`/`sdk.tracer`,
and close out with an `sdk.audit` trail entry and an `sdk.notification`
email on a simulated row failure. Run it with:

```
uv run --package boogie-sdk python .claude/skills/python-template/vendor/boogie-sdk-python/examples/etl_demo/main.py
```
