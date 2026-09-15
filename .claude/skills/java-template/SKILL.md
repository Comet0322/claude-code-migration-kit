---
name: java-template
description: >
  Company-internal Java target-side knowledge base — usage rules for the
  boogie-sdk all-in-one package (config, crypto, infra/DB, device I/O,
  observability, governance) and the one project-shape template the company
  currently supports (background ETL batch, using Spring Boot's
  `CommandLineRunner`, runs to completion and exits — not a resident web
  service) live here, so the same target-side knowledge doesn't fragment
  across several skills. Use when writing or reviewing any company-internal
  Java batch code that talks to the DB, does crypto/masking, or needs
  logging — not limited to legacy migration. In the legacy-to-Java migration
  context, a domain-* skill's target-side knowledge (template project,
  library docs, test/build method) points here — don't duplicate it (also
  the direct target when no domain-* skill is installed and the migration
  orchestrator picks this template on its own). A different-language binding
  of the same company boogie-sdk convention as `python-template` — same backend MS SQL
  Server, same log-collection format, just the Java-side implementation.
  Java currently has only this one project shape, unlike the Python side
  where `python-template` itself splits into FastAPI-service/ETL-batch
  sections; if Java ever needs a long-running-service shape too, add a
  section here the same way `python-template` does — don't split into a
  separate skill.
---

# java-template: Company-Internal Java Target-Side Knowledge (Library + Project-Shape Templates)

This skill is the single entry point for company-internal Java target-side
knowledge, covering two things:

1. **How to use boogie-sdk** — applies no matter which project shape you're
   installing it into, stated once, not repeated. Full API reference:
   [`boogie-sdk-api.md`](boogie-sdk-api.md) (facade pattern in section 3,
   per-module API in section 5, and a "migration cheat sheet" in section 7
   mapping common legacy Delphi/VB6 patterns onto `boogie-sdk` calls — that
   mapping is the actual purpose of this library).
2. **Project-shape templates** — Java currently has only one: **background
   ETL batch**.

In the legacy migration context, a matching `domain-*` skill references this
skill as its "template project / new-language library docs / test-build
method" content — not maintained separately. When no domain-* skill matches
a batch, the `migration` orchestrator can also point a migration straight at
this skill as `domain_skill`, no domain-* skill involved at all.

The `vendor/boogie-sdk-java/` subfolder holds a real, compilable, runnable
implementation of `boogie-sdk` — a single-module Maven project (`com.boogie.sdk`,
Java 17). It's a training/simulation SDK: infra connectivity (DB, cache,
queue, object storage, service discovery, HTTP, scheduler/locking, device
protocols) is all in-memory fakes or a private embedded H2 database, not the
real company infrastructure this document describes; but where the operation
itself is the point rather than the infra behind it, the implementation is
real (AES-256-GCM, SHA-256/512, Ed25519, real SQL via H2, real Excel/PDF/CSV
generation and parsing via Apache POI/PDFBox/Commons CSV) — enough to
actually exercise the harness test infrastructure end to end (compiles,
runs, tests pass/fail for real). It's maintained inside this same skill
folder alongside this `SKILL.md`, not a separate thing.

## Project shape: background ETL batch

The reference implementation of this shape is
[`vendor/boogie-sdk-java/src/main/java/com/boogie/sdk/examples/etldemo/`](vendor/boogie-sdk-java/src/main/java/com/boogie/sdk/examples/etldemo/)
— **`migration-convert`'s scaffold step copies this directory wholesale,
unmodified, into the target path, then runs it once as-is (its own entry
point and test command) before any unit's real translation work starts** —
it does not read this section's description and hand-write a matching
structure from scratch. The ASCII tree and file-by-file notes below are for
understanding what you're copying and why it's laid out this way, not a
spec to reimplement independently — that copy-then-run-once step is what
actually confirms the DB/SDK/config wiring works in this environment, which
a hand-rebuilt look-alike wouldn't verify. Every boogie-sdk ETL example,
regardless of language, uses this same fixed 4-file shape (Extract/
Transform/Load plus an orchestrator), mapped onto Java class names:

```
target/<unit-group-or-app-name>/
└── src/main/java/com/company/<app>/
    ├── Main.java             # Orchestrator: wires up BoogieSdk, batch/shift
    │                         # tracking, sdk.logger()/sdk.metrics()/
    │                         # sdk.tracer(), calls Download -> Process ->
    │                         # Upload in order, prints the final summary.
    │                         # Owns the DbClient (sdk.db()) and hands it to
    │                         # Download -- Download never reaches back into
    │                         # the wider sdk facade itself.
    ├── Download.java         # Extract: seeds/reads the source data. This is
    │                         # the only stage that touches the database, so
    │                         # its SQL lives as .sql resource files under
    │                         # src/main/resources/.../sql/ (loaded via
    │                         # Download.class.getResourceAsStream(...))
    │                         # rather than being embedded as string
    │                         # literals. If a real migrated job's
    │                         # Transform/Load stages don't touch the DB
    │                         # either (transform is pure in-memory, load is
    │                         # object storage/queue), don't force SQL into
    │                         # them just to have three files with SQL.
    ├── Process.java          # Transform: masks/encrypts a PII field via
    │                         # sdk.crypto(), validates each row, isolates a
    │                         # bad row (audit + notification) without
    │                         # crashing the batch.
    └── Upload.java           # Load: writes to sdk.objectStorage()/
                              # sdk.queue(), produces the Excel/PDF summary
                              # report via sdk.deviceIo().reportGenerator().
```

