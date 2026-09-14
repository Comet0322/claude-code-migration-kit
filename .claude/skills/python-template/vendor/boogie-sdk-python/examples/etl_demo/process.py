"""Process (Transform) stage of the ETL demo.

See boogie-sdk-api.md section 7 (migration cheat sheet).
"""

from __future__ import annotations

from typing import Any

from boogie_sdk import BoogieSdk
from boogie_sdk.crypto import mask_util
from boogie_sdk.infra.db_client import Row

KEY_ID = "etl-demo-pii"  # AES key id used for encrypting the raw phone number at rest


def process_row(sdk: BoogieSdk, row: Row) -> dict[str, Any]:
    """Transform a single row. Raises on bad data -- the caller decides
    whether that's fatal for the whole batch (it isn't, here).

    Cheat sheet:
    - 自製 XOR / 簡易加密函式 -> `sdk.crypto.encrypt_aes(...)` (the raw phone
      number gets encrypted at rest, not just hidden behind a weak cipher).
    - PII shown in logs/reports uses `mask_util.mask_phone(...)` instead of
      printing the number in full, the way a legacy log line often did.
    """
    reading_value = float(row["reading_value"])  # legacy data stored everything as text; this is where a bad value blows up

    encrypted_phone = sdk.crypto.encrypt_aes(row["contact_phone"].encode("utf-8"), key_id=KEY_ID)

    return {
        "device_id": row["device_id"],
        "reading_value": reading_value,
        "masked_phone": mask_util.mask_phone(row["contact_phone"]),
        "encrypted_phone_hex": encrypted_phone.hex(),
        "recorded_at": row["recorded_at"],
        "status": "OK",
    }


def process(sdk: BoogieSdk, rows: list[Row], batch_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Transform stage: apply `process_row` to every downloaded row.

    A bad row is caught, logged, notified, and audited -- then the batch
    keeps going. This mirrors what new hires are told to expect from a
    migrated legacy job: one malformed record from a flaky sensor should
    never crash the whole nightly run.
    """
    ok_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    processed_counter = sdk.metrics.counter("etl.rows.processed")
    failed_counter = sdk.metrics.counter("etl.rows.failed")

    for row in rows:
        try:
            ok_rows.append(process_row(sdk, row))
            processed_counter.increment()
        except (ValueError, TypeError) as exc:
            # Cheat sheet: 用 TStringList.SaveToFile 寫純文字 log -> `sdk.logger`
            # (structured, not a flat text file); and this is exactly the
            # kind of failure a legacy job would silently swallow or crash on.
            sdk.logger.error(
                "row transform failed, skipping row and continuing batch",
                exc=exc,
                batch_id=batch_id,
                row_id=row["id"],
                device_id=row["device_id"],
            )
            # Cheat sheet: CDO.Message / Indy SMTP 寄信 -> `sdk.notification.send_email(...)`.
            sdk.notification.send_email(
                to="etl-oncall@example.com",
                subject=f"[ETL] row {row['id']} failed in batch {batch_id}",
                body=(
                    f"device_id={row['device_id']!r} reading_value={row['reading_value']!r} "
                    f"error={exc}"
                ),
            )
            sdk.audit.record(
                actor="etl_batch_job",
                action="transform_row",
                resource=f"sensor_readings:{row['id']}",
                result="failed",
            )
            failed_counter.increment()
            failed_rows.append(
                {
                    "device_id": row["device_id"],
                    "reading_value": row["reading_value"],
                    "masked_phone": mask_util.mask_phone(row["contact_phone"]),
                    "recorded_at": row["recorded_at"],
                    "status": "FAILED",
                    "error": str(exc),
                }
            )

    return ok_rows, failed_rows
