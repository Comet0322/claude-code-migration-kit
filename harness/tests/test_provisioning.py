import json
import re
from pathlib import Path

from harness.provisioning import create_run_dir, provision_e2e, provision_convert_only


def test_create_run_dir_makes_timestamped_directory(tmp_path: Path):
    runs_root = tmp_path / "runs"

    run_dir = create_run_dir("dept200-vb6", "e2e", runs_root)

    assert run_dir.exists()
    assert run_dir.parent == runs_root
    assert re.match(r"^dept200-vb6-e2e-\d{8}T\d{6}Z$", run_dir.name)


def _make_fixture(fixtures_root: Path, name: str) -> Path:
    fixture_dir = fixtures_root / name
    (fixture_dir / "legacy").mkdir(parents=True)
    (fixture_dir / "legacy" / "UserSync.bas").write_text("' code\n", encoding="utf-8")
    return fixture_dir


def _make_templates(templates_root: Path) -> None:
    templates_root.mkdir(parents=True, exist_ok=True)
    (templates_root / "settings.json").write_text('{"permissions": {"deny": []}}', encoding="utf-8")


def test_provision_e2e_copies_legacy_seeds_settings_and_writes_marker(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, tmp_path, templates_root)

    assert (run_dir / "legacy" / "UserSync.bas").exists()
    assert (run_dir / ".claude" / "settings.json").exists()
    assert (run_dir / "migration" / "clarify" / ".headless-test").exists()


def test_provision_e2e_copies_hooks_dir_into_run_claude_dir(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    _make_templates(templates_root)
    (templates_root / "hooks").mkdir(parents=True)
    (templates_root / "hooks" / "syntax-check.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, tmp_path, templates_root)

    copied = run_dir / ".claude" / "hooks" / "syntax-check.sh"
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "#!/bin/bash\nexit 0\n"


def test_provision_e2e_skips_hooks_copy_when_templates_have_none(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, tmp_path, templates_root)

    assert not (run_dir / ".claude" / "hooks").exists()


def test_provision_e2e_writes_force_domain_skill_marker_when_given(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-delphi")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e(
        "dept200-delphi", run_dir, fixtures_root, tmp_path, templates_root,
        force_domain_skill="domain-200-delphi-java",
    )

    marker = run_dir / "migration" / "clarify" / ".headless-test-domain-skill"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == "domain-200-delphi-java"


def test_provision_e2e_omits_force_domain_skill_marker_by_default(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, tmp_path, templates_root)

    assert not (run_dir / "migration" / "clarify" / ".headless-test-domain-skill").exists()


def test_provision_convert_only_copies_golden_input_without_marker(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    fixture_dir = _make_fixture(fixtures_root, "dept200-vb6")
    golden_dir = fixture_dir / "golden-convert-input"
    # golden-convert-input 底下的目錄結構本身就要已經是 migration/ 的新
    # 巢狀分層（clarify/、convert/ ...），provision_convert_only 只是原樣
    # copytree 過去，不做任何路徑轉換。
    (golden_dir / "clarify").mkdir(parents=True)
    (golden_dir / "clarify" / "manifest.tsv").write_text(
        "UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\n", encoding="utf-8"
    )
    (golden_dir / "clarify" / "RULEBOOK.md").write_text("# rules\n", encoding="utf-8")
    _make_templates(templates_root)
    (templates_root / "hooks").mkdir(parents=True)
    (templates_root / "hooks" / "syntax-check.sh").write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    run_dir = tmp_path / "runs" / "run2"
    run_dir.mkdir(parents=True)

    provision_convert_only("dept200-vb6", run_dir, fixtures_root, tmp_path, templates_root)

    assert (run_dir / "migration" / "clarify" / "manifest.tsv").exists()
    assert (run_dir / "migration" / "clarify" / "RULEBOOK.md").exists()
    # convert-only 也會叫到 migration-translator/migration-test-writer，
    # SubagentStop hook 一樣要就位，不是只有 e2e 模式需要。
    assert (run_dir / ".claude" / "hooks" / "syntax-check.sh").exists()
    assert not (run_dir / "migration" / "clarify" / ".headless-test").exists()


def test_provision_e2e_sandboxes_run_dir_and_keeps_existing_deny_rules(tmp_path: Path):
    # regression test: Task 9 端到端驗收發現 agent 會用 Bash 的 cd 逃出
    # run_dir，讀到 repo 根目錄殘留的其他遷移產物當「先例」污染決策。修法
    # 是預設整個 repo 都讀不到、寫不到，只白名單 .claude/（domain skill 跟
    # 目標端 library 文件，包含各 template skill 自己 vendor/ 底下的真實
    # 可執行實作）跟這次 run 自己的工作目錄。
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    templates_root.mkdir(parents=True, exist_ok=True)
    (templates_root / "settings.json").write_text(
        json.dumps({"permissions": {"deny": ["Bash(git commit:*)"]}}), encoding="utf-8"
    )
    repo_root = tmp_path
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, repo_root, templates_root)

    settings = json.loads((run_dir / ".claude" / "settings.json").read_text(encoding="utf-8"))

    repo_root_abs = str(repo_root.resolve()).lstrip("/")
    run_dir_abs = str(run_dir.resolve()).lstrip("/")

    assert settings["sandbox"]["enabled"] is True
    assert settings["sandbox"]["failIfUnavailable"] is True
    deny_read = settings["sandbox"]["filesystem"]["denyRead"]
    allow_read = settings["sandbox"]["filesystem"]["allowRead"]
    assert f"//{repo_root_abs}/**" in deny_read
    assert f"//{repo_root_abs}/.claude/**" in allow_read
    assert f"//{run_dir_abs}/**" in allow_read

    # permissions.deny/allow 的語意跟 sandbox filesystem 不同——deny 永遠
    # 贏，較窄的 allow 蓋不過較寬的 deny（實測發現對 repo_root 整個 deny
    # 會連自己 run_dir 的 Write/Edit 都一起擋掉），所以這層改成靜態列出
    # 跟 run_dir 不可能重疊的子樹分別擋，不靠 allow 覆蓋 deny。
    permissions = settings["permissions"]
    assert f"Read(//{repo_root_abs}/migration/**)" in permissions["deny"]
    assert f"Edit(//{repo_root_abs}/migration/**)" in permissions["deny"]
    assert f"Read(//{repo_root_abs}/harness/**)" in permissions["deny"]
    assert f"Read(//{repo_root_abs}/fixtures/**)" in permissions["deny"]
    # `_seed_settings` 合併沙盒規則時，template 裡任何既有的 deny 規則都
    # 要保留、不能被沙盒新增的規則整份覆蓋掉——這裡塞一條合成的
    # `Bash(git commit:*)` 純粹是測這條合併邏輯本身，不代表真正的
    # `.claude/skills/migration/templates/settings.json` 現在真的有這條規
    # 則（那份 template 現在完全沒有 `permissions.deny`，git commit/push/
    # 套件安裝改成純 prompt 層級紀律，見 settings.README.md）。
    assert "Bash(git commit:*)" in permissions["deny"]

