"""ReportGenerator stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl
from fpdf import FPDF


class ReportGenerator:
    def generate_excel(
        self, data: list[dict[str, Any]], template: Path, out_file: Path
    ) -> None:
        workbook = openpyxl.Workbook()
        sheet = workbook.active

        if data:
            header = list(data[0].keys())
            sheet.append(header)
            for row in data:
                sheet.append([row.get(key) for key in header])

        workbook.save(out_file)

    def generate_pdf(
        self, data: list[dict[str, Any]], template: Path, out_file: Path
    ) -> None:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)

        if data:
            header = list(data[0].keys())
            pdf.cell(0, 10, text=" | ".join(str(h) for h in header), new_x="LMARGIN", new_y="NEXT")
            for row in data:
                line = " | ".join(str(row.get(key, "")) for key in header)
                pdf.cell(0, 10, text=line, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(0, 10, text="", new_x="LMARGIN", new_y="NEXT")

        pdf.output(str(out_file))
