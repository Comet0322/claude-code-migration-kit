# 遷移 kit 自動化測試框架 — 設計文件

日期：2026-09-13
狀態：待人審核

## 1. 目標與範圍

給定一份「拿來測試的舊程式碼」（`fixtures/<name>/`），自動、無人值守地跑一次
（或多次）這個 repo 的 migration kit（`migration` 頂層指揮 skill + 對應
domain skill + 目標端 corp lib），驗證「domain skill + corp lib 的內容能不
能讓 kit 生出經過完善測試的程式碼」，並保留完整的過程紀錄（誰在哪裡做了什麼
決定、根據什麼理由），讓使用者（yuhsiang）事後檢討、調整 kit 的設計（skill
文字、domain skill 內容、rulebook 種子規則）。

**不是**：對 kit 本身做單元測試框架（那是另一件事）；**不是**：取代
`migration` router 既有的人類簽核流程——這個框架的「無人值守」是**外顯、可
關閉的測試模式**，靠一個標記檔案觸發，真實使用者跑 kit 時行為完全不變。

**範圍包含兩種驗證模式**（見第 3 節），皆屬於本次設計；**不包含**：多人格
persona 模擬、Agent SDK 層級的工具攔截（已查證不可行，見第 8 節）、對
`migration-analyze`/`migration-convert` 的任何修改（它們不呼叫
`AskUserQuestion`，天生 headless-safe，不需要動）。

## 2. 前提事實（查證過，設計依據）

- `migration-clarify` 是唯一在單次 skill 呼叫過程中會呼叫 `AskUserQuestion`
  的 skill（grep 全部 `.claude/skills`，只有它跟 `domain-template`
  的說明文字提到，`domain-template` 本身不會被執行）。三個呼叫點：
  - 第 1 節：選 domain skill（靠 Fingerprint 證據判斷）。
  - 第 7 節：選目標端專案形狀（可能無法純從程式碼推論）。
  - 第 171-197 行：UI 層保留/捨棄範疇決定（範疇決定，非證據判斷）。
  - 第 3 節 ground-truth 策略雖然沒有字面呼叫 `AskUserQuestion`，性質上一樣
    是「停下來問人類」，一併納入 headless 協定。
- 查證結論（來源：claude-code-guide agent 查 Agent SDK 官方文件）：Agent
  SDK 的 `canUseTool`/permission callback 只能准駁工具呼叫，**不能**代填
  `AskUserQuestion` 的答案；`--permission-prompts none` 是把工具整個拿掉而
  非幫它作答；純 `claude -p` 遇到它會卡住或被拒絕。**結論：無法在完全不改
  skill 的情況下無人值守跑過 `AskUserQuestion`**，必須修改
  `migration-clarify` 本身，改成外顯的 headless 協定（見第 4 節）。
- `migration-convert` 的開跑前檢查（其 SKILL.md 第 24-50 行）要求
  `.claude/settings.json` 已有擋 `git commit`/`git push`/套件安裝的 deny
  規則，且**明確禁止 agent 自己在對話裡編輯這個檔案**——這是
  `migration/SKILL.md` 開頭就講的「人類的一次性 repo 設定」。框架的 run
  provisioning（第三方腳本，發生在呼叫 `claude` 之前，不是 claude 自己在
  對話裡動手）比照這個一次性設定，把 `templates/settings.json` 複製進每個
  新建的 run 工作目錄——這跟一個人類操作者手動 `cp` 完全等價，不是讓 agent
  繞過紅線。

## 3. 兩種驗證模式

### 3.1 端到端模式（主要模式）

從 `fixtures/<name>/legacy/` 開始，跑完整 `migration` router：
analyze → clarify（headless 自決協定生效）→ convert（pilot → 完整批次 →
整合檢查）。目的：抓真實使用者會撞到的整體摩擦（domain skill 內容夠不夠讓
clarify 自己判斷對、rulebook 種子規則夠不夠、corp lib 文件夠不夠讓三個
subagent 產出通過測試的程式碼）。