Don't mix these four files' responsibilities (e.g. don't put transform logic
in `Main`), and don't split into a 5th file to make it feel more granular —
exactly 4 files, responsibilities as above.

Entry point: `java -jar target/<app>.jar` (or, for the vendored reference
demo itself, `mvn -f vendor/boogie-sdk-java/pom.xml compile exec:java
-Dexec.mainClass="com.boogie.sdk.examples.etldemo.Main"`). Success
criterion: the process runs to completion and exits naturally with exit
code 0, and the log shows each stage's own completion message — **no HTTP
health check**, since this isn't a resident service; any stage that raises
an uncaught exception outside the per-row isolation in `Process` must let
the whole process exit with a non-zero code — don't swallow the error and
let the process look like it finished normally.

External packages (not pure standard library):
- `spring-boot-starter` (core — not `spring-boot-starter-web`/`actuator`,
  since this isn't a resident service and has no HTTP endpoint) — needed
  once a converted unit's `Main` is wired as a real Spring Boot
  `CommandLineRunner` app; the vendored reference demo itself has no Spring
  dependency, it's a plain `public static void main`.
- `com.boogie.sdk:boogie-sdk` — vendored locally in this skill folder (see
  below), not on public Maven Central. A converted project outside this
  repo would need this jar published to an internal Nexus/Artifactory
  mirror or placed in the local `.m2` repository first; within this repo,
  point straight at `vendor/boogie-sdk-java/`.

## Using boogie-sdk

Conversion rules reference these interfaces directly — no need to pick your
own DB/crypto/logging solution, and don't bypass this to wire up JDBC/
`java.util.logging`/`javax.crypto` from the standard library yourself. Full
signatures for every client below: [`boogie-sdk-api.md`](boogie-sdk-api.md)
section 5.

```java
import com.boogie.sdk.BoogieSdk;

BoogieSdk sdk = BoogieSdk.init();

// DB (infra) -- named `:param` placeholders, never string concatenation
try (var conn = sdk.db().session()) {
    var rows = conn.fetchAll("SELECT id, name FROM users WHERE dept = :dept", Map.of("dept", "200"));
}
try (var tx = sdk.db().transaction()) {
    tx.execute("UPDATE users SET name = :name WHERE id = :id", Map.of("name", "foo", "id", 1));
    tx.commit(); // not calling commit() before leaving try-with-resources rolls back automatically
}

// Logging (observability) -- one JSON object per line to stdout
sdk.logger().info("fetched user", Map.of("unitId", "u123", "userId", 1));
sdk.logger().error("db timeout", Map.of("unitId", "u123"), ex);

// Crypto -- real AES-256-GCM/SHA/Ed25519, in-memory key management
byte[] ciphertext = sdk.crypto().encryptAes(plaintext, "key-1");
String masked = sdk.crypto().mask(rawValue); // PII masking helper

sdk.close();
```

Every accessor on `BoogieSdk` is a **method**, not a property (`sdk.db()`,
`sdk.crypto()`, `sdk.deviceIo().reportGenerator()`), matching ordinary Java
getter conventions. Module summary (full detail in
[`boogie-sdk-api.md`](boogie-sdk-api.md) section 5):

| Module | Covers | Example call |
|---|---|---|
| `config` | Remote config-center client with hot-reload callbacks | `sdk.config().get("some.key", "default")` |
| `crypto` | Encryption, secrets, tokens, certs, masking (real AES/SHA/Ed25519) | `sdk.crypto().encryptAes(data, "key-1")` |
| `infra` | DB, cache, queue, object storage, service discovery, HTTP, scheduler/locking | `sdk.db().query("SELECT * FROM t", params)` |
| `deviceIo` | Device protocols, file polling, flat-file parsing, Excel/PDF reports, batch/shift tracking, SPC | `sdk.deviceIo().reportGenerator().generateExcel(...)` |
| `observability` | Structured logging, metrics, tracing | `sdk.logger().info("done", Map.of("batchId", id))` |
| `governance` | ID generation, feature flags, rate limiting, notifications, health checks, audit trail | `sdk.audit().record(actor, action, resource, result)` |

- DB parameters always use named `:name` placeholders — `conn`/`tx` handle
  escaping themselves.
- Connection pooling/retries/timeouts, log formatting, and crypto key
  management are all built into `BoogieSdk.init()` — conversion rules don't
  need to reimplement any of this.
- Output is always one JSON object per line (timestamp, level, logger name,
  message, extra fields) written to stdout — the same format as
  `python-template`'s logger; no need to configure a logback/log4j pattern
  layout yourself.

## Test / build method

- Run tests: `mvn -f vendor/boogie-sdk-java/pom.xml test` (from inside this
  skill folder), or `mvn -f
  .claude/skills/java-template/vendor/boogie-sdk-java/pom.xml test` from the
  repo root. 266 tests as of this writing, all against the observable
  behavior of the fakes/real libraries (no external services, Docker, or
  network access required).
- Confirm the whole app compiles (no real DB connection involved): `mvn -q
  -f vendor/boogie-sdk-java/pom.xml compile`
- Integration check (run once after migration-convert has every unit
  passing): run the app (or the vendored reference demo via `exec:java`,
  see above), confirm the process exits with code 0 and the log shows every
  stage's completion message, then run the full test suite once more.
