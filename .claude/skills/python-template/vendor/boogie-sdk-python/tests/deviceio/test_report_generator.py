"""Tests for ReportGenerator. See boogie-sdk-api.md (this skill's library doc)
section 5.3 (deviceio).

Unlike the rest of `deviceio`, this fake follows the same "fake infra, real
output" philosophy as `crypto`: there is no real Excel/PDF engine behind it
(no COM automation, no print server), but the *files it produces are real,
valid* `.xlsx` / `.pdf` documents — far more useful as a training template
than a stub that just touches an empty file.

Conventions invented for this module:

- **`template` is accepted for API-shape parity but not applied.** Both
  `generate_excel` and `generate_pdf` ignore the `template` argument
  entirely and always build a fresh document from `data`. This is the
  "simple, robust choice" called out in the task brief — a real
  implementation might open `template` as a base workbook/PDF and append to
  it, but this fake does not. Tests below pass a `template` path that does
  not even need to exist, to make this convention unambiguous.
- **`generate_excel` layout**: row 1 is a header row taken from the keys of
  the first dict in `data` (in insertion order); each subsequent row holds
  the values of one dict in `data`, in the same column order as the header.
  Verified here by round-tripping the output through
  `openpyxl.load_workbook`.
- **`generate_pdf` verification**: PDF content is not deeply parsed — only
  that `out_file` exists, is non-empty, and starts with the `%PDF-` magic
  bytes (the standard, format-defined way to identify a well-formed PDF
  without a full parser).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl
import pytest

from boogie_sdk.deviceio.report_generator import ReportGenerator


@pytest.fixture
def generator() -> ReportGenerator:
    return ReportGenerator()


SAMPLE_DATA: list[dict[str, Any]] = [
    {"device_id": "dev-1", "reading": 12.5, "status": "ok"},
    {"device_id": "dev-2", "reading": 7.0, "status": "warn"},
]


# -- generate_excel -------------------------------------------------------


def test_generate_excel_creates_output_file(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    template = tmp_path / "template.xlsx"  # deliberately never created
    out_file = tmp_path / "report.xlsx"

    generator.generate_excel(SAMPLE_DATA, template, out_file)

    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_generate_excel_writes_header_row_from_dict_keys(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    template = tmp_path / "template.xlsx"
    out_file = tmp_path / "report.xlsx"

    generator.generate_excel(SAMPLE_DATA, template, out_file)

    workbook = openpyxl.load_workbook(out_file)
    sheet = workbook.active
    header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]

    assert header == ["device_id", "reading", "status"]


def test_generate_excel_writes_one_row_per_data_dict(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    template = tmp_path / "template.xlsx"
    out_file = tmp_path / "report.xlsx"

    generator.generate_excel(SAMPLE_DATA, template, out_file)

    workbook = openpyxl.load_workbook(out_file)
    sheet = workbook.active
    rows = list(sheet.iter_rows(min_row=2, values_only=True))

    assert rows == [
        ("dev-1", 12.5, "ok"),
        ("dev-2", 7.0, "warn"),
    ]


def test_generate_excel_ignores_template_even_when_it_exists_with_content(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    # Even if `template` points at an existing (unrelated) workbook, the
    # output must reflect only `data` — proving `template` is not applied.
    template = tmp_path / "template.xlsx"
    pre_existing = openpyxl.Workbook()
    pre_existing.active.append(["should", "not", "appear"])
    pre_existing.save(template)

    out_file = tmp_path / "report.xlsx"
    generator.generate_excel(SAMPLE_DATA, template, out_file)

    workbook = openpyxl.load_workbook(out_file)
    sheet = workbook.active
    header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]

    assert header == ["device_id", "reading", "status"]


# -- generate_pdf -----------------------------------------------------------


def test_generate_pdf_creates_non_empty_valid_pdf_file(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    template = tmp_path / "template.pdf"  # deliberately never created
    out_file = tmp_path / "report.pdf"

    generator.generate_pdf(SAMPLE_DATA, template, out_file)

    assert out_file.exists()
    content = out_file.read_bytes()
    assert len(content) > 0
    assert content.startswith(b"%PDF-")


def test_generate_pdf_ignores_template_argument(
    generator: ReportGenerator, tmp_path: Path
) -> None:
    template = tmp_path / "template.pdf"
    template.write_bytes(b"not a real pdf at all")

    out_file = tmp_path / "report.pdf"
    generator.generate_pdf(SAMPLE_DATA, template, out_file)

    content = out_file.read_bytes()
    assert content.startswith(b"%PDF-")
