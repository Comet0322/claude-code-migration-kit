# 遷移 kit 自動化測試框架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建一個無人值守的 headless 測試框架，能對給定的 fixture 老舊程式碼
自動跑完整個 migration kit pipeline（或單獨跑 convert 段），並產出結構化的
評估報告，供事後檢討 domain skill / corp lib / rulebook 種子規則的設計品質。

**Architecture:** 修改 `migration-clarify` 加一個標記檔觸發的 headless
自決協定（不問人，改成自己判斷 + 寫 decision-log，卡住才停）；外部 Python
腳本（`harness/`）用 `claude -p --output-format json --permission-mode
acceptEdits --allowedTools <白名單>` 反覆呼叫、靠讀檔案狀態決定下一步（跟
`migration` 頂層 router 同一套邏輯），在路由層級的 gate（pilot-signoff）
用決定性規則自己核准或標記 `needs-human`；跑完比對 fixture 的
`test-config.json` 產出報告。

**Ruling（Task 1 執行期間跟使用者確認，取代原本設計）：** 不用
`--permission-mode bypassPermissions`——這個 flag 在「一個 agent 呼叫另一
個帶 bypassPermissions 的 claude」這個模式下會被 Claude Code Auto Mode 的
安全分類器判定成「Create Unsafe Agents」擋下（在這個 plan 的實作過程中實
測撞到）。改用 `--permission-mode acceptEdits` 搭配明確的
`--allowedTools` 白名單：`Bash,Edit,Write,Read,Glob,Grep,Skill,Task`（涵
蓋讀寫檔案、跑 build/test 用的 Bash、載入 domain skill 用的 Skill 工具、
派送 migration-test-writer/migration-converter/migration-test-reviewer 三
個 subagent 用的 Task 工具——若實作時發現這個 Claude Code 版本裡派送
subagent 的工具名稱不是 `Task`，用實際名稱替換，並在該任務的報告裡註
明）。真正的危險操作邊界一律靠 run 自己的 `.claude/settings.json` deny 規
則擋，這點跟原本的設計精神一致，只是換了允許清單的表達方式。

**Tech Stack:** Python 3（標準庫為主：`subprocess`/`json`/`pathlib`/
`argparse`/`dataclasses`/`enum`/`shutil`/`csv`），測試用 `pytest`（開發期
依賴，跑 `pip install pytest` 即可，不影響 migration kit 本身跑在
air-gapped 環境的假設——這個依賴只給開發這個 harness 用，harness 執行期本
身不需要它）。

**Spec:** `docs/superpowers/specs/2026-09-13-migration-test-harness-design.md`

## Global Constraints

- 零外部執行期依賴：`harness/` 底下的程式只能用 Python 標準庫，不引入
  `pyyaml` 等套件——`test-config` 用 **JSON**（`test-config.json`），不是
  spec 草稿裡寫的 `.yaml`（純粹格式選擇，內容結構不變）。
- `migration/.headless-test` 標記檔存在時才觸發 headless 自決；標記檔不存
  在時 `migration-clarify` 的行為必須跟修改前逐字一致——這是唯一的行為開
  關依據，不要用環境變數或其他隱性訊號。
- `manifest.tsv`、`manifest-draft.tsv`、`deviation-log.tsv`、
  `cost-log.tsv` 一律 tab 分隔，沿用既有欄位定義（見
  `.claude/skills/migration-clarify/SKILL.md`、
  `.claude/skills/migration-convert/SKILL.md`），不新增、不改變既有欄位語
  意。
- `harness/` 的程式碼**不**自己安裝套件、不編輯 `fixtures/` 底下任何檔案
  （只讀取複製）、不繞過或修改任何 run 自己的 `.claude/settings.json` deny
  規則。真正的危險操作邊界一律靠 `.claude/settings.json` 的 deny 規則擋，
  不是靠 CLI 權限旗標。
- 每次執行都建立全新的 `runs/<fixture>-<mode>-<timestamp>/`，不覆蓋既有
  run 目錄。
- `claude -p` 每輪呼叫都是**全新 session**（不用 `--continue`/session
  id），因為 `migration` router 本身設計成從檔案狀態重新判斷下一步、可重
  複呼叫——這跟修改任何 migration skill 無關，純粹是 driver 的呼叫方式。

---

## Task 1: `migration-clarify` headless 自決協定

**Files:**
- Modify: `.claude/skills/migration-clarify/SKILL.md`

**Interfaces:**
- Consumes: 無（純 prompt 文字修改）
- Produces: 新的檔案格式契約，後面的 Python 程式碼依賴這些格式：
  - `migration/decision-log.md`：每次自決追加一個區塊，格式：
    ```
    ## <節次標題>

    <候選比較/理由/信心程度的自由文字>

    STATUS: decided
    ```
    或卡住時：
    ```
    ## <節次標題>

    <困境理由>

    STATUS: needs-human
    ```
  - `migration/ground-truth-strategy.md`：**第一行**固定格式
    `tier: environment|snapshot|inference`，其後接自由文字理由（不論
    headless 與否都要求這個格式——這是對既有規範的相容性補強，不影響決策
    邏輯本身，只是讓這個檔案除了給人看也能被程式解析）。

這個任務沒有自動化測試（skill 檔案是 prompt，不是可執行程式碼），改用「手
動整合驗證」步驟確認行為正確。

- [ ] **Step 1: 在 `migration-clarify` 開頭加共用協定說明**

在 `.claude/skills/migration-clarify/SKILL.md` 的 `# 釐清需求跟 Gap
skill` 標題後、`## 1. 選 domain skill` 之前，插入新的一節：

```markdown
## Headless 測試協定（`migration/.headless-test` 標記檔存在時生效）

這個 skill 平常靠 `AskUserQuestion` 讓真人在幾個地方做決定。如果
`migration/.headless-test` 這個標記檔存在，代表你正在被自動化測試框架
無人值守驅動，這種情況下：

- 任何一節原本會呼叫 `AskUserQuestion`（或用任何其他方式停下來等對話回
  覆）的地方，改成：依照這一節原本用來排推薦選項的同一套證據跟推理，直
  接**採用你自己認為最合理的選項**，把完整的候選比較、理由、信心程度，
  以追加（append）方式寫進 `migration/decision-log.md`（用
  `## <節次標題>` 當這筆記錄的標題），然後照這個決定繼續往下做這一節，
  不停下。這筆記錄結尾固定寫一行 `STATUS: decided`。
- 例外：如果依照現有證據，你判斷任何一個選項都缺乏客觀依據支持（例如
  Fingerprint 比對分數幾乎打平、或程式碼裡完全沒有能推斷目標形狀/UI 範
  疇的線索），一樣把判斷跟理由寫進 `migration/decision-log.md`，結尾這
  次寫 `STATUS: needs-human`，然後**停止整個 skill 呼叫**——這不是失
  敗，是這個情境對真人來說也需要問，如實記錄比硬猜一個答案更有價值。
- 標記檔不存在時（一般情況），以上都不適用，照原本的 `AskUserQuestion`
  流程做。