### 3.2 convert-only 模式（獨立、快、低雜訊）

直接餵 `fixtures/<name>/golden-convert-input/`（見第 5.2 節）給
`migration-convert`，跳過 analyze/clarify。目的：domain skill/corp lib 文
件一有更動，可以快速重跑，只看「轉換品質」這一段訊號，不被 clarify 自己的
問題（例如某次 headless 判斷卡住）汙染。

兩種模式共用同一套 driver 迴圈邏輯（第 6 節）、gate 決策政策（第 7 節）、
evaluator（第 9 節），差別只在起點跟略過的步驟。

## 4. `migration-clarify` headless 自決協定（唯一要改的 skill 檔案）

在檔案開頭（第 1 節之前）加一段共用說明，定義協定；在第 1、7 節、
171-197 行的 UI 範疇段落、第 3 節，各自的 `AskUserQuestion`/「問人類」處加
一句條件判斷：

> 若 `migration/.headless-test` 標記檔存在：不要呼叫 `AskUserQuestion`，
> 也不要用任何其他方式停下來等對話回覆。改成：依照這一節原本會用來排推薦
> 選項的同一套證據跟推理，直接**採用你自己認為最合理的選項**，把完整的候
> 選比較、理由、信心程度，以追加（append）方式寫進
> `migration/decision-log.md`（含小節標題，例如 `## 1. domain skill 選
> 定`），然後照這個決定繼續往下做這一節，不停下。
>
> 例外：如果依照現有證據，你判斷任何一個選項都缺乏客觀依據支持（例如
> Fingerprint 比對分數幾乎打平、或程式碼裡完全沒有能推斷目標形狀/UI 範疇
> 的線索），把這個判斷連同理由寫進 `migration/decision-log.md`，然後**停
> 止整個 skill 呼叫**——這不是失敗，是這個情境對真人來說也需要問，如實記
> 錄比硬猜一個答案更有價值。停止時在 `decision-log.md` 該筆記錄結尾固定
> 寫一行 `STATUS: needs-human`，讓 driver 用簡單字串比對判斷，不必解析自
> 然語言（正常自決完成的記錄則不寫這一行，或寫 `STATUS: decided`——確切
> 格式在實作階段釘死，這裡只定規範）。

第 3 節 ground-truth 策略額外加一句：

> headless 模式下，如果第 1 層（執行環境）探測失敗、且沒有第 2 層需要的
> `migration/behavior-snapshots/` 素材，**預設直接採用 tier=`inference`**，
> 理由寫「自動化測試環境，無來源端執行環境或行為快照可用」，記進
> `migration/ground-truth-strategy.md`，不停下。這是刻意放寬的測試預設
> 值，跟正常情境下「兩者都沒有才是最後手段、需要明確人類同意」的原則不
> 同，只在標記檔存在時生效。

標記檔不存在時（真實使用者的一般用法），以上條件都不成立，原本的
`AskUserQuestion` 呼叫、正常 tier 判斷邏輯完全不變。

## 5. Fixture 測試資料

### 5.1 `fixtures/<name>/test-config.yaml`

**只給 evaluator 事後評分用，不餵給 clarify 當決策輸入**（否則等於作弊，
測不出真實資訊夠不夠）。內容：

```yaml
expected_domain_skill: domain-200-delphi-python
expected_units:
  CurrencyRules: pass
  DriverImpl: excluded   # 私有套件本身，預期被排除
notes: "CurrencyRules 依賴一個第三方 rounding 演算法，rulebook 需要種子規則覆蓋"
```

### 5.2 `fixtures/<name>/golden-convert-input/`（convert-only 模式專用）

人工審過、確認正確的 clarify 產物凍結版，來源通常是某次端到端模式跑完、
人類檢查沒問題後手動複製/凍結的結果：`manifest.tsv`、`RULEBOOK.md`、
`ground-truth-strategy.md`、`target-shape.txt`（如適用）、以及一份**尚未
轉換任何 unit**的初始 `target/` scaffold 快照（複製自 clarify 第 9 節跑完
後、`migration-convert` 開跑前的狀態）。convert-only 模式的 run
provisioning 直接把這些連同 `legacy/` 複製進新 run 目錄，不重新 scaffold。

