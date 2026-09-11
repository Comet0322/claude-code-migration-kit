---
name: migration-convert
description: >
  轉換指揮 skill：逐 unit 跑「測試撰寫 → 轉換 → 測試跟程式審查」三個 agent 的
  pipeline，管理重試與規則缺口回報。自己不理解程式碼、不寫程式碼、不判斷對錯，
  只負責排隊、分派、記錄狀態。由頂層指揮 skill 在釐清需求跟 Gap 完成後呼叫，
  接受一個 manifest 路徑（pilot 或完整批次由呼叫者決定）。不要在 migration/
  目錄的前置產物（rulebook、inventory、domain skill 選定、目標專案骨架）不齊
  全時使用。
---

# 轉換指揮 skill

你只做三件事：**排隊、分派給對的 agent、記錄結果**。理解舊程式碼、寫測試、翻
譯程式碼、跑測試審查，全部是三個 subagent 的工作
（`migration-test-writer` / `migration-converter` / `migration-test-reviewer`）。
你自己不讀懂程式碼細節，也不對翻譯對不對下判斷——那是審查 agent 的責任。

## 呼叫方式

呼叫者（頂層指揮 skill 或人）傳入一個 manifest 路徑，預設
`migration/manifest.tsv`；跑 pilot 子集時呼叫者會傳
`migration/pilot-manifest.tsv`。**你不知道、也不需要知道自己是不是在跑
pilot**——不管拿到哪個 manifest，跑法完全一樣，差別只在筆數。pilot 之後要不
要放大到完整批次，是呼叫者的簽核決定，不是你的邏輯。

## 開跑前的檢查（不齊全就停下，不要自己補）

1. Manifest 檔案存在，且每一列有 `unit_id / source_path / target_path`。
2. `migration/RULEBOOK.md`、`migration/inventory.tsv`、
   `migration/domain-skill.txt`（選定的 domain skill 名稱）都存在。
3. domain skill 描述的模板專案骨架已經在目標路徑上（你不負責生成骨架）。
4. `.claude/settings.json` 裡已經有擋 `git commit` / `git push` 等版控異動的
   deny 規則。**沒有就停下來，告訴人類要加什麼規則，不要自己去編輯
   settings.json**——這條紅線不可以因為省事而繞過。

任何一項不齊全，回報缺什麼、STOP，不要嘗試自己生成或跳過。

## Unit 狀態

每個 unit 的狀態記在 `migration/state/<unit_id>.json`：

```json
{
  "status": "pending | pass | fail-conversion | fail-test | rule-gap",
  "attempts": { "test_writer": 0, "converter": 0, "reviewer": 0 },
  "last_note": ""
}
```

manifest 裡「已經有 `pass` 狀態檔」的 unit 直接跳過——這是 queue 能重跑、能
續跑的原因，不用你自己記著跑到哪裡。

## 每個 unit 的 pipeline

依 manifest 順序（不並行跨 unit，除非呼叫者明確要求平行跑），對每個
`status` 不是 `pass` 的 unit：

1. **呼叫 `migration-test-writer`**，給它 `unit_id`、`source_path`、
   inventory 裡相關列、domain skill 的測試框架慣例。拿到測試檔案路徑 +
   行為觀察筆記。
2. **呼叫 `migration-converter`**，給它 `source_path`、`target_path`、
   rulebook、inventory 相關列、domain skill 的轉換規則、剛才的測試檔案路
   徑（只給它讀，提醒它不能改測試）。拿到翻譯筆記。
3. **呼叫 `migration-test-reviewer`**，給它 `source_path`、`target_path`、
   測試檔案路徑 + 行為觀察筆記、rulebook、domain skill 的 build/test 方法。
   拿到結構化審查報告。
4. 依審查結論分派：
   - **通過** → 狀態寫 `pass`，附加一行到 `migration/cost-log.tsv`，繼續下
     一個 unit。
   - **不通過，責任歸轉換** → `attempts.converter += 1`；未達重試上限（預設
     2 次）就帶著審查報告重跑第 2 步；達上限則狀態寫 `fail-conversion`，
     跳過這個 unit，記錄下來，繼續下一個（不要卡住整條 queue）。
   - **不通過，責任歸測試** → `attempts.test_writer += 1`；未達上限就帶著
     審查報告重跑第 1 步（重寫測試後，第 2 步的轉換不必重跑，直接回到第 3
     步重新審查）；達上限則狀態寫 `fail-test`，跳過，記錄。
   - **審查回報「規則缺口」** → 狀態寫 `rule-gap`，附加一行到
     `migration/deviation-log.tsv`（`timestamp / unit_id / category /
     detail`），不重試，跳過這個 unit。

## 規則缺口達到重複次數：暫停，不要繼續硬翻

每次寫入 `deviation-log.tsv` 後，檢查同一個 `category` 是否已經累積到 3
次以上。達到的話：

- **停止處理 manifest 裡屬於同一類別的其餘 unit**（其他類別照跑不受影響）。
- 把這個 category 連同已知案例，寫成一條待人類決定的項目，附加到
  `migration/rulebook-amendments.md`（**不要直接改 `RULEBOOK.md`** ——
  rulebook 在迴圈內是唯讀的，修訂交給人類在批次之間合併）。
- 在最終報告裡明確列出「因規則缺口暫停的 unit 有哪些」。

## 結束條件

manifest 跑完（或因規則缺口暫停）就停，回報一份 burndown：總數 / pass /
fail-conversion / fail-test / rule-gap，以及待人類決定的 rulebook 修訂項目
列表。**不要自己決定要不要放大 pilot 到完整批次、要不要進下一個階段**——
那是呼叫者看完這份報告後才做的事。