`migration/ground-truth-strategy.md` 不論標記檔存不存在，都要求**第一
行**固定寫 `tier: environment` / `tier: snapshot` / `tier: inference`
其中一個，其後才是原本要求的理由文字——這是格式補強，不改變原本三層擇一
的判斷邏輯。
```

- [ ] **Step 2: 在第 1 節（選 domain skill）套用協定**

把第 1 節裡「用 `AskUserQuestion` 問人類要用哪一個（列出候選 + 推薦值 +
理由）」這句，改成：

```markdown
- 找到候選：用 `migration/analysis/modules.tsv` 觀察到的匯入路徑、設定檔
  名稱等指紋，跟每個候選 domain skill 的 Fingerprint 小節比對，猜出最可能
  符合的一個，排成推薦選項。若 `migration/.headless-test` 不存在，用
  `AskUserQuestion` 問人類要用哪一個（列出候選 + 推薦值 + 理由）；標記檔
  存在則依照上面「Headless 測試協定」處理。
```

- [ ] **Step 3: 在第 3 節（ground-truth 策略）套用協定**

在第 3 節最後（「三層擇一寫進 `migration/ground-truth-strategy.md`」那段
之後）加一段：

```markdown
headless 模式下（`migration/.headless-test` 存在），如果第 1 層（執行環
境）探測失敗、且 `migration/behavior-snapshots/` 沒有可用素材，**預設直
接採用 tier=`inference`**，理由寫「自動化測試環境，無來源端執行環境或行
為快照可用」，記進 `migration/ground-truth-strategy.md`，不停下——這是刻
意放寬的測試預設值，跟一般情境「兩者都沒有才是最後手段、需要明確人類同
意」的原則不同，只在標記檔存在時生效。
```

- [ ] **Step 4: 在第 7 節（目標形狀）套用協定**

把第 7 節「用 `AskUserQuestion` 跟人類確認…是哪一種形狀」那句後面加：

```markdown
（若 `migration/.headless-test` 存在，依照「Headless 測試協定」處理，不
呼叫 `AskUserQuestion`。）
```

- [ ] **Step 5: 在 UI 範疇段落套用協定**

在「用 `AskUserQuestion` 問人類這次遷移整批要『保留 UI…』還是『捨棄
UI…』」那句後面加：

```markdown
（若 `migration/.headless-test` 存在，依照「Headless 測試協定」處理，不
呼叫 `AskUserQuestion`。）
```

- [ ] **Step 6: 手動整合驗證**

在 `/tmp` 或 scratchpad 建一個最小假 fixture（例如複製
`fixtures/dept200-vb6/legacy/` 到一個 scratch 工作目錄，跑
`migration-analyze` 產生 `migration/analysis/manifest-draft.tsv` 之
後）：

1. 不建立 `migration/.headless-test`，跑一次 `claude -p "用 migration
   skill 處理這次遷移"`，確認遇到 domain skill 選定時行為維持原本呼叫
   `AskUserQuestion`（在互動模式下手動跑一次確認，或至少確認 headless
   `-p` 模式下這一步會卡住/被拒絕——這是修改前後行為不變的證據）。
2. 建立空的 `migration/.headless-test`，重跑，確認：
   - 不再卡住等 `AskUserQuestion`。
   - `migration/decision-log.md` 出現 `## 1. domain skill 選定` 區塊，
     結尾有 `STATUS: decided`（因為 `dept200-vb6` 的 Fingerprint 只對得
     上 `domain-200-vb-java` 一個候選，證據充分，不該卡住）。
   - `migration/domain-skill.txt` 內容是 `domain-200-vb-java`。
   - `migration/ground-truth-strategy.md` 第一行是
     `tier: inference`（測試機沒有 VB6 執行環境）。

記錄這次手動驗證的指令跟結果到 commit message 裡，作為這個任務「測試通過」
的證據（skill prompt 沒有自動化單元測試可跑，這一步是它的驗收標準）。

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/migration-clarify/SKILL.md
git commit -m "feat: migration-clarify 加 headless 自決測試協定"
```

---

## Task 2: `harness/state.py` — 讀取 run 目錄狀態

**Files:**
- Create: `harness/__init__.py`（空檔，讓 `harness` 成為套件）
- Create: `harness/state.py`
- Test: `harness/tests/test_state.py`
- Test: `harness/tests/__init__.py`（空檔）

**Interfaces:**
- Consumes: 無（只讀檔案系統）
- Produces（後面任務會用到）：
  ```python
  @dataclass
  class UnitState:
      unit_id: str
      status: str
      attempts: dict[str, int]
      last_note: str

  @dataclass
  class RunState:
      run_dir: Path
      manifest_rows: list[dict[str, str]]       # unit_id/source_path/target_path
      pilot_manifest_exists: bool
      pilot_signoff_exists: bool
      unit_states: dict[str, UnitState]
      integration_status: str | None            # None|"pass"|"fail"
      deviation_rows: list[dict[str, str]]      # timestamp/unit_id/category/detail
      rulebook_amendments_pending: bool
      decision_log_last_status: str | None      # None|"decided"|"needs-human"
      ground_truth_tier: str | None             # None|"environment"|"snapshot"|"inference"

  def read_run_state(run_dir: Path) -> RunState: ...
  ```

- [ ] **Step 1: 寫第一個失敗測試（空 run 目錄）**

`harness/tests/test_state.py`:

```python
from pathlib import Path
from harness.state import read_run_state


def test_empty_run_dir_has_empty_manifest_and_no_flags(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "migration").mkdir(parents=True)

    state = read_run_state(run_dir)

    assert state.manifest_rows == []
    assert state.pilot_manifest_exists is False
    assert state.pilot_signoff_exists is False
    assert state.unit_states == {}
    assert state.integration_status is None
    assert state.deviation_rows == []
    assert state.rulebook_amendments_pending is False
    assert state.decision_log_last_status is None
    assert state.ground_truth_tier is None
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `cd /Users/asteroid/Code/CodeMigration && python3 -m pytest
harness/tests/test_state.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'harness'` 或
`state`）

- [ ] **Step 3: 寫最小實作**

`harness/__init__.py`：空檔。

`harness/state.py`:

