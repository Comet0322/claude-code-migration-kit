# boogie-sdk (Java)

`boogie-sdk` is a simulated internal-platform library used for training and
onboarding: it stands in for the kind of all-in-one corporate SDK a large
org builds around its infra (DB, cache, queue, object storage, device
protocols, observability, governance, ...). Backends that would normally
mean standing up real infrastructure — databases, message queues, object
storage, device connections — are **fakes** (in-memory or a private
embedded H2 database), so the whole thing runs with zero external
services. Where the operation itself is the point rather than the infra
behind it, the implementation is real: AES-256-GCM encryption, SHA-256/512
hashing, Ed25519 signing, real SQL execution (H2 under the hood), and real
Excel (Apache POI)/PDF (PDFBox)/CSV (Apache Commons CSV) file generation
and parsing all do genuine work. Every module is reached through a single
facade, `BoogieSdk`, mirroring how a real internal platform SDK is usually
consumed.

See [`boogie-sdk-api.md`](../../boogie-sdk-api.md) for the full design
doc and API reference, including the facade pattern (section 3) and a
"migration cheat sheet" (section 7) mapping common legacy Delphi/VB6
patterns onto `boogie-sdk` calls — that mapping is the actual purpose of
this library: helping migrate old internal tools to Java.

## Build / setup

This is a standalone Maven project (single module, groupId
`com.boogie.sdk`, artifactId `boogie-sdk`, Java 17), vendored inside the
`java-template` skill so `migration-clarify`/`migration-convert` can find it
without any extra setup. From the **repo root**:

```
mvn -f .claude/skills/java-template/vendor/boogie-sdk-java/pom.xml package
```

(or just `mvn package` if you `cd .claude/skills/java-template/vendor/boogie-sdk-java` first).

## Running tests

From the repo root:

```
mvn -f .claude/skills/java-template/vendor/boogie-sdk-java/pom.xml test
```

267 tests as of this writing, all against the observable behavior of the
fakes/real libraries (no external services, Docker, or network access
required).

## Quickstart

```java
import com.boogie.sdk.BoogieSdk;

BoogieSdk sdk = BoogieSdk.init();

byte[] ciphertext = sdk.crypto().encryptAes("secret payload".getBytes(), "key-1");
sdk.db().execute("CREATE TABLE widgets (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(50))", Map.of());
sdk.db().execute("INSERT INTO widgets (name) VALUES (:name)", Map.of("name", "gadget"));
sdk.logger().info("widget inserted", Map.of("table", "widgets"));

sdk.close();
```

Note the method-call style throughout (`sdk.crypto()`, `sdk.db()`,
`sdk.deviceIo().spcAnalyzer()`) — every accessor on `BoogieSdk` is a method,
not a property, matching ordinary Java getter conventions.

## Modules

Every module is reached off the `sdk` facade returned by `BoogieSdk.init()`
(see [`boogie-sdk-api.md` section 5](../../boogie-sdk-api.md#5-模組-api-參考)
for the complete API of each). `deviceio` clients are grouped one level
deeper, e.g. `sdk.deviceIo().reportGenerator()`.

| Module | Simulates | Example call |
|---|---|---|
| `config` | Remote config-center client with hot-reload callbacks | `sdk.config().get("some.key", "default")` |
| `crypto` | KMS-backed encryption, secrets, tokens, certs (real AES/SHA/Ed25519) | `sdk.crypto().encryptAes(data, "key-1")` |
| `infra` | DB, cache, queue, object storage, service discovery, HTTP, scheduler/locking | `sdk.db().query("SELECT * FROM t", params)` |
| `deviceio` | Device protocols, file polling, flat-file parsing, Excel/PDF reports, batch/shift tracking, SPC | `sdk.deviceIo().reportGenerator().generateExcel(...)` |
| `observability` | Structured logging, metrics, tracing | `sdk.logger().info("done", Map.of("batchId", id))` |
| `governance` | ID generation, feature flags, rate limiting, notifications, health checks, audit trail | `sdk.audit().record(actor, action, resource, result)` |

## Example: a full migrated batch job

[`src/main/java/com/boogie/sdk/examples/etldemo/`](src/main/java/com/boogie/sdk/examples/etldemo/)
is the reference template for what a full migrated legacy batch job looks
like end to end, split into the standard 4-file ETL shape used across every
boogie-sdk example, regardless of language:

- `Main.java` — orchestration: wires up `BoogieSdk`, batch/shift tracking,
  `sdk.logger()`/`sdk.metrics()`/`sdk.tracer()`, calls
  `Download` → `Process` → `Upload` in order, prints the final summary.
- `Download.java` — Extract: seeds and reads the source data. `Main.java`
  owns the `DbClient` (`sdk.db()`) and hands it to `Download.download()`;
  the actual SQL statements live as `.sql` resource files under
  `src/main/resources/.../etldemo/sql/` rather than being embedded as
  string literals, since this is the only stage that touches the database.
- `Process.java` — Transform: masks/encrypts a PII field, isolates a bad
  row without crashing the batch.
- `Upload.java` — Load: writes to `sdk.objectStorage()`/`sdk.queue()`, and
  produces the Excel summary report via `sdk.deviceIo().reportGenerator()`.

It closes out with an `sdk.audit()` trail entry and an `sdk.notification()`
email on the simulated row failure. See the class-level Javadoc at the top
of `Main.java` for the full scenario writeup.

Run it from the repo root with:

```
mvn -f .claude/skills/java-template/vendor/boogie-sdk-java/pom.xml compile exec:java -Dexec.mainClass="com.boogie.sdk.examples.etldemo.Main"
```

It is fully self-contained (private in-memory H2 database, in-memory
object storage/queue, etc. — no external services needed) and finishes
with exit code 0. It writes a small Excel report to
`target/etl-demo-output/etl_report_<batch_id>.xlsx`; that path is already
covered by Maven's standard `.gitignore`-worthy `target/` build-output
convention, so no extra ignore rule is needed.
