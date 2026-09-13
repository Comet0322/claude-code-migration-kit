"""regression test：depmap_vb6.py 的外部依賴（external-refs.tsv）擷取。

這支腳本本身是隨 `migration` skill 打包、給 migration-analyze 直接呼叫的
CLI（見 `.claude/skills/migration/scripts/depmap_vb6.py`），不是 import 進
harness 的模組——用 subprocess 呼叫，跟腳本自己 docstring 裡的自我測試方式
一致，而不是 import 它（import 時機不對：ROOT/OUT_DIR 是模組層級從
sys.argv 讀的）。
"""
import subprocess
import sys
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude"
    / "skills"
    / "migration"
    / "scripts"
    / "depmap_vb6.py"
)


def _run_depmap(legacy_dir: Path, out_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(legacy_dir), str(out_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0


def _write_module(legacy_dir: Path) -> None:
    (legacy_dir / "UserSync.bas").write_text(
        'Attribute VB_Name = "UserSync"\n'
        "Public Sub RunNightlySync()\n"
        "    Dim Conn As New clsDBConn\n"
        "End Sub\n",
        encoding="utf-8",
    )


def test_object_line_private_package_captured(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    _write_module(legacy_dir)
    (legacy_dir / "App.vbp").write_text(
        "Type=Exe\n"
        "Object={9A7C1B10-0000-0000-0000-000000000200}#1.0#0; Dept200Common.dll\n"
        "Module=UserSync; UserSync.bas\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "Dept200Common.dll" in refs


def test_reference_line_private_package_captured(tmp_path: Path):
    # regression test：私有業務邏輯 ActiveX DLL 實務上常透過
    # Project→References 加入（寫成 `Reference=`），不是 `Object=`（那個是
    # Project→Components 加的 ActiveX 控制項/OCX）——只認 Object= 會把這類
    # 私有套件完全漏掉，migration-clarify 永遠看不到這個依賴訊號。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    _write_module(legacy_dir)
    (legacy_dir / "App.vbp").write_text(
        "Type=Exe\n"
        "Reference=*\\G{00020430-0000-0000-C000-000000000046}#2.0#0#..\\Windows\\System32\\stdole2.tlb#OLE Automation\n"
        "Reference=*\\G{9A7C1B10-0000-0000-0000-000000000200}#1.0#0#..\\lib\\Dept200Common.dll#Dept200Common\n"
        "Module=UserSync; UserSync.bas\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "Dept200Common.dll" in refs
    # 原樣列出，連看起來像標準函式庫的也不篩選——篩選判斷交給
    # migration-clarify，不是這支腳本的工作。
    assert "stdole2.tlb" in refs


def test_no_private_package_reference_yields_empty_external_refs(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    _write_module(legacy_dir)
    (legacy_dir / "App.vbp").write_text(
        "Type=Exe\nModule=UserSync; UserSync.bas\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    assert (out_dir / "external-refs.tsv").read_text(encoding="utf-8") == ""