```python
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UnitState:
    unit_id: str
    status: str
    attempts: dict[str, int]
    last_note: str


@dataclass
class RunState:
    run_dir: Path
    manifest_rows: list[dict[str, str]] = field(default_factory=list)
    pilot_manifest_exists: bool = False
    pilot_signoff_exists: bool = False
    unit_states: dict[str, UnitState] = field(default_factory=dict)
    integration_status: str | None = None
    deviation_rows: list[dict[str, str]] = field(default_factory=list)
    rulebook_amendments_pending: bool = False
    decision_log_last_status: str | None = None
    ground_truth_tier: str | None = None


_MANIFEST_FIELDS = ["unit_id", "source_path", "target_path"]
_DEVIATION_FIELDS = ["timestamp", "unit_id", "category", "detail"]


def _read_tsv(path: Path, fieldnames: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, fieldnames=fieldnames, delimiter="\t")
        return list(reader)


def _read_unit_states(migration_dir: Path) -> dict[str, UnitState]:
    state_dir = migration_dir / "state"
    if not state_dir.exists():
        return {}
    result: dict[str, UnitState] = {}
    for path in state_dir.glob("*.json"):
        if path.stem == "_integration":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        result[path.stem] = UnitState(
            unit_id=path.stem,
            status=data.get("status", "pending"),
            attempts=data.get("attempts", {}),
            last_note=data.get("last_note", ""),
        )
    return result


def _read_integration_status(migration_dir: Path) -> str | None:
    path = migration_dir / "state" / "_integration.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("status")


def _read_rulebook_amendments_pending(migration_dir: Path) -> bool:
    path = migration_dir / "rulebook-amendments.md"
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8").strip() != ""


_STATUS_LINE_RE = re.compile(r"^STATUS:\s*(decided|needs-human)\s*$", re.MULTILINE)


def _read_decision_log_last_status(migration_dir: Path) -> str | None:
    path = migration_dir / "decision-log.md"
    if not path.exists():
        return None
    matches = _STATUS_LINE_RE.findall(path.read_text(encoding="utf-8"))
    return matches[-1] if matches else None


def _read_ground_truth_tier(migration_dir: Path) -> str | None:
    path = migration_dir / "ground-truth-strategy.md"
    if not path.exists():
        return None
    first_line = path.read_text(encoding="utf-8").splitlines()[0] if path.stat().st_size else ""
    match = re.match(r"^tier:\s*(environment|snapshot|inference)\s*$", first_line.strip())
    return match.group(1) if match else None


def read_run_state(run_dir: Path) -> RunState:
    migration_dir = run_dir / "migration"
    manifest_path = migration_dir / "manifest.tsv"
    return RunState(
        run_dir=run_dir,
        manifest_rows=_read_tsv(manifest_path, _MANIFEST_FIELDS),
        pilot_manifest_exists=(migration_dir / "pilot-manifest.tsv").exists(),
        pilot_signoff_exists=(migration_dir / "pilot-signoff.txt").exists(),
        unit_states=_read_unit_states(migration_dir),
        integration_status=_read_integration_status(migration_dir),
        deviation_rows=_read_tsv(migration_dir / "deviation-log.tsv", _DEVIATION_FIELDS),
        rulebook_amendments_pending=_read_rulebook_amendments_pending(migration_dir),
        decision_log_last_status=_read_decision_log_last_status(migration_dir),
        ground_truth_tier=_read_ground_truth_tier(migration_dir),
    )
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_state.py -v`
Expected: PASS

- [ ] **Step 5: 加第二個測試（有資料的 run 目錄）**

在 `harness/tests/test_state.py` 加：

```python
def test_populated_run_dir_parses_all_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    migration_dir = run_dir / "migration"
    state_dir = migration_dir / "state"
    state_dir.mkdir(parents=True)

    (migration_dir / "manifest.tsv").write_text(
        "UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\n",
        encoding="utf-8",
    )
    (migration_dir / "pilot-manifest.tsv").write_text("", encoding="utf-8")
    (migration_dir / "pilot-signoff.txt").write_text("ok\n", encoding="utf-8")
    (state_dir / "UserSync.json").write_text(
        json.dumps({"status": "pass", "attempts": {"test_writer": 1}, "last_note": ""}),
        encoding="utf-8",
    )
    (state_dir / "_integration.json").write_text(
        json.dumps({"status": "pass", "note": "ok"}), encoding="utf-8"
    )
    (migration_dir / "deviation-log.tsv").write_text(
        "2026-09-13T00:00:00Z\tUserSync\tnaming\tfoo\n", encoding="utf-8"
    )
    (migration_dir / "rulebook-amendments.md").write_text("- pending item\n", encoding="utf-8")
    (migration_dir / "decision-log.md").write_text(
        "## 1. domain skill 選定\n\nrecommend X\n\nSTATUS: decided\n", encoding="utf-8"
    )
    (migration_dir / "ground-truth-strategy.md").write_text(
        "tier: inference\nno environment available\n", encoding="utf-8"
    )

    state = read_run_state(run_dir)

    assert state.manifest_rows == [
        {"unit_id": "UserSync", "source_path": "legacy/UserSync.bas", "target_path": "target/user_sync.py"}
    ]
    assert state.pilot_manifest_exists is True
    assert state.pilot_signoff_exists is True
    assert state.unit_states["UserSync"].status == "pass"
    assert state.integration_status == "pass"
    assert state.deviation_rows[0]["category"] == "naming"
    assert state.rulebook_amendments_pending is True
    assert state.decision_log_last_status == "decided"
    assert state.ground_truth_tier == "inference"
```

需要在測試檔頂端加 `import json`。

- [ ] **Step 6: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_state.py -v`
Expected: PASS（2 個測試都過）

- [ ] **Step 7: Commit**

```bash
git add harness/__init__.py harness/state.py harness/tests/
git commit -m "feat: harness.state 讀取 run 目錄狀態"
```

---

## Task 3: `harness/gates.py` — Gate 決策政策

**Files:**
- Create: `harness/gates.py`
- Test: `harness/tests/test_gates.py`

**Interfaces:**
- Consumes: `harness.state.RunState`（Task 2）
- Produces:
  ```python
  class Outcome(str, Enum):
      CONTINUE = "continue"
      SUCCESS = "success"
      NEEDS_HUMAN = "needs-human"
      ERROR = "error"

  @dataclass
  class GateDecision:
      outcome: Outcome
      reason: str
      write_pilot_signoff: bool = False

  def evaluate_gate(state: RunState) -> GateDecision: ...
  ```

- [ ] **Step 1: 寫失敗測試（clarify 卡住 → needs-human）**

`harness/tests/test_gates.py`:

```python
from harness.gates import Outcome, evaluate_gate
from harness.state import RunState


def _base_state(**overrides) -> RunState:
    from pathlib import Path
    defaults = dict(run_dir=Path("/tmp/run"))
    defaults.update(overrides)
    return RunState(**defaults)


def test_needs_human_when_decision_log_says_so():
    state = _base_state(decision_log_last_status="needs-human")

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN
    assert "decision-log" in decision.reason
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_gates.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'harness.gates'`）

- [ ] **Step 3: 寫最小實作**

`harness/gates.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from harness.state import RunState


class Outcome(str, Enum):
    CONTINUE = "continue"
    SUCCESS = "success"
    NEEDS_HUMAN = "needs-human"
    ERROR = "error"


@dataclass
class GateDecision:
    outcome: Outcome
    reason: str
    write_pilot_signoff: bool = False


_FAILURE_STATUSES = {"fail-conversion", "fail-test", "rule-gap"}


