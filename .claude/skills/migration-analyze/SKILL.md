---
name: migration-analyze
description: >
  分析 skill：由頂層指揮 skill 在 migration/analysis/ 產物還不存在時呼
  叫，唯讀掃描舊程式碼決定 unit 遷移順序。不要在其他情境下使用——規則決
  策、domain skill 選定、目標路徑都不是這裡的工作。
---

# 分析 skill

你只產生**事實**，不做**決策**。依賴圖是誰依賴誰，是客觀的；要不要照這個順
序翻譯、翻譯成什麼樣子，不是你的工作。

## 為什麼這步不能決定 target_path

目標路徑的命名慣例來自 domain skill 的模板專案，而 domain skill 要到
migration-clarify 才會被選定（分析先跑，選 domain skill 在後面）。所以這裡
只排「順序」，不填「目標在哪」——manifest 草稿留給 migration-clarify 補完。

## 依賴圖：用腳本，不要用判斷力排序

依賴順序、循環偵測是可以被腳本精確算出來的問題，不要靠 agent 讀程式碼用直
覺排。

1. 檢查 `migration/scripts/depmap_<source language>.*` 是否已經存在——如果
   這個批次先前的實例已經寫過同語言的依賴分析腳本，直接重用，不要重寫。
2. 不存在就依源語言寫一支（parse import/require/include 語句，產出檔案層
   級的邊），存到這個路徑供批次後續實例重用。
3. 跑腳本，輸出：
   - `migration/analysis/depmap/edges.tsv`（from, to）
   - `migration/analysis/depmap/order.txt`（拓樸排序後的檔案順序）
   - `migration/analysis/depmap/cycles.txt`（循環依賴的分組，如果有）

## 循環依賴怎麼處理

不要嘗試自己解開循環。同一個循環裡的所有檔案，在 manifest 草稿裡合併成同
一個 `unit_id`（一起轉換、一起測試、一起審查），用同一個 `cycle_group` 值
標記。這是唯一能讓拓樸順序在有循環的情況下依然成立的做法。

## 輸出

1. `migration/analysis/modules.tsv` — 欄位：`unit_id, source_path,
   cycle_group`（無循環則空白）。
2. `migration/analysis/risk-notes.tsv` — 欄位：`unit_id, risk_flag
   (high/normal), reason`。高風險判斷依據：檔案大小/複雜度異常、fan-out
   異常高、出現分析腳本無法完整解析的語法。這份清單後面會被 pilot 子集選樣
   用到。
3. `migration/analysis/manifest-draft.tsv` — 欄位：`unit_id, source_path,
   cycle_group, order_index`，依拓樸順序排列。

## 邊界

唯讀。不碰 rulebook、inventory、domain skill 選擇，不寫任何 unit 的程式碼，
不產生最終 `migration/manifest.tsv`（那需要 target_path，屬於
migration-clarify 的工作）。

## 結束條件

四個輸出檔案都產出就停，回報摘要（unit 數、循環組數、高風險 unit 數）。這
步是唯讀、可重跑，不需要人類簽核就能讓頂層指揮 skill 直接接著跑
migration-clarify——除非循環依賴的規模或複雜度反常到你判斷應該讓人類先看
一眼，才主動提示。
