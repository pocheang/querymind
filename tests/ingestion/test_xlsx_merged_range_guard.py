"""A merged range is checked before openpyxl is allowed to materialise it.

Full-mode openpyxl creates one MergedCell object per merged cell while it
loads, so a few bytes of XML declaring `A1:XFD1048576` (17 billion cells)
exhausted memory inside `load_workbook` -- before the 5000-row guard, which
runs afterwards, could do anything. The loader now reads the declared area from
the archive first and streams (read-only, no forward fill) past a cap.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from app.ingestion.loaders import office_loader  # noqa: E402


def _workbook(path: Path, merged_ref: str | None) -> Path:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Dept", "Q1"])
    sheet.append(["R&D", 10])
    workbook.save(path)
    if merged_ref is None:
        return path
    # Written into the XML directly: asking openpyxl to merge this range would
    # build the very objects the guard exists to avoid.
    patched = path.with_name(f"patched-{path.name}")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(patched, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet"):
                merge = f'<mergeCells count="1"><mergeCell ref="{merged_ref}"/></mergeCells>'.encode()
                data = re.sub(rb"</sheetData>", b"</sheetData>" + merge, data, count=1)
            dst.writestr(item, data)
    return patched


def test_the_declared_area_is_read_from_the_archive(tmp_path: Path) -> None:
    assert office_loader._declared_merged_area(_workbook(tmp_path / "a.xlsx", "A1:B3")) == 6
    huge = office_loader._declared_merged_area(_workbook(tmp_path / "b.xlsx", "A1:XFD1048576"))
    assert huge > office_loader._MAX_MERGED_CELLS


def test_a_huge_merged_range_is_never_loaded_in_full_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _workbook(tmp_path / "bomb.xlsx", "A1:XFD1048576")
    real = openpyxl.load_workbook
    modes: list[bool] = []

    def recording(*args, **kwargs):
        modes.append(bool(kwargs.get("read_only")))
        if not kwargs.get("read_only"):
            raise AssertionError("full-mode load attempted on a workbook declaring 17 billion merged cells")
        return real(*args, **kwargs)

    monkeypatch.setattr(openpyxl, "load_workbook", recording)

    sheets = office_loader._xlsx_rows(path)

    assert modes == [True]
    assert sheets[0][1][0][:2] == ["Dept", "Q1"]


def test_an_ordinary_merged_range_is_still_forward_filled(tmp_path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Dept", "Team"])
    sheet.append(["R&D", "A"])
    sheet.append([None, "B"])
    sheet.merge_cells("A2:A3")
    path = tmp_path / "merged.xlsx"
    workbook.save(path)

    rows = office_loader._xlsx_rows(path)[0][1]

    assert rows[2][0] == "R&D"


def test_a_sheet_that_fits_is_not_reported_as_truncated(tmp_path: Path) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["A"])
    sheet.cell(row=40, column=1, value="last")  # blank rows between inflate max_row
    path = tmp_path / "sparse.xlsx"
    workbook.save(path)

    rows = office_loader._xlsx_rows(path)[0][1]

    assert not any("Truncated" in str(row[0]) for row in rows)