def evaluate_gate(state: RunState) -> GateDecision:
    if state.decision_log_last_status == "needs-human":
        return GateDecision(
            Outcome.NEEDS_HUMAN,
            "migration-clarify 在 decision-log.md 記錄 needs-human：缺乏客觀依據自決",
        )

    if state.rulebook_amendments_pending and any(
        u.status in _FAILURE_STATUSES for u in state.unit_states.values()
    ):
        return GateDecision(
            Outcome.NEEDS_HUMAN,
            "有 unit 卡在失敗狀態且 rulebook-amendments.md 有待處理項目",
        )

    if state.pilot_manifest_exists and not state.pilot_signoff_exists:
        pilot_unit_ids = _pilot_unit_ids(state)
        pilot_units = [state.unit_states.get(u) for u in pilot_unit_ids]
        all_terminal_clean = bool(pilot_unit_ids) and all(
            u is not None and u.status in ("pass", "excluded") for u in pilot_units
        )
        if all_terminal_clean and not state.rulebook_amendments_pending:
            return GateDecision(
                Outcome.CONTINUE,
                "pilot 全數 pass/excluded 且無待處理 rulebook-amendments，自動簽核",
                write_pilot_signoff=True,
            )
        return GateDecision(
            Outcome.NEEDS_HUMAN,
            "pilot 尚未全數 pass/excluded，或有待處理 rulebook-amendments，需要人類確認",
        )

    if state.manifest_rows:
        all_done = all(
            state.unit_states.get(row["unit_id"], None) is not None
            and state.unit_states[row["unit_id"]].status in ("pass", "excluded")
            for row in state.manifest_rows
        )
        if all_done:
            if state.integration_status == "pass":
                return GateDecision(Outcome.SUCCESS, "manifest 全數 pass/excluded 且整合檢查 pass")
            if state.integration_status == "fail":
                return GateDecision(Outcome.NEEDS_HUMAN, "整合檢查失敗，需要人類判斷退回哪個 unit")

    return GateDecision(Outcome.CONTINUE, "尚未到終止條件，繼續下一輪")


def _pilot_unit_ids(state: RunState) -> list[str]:
    pilot_path = state.run_dir / "migration" / "pilot-manifest.tsv"
    if not pilot_path.exists():
        return []
    ids = []
    for line in pilot_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ids.append(line.split("\t", 1)[0])
    return ids
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_gates.py -v`
Expected: PASS

- [ ] **Step 5: 補齊其餘情境的測試**

在 `harness/tests/test_gates.py` 加：

```python
from harness.state import UnitState


def test_continue_and_auto_signoff_when_pilot_clean():
    state = _base_state(
        pilot_manifest_exists=True,
        pilot_signoff_exists=False,
        unit_states={
            "A": UnitState("A", "pass", {}, ""),
            "B": UnitState("B", "excluded", {}, ""),
        },
        rulebook_amendments_pending=False,
    )
    # pilot-manifest.tsv 需要真的存在讓 _pilot_unit_ids 讀得到
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        migration_dir = run_dir / "migration"
        migration_dir.mkdir()
        (migration_dir / "pilot-manifest.tsv").write_text("A\tx\ty\nB\tx\ty\n", encoding="utf-8")
        state.run_dir = run_dir

        decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
    assert decision.write_pilot_signoff is True


def test_needs_human_when_pilot_not_clean():
    import tempfile
    from pathlib import Path
    state = _base_state(
        pilot_manifest_exists=True,
        pilot_signoff_exists=False,
        unit_states={"A": UnitState("A", "fail-test", {}, "")},
    )
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        migration_dir = run_dir / "migration"
        migration_dir.mkdir()
        (migration_dir / "pilot-manifest.tsv").write_text("A\tx\ty\n", encoding="utf-8")
        state.run_dir = run_dir

        decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN


def test_needs_human_when_pilot_unit_still_pending_with_no_state_file():
    # regression test: a unit listed in pilot-manifest.tsv with no state
    # file yet (still pending) must NOT be silently skipped — it must block
    # auto-signoff, not be treated as "not clean enough to matter".
    import tempfile
    from pathlib import Path
    state = _base_state(
        pilot_manifest_exists=True,
        pilot_signoff_exists=False,
        unit_states={"A": UnitState("A", "pass", {}, "")},  # B has no entry at all
    )
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        migration_dir = run_dir / "migration"
        migration_dir.mkdir()
        (migration_dir / "pilot-manifest.tsv").write_text("A\tx\ty\nB\tx\ty\n", encoding="utf-8")
        state.run_dir = run_dir

        decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN
    assert decision.write_pilot_signoff is False