## 6. Driver（`harness/run.py`）

外部腳本，plain headless `claude -p` 迴圈（不用 Agent SDK——第 4 節的協定
讓 headless clarify 完全不需要程式化回答 `AskUserQuestion`，用不到 SDK 的
攔截能力）。

**建立 run（provisioning，第三方腳本動作，不是 claude 對話裡的動作）**：

1. 建立 `runs/<fixture>-<mode>-<timestamp>/`。
2. 複製 `fixtures/<name>/legacy/`（端到端模式）或
   `fixtures/<name>/golden-convert-input/` + `legacy/`（convert-only 模
   式）進去。
3. 複製 `templates/settings.json` 的 deny 規則到這個 run 的
   `.claude/settings.json`（比照 `migration/SKILL.md` 要求的人類一次性設
   定，見第 2 節）。
4. 端到端模式：寫入 `migration/.headless-test` 標記檔。convert-only 模式
   不需要（不會經過 clarify）。

**主迴圈**：

```
while not done and turns < MAX_TURNS and elapsed < MAX_WALLCLOCK:
    invoke `claude -p <prompt>` in run dir
        （端到端模式 prompt："用 migration skill 處理這次遷移"；
         convert-only 模式 prompt：直接指名呼叫 migration-convert，
         manifest 路徑帶 migration/manifest.tsv）
        --permission-mode acceptEdits（允許讀寫/Bash 在這個工作目錄內執行，
        真正危險操作靠 settings.json 的 deny 規則擋，不靠這個旗標）
    inspect 檔案狀態（跟 migration/SKILL.md 的路由邏輯一致）：
      - clarify 產出的 decision-log.md 出現「無客觀依據」的停止記錄
          → mark needs-human, done
      - pilot-manifest.tsv 存在但 pilot-signoff.txt 不存在
          → 讀 migration/state/*.json + deviation-log.tsv：
            全部 pass/excluded 且 deviation-log 沒有新增未解決項目
              → 腳本自己寫 pilot-signoff.txt（決定性規則，不呼叫 LLM）
            否則 → mark needs-human, done
      - manifest.tsv 全部 pass/excluded 且 state/_integration.json 不是 pass
          → 繼續迴圈（router 自己會觸發整合檢查）
      - manifest.tsv 全部 pass/excluded 且整合檢查 pass
          → done, success
      - 其他非預期 STOP／錯誤訊息
          → mark needs-human, done, 記錄原始輸出
    else → 繼續迴圈
```

## 7. Gate 決策政策總表

| Gate | 誰決定 | 政策 |
|---|---|---|
| domain skill 選定 | clarify 自己（headless 自決） | 用自己的 Fingerprint 推理；無法判斷就停止並記錄 |
| 目標形狀 / UI 範疇 | clarify 自己（headless 自決） | 同上；多數 fixture（純批次/CLI）根本不會觸發 |
| ground-truth tier | clarify 自己（headless 自決，測試環境預設寬鬆） | 有環境/snapshot 才用；否則預設 `inference` 並記錄 |
| pilot-signoff | driver 腳本（決定性規則，非 LLM） | 100% pass 且無新增未解決 deviation 才自動簽；否則 needs-human |
| 完整批次 → 整合檢查觸發 | driver 腳本 | 純粹檔案狀態判斷，同 `migration/SKILL.md` 路由邏輯 |
| settings.json deny 規則 | run provisioning（第三方腳本，非對話內動作） | 直接沿用 `templates/settings.json`，比照人類一次性設定 |
| 套件安裝確認（clarify §9 / convert 前置檢查） | 不自動處理 | 若 domain skill 要求外部套件而 fixture 環境沒裝好，一律 needs-human；不讓 harness 自己裝 |

## 8. 已知限制／刻意不做

