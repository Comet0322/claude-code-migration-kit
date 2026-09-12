---
name: migration
description: >
  遷移流程的頂層指揮 skill。只做路由：依 migration/ 目錄底下有沒有對應產
  物，決定呼叫 migration-analyze / migration-clarify / migration-convert 中
  的哪一個。自己不分析程式碼、不做規則決策、不轉換程式碼。適用於「批次同類
  老舊應用」的語言遷移，每個 gate 結束就停，等人類簽核才進下一步。Use when
  the user wants to migrate/port/rewrite a legacy application to a new
  language using the pre-packaged domain knowledge (domain-* skills).
---

# 遷移頂層指揮 skill

你只做一件事：**看 `migration/` 目錄底下現在有什麼，決定下一步呼叫誰**。
不要自己動手分析、決策或翻譯——那分別是 migration-analyze /
migration-clarify / migration-convert 的工作。每次呼叫完子 skill，照它自己
的 gate 規則決定是否停下。

## 範圍

範圍到「轉換完成、每個 unit 測試通過、加上一次輕量的整合 build/run 檢
查」為止（整合檢查的細節在 `migration-convert` 裡，全部 unit pass 後自動
觸發一次，不需要你額外呼叫誰）。**不包含**原始 kit 裡那種獨立的全域
build 階段（錯誤變機器佇列、切片給不碰編譯器的 fixer、重跑到乾淨）跟
Step 6 的行為比對（inherited test suite burndown / parity referee）——這
兩個是為大規模批次設計的重機械，如果人類要，是刻意的擴充，不要自己假設
已經包含在內。

## 路由

1. **`migration/analysis/manifest-draft.tsv` 不存在**：呼叫
   `migration-analyze`。它是唯讀且可重跑的，跑完**不用等簽核**，直接進第
   2 步（除非它自己因為循環依賴規模異常而主動要求人類先看）。

2. **分析產物齊全，但 `migration/RULEBOOK.md` 或 `migration/manifest.tsv`
   或 `migration/domain-skill.txt` 缺任一個**：呼叫 `migration-clarify`。
   它結尾一定會停——**STOP，等人類確認**，不要自己判斷「看起來沒問題」就
   接著跑第 3 步。

3. **`migration/pilot-manifest.tsv` 存在，但 `migration/pilot-signoff.txt`
   不存在**：呼叫 `migration-convert`，manifest 路徑帶
   `migration/pilot-manifest.tsv`。跑完呈現它回報的 burndown，**STOP，請
   人類看過結果**。人類（或你在人類明確同意後）才寫
   `migration/pilot-signoff.txt` 當簽核記號——**即使 pilot 全部
   pass、沒有任何 rule-gap，也不要自己直接寫這個檔案跳過確認**：pilot 乾
   淨不等於人類已經簽核，這條線不能省。

4. **pilot 已簽核，`migration/manifest.tsv` 裡還有 unit 不是 `pass`
   狀態**：呼叫 `migration-convert`，manifest 路徑帶
   `migration/manifest.tsv`（完整批次）。pilot 跑過的 unit 因為狀態已經是
   `pass`，這次會自動跳過，不會重做。跑完呈現最終 burndown，STOP。

5. **manifest 全部 `pass`，但 `migration/state/_integration.json` 不存在
   或 `status` 不是 `pass`**：再呼叫一次 `migration-convert`（帶完整
   manifest）——它會發現所有 unit 都過了，觸發那次一次性的整合 build/run
   檢查。整合檢查失敗不算「完成」，STOP，列出症狀給人類判斷退回哪個
   unit。

6. **manifest 全部 `pass` 且整合檢查也 `pass`**：回報完成。如果
   `migration/rulebook-amendments.md` 裡還有待處理項目，列出來提醒人
   類——那些是規則缺口的紀錄，不會自己被套用。

## 批次使用

同一批老舊應用通常是多個各自獨立的 repo/checkout，不是同一個 repo 裡塞多
個實例。對下一個實例重跑這個 skill，會是全新的 `migration/` 目錄、從第 1
步開始——只是 migration-clarify 選 domain skill 那步，多半會因為指紋比對
猜對而很快確認，不用每次重新想一輪。

## 你不該做的事

- 不要因為某一步「看起來很簡單」就自己動手做掉，改成呼叫對應的子 skill。
- 不要在任何一個 STOP 點之後自己判斷「應該沒問題」就繼續——每個 gate 存
  在都是因為錯在這裡最貴，用停下來換確定性。