def test_success_when_manifest_all_done_and_integration_pass():
    state = _base_state(
        manifest_rows=[{"unit_id": "A", "source_path": "x", "target_path": "y"}],
        unit_states={"A": UnitState("A", "pass", {}, "")},
        integration_status="pass",
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.SUCCESS


def test_needs_human_when_integration_fails():
    state = _base_state(
        manifest_rows=[{"unit_id": "A", "source_path": "x", "target_path": "y"}],
        unit_states={"A": UnitState("A", "pass", {}, "")},
        integration_status="fail",
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN


def test_continue_when_nothing_terminal_yet():
    state = _base_state()

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
```

- [ ] **Step 6: 跑全部測試確認通過**

Run: `python3 -m pytest harness/tests/test_gates.py -v`
Expected: PASS（7 個測試都過）

- [ ] **Step 7: Commit**

```bash
git add harness/gates.py harness/tests/test_gates.py
git commit -m "feat: harness.gates 決定性 gate 決策政策"
```

---

## Task 4: `harness/provisioning.py` — 建立 run 工作目錄

**Files:**
- Create: `harness/provisioning.py`
- Test: `harness/tests/test_provisioning.py`

**Interfaces:**
- Consumes: 無（純檔案系統操作）
- Produces:
  ```python
  def create_run_dir(fixture_name: str, mode: str, runs_root: Path) -> Path: ...

  def provision_e2e(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None: ...

  def provision_convert_only(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None: ...
  ```

- [ ] **Step 1: 寫失敗測試（`create_run_dir` 命名+建立）**

`harness/tests/test_provisioning.py`:

```python
import re
from pathlib import Path

from harness.provisioning import create_run_dir, provision_e2e, provision_convert_only


def test_create_run_dir_makes_timestamped_directory(tmp_path: Path):
    runs_root = tmp_path / "runs"

    run_dir = create_run_dir("dept200-vb6", "e2e", runs_root)

    assert run_dir.exists()
    assert run_dir.parent == runs_root
    assert re.match(r"^dept200-vb6-e2e-\d{8}T\d{6}Z$", run_dir.name)
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_provisioning.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 寫最小實作**

`harness/provisioning.py`:

```python
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def create_run_dir(fixture_name: str, mode: str, runs_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runs_root / f"{fixture_name}-{mode}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _seed_settings(run_dir: Path, templates_root: Path) -> None:
    claude_dir = run_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(templates_root / "settings.json", claude_dir / "settings.json")


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
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_provisioning.py -v`
Expected: PASS

- [ ] **Step 5: 補測試（e2e 複製內容 + 標記檔 + convert-only 不寫標記檔）**

在 `harness/tests/test_provisioning.py` 加：

```python
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

    provision_e2e("dept200-vb6", run_dir, fixtures_root, templates_root)

    assert (run_dir / "legacy" / "UserSync.bas").exists()
    assert (run_dir / ".claude" / "settings.json").exists()
    assert (run_dir / "migration" / ".headless-test").exists()


def test_provision_convert_only_copies_golden_input_without_marker(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    fixture_dir = _make_fixture(fixtures_root, "dept200-vb6")
    golden_dir = fixture_dir / "golden-convert-input"
    golden_dir.mkdir()
    (golden_dir / "manifest.tsv").write_text("UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\n", encoding="utf-8")
    (golden_dir / "RULEBOOK.md").write_text("# rules\n", encoding="utf-8")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run2"
    run_dir.mkdir(parents=True)

    provision_convert_only("dept200-vb6", run_dir, fixtures_root, templates_root)

    assert (run_dir / "migration" / "manifest.tsv").exists()
    assert (run_dir / "migration" / "RULEBOOK.md").exists()
    assert not (run_dir / "migration" / ".headless-test").exists()
```

- [ ] **Step 6: 跑全部測試確認通過**

Run: `python3 -m pytest harness/tests/test_provisioning.py -v`
Expected: PASS（3 個測試都過）

- [ ] **Step 7: Commit**

```bash
git add harness/provisioning.py harness/tests/test_provisioning.py
git commit -m "feat: harness.provisioning 建立 run 工作目錄"
```

---

## Task 5: `harness/driver.py` — headless 主迴圈

**Files:**
- Create: `harness/driver.py`
- Test: `harness/tests/test_driver.py`

**Interfaces:**
- Consumes: `harness.state.read_run_state`（Task 2）、
  `harness.gates.evaluate_gate` / `Outcome`（Task 3）
- Produces:
  ```python
  @dataclass
  class DriverConfig:
      max_turns: int = 20
      max_wallclock_seconds: int = 3600
      claude_bin: str = "claude"
      per_call_timeout_seconds: int = 900
      allowed_tools: str = "Bash,Edit,Write,Read,Glob,Grep,Skill,Task"

  @dataclass
  class DriverResult:
      outcome: Outcome
      turns_used: int
      last_reason: str
      last_stdout: str

  def invoke_claude(run_dir: Path, prompt: str, config: DriverConfig) -> str: ...

  def run_loop(run_dir: Path, mode: str, config: DriverConfig = DriverConfig()) -> DriverResult: ...
  ```

**注意**：`invoke_claude` 呼叫真正的 `claude` CLI（`-p`,
`--output-format json`, `--permission-mode acceptEdits`,
`--allowedTools <config.allowed_tools>`）。**不要用
`--permission-mode bypassPermissions`**——見這份 plan 開頭 Architecture 段
落的 Ruling：這個 flag 在「agent 呼叫另一個帶 bypassPermissions 的
claude」的模式下會被 Claude Code Auto Mode 的安全分類器擋下（Task 1 執行
期間實測撞到）。`allowed_tools` 預設的白名單裡 `Task` 是派送
migration-test-writer/migration-converter/migration-test-reviewer 三個
subagent 用的工具——如果實作時發現這個 Claude Code 版本裡派送 subagent
的工具名稱不是 `Task`，用 `claude --help` 或實際測試確認正確名稱，改掉
這個預設值，並在報告裡註明改了什麼、為什麼。單元測試不會真的呼叫
claude——用 `monkeypatch` 替換 `subprocess.run`。這個 CLI 呼叫的 JSON 回
傳格式（`result`/`is_error` 等欄位名稱）要在 Task 9 的手動驗證步驟對照
真實輸出確認一次，如果實際欄位名稱不同，回頭調整 `invoke_claude` 的解析
邏輯。

- [ ] **Step 1: 寫失敗測試（`invoke_claude` 組出正確指令、解析 JSON）**

`harness/tests/test_driver.py`:

```python
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.driver import DriverConfig, invoke_claude


def test_invoke_claude_builds_command_and_parses_result(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_run(cmd, cwd, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return SimpleNamespace(
            stdout=json.dumps({"result": "done", "is_error": False}),
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr("harness.driver.subprocess.run", fake_run)

    output = invoke_claude(tmp_path, "跑 migration skill", DriverConfig())

    assert output == "done"
    assert captured["cmd"][0] == "claude"
    assert "-p" in captured["cmd"]
    assert "跑 migration skill" in captured["cmd"]
    assert "--output-format" in captured["cmd"]
    assert "json" in captured["cmd"]
    assert "--permission-mode" in captured["cmd"]
    assert "acceptEdits" in captured["cmd"]
    assert "--allowedTools" in captured["cmd"]
    assert "Bash,Edit,Write,Read,Glob,Grep,Skill,Task" in captured["cmd"]
    assert captured["cwd"] == tmp_path
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_driver.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 寫最小實作（`invoke_claude`）**

`harness/driver.py`:

```python
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass

from harness.gates import Outcome, evaluate_gate
from harness.state import read_run_state


@dataclass
class DriverConfig:
    max_turns: int = 20
    max_wallclock_seconds: int = 3600
    claude_bin: str = "claude"
    per_call_timeout_seconds: int = 900
    allowed_tools: str = "Bash,Edit,Write,Read,Glob,Grep,Skill,Task"


@dataclass
class DriverResult:
    outcome: Outcome
    turns_used: int
    last_reason: str
    last_stdout: str


_E2E_PROMPT = "用 migration skill 處理這次遷移。"
_CONVERT_ONLY_PROMPT = "呼叫 migration-convert，manifest 路徑帶 migration/manifest.tsv。"


def invoke_claude(run_dir, prompt: str, config: DriverConfig) -> str:
    cmd = [
        config.claude_bin,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        config.allowed_tools,
    ]
    result = subprocess.run(
        cmd,
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=config.per_call_timeout_seconds,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout
    return data.get("result", result.stdout)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_driver.py -v`
Expected: PASS

- [ ] **Step 5: 寫失敗測試（`run_loop` 串接 gate 決策）**

在 `harness/tests/test_driver.py` 加：

```python
from harness.driver import run_loop
from harness.gates import GateDecision


def test_run_loop_stops_on_success(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    calls = {"invoke": 0}

    def fake_invoke(run_dir, prompt, config):
        calls["invoke"] += 1
        return "ok"

    decisions = [
        GateDecision(Outcome.CONTINUE, "still going"),
        GateDecision(Outcome.SUCCESS, "done"),
    ]

    def fake_evaluate_gate(state):
        return decisions.pop(0)

    monkeypatch.setattr("harness.driver.invoke_claude", fake_invoke)
    monkeypatch.setattr("harness.driver.evaluate_gate", fake_evaluate_gate)
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=5, max_wallclock_seconds=60))

    assert result.outcome == Outcome.SUCCESS
    assert result.turns_used == 2
    assert calls["invoke"] == 2


def test_run_loop_writes_pilot_signoff_then_continues(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()

    def fake_invoke(run_dir, prompt, config):
        return "ok"

    decisions = [
        GateDecision(Outcome.CONTINUE, "auto sign", write_pilot_signoff=True),
        GateDecision(Outcome.SUCCESS, "done"),
    ]

    def fake_evaluate_gate(state):
        return decisions.pop(0)

    monkeypatch.setattr("harness.driver.invoke_claude", fake_invoke)
    monkeypatch.setattr("harness.driver.evaluate_gate", fake_evaluate_gate)
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=5, max_wallclock_seconds=60))

    assert result.outcome == Outcome.SUCCESS
    assert (tmp_path / "migration" / "pilot-signoff.txt").exists()


def test_run_loop_stops_at_max_turns(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    monkeypatch.setattr("harness.driver.invoke_claude", lambda *a, **k: "ok")
    monkeypatch.setattr("harness.driver.evaluate_gate", lambda state: GateDecision(Outcome.CONTINUE, "loop forever"))
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=3, max_wallclock_seconds=60))

    assert result.outcome == Outcome.ERROR
    assert "max_turns" in result.last_reason
    assert result.turns_used == 3
```

- [ ] **Step 6: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_driver.py -v`
Expected: FAIL（`run_loop` 還不存在）

- [ ] **Step 7: 實作 `run_loop`**

在 `harness/driver.py` 加：

```python
def run_loop(run_dir, mode: str, config: DriverConfig = DriverConfig()) -> DriverResult:
    prompt = _E2E_PROMPT if mode == "e2e" else _CONVERT_ONLY_PROMPT
    start = time.monotonic()
    turns = 0
    last_stdout = ""

    while True:
        if turns >= config.max_turns:
            return DriverResult(Outcome.ERROR, turns, f"超過 max_turns={config.max_turns}", last_stdout)
        if time.monotonic() - start >= config.max_wallclock_seconds:
            return DriverResult(Outcome.ERROR, turns, "超過 max_wallclock_seconds", last_stdout)

        last_stdout = invoke_claude(run_dir, prompt, config)
        turns += 1

        state = read_run_state(run_dir)
        decision = evaluate_gate(state)

        if decision.write_pilot_signoff:
            (run_dir / "migration" / "pilot-signoff.txt").write_text(
                f"auto-approved by harness: {decision.reason}\n", encoding="utf-8"
            )

        if decision.outcome in (Outcome.SUCCESS, Outcome.NEEDS_HUMAN, Outcome.ERROR):
            return DriverResult(decision.outcome, turns, decision.reason, last_stdout)
        # Outcome.CONTINUE：進下一輪
```

- [ ] **Step 8: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_driver.py -v`
Expected: PASS（全部測試都過）

- [ ] **Step 9: Commit**

```bash
git add harness/driver.py harness/tests/test_driver.py
git commit -m "feat: harness.driver headless 主迴圈"
```

---

## Task 6: `harness/evaluate.py` — 報告與歷史紀錄

**Files:**
- Create: `harness/evaluate.py`
- Test: `harness/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `harness.state.RunState`（Task 2）、`harness.driver.DriverResult`
  / `harness.gates.Outcome`（Task 3、5）
- Produces:
  ```python
  def load_test_config(fixture_name: str, fixtures_root: Path) -> dict: ...

  def build_eval_report(
      fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
  ) -> str: ...

  def append_history(
      history_path: Path, fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
  ) -> None: ...
  ```

- [ ] **Step 1: 寫失敗測試（`load_test_config`）**

`harness/tests/test_evaluate.py`:

```python
import json
from pathlib import Path

from harness.evaluate import load_test_config


def test_load_test_config_reads_json(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    fixture_dir = fixtures_root / "dept200-vb6"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "test-config.json").write_text(
        json.dumps({"expected_outcome": "success", "expected_domain_skill": "domain-200-vb-java"}),
        encoding="utf-8",
    )

    config = load_test_config("dept200-vb6", fixtures_root)

    assert config["expected_outcome"] == "success"
    assert config["expected_domain_skill"] == "domain-200-vb-java"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_evaluate.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 實作 `load_test_config` + `build_eval_report` + `append_history`**

`harness/evaluate.py`:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path

from harness.driver import DriverResult
from harness.state import RunState


def load_test_config(fixture_name: str, fixtures_root: Path) -> dict:
    path = fixtures_root / fixture_name / "test-config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _read_domain_skill_file(state: RunState) -> str | None:
    path = state.run_dir / "migration" / "domain-skill.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def build_eval_report(
    fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
) -> str:
    expected_outcome = test_config.get("expected_outcome", "success")
    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = _read_domain_skill_file(state)
    expected_units = test_config.get("expected_units", {})

    lines = [
        f"# Eval report: {fixture_name} ({mode})",
        "",
        f"- outcome: {result.outcome.value} (expected: {expected_outcome}, "
        f"{'MATCH' if result.outcome.value == expected_outcome else 'MISMATCH'})",
        f"- reason: {result.last_reason}",
        f"- turns_used: {result.turns_used}",
        "",
        "## Domain skill",
        f"- expected: {expected_domain_skill}",
        f"- actual: {actual_domain_skill}",
        f"- {'MATCH' if actual_domain_skill == expected_domain_skill else 'MISMATCH (or ambiguity by design)'}",
        "",
        "## Units",
    ]
    for unit_id, expected_status in expected_units.items():
        actual = state.unit_states.get(unit_id)
        actual_status = actual.status if actual else "(missing)"
        verdict = "MATCH" if actual_status == expected_status else "MISMATCH"
        lines.append(f"- {unit_id}: expected={expected_status} actual={actual_status} [{verdict}]")

    lines += [
        "",
        "## Deviations",
        f"- total: {len(state.deviation_rows)}",
        f"- rulebook_amendments_pending: {state.rulebook_amendments_pending}",
    ]
    return "\n".join(lines) + "\n"


_HISTORY_FIELDS = [
    "timestamp",
    "fixture",
    "mode",
    "outcome",
    "domain_skill_match",
    "units_pass",
    "units_total",
]


def append_history(
    history_path: Path, fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
) -> None:
    from datetime import datetime, timezone

    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = _read_domain_skill_file(state)
    expected_units = test_config.get("expected_units", {})
    units_pass = sum(
        1
        for unit_id, expected_status in expected_units.items()
        if state.unit_states.get(unit_id) and state.unit_states[unit_id].status == expected_status
    )

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fixture": fixture_name,
        "mode": mode,
        "outcome": result.outcome.value,
        "domain_skill_match": str(actual_domain_skill == expected_domain_skill),
        "units_pass": str(units_pass),
        "units_total": str(len(expected_units)),
    }

    is_new = not history_path.exists()
    with history_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_HISTORY_FIELDS, delimiter="\t")
        if is_new:
            writer.writeheader()
        writer.writerow(row)
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_evaluate.py -v`
Expected: PASS

- [ ] **Step 5: 補測試（`build_eval_report`、`append_history`）**

在 `harness/tests/test_evaluate.py` 加：

```python
from harness.driver import DriverResult
from harness.gates import Outcome
from harness.state import RunState, UnitState
from harness.evaluate import build_eval_report, append_history


def test_build_eval_report_flags_mismatch(tmp_path: Path):
    (tmp_path / "migration").mkdir()
    (tmp_path / "migration" / "domain-skill.txt").write_text("domain-200-vb-java\n", encoding="utf-8")
    state = RunState(
        run_dir=tmp_path,
        unit_states={"UserSync": UnitState("UserSync", "pass", {}, "")},
    )
    result = DriverResult(Outcome.SUCCESS, 3, "ok", "")
    test_config = {
        "expected_outcome": "success",
        "expected_domain_skill": "domain-200-vb-java",
        "expected_units": {"UserSync": "pass"},
    }

    report = build_eval_report("dept200-vb6", "e2e", result, state, test_config)

    assert "MATCH" in report
    assert "domain-200-vb-java" in report
    assert "UserSync: expected=pass actual=pass [MATCH]" in report


def test_append_history_writes_header_once(tmp_path: Path):
    (tmp_path / "migration").mkdir()
    state = RunState(run_dir=tmp_path, unit_states={"UserSync": UnitState("UserSync", "pass", {}, "")})
    result = DriverResult(Outcome.SUCCESS, 3, "ok", "")
    test_config = {"expected_domain_skill": None, "expected_units": {"UserSync": "pass"}}
    history_path = tmp_path / "history.tsv"

    append_history(history_path, "dept200-vb6", "e2e", result, state, test_config)
    append_history(history_path, "dept200-vb6", "e2e", result, state, test_config)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("timestamp\t")
    assert len(lines) == 3
```

- [ ] **Step 6: 跑全部測試確認通過**

Run: `python3 -m pytest harness/tests/test_evaluate.py -v`
Expected: PASS（4 個測試都過）

- [ ] **Step 7: Commit**

```bash
git add harness/evaluate.py harness/tests/test_evaluate.py
git commit -m "feat: harness.evaluate 產出 eval-report 跟 history"
```

---

## Task 7: `harness/run.py` — CLI 進入點

**Files:**
- Create: `harness/run.py`
- Test: `harness/tests/test_run.py`

**Interfaces:**
- Consumes: 全部前面任務的模組
- Produces: `def main(argv: list[str] | None = None) -> int`（可執行腳本入
  口，`0`=success，`1`=needs-human，`2`=error）

- [ ] **Step 1: 寫失敗測試（CLI 串接，全部依賴 monkeypatch）**

`harness/tests/test_run.py`:

```python
from pathlib import Path

from harness.gates import Outcome
from harness.driver import DriverResult
from harness.run import main


def test_main_wires_provisioning_driver_and_evaluate(monkeypatch, tmp_path: Path):
    calls = []

    def fake_create_run_dir(fixture_name, mode, runs_root):
        calls.append(("create_run_dir", fixture_name, mode))
        run_dir = tmp_path / "runs" / "fake-run"
        run_dir.mkdir(parents=True)
        (run_dir / "migration").mkdir()
        return run_dir

    def fake_provision_e2e(fixture_name, run_dir, fixtures_root, templates_root):
        calls.append(("provision_e2e", fixture_name))

    def fake_run_loop(run_dir, mode, config):
        calls.append(("run_loop", mode))
        return DriverResult(Outcome.SUCCESS, 2, "ok", "")

    def fake_read_run_state(run_dir):
        calls.append(("read_run_state",))
        from harness.state import RunState
        return RunState(run_dir=run_dir)

    def fake_load_test_config(fixture_name, fixtures_root):
        return {"expected_outcome": "success", "expected_units": {}}

    written = {}

    def fake_build_eval_report(*a, **k):
        return "report text"

    def fake_append_history(*a, **k):
        written["history"] = True

    monkeypatch.setattr("harness.run.create_run_dir", fake_create_run_dir)
    monkeypatch.setattr("harness.run.provision_e2e", fake_provision_e2e)
    monkeypatch.setattr("harness.run.run_loop", fake_run_loop)
    monkeypatch.setattr("harness.run.read_run_state", fake_read_run_state)
    monkeypatch.setattr("harness.run.load_test_config", fake_load_test_config)
    monkeypatch.setattr("harness.run.build_eval_report", fake_build_eval_report)
    monkeypatch.setattr("harness.run.append_history", fake_append_history)

    exit_code = main(["--fixture", "dept200-vb6", "--mode", "e2e",
                       "--fixtures-root", str(tmp_path / "fixtures"),
                       "--templates-root", str(tmp_path / "templates"),
                       "--runs-root", str(tmp_path / "runs"),
                       "--history-path", str(tmp_path / "history.tsv")])

    assert exit_code == 0
    assert ("provision_e2e", "dept200-vb6") in calls
    assert ("run_loop", "e2e") in calls
    assert written["history"] is True
    assert (tmp_path / "runs" / "fake-run" / "eval-report.md").read_text(encoding="utf-8") == "report text"
```

- [ ] **Step 2: 跑測試確認失敗**

Run: `python3 -m pytest harness/tests/test_run.py -v`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: 實作 `harness/run.py`**

```python
from __future__ import annotations

import argparse
from pathlib import Path

from harness.driver import DriverConfig, run_loop
from harness.evaluate import append_history, build_eval_report, load_test_config
from harness.gates import Outcome
from harness.provisioning import create_run_dir, provision_convert_only, provision_e2e
from harness.state import read_run_state

_EXIT_CODES = {
    Outcome.SUCCESS: 0,
    Outcome.NEEDS_HUMAN: 1,
    Outcome.ERROR: 2,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="遷移 kit 自動化測試框架")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--mode", choices=["e2e", "convert-only"], required=True)
    parser.add_argument("--fixtures-root", default="fixtures")
    parser.add_argument("--templates-root", default="templates")
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--history-path", default="harness/history.tsv")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-wallclock-seconds", type=int, default=3600)
    args = parser.parse_args(argv)

    fixtures_root = Path(args.fixtures_root)
    templates_root = Path(args.templates_root)
    runs_root = Path(args.runs_root)

    run_dir = create_run_dir(args.fixture, args.mode, runs_root)
    if args.mode == "e2e":
        provision_e2e(args.fixture, run_dir, fixtures_root, templates_root)
    else:
        provision_convert_only(args.fixture, run_dir, fixtures_root, templates_root)

    config = DriverConfig(max_turns=args.max_turns, max_wallclock_seconds=args.max_wallclock_seconds)
    result = run_loop(run_dir, args.mode, config)

    state = read_run_state(run_dir)
    test_config = load_test_config(args.fixture, fixtures_root)
    report = build_eval_report(args.fixture, args.mode, result, state, test_config)
    (run_dir / "eval-report.md").write_text(report, encoding="utf-8")
    append_history(Path(args.history_path), args.fixture, args.mode, result, state, test_config)

    print(report)
    return _EXIT_CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑測試確認通過**

Run: `python3 -m pytest harness/tests/test_run.py -v`
Expected: PASS

- [ ] **Step 5: 跑全部 harness 測試一次確認沒有互相影響**

Run: `python3 -m pytest harness/ -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add harness/run.py harness/tests/test_run.py
git commit -m "feat: harness.run CLI 進入點串接 provisioning/driver/evaluate"
```

---

## Task 8: 三個既有 fixture 的 `test-config.json`

**Files:**
- Create: `fixtures/dept200-delphi/test-config.json`
- Create: `fixtures/dept200-vb6/test-config.json`
- Create: `fixtures/dept300-vb6/test-config.json`

這個任務是資料建立，不是程式碼——內容依據對 domain skill Fingerprint 章節
的分析（見下方每個 fixture 的理由）。沒有 pytest 可跑，用
`python3 -m json.tool` 驗證每個檔案是合法 JSON 當驗收。

- [ ] **Step 1: `fixtures/dept200-vb6/test-config.json`**

`domain-200-vb-java` 的 Fingerprint 明確要求 `.vbp` 裡有
`#Dept200Common#` 這行 COM reference，跟 `domain-300-vb-python`（要求
`#CorpUtil300#`）互斥，不會混淆——這個 fixture 的 domain skill 選定沒有
歧義。`Dept200Common.dll` 是外部編譯好的 COM DLL，repo 裡沒有它的原始碼
檔案，所以沒有 unit 會被標成 `excluded`（見
`.claude/skills/legacy-200-delphi/SKILL.md` 的說明邏輯，VB6 這邊也是同
樣道理，只是 private package skill 換成 `domain-200-vb-java` 自己內
嵌）。

```json
{
  "expected_outcome": "success",
  "expected_domain_skill": "domain-200-vb-java",
  "expected_units": {
    "UserSync": "pass"
  },
  "notes": "Fingerprint 唯一對應 domain-200-vb-java（.vbp 裡的 #Dept200Common# COM reference），私有套件是外部編譯 DLL 沒有原始碼檔案，不會有 excluded unit。"
}
```

- [ ] **Step 2: `fixtures/dept300-vb6/test-config.json`**

跟上面同理，但 Fingerprint 對到 `domain-300-vb-python`（`#CorpUtil300#`
COM reference + registry key 存取模式），一樣沒有 excluded unit。

```json
{
  "expected_outcome": "success",
  "expected_domain_skill": "domain-300-vb-python",
  "expected_units": {
    "UserSync": "pass"
  },
  "notes": "Fingerprint 唯一對應 domain-300-vb-python（.vbp 裡的 #CorpUtil300# COM reference、HKLM\\Software\\Dept300\\DB registry key 存取），私有套件是外部編譯 DLL，不會有 excluded unit。"
}
```

- [ ] **Step 3: `fixtures/dept200-delphi/test-config.json`**

這個 fixture 刻意讓 `domain-200-delphi-java` 跟 `domain-200-delphi-python`
共用同一份來源端 Fingerprint（`legacy-200-delphi`），純從程式碼證據無法
判斷目標語言是 Java 還是 Python——這是已知、刻意保留的設計（見
`legacy-200-delphi/SKILL.md` 開頭說明）。預期 headless 自決在這裡應該
**卡住**（`needs-human`），不是選錯，evaluator 看到這個 fixture 的
`needs-human` 結果要當作「符合預期」而不是缺陷。

```json
{
  "expected_outcome": "needs-human",
  "expected_domain_skill": null,
  "expected_units": {
    "Dept200Data": "excluded",
    "Dept200Log": "excluded",
    "UserSync": "pass"
  },
  "notes": "domain-200-delphi-java 跟 domain-200-delphi-python 共用同一份來源端 Fingerprint，純程式碼證據無法判斷目標語言，預期 clarify 的 headless 自決在這裡卡住（needs-human）——這是已知、刻意保留的設計，不是缺陷。Dept200Data.pas / Dept200Log.pas 是私有套件本身的原始碼，預期被標 excluded。"
}
```

- [ ] **Step 4: 驗證三份都是合法 JSON**

Run:
```bash
python3 -m json.tool fixtures/dept200-delphi/test-config.json
python3 -m json.tool fixtures/dept200-vb6/test-config.json
python3 -m json.tool fixtures/dept300-vb6/test-config.json
```
Expected: 三個都印出格式化後的 JSON，沒有錯誤。

- [ ] **Step 5: Commit**

```bash
git add fixtures/dept200-delphi/test-config.json fixtures/dept200-vb6/test-config.json fixtures/dept300-vb6/test-config.json
git commit -m "test: 補三個既有 fixture 的預期結果設定"
```

---

## Task 9: 端到端手動驗證（不是自動化測試，是驗收）

**Files:** 無新檔案，執行 Task 1-8 的成果。

這個任務沒有 pytest 步驟——它是對整個 harness 的第一次真實驗收，用最簡單、
證據最充分的 fixture（`dept200-vb6`，domain skill 選定無歧義）跑一次完
整的端到端模式，確認前面各任務接起來真的能動。

- [ ] **Step 1: 確認 `.claude/settings.json` 模板存在且有 deny 規則**

Run: `cat templates/settings.json`
Expected: 看到 `git commit`/`git push`/套件安裝相關的 deny 規則（模板既
有內容，不用新增）。

- [ ] **Step 2: 跑 harness**

Run:
```bash
cd /Users/asteroid/Code/CodeMigration
python3 -m harness.run --fixture dept200-vb6 --mode e2e
```

- [ ] **Step 3: 檢查產出**

Run: `ls runs/dept200-vb6-e2e-*/`
Expected: 看到 `legacy/`、`migration/`（含 `decision-log.md`、
`domain-skill.txt`、`manifest.tsv` 等）、`.claude/settings.json`、
`eval-report.md`。

Run: `cat runs/dept200-vb6-e2e-*/eval-report.md`
Expected: `outcome: success (expected: success, MATCH)`，domain skill 顯
示 `domain-200-vb-java`、`MATCH`，`UserSync: expected=pass actual=pass
[MATCH]`。如果實際結果是 `needs-human` 或 `error`，把 `eval-report.md`
跟對應 run 目錄下的檔案內容記下來，回頭檢查是 Task 1 的 skill 修改有問
題、還是 `invoke_claude` 對 `claude -p --output-format json` 實際回傳格
式的假設跟真實不符（見 Task 5 的注意事項），修正後重跑這個任務，不要略
過直接進下一步。

- [ ] **Step 4: 確認 `harness/history.tsv` 有記一筆**

Run: `cat harness/history.tsv`
Expected: 看到 header 行 + 一筆 `dept200-vb6  e2e  success  ...`（tab 分
隔）。

- [ ] **Step 5: Commit（只 commit history.tsv，run 產物不進版控）**

先確認 `.gitignore` 排除 `runs/`（如果還沒排除，加進去）：

```bash
grep -q "^runs/$" .gitignore || echo "runs/" >> .gitignore
git add .gitignore harness/history.tsv
git commit -m "test: 端到端驗收跑過 dept200-vb6，harness 可用"
```

---

## Self-Review 備忘（實作時每完成一個 Task 都回頭對一次）

- Spec 第 4 節（headless 協定）→ Task 1。
- Spec 第 5 節（test-config、golden-convert-input）→ Task 4（provisioning
  讀 golden-convert-input）、Task 8（test-config 內容）。
- Spec 第 6 節（driver 迴圈）→ Task 2/3/5。
- Spec 第 7 節（gate 政策表）→ Task 3 的 `evaluate_gate` 邏輯逐條對照。
- Spec 第 9 節（evaluator）→ Task 6。
- Spec 第 10 節（安全）→ Global Constraints + Task 9 Step 1 確認 deny 規
  則存在。
- `golden-convert-input/` 實際內容（給 convert-only 模式跑）目前**沒有**
  在任何 Task 產生——它需要先有一次人工審過的端到端 run 結果才能凍結，屬
  於 Task 9 之後的人工後續動作，不是這份 plan 能自動化的步驟：等 Task 9
  跑出乾淨的 `dept200-vb6` run、人工確認 `RULEBOOK.md`/`manifest.tsv` 沒
  問題後，手動複製到 `fixtures/dept200-vb6/golden-convert-input/`，才能
  真正跑 `--mode convert-only` 驗證。