- **persona 判官 / 多人格模擬**：原本設計想另開一個獨立 Claude 呼叫扮演使
  用者回答 `AskUserQuestion`，後來確認用 clarify 自決 + `decision-log.md`
  更簡單、訊號更直接（測的是「clarify 自己給的資訊夠不夠讓它做對」，不是
  「模擬人格判斷得準不準」），故不建立額外的判官 agent。
- **Agent SDK 層級攔截 `AskUserQuestion`**：查證不可行（見第 2 節），放棄
  此路徑，改用 skill 內顯式協定。
- **`migration-analyze`/`migration-convert` 不修改**：兩者都不呼叫
  `AskUserQuestion`，headless 天生安全，不在本次改動範圍。

## 9. Evaluator / 報告

跑完（不論以下哪一種終止狀態）產出 `runs/<...>/eval-report.md`：

- `success`：manifest 全 pass/excluded 且整合檢查 pass。
- `needs-human`：撞到第 7 節任一 gate 的保守政策邊界（clarify 自決卡住、
  pilot 不乾淨、套件沒裝好等）——**這是預期內、有資訊價值的正常終止**，
  不是 bug。
- `error`：非預期的崩潰、逾時、或狀態檔格式跟預期不符——代表 harness 本
  身或 skill 出現非預期行為，需要當 bug 處理，跟 `needs-human` 分開列，
  不要混在一起統計。

- **決策正確性**：比對 `migration/decision-log.md` + `domain-skill.txt`
  跟 `fixtures/<name>/test-config.yaml` 的 `expected_domain_skill`，是否
  一致；不一致時附上 decision-log 裡的理由，方便判斷是證據不足還是判斷邏
  輯有問題。
- **Unit 結果**：比對每個 unit 最終 `state/<unit_id>.json` 的 `status`
  跟 `test-config.yaml` 的 `expected_units`。
- **品質訊號**：彙整既有的 `migration/deviation-log.tsv`、
  `migration/rulebook-amendments.md`、每個 unit 的 test-reviewer 裁決——
  不另外跑一次獨立的語意評分 agent（避免重複現有訊號、增加不必要成本），
  用既有資料算出通過率、deviation 分類分布。
- **成本**：彙整 `migration/cost-log.tsv` 的總計。
- 同時把這次跑的關鍵欄位（fixture、mode、timestamp、success/needs-human/
  error、domain skill 對不對、pass 率、總 token）附加一行到
  `harness/history.tsv`，供跨版本（kit 設計調整前後）比較。

## 10. 錯誤處理與安全

- 每個 run 是獨立目錄，彼此不共用狀態，run provisioning 不修改
  `fixtures/` 底下任何檔案（純讀取複製）。
- driver 對每輪 `claude -p` 呼叫設總輪數上限與總時長上限，避免因某個
  skill 行為異常造成無限迴圈。
- 任何危險操作（git commit/push、裝套件）一律靠 run 自己的
  `.claude/settings.json` deny 規則擋在 Claude 那一層，driver 腳本自己也
  不執行任何寫入 fixture 來源、或跨 run 目錄的操作。
- persona/自決邏輯故障（例如 decision-log.md 格式不如預期、找不到預期檔
  案）一律視為 `needs-human`，不讓 driver 自己猜測繼續。

## 11. 後續實作順序（給 writing-plans 用的粗略順序，非最終計畫）

1. 改 `migration-clarify`（第 4 節協定）+ 手動跑一次確認標記檔存在/不存
   在兩種情況行為都對。
2. 建 `harness/run.py` 端到端模式，先在既有的 `fixtures/dept200-delphi`
   （或最簡單的一個 fixture）跑通。
3. 補 `test-config.yaml`、`golden-convert-input/`，實作 convert-only 模
   式。
4. 實作 evaluator + `eval-report.md` + `harness/history.tsv`。
5. 對三個既有 fixture（`dept200-delphi`、`dept200-vb6`、`dept300-vb6`）
   跑過一輪，確認整體可用，再交給使用者做第一次真正的「事後檢討」。
