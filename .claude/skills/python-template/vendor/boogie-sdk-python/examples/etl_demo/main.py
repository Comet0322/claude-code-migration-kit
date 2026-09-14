"""ETL demo: a "migrated" nightly batch job built on boogie-sdk.

The scenario this script tells: imagine this used to be a Delphi/VB6 night
job that read a `.ini` config, hit an Access/SQL Server DB directly via
`ADODB.Connection`, wrote a plaintext log with `TStringList.SaveToFile`,
produced an Excel report via COM automation, and emailed someone by hand
when a row blew up. Every step below is annotated with which line of the
"migration cheat sheet" (see boogie-sdk-api.md section 7) it
replaces.

This example is split into the standard 4-file ETL template shape:
`main.py` (this file, orchestration + cross-cutting observability),
`download.py` (Extract), `process.py` (Transform), `upload.py` (Load +
report).

Run it with:

    uv run --package boogie-sdk python .claude/skills/python-template/vendor/boogie-sdk-python/examples/etl_demo/main.py

from the repo root. It is fully self-contained: `sdk.db` is an in-memory
SQLite fake, so this script creates and seeds its own table before reading
it back -- there is no external database to set up.
"""

from __future__ import annotations

from datetime import datetime

from boogie_sdk import BoogieSdk
from download import download
from process import process
from upload import build_report, upload


def main() -> None:
    sdk = BoogieSdk.init()
    # `main` owns the DB connection/session and hands it to `download()` --
    # `download.py` never reaches back into the wider `sdk` facade itself.
    db = sdk.db
    batch_tracker = sdk.deviceio.batch_tracker()
    now = datetime.now()
    batch_id = f"NIGHTLY-{now:%Y%m%d}-{sdk.id_generator.next_id()}"

    # Cheat sheet: `CreateMutex` / 檔案鎖做單例執行保護 has no equivalent needed
    # here (single-process demo) -- but batch/shift tracking below is the
    # observability a legacy job never had at all.
    with sdk.tracer.start_span("nightly_etl_run"):
        shift = sdk.deviceio.shift_calendar().current_shift(now)
        batch_tracker.create_batch(batch_id)

        sdk.logger.info("etl run started", batch_id=batch_id, shift=shift.name)
        sdk.audit.record(actor="etl_batch_job", action="run_start", resource=f"batch:{batch_id}", result="started")

        print(f"=== boogie-sdk ETL demo :: batch {batch_id} (shift={shift.name}) ===")

        print("\n-- download --")
        batch_tracker.update_status(batch_id, "extracting")
        rows = download(db)
        sdk.logger.info("download complete", batch_id=batch_id, row_count=len(rows))
        print(f"  downloaded {len(rows)} rows from sdk.db (sensor_readings)")

        print("\n-- process --")
        batch_tracker.update_status(batch_id, "transforming")
        ok_rows, failed_rows = process(sdk, rows, batch_id)
        sdk.logger.info("process complete", batch_id=batch_id, ok=len(ok_rows), failed=len(failed_rows))
        print(f"  {len(ok_rows)} rows processed OK, {len(failed_rows)} row(s) failed (see logger.error above)")

        print("\n-- upload --")
        batch_tracker.update_status(batch_id, "loading")
        upload(sdk, batch_id, ok_rows)
        print("  uploaded batch JSON to object_storage and published etl.batch.completed")

        report_path = build_report(sdk, batch_id, ok_rows, failed_rows)
        print(f"  wrote Excel summary report to {report_path}")

        final_status = "completed" if not failed_rows else "completed_with_errors"
        batch_tracker.update_status(batch_id, final_status)
        sdk.audit.record(actor="etl_batch_job", action="run_finish", resource=f"batch:{batch_id}", result=final_status)
        sdk.logger.info("etl run finished", batch_id=batch_id, status=final_status)

    print(f"\n=== batch {batch_id} finished: {final_status} ===")

    print("\n-- batch_tracker history --")
    for event in batch_tracker.get_history(batch_id):
        print(f"  {event.at.isoformat()}  {event.status}")

    print("\n-- metrics snapshot --")
    for name, value in sdk.metrics.snapshot().items():
        print(f"  {name} = {value}")

    print("\n-- tracer spans --")
    for name, duration in sdk.tracer.finished_spans:
        print(f"  {name}: {duration:.4f}s")

    print("\n-- notifications sent (would-be emails) --")
    for to, subject, _body in sdk.notification.sent_emails:
        print(f"  to={to!r} subject={subject!r}")

    print("\n-- audit trail --")
    for record in sdk.audit.records:
        print(f"  {record}")

    sdk.close()


if __name__ == "__main__":
    main()
