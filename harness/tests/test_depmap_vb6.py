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


def test_single_vbp_reports_one_entry_point_and_no_ambiguity(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    _write_module(legacy_dir)
    (legacy_dir / "App.vbp").write_text(
        "Type=Exe\nModule=UserSync; UserSync.bas\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    entry_points = [
        line for line in (out_dir / "entry-points.tsv").read_text(encoding="utf-8").splitlines() if line
    ]
    assert entry_points == [f"{legacy_dir / 'App.vbp'}\t1"]
    assert (out_dir / "ambiguous-units.tsv").read_text(encoding="utf-8") == ""


def test_multiple_vbp_entry_points_each_reported_with_module_count(tmp_path: Path):
    # regression test：一個 repo 底下有不止一個 .vbp——可能兩個都是真的要
    # 建置的程式，也可能其中一個其實是沒人在用的舊 prototype。這支腳本
    # 無法從原始碼判斷哪個是真的，只能把每個 .vbp 自己宣告了幾個模組列
    # 出來交給人確認，同時仍然把兩邊的模組都納入分析範圍（不擅自排除）。
    legacy_dir = tmp_path / "legacy"
    (legacy_dir / "app1").mkdir(parents=True)
    (legacy_dir / "app2").mkdir(parents=True)
    (legacy_dir / "app1" / "App.vbp").write_text(
        "Type=Exe\nModule=UserSync; UserSync.bas\n", encoding="utf-8"
    )
    (legacy_dir / "app1" / "UserSync.bas").write_text(
        'Attribute VB_Name = "UserSync"\nPublic Sub RunNightlySync()\nEnd Sub\n',
        encoding="utf-8",
    )
    (legacy_dir / "app2" / "OldPrototype.vbp").write_text(
        "Type=Exe\nModule=AbandonedProto; AbandonedProto.bas\n", encoding="utf-8"
    )
    (legacy_dir / "app2" / "AbandonedProto.bas").write_text(
        'Attribute VB_Name = "AbandonedProto"\nPublic Sub DeadEntry()\nEnd Sub\n',
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    entry_points = sorted(
        line for line in (out_dir / "entry-points.tsv").read_text(encoding="utf-8").splitlines() if line
    )
    assert entry_points == sorted(
        [
            f"{legacy_dir / 'app1' / 'App.vbp'}\t1",
            f"{legacy_dir / 'app2' / 'OldPrototype.vbp'}\t1",
        ]
    )
    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "UserSync.bas" in order
    assert "AbandonedProto.bas" in order


def test_duplicate_module_name_flagged_not_silently_picked(tmp_path: Path):
    # regression test：兩個不同 .vbp 專案各自宣告一個同名模組（VB_Name 一
    # 樣，檔案內容/路徑不同）——這支腳本沒有真正的專案建置資訊可用，無法
    # 判斷該用哪一份，只能挑一個繼續分析，但兩個候選都要原樣記進
    # ambiguous-units.tsv，不能靜默吃掉一個（原本的行為：dict 直接互相覆
    # 蓋，完全沒有警示）。
    legacy_dir = tmp_path / "legacy"
    (legacy_dir / "app1").mkdir(parents=True)
    (legacy_dir / "app2").mkdir(parents=True)
    (legacy_dir / "app1" / "App.vbp").write_text(
        "Type=Exe\nModule=UserSync; UserSync.bas\n", encoding="utf-8"
    )
    (legacy_dir / "app1" / "UserSync.bas").write_text(
        'Attribute VB_Name = "UserSync"\nPublic Sub RunNightlySync()\nEnd Sub\n',
        encoding="utf-8",
    )
    (legacy_dir / "app2" / "App2.vbp").write_text(
        "Type=Exe\nModule=UserSync; UserSync.bas\n", encoding="utf-8"
    )
    (legacy_dir / "app2" / "UserSync.bas").write_text(
        'Attribute VB_Name = "UserSync"\nPublic Sub RunNightlySync()\nEnd Sub\n',
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    ambiguous = (out_dir / "ambiguous-units.tsv").read_text(encoding="utf-8")
    lines = [line for line in ambiguous.splitlines() if line]
    assert len(lines) == 2
    assert all(line.startswith("UserSync\t") for line in lines)
    assert str(legacy_dir / "app1" / "UserSync.bas") in ambiguous
    assert str(legacy_dir / "app2" / "UserSync.bas") in ambiguous
