"""Upload (Load) stage of the ETL demo.

See boogie-sdk-api.md section 7 (migration cheat sheet). Covers
both writing the transformed batch out and producing the summary report --
both are "output" concerns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from boogie_sdk import BoogieSdk
from boogie_sdk.infra.queue_client import Message

OUTPUT_DIR = Path(__file__).parent / "output"


def upload(sdk: BoogieSdk, batch_id: str, ok_rows: list[dict[str, Any]]) -> None:
    """Load stage: publish the transformed batch to object storage, then
    announce completion on a queue for whatever downstream system cares.

    No cheat-sheet line covers object storage / pub-sub directly (they're
    infra primitives a legacy Delphi/VB6 job usually didn't have at all --
    it just wrote a file to a shared drive); this is the "what you get for
    free once you're on boogie-sdk" half of the story.
    """
    payload = json.dumps({"batch_id": batch_id, "rows": ok_rows}, default=str).encode("utf-8")
    sdk.object_storage.upload(bucket="etl-demo-reports", key=f"batches/{batch_id}/transformed.json", data=payload)
    sdk.logger.info("uploaded transformed batch to object storage", batch_id=batch_id, row_count=len(ok_rows))

    def _on_batch_completed(message: Message) -> None:
        print(f"    [downstream consumer] received on {message.topic!r}: {message.body.decode('utf-8')}")

    sdk.queue.subscribe("etl.batch.completed", _on_batch_completed)
    sdk.queue.publish(
        "etl.batch.completed",
        json.dumps({"batch_id": batch_id, "row_count": len(ok_rows)}).encode("utf-8"),
    )


def build_report(sdk: BoogieSdk, batch_id: str, ok_rows: list[dict[str, Any]], failed_rows: list[dict[str, Any]]) -> Path:
    """Report stage.

    Cheat sheet: Excel COM 自動化(`TExcelApplication`)產報表 ->
    `sdk.deviceio.report_generator()`. No COM, no Excel installed on the
    box required -- this writes a real .xlsx via openpyxl under the hood.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = [
        {
            "device_id": row["device_id"],
            "status": row["status"],
            "reading_value": row["reading_value"],
            "masked_phone": row["masked_phone"],
            "recorded_at": row["recorded_at"],
        }
        for row in (*ok_rows, *failed_rows)
    ]

    out_file = OUTPUT_DIR / f"etl_report_{batch_id}.xlsx"
    # `template` isn't consulted by the current fake implementation, but the
    # API requires a Path -- pass a placeholder, same as real call sites do.
    sdk.deviceio.report_generator().generate_excel(
        data=summary_rows, template=Path("unused-template.xlsx"), out_file=out_file
    )
    return out_file
