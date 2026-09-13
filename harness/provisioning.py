from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

# 這批子目錄是 domain skill / migration-convert 在跑的過程中真的需要讀的
# 參考資料（skill 定義、目標端 library 原始碼）。除了這幾個子樹跟這次 run
# 自己的工作目錄之外，repo 裡其他任何東西（其他 run 的產物、fixtures/、
# harness/ 自己的原始碼、之前手動跑過留下的範例 migration/ 產出……）一律
# 讀不到、寫不到——Task 9 端到端驗收時撞到一次真的問題：agent 在 repo 根
# 目錄翻到一份之前手動跑過的部門 200 遷移範例，拿它的實作當「先例」推翻
# 自己原本從 domain skill/rulebook 推出的決定，汙染了這次本該獨立判斷的
# headless 測試。
_ALLOWED_REPO_SUBTREES = (".claude", "vendor")

# permissions.deny/allow（管 Read/Edit/Grep/Glob 這些內建工具）跟 sandbox
# filesystem 的 deny/allow 語意不一樣：sandbox 那邊「較窄的 allow 可以重新
# 打開較寬的 deny 蓋住的區域」（實測驗證過），但 permissions 這邊「deny 永
# 遠贏」，較窄的 allow 蓋不過較寬的 deny——實測發現若對整個 repo_root 下
# Read/Edit deny，就算另外加一條只 allow 這次 run_dir 的規則，Write/Edit
# 工具寫自己的 run_dir 照樣被擋（`File is in a directory that is denied by
# your permission settings.`），會直接讓 migration-convert 沒辦法寫任何檔
# 案。所以這裡改成靜態列出「repo 裡跟這次 run 的工作目錄不可能重疊」的子
# 樹分別擋掉，不去動態组「deny 全部、allow 白名單」這種需要 allow 覆蓋
# deny 的寫法。sibling 的 runs/<其他 run> 沒辦法用這個模型安全擋掉（會跟
# 自己的 run_dir 撞在同一個 runs/** 底下），這塊的防護只能靠 sandbox 那層
# （已驗證對 Bash 有效）；permissions 這層是第二道防線，擋原生 Read/Edit/
# Grep/Glob 工具，覆蓋率比 sandbox 窄，屬於刻意的取捨。
_DENIED_REPO_SUBTREES_FOR_NATIVE_TOOLS = (
    "migration",
    "fixtures",
    "harness",
    "templates",
    "docs",
    "code-migration-kit-with-claude-code",
)


def _sandbox_settings(repo_root: Path, run_dir: Path) -> dict:
    # Read/Edit 規則跟 sandbox filesystem 規則的 `//` 前綴本身就代表「絕對
    # 路徑從檔案系統根目錄開始」（例：絕對路徑 /Users/alice 寫成規則要寫
    # //Users/alice，不是 ///Users/alice）——`//` 後面接的是路徑本身去掉
    # 開頭那個 `/` 的版本，所以這裡要先把 resolve() 回傳的前導 `/` 去掉。
    repo_root_abs = str(repo_root.resolve()).lstrip("/")
    run_dir_abs = str(run_dir.resolve()).lstrip("/")
    allowed_repo_reads = [f"//{repo_root_abs}/{name}/**" for name in _ALLOWED_REPO_SUBTREES]
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            # 這台機器本身已經跑在一層不特權的容器裡，bwrap 自己再起一層
            # network namespace 會撞到 `Failed RTM_NEWADDR: Operation not
            # permitted`（跟官方文件 troubleshooting 那條「在容器裡跑
            # bubblewrap」的已知案例同一類問題，只是我們撞到的是網路
            # namespace 而不是 /proc）——外層容器本身已經提供隔離邊界，這
            # 裡放寬成較弱的巢狀沙盒讓 Bash 至少能正常執行，檔案系統
            # allow/deny 的判斷邏輯不受影響。
            "enableWeakerNestedSandbox": True,
            "filesystem": {
                "denyRead": [f"//{repo_root_abs}/**"],
                "allowRead": [*allowed_repo_reads, f"//{run_dir_abs}/**"],
            },
        },
        "permissions_extra_deny": [
            f"Read(//{repo_root_abs}/{name}/**)" for name in _DENIED_REPO_SUBTREES_FOR_NATIVE_TOOLS
        ]
        + [f"Edit(//{repo_root_abs}/{name}/**)" for name in _DENIED_REPO_SUBTREES_FOR_NATIVE_TOOLS],
    }


def create_run_dir(fixture_name: str, mode: str, runs_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runs_root / f"{fixture_name}-{mode}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _seed_settings(run_dir: Path, templates_root: Path) -> None:
    base = json.loads((templates_root / "settings.json").read_text(encoding="utf-8"))
    repo_root = templates_root.resolve().parent
    sandboxed = _sandbox_settings(repo_root, run_dir)

    permissions = base.setdefault("permissions", {})
    permissions["deny"] = [*permissions.get("deny", []), *sandboxed.pop("permissions_extra_deny")]
    base["sandbox"] = sandboxed["sandbox"]

    claude_dir = run_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def provision_e2e(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None:
    fixture_dir = fixtures_root / fixture_name
    shutil.copytree(fixture_dir / "legacy", run_dir / "legacy")
    _seed_settings(run_dir, templates_root)
    migration_dir = run_dir / "migration"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / ".headless-test").write_text("", encoding="utf-8")


def provision_convert_only(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None:
    fixture_dir = fixtures_root / fixture_name
    shutil.copytree(fixture_dir / "legacy", run_dir / "legacy")
    _seed_settings(run_dir, templates_root)
    golden_dir = fixture_dir / "golden-convert-input"
    shutil.copytree(golden_dir, run_dir / "migration", dirs_exist_ok=True)
