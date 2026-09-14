# ETL demo: a migrated nightly batch job

This is a reference template for what a legacy Delphi/VB6 nightly batch job
looks like once it's been migrated onto `boogie-sdk`. The scenario: a plant
floor used to run a job that read an `.ini` config, pulled rows straight out
of an Access/SQL Server table via `ADODB.Connection`, wrote a plaintext log,
produced an Excel report through COM automation, and emailed someone by hand
when something broke. The demo follows the standard 4-file ETL template
shape used across every boogie-sdk example, regardless of language:

- `main.py` -- orchestration: wires up `BoogieSdk`, batch/shift tracking,
  logging/tracing/metrics, calls download -> process -> upload in order,
  prints the final summary.
- `download.py` -- Extract: seeds and reads the source data. `main.py`
  owns the DB connection (`sdk.db`) and hands it to `download()`; the
  actual SQL statements live as separate files under `sql/` rather than
  being embedded as string literals, since this is the only stage that
  touches the database.
- `process.py` -- Transform: encrypts/masks the sensitive field, validates
  each row, isolates a bad row without crashing the batch.
- `upload.py` -- Load: writes the transformed batch to object storage +
  queue, and produces the Excel summary report.

Every step has comments calling out which line of the
[migration cheat sheet](../../../../boogie-sdk-api.md#7-migration-對照速查表)
it maps to.

It extracts a small "sensor readings" table (seeded in-memory for the demo)
that includes a personal-data field (a phone number) and one deliberately
malformed row, encrypts/masks the sensitive field, uploads the transformed
batch to object storage and announces completion on a queue, tracks the run
through `batch_tracker`/`shift_calendar`, logs/traces/measures it with the
observability module, and writes a compliance audit trail plus an
email-on-failure with the governance module -- all without crashing the
batch when one row is bad.

## Run it

From the repo root:

```
uv run --package boogie-sdk python .claude/skills/python-template/vendor/boogie-sdk-python/examples/etl_demo/main.py
```

It's fully self-contained (in-memory SQLite, in-memory object storage/queue,
etc. -- no external services needed) and finishes with exit code 0. It
writes a small Excel report to `output/etl_report_<batch_id>.xlsx`; that
`output/` directory is git-ignored (see `.gitignore` in this folder) since
its contents are regenerated on every run.
