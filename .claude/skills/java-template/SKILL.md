---
name: java-template
description: >
  Company-internal Java target-side knowledge base — usage rules for the
  corplib all-in-one package (DB access + structured logging) and the one
  project-shape template the company currently supports (background ETL
  batch, using Spring Boot's `CommandLineRunner`, runs to completion and
  exits — not a resident web service) live here, so the same target-side
  knowledge doesn't fragment across several skills. Use when writing or
  reviewing any company-internal Java batch code that talks to the DB or
  needs logging — not limited to legacy migration. In the legacy-to-Java
  migration context, domain-200-vb-java's and domain-200-delphi-java's
  target-side knowledge (template project, library docs, test/build method)
  all point here — don't duplicate it. A different-language binding of the
  same company DB/logging convention as `python-template` — same backend MS
  SQL Server, same log-collection format, just the Java-side
  implementation. Java currently has only this one shape, unlike the Python
  side where `python-template` itself splits into FastAPI-service/ETL-batch
  sections; if Java ever needs a long-running-service shape too, add a
  section here the same way `python-template` does — don't split into a
  separate skill.
---

# java-template: Company-Internal Java Target-Side Knowledge (Library + Project-Shape Templates)

This skill is the single entry point for company-internal Java target-side
knowledge, covering two things:

1. **How to use corplib** (DB + Logging) — applies no matter which project
   shape you're installing it into, stated once, not repeated.
2. **Project-shape templates** — Java currently has only one: **background
   ETL batch**.

In the legacy migration context, both `domain-200-vb-java` and
`domain-200-delphi-java` reference this skill as their "template project /
new-language library docs / test-build method" content — not maintained
separately.

The `vendor/corplib-java/` subfolder holds a real, compilable, runnable
minimal implementation of `corplib-java` (backed by SQLite, not the real MS
SQL Server this document describes — purely so the harness test
infrastructure can verify the whole pipeline actually compiles, runs, and
passes/fails tests; it's not the company's real production package, nor a
substitute for the behavior this document describes) — maintained inside
this same skill folder alongside this `SKILL.md`, not a separate thing.

## Project shape: background ETL batch

```
target/<unit-group-or-app-name>/
├── src/main/java/com/company/<app>/
│   ├── Application.java              # Entry point: SpringApplication.run,
│   │                                  # implements CommandLineRunner, runs
│   │                                  # each job in sequence then exits
│   │                                  # (not a resident service)
│   ├── job/
│   │   └── <UnitId>Job.java          # One batch-job class per migrated
│   │                                  # unit, exposing a run() method
│   ├── config/
│   │   └── CorplibConfig.java        # reads application.yml, configures
│   │                                  # DB DSN, log level, etc.
│   └── model/
│       └── <UnitId>Dto.java          # data object for this unit
├── src/test/java/com/company/<app>/
│   └── <UnitId>JobTest.java
├── src/main/resources/application.yml
└── pom.xml
```

Entry point: `java -jar target/<app>.jar`. Success criterion: the process
runs to completion and exits naturally with exit code 0, and the log shows
each `<UnitId>Job`'s own completion message (e.g. `logger.info("job done",
Map.of("job", "<unitId>"))`) — **no HTTP health check**, since this isn't a
resident service; any job that raises an uncaught exception inside
`Application.java`'s `CommandLineRunner.run()` must let the whole process
exit with a non-zero code — don't swallow the error and let the process
look like it finished normally.

External packages (not pure standard library):
- `spring-boot-starter` (core — not `spring-boot-starter-web`/`actuator`,
  since this isn't a resident service and has no HTTP endpoint).
- `com.company:corplib-java` (the company-internal all-in-one package, see
  below — not on public Maven Central; an air-gapped environment needs a
  human to first set up an internal Nexus/Artifactory mirror or place the
  jar in the local `.m2` repository).

The human must manually set up the internal repository mirror in
`settings.xml` beforehand and confirm `corplib-java` is reachable.
Read-only confirmation: `mvn -q dependency:tree | grep corplib`, or check
whether `~/.m2/repository/com/company/corplib-java` exists locally —
nothing found → stop and tell the human to set it up/install it first,
don't run the install command yourself.

## Using corplib (DB + Logging)

Conversion rules reference these interfaces directly — no need to pick your
own DB/logging solution, and don't bypass this to wire up JDBC/
`java.util.logging` from the standard library yourself.

### `com.company.corplib.db.Database`

```java
import com.company.corplib.db.Database;

Database db = Database.fromEnv();
// reads the CORPLIB_DB_DSN env var; internally uses a HikariCP connection
// pool pointing at the same MS SQL Server as the old system (the same
// server python-template's corplib.db connects to)

// Query
try (var conn = db.session()) {
    var rows = conn.fetchAll(
        "SELECT id, name FROM users WHERE dept = :dept", Map.of("dept", "200"));
    var row = conn.fetchOne("SELECT * FROM users WHERE id = :id", Map.of("id", 1));
}

// Write / transaction
try (var tx = db.transaction()) {
    tx.execute(
        "UPDATE users SET name = :name WHERE id = :id",
        Map.of("name", "foo", "id", 1));
    tx.commit(); // not calling commit() before leaving try-with-resources
                 // rolls back automatically
}
```

- Parameters always use named `:name` placeholders — `conn`/`tx` handle
  escaping themselves; never build SQL by string concatenation.
- Connection pooling, retries, and timeouts are all built into
  `Database.fromEnv()` — conversion rules don't need to reimplement any of
  this.

### `com.company.corplib.logging.Loggers`

```java
import com.company.corplib.logging.Loggers;

var logger = Loggers.get(MyClass.class);
logger.info("fetched user", Map.of("unitId", "u123", "userId", 1));
logger.error("db timeout", Map.of("unitId", "u123"), ex);
```

- Output is always one JSON object per line (timestamp, level, logger name,
  message, extra fields) written to stdout, handled by an external log
  collector — the same format as `python-template`'s `corplib.logging`; no
  need to configure a logback/log4j pattern layout yourself.

## Test / build method

- Run tests: `mvn test`
- Confirm the whole app compiles (no real DB connection involved): `mvn -q
  compile`
- Integration check (run once after migration-convert has every unit
  passing): `java -jar target/<app>.jar`, confirm the process exits with
  code 0 and the log shows every job's completion message, then run the
  full `mvn test` once more.
