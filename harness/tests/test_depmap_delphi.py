"""regression test：depmap_delphi.py 的可達性分析與外部依賴擷取。

跟 test_depmap_vb6.py 同樣理由，用 subprocess 呼叫這支腳本，不 import
它（ROOT/OUT_DIR 是模組層級從 sys.argv 讀的，import 時機不對）。
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
    / "depmap_delphi.py"
)


def _run_depmap(legacy_dir: Path, out_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), str(legacy_dir), str(out_dir)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0


def test_reachable_units_and_their_uses_captured(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\nuses\n  UserSync;\nbegin\n  UserSync.RunNightlySync;\nend.\n",
        encoding="utf-8",
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\n"
        "interface\n"
        "procedure RunNightlySync;\n"
        "implementation\n"
        "uses\n"
        "  SysUtils;\n"
        "procedure RunNightlySync;\n"
        "begin\n"
        "end;\n"
        "end.\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "UserSync.pas" in order
    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "SysUtils" in refs


def test_unreachable_unit_excluded_from_analysis(tmp_path: Path):
    # regression test：ROOT 底下存在、但沒有任何路徑從 .dpr 走得到的
    # .pas 檔案（棄用的實驗性程式碼、複製留下的舊版本……）不該被當成本地
    # 模組，它自己內部瞎猜的依賴也不該污染 external-refs.tsv。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\nuses\n  UserSync;\nbegin\n  UserSync.RunNightlySync;\nend.\n",
        encoding="utf-8",
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\n"
        "interface\n"
        "procedure RunNightlySync;\n"
        "implementation\n"
        "procedure RunNightlySync;\n"
        "begin\n"
        "end;\n"
        "end.\n",
        encoding="utf-8",
    )
    (legacy_dir / "OldExperiment.pas").write_text(
        "unit OldExperiment;\n"
        "interface\n"
        "procedure DeadEntry;\n"
        "implementation\n"
        "uses\n"
        "  SomeAbandonedThirdPartyLib;\n"
        "procedure DeadEntry;\n"
        "begin\n"
        "end;\n"
        "end.\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "OldExperiment.pas" not in order
    assert "UserSync.pas" in order
    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "SomeAbandonedThirdPartyLib" not in refs


def test_dependency_declared_only_in_dpr_uses_is_captured(tmp_path: Path):
    # regression test：私有套件有時只在 .dpr 自己的 uses 子句宣告（例如
    # 純粹為了觸發全域初始化的 side-effect unit），沒有任何 .pas 檔案的
    # uses 提到它——這支腳本以前完全不讀 .dpr，這種依賴會整個消失。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\n"
        "uses\n"
        "  UserSync,\n"
        "  Dept200CommonInit;\n"
        "begin\n"
        "  UserSync.RunNightlySync;\n"
        "end.\n",
        encoding="utf-8",
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\n"
        "interface\n"
        "procedure RunNightlySync;\n"
        "implementation\n"
        "procedure RunNightlySync;\n"
        "begin\n"
        "end;\n"
        "end.\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "Dept200CommonInit" in refs
    # source_path 欄要指向 .dpr 本身，不是任何呼叫端 .pas（跟
    # depmap_vb6.py 對專案層級參考的做法一致）。
    ref_line = next(line for line in refs.splitlines() if "Dept200CommonInit" in line)
    assert ref_line.startswith(str(legacy_dir / "App.dpr"))


def test_dpr_uses_with_in_clause_resolves_to_local_unit(tmp_path: Path):
    # .dpr 的 uses 子句常見寫法是 `UnitName in 'path.pas'`——要能剝掉
    # `in '...'` 後綴才能比對回本地單元名稱，否則會被誤判成外部依賴。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\n"
        "uses\n"
        "  UserSync in 'UserSync.pas';\n"
        "begin\n"
        "  UserSync.RunNightlySync;\n"
        "end.\n",
        encoding="utf-8",
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\n"
        "interface\n"
        "procedure RunNightlySync;\n"
        "implementation\n"
        "procedure RunNightlySync;\n"
        "begin\n"
        "end;\n"
        "end.\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "UserSync.pas" in order
    refs = (out_dir / "external-refs.tsv").read_text(encoding="utf-8")
    assert "UserSync" not in refs


def test_no_dpr_falls_back_to_scanning_all_pas_files(tmp_path: Path):
    # 找不到任何 .dpr 時（理論上不該發生）退回舊行為：全部掃到的 .pas
    # 都當本地模組，不做可達性篩選。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "Orphan.pas").write_text(
        "unit Orphan;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "Orphan.pas" in order


def test_duplicate_unit_name_flagged_not_silently_picked(tmp_path: Path):
    # regression test：同一個 unit 名稱在不同目錄各出現一次（新舊備份、
    # 真實搜尋路徑優先序決定用哪一份的情況）——這支腳本沒有專案的搜尋路
    # 徑設定可用，無法真正判斷該用哪一份，只能挑一個繼續分析，但兩個候
    # 選都要原樣記進 ambiguous-units.tsv，不能靜默吃掉一個。
    legacy_dir = tmp_path / "legacy"
    (legacy_dir / "dir1").mkdir(parents=True)
    (legacy_dir / "dir2").mkdir(parents=True)
    (legacy_dir / "App.dpr").write_text(
        "program App;\nuses\n  UserSync in 'dir1\\UserSync.pas';\nbegin\nend.\n",
        encoding="utf-8",
    )
    (legacy_dir / "dir1" / "UserSync.pas").write_text(
        "unit UserSync;\ninterface\nimplementation\nuses\n  Utils;\nend.\n",
        encoding="utf-8",
    )
    (legacy_dir / "dir1" / "Utils.pas").write_text(
        "unit Utils;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "dir2" / "Utils.pas").write_text(
        "unit Utils;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    ambiguous = (out_dir / "ambiguous-units.tsv").read_text(encoding="utf-8")
    lines = [line for line in ambiguous.splitlines() if line]
    assert len(lines) == 2
    assert all(line.startswith("Utils\t") for line in lines)
    assert str(legacy_dir / "dir1" / "Utils.pas") in ambiguous
    assert str(legacy_dir / "dir2" / "Utils.pas") in ambiguous


def test_no_ambiguity_yields_empty_ambiguous_units_file(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\nuses\n  UserSync;\nbegin\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    assert (out_dir / "ambiguous-units.tsv").read_text(encoding="utf-8") == ""


def test_multiple_entry_points_each_reported_with_reachable_count(tmp_path: Path):
    # regression test：一個 repo 底下有不止一個 .dpr——可能兩個都是真的
    # 要建置的程式（例如共用同一批私有套件的主程式 + 小工具），也可能其
    # 中一個其實是沒人在用的舊 prototype。這支腳本無法從原始碼判斷哪個是
    # 真的，只能把每個進入點各自可達到幾個檔案列出來交給人確認。
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "MainApp.dpr").write_text(
        "program MainApp;\nuses\n  UserSync;\nbegin\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "OldPrototype.dpr").write_text(
        "program OldPrototype;\nuses\n  AbandonedProto;\nbegin\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "AbandonedProto.pas").write_text(
        "unit AbandonedProto;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    entry_points = (out_dir / "entry-points.tsv").read_text(encoding="utf-8")
    lines = sorted(line for line in entry_points.splitlines() if line)
    assert lines == sorted(
        [
            f"{legacy_dir / 'MainApp.dpr'}\t1",
            f"{legacy_dir / 'OldPrototype.dpr'}\t1",
        ]
    )
    # 兩個進入點各自可達的檔案都還是要進 order.txt——腳本無法自己判斷哪個
    # 是廢棄的，只是把事實攤開來給人確認，不是自作主張排除掉。
    order = (out_dir / "order.txt").read_text(encoding="utf-8")
    assert "AbandonedProto.pas" in order
    assert "UserSync.pas" in order


def test_single_entry_point_reports_one_row(tmp_path: Path):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "App.dpr").write_text(
        "program App;\nuses\n  UserSync;\nbegin\nend.\n", encoding="utf-8"
    )
    (legacy_dir / "UserSync.pas").write_text(
        "unit UserSync;\ninterface\nimplementation\nend.\n", encoding="utf-8"
    )
    out_dir = tmp_path / "out"

    _run_depmap(legacy_dir, out_dir)

    entry_points = [
        line for line in (out_dir / "entry-points.tsv").read_text(encoding="utf-8").splitlines() if line
    ]
    assert len(entry_points) == 1
    assert entry_points[0] == f"{legacy_dir / 'App.dpr'}\t1"
