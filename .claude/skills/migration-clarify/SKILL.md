---
name: migration-clarify
description: >
  釐清需求跟 Gap skill：選定 domain skill、跟人draft rulebook 跟 gap
  inventory、比對 domain skill 假設跟實際程式碼的落差、幫 manifest 補上
  target_path、scaffold 目標專案骨架、產生 pilot 子集。結尾一定停下來等人
  簽核，不自動進轉換。由頂層指揮 skill 在 migration/analysis/ 產物齊全、但
  rulebook 或 manifest 還缺的時候呼叫。
---

# 釐清需求跟 Gap skill

這是整條流程裡人機協作最重的一步。你的產出決定了轉換階段的規則從哪來——
錯在這裡最貴，所以每個小節做完都要讓人看得到你依據什麼做的判斷，不要悶頭
自己決定完就跳過。

## 1. 選 domain skill（每個 repo 問一次，不是每個 unit）

- 先檢查 `migration/domain-skill.txt` 是否已存在——這一輪對話裡如果已經選
  過（例如同個 session 重跑這個 skill），直接載入，不要重問。
- 不存在：掃描 `domain-*` 命名的已安裝 skill（workspace 跟 user-level 都
  找，`domain-template` 本身不算數，跳過）。如果一個都找不到，**停下來告
  訴人類要先準備一個**——可以複製 `domain-template` skill 改名填內容——不
  要自己憑空編一份領域知識出來頂替。
- 找到候選：用 `migration/analysis/modules.tsv` 觀察到的匯入路徑、設定檔
  名稱等指紋，跟每個候選 domain skill 的 Fingerprint 小節比對，猜出最可能
  符合的一個，排成推薦選項。用 AskUserQuestion 問人類要用哪一個（列出候
  選 + 推薦值 + 理由）。
- 選定後寫入 `migration/domain-skill.txt`（單行，domain skill 名稱）。

批次情境的提醒：這個檔案是**這個 repo 自己的紀錄**，不是跨 repo 共用的。同
批次的下一個老舊程式實例通常是另一個獨立的 repo/checkout，那邊會是全新的
`migration/` 目錄，一樣要問一次——只是因為指紋比對通常會猜對同一個 domain
skill，實際上人類多半只是確認推薦值，不是重新想一次。

## 2. 載入 domain skill 內容

讀進：私有套件文件、模板專案、語法轉換/library 替換規則、新語言 library 文
件、測試/build 方法。這些會餵給後面每一節跟轉換階段的三個 subagent。

## 3. 取得 ground truth 的方式（三層，人類決定，不是 agent 自己選）

轉換階段的測試撰寫 agent 需要「舊程式碼實際執行的真實行為」當測試斷言依
據——但這台機器不一定裝得了舊語言的執行環境。**這件事必須在這裡先問清
楚，不能留到轉換階段才讓測試撰寫 agent 自己發現、自己想辦法解決**：曾經
真實發生過，test-writer 發現沒有 Delphi 編譯器，自己執行 `brew install
fpc` 把編譯器裝到機器上——這是不可接受的，裝軟體/改環境是人類的決定，不
是 agent 可以自己動手處理的範圍。

依序檢查，選出這批（或這個 repo）要用哪一層：

1. **有可用的執行環境**：先看 domain skill 的「來源語言執行環境」小節有
   沒有寫怎麼呼叫；沒寫，或寫的方法在這台機器上試了失敗，用唯讀方式探測
   （例如 `which <compiler>`，只查詢、不安裝）確認有沒有現成的。找到就把
   確切呼叫方式寫進 `migration/ground-truth-strategy.md`，tier 記為
   `environment`。
2. **沒有環境：跟人類要 mock data / snapshot**：要這批程式碼的輸入輸出
   範例、既有測試案例、或 production 資料快照，存進
   `migration/behavior-snapshots/`，tier 記為 `snapshot`。這是次選，但比
   环境更貼近多數真實遷移情境——很多 legacy 系統本來就沒辦法在遷移用的
   sandbox 裡裝起來跑。
3. **兩者都沒有，最後手段**：明確跟人類確認「這批要接受用讀文件/程式碼推
   論出來的行為，沒有實測或人工資料驗證」，tier 記為 `inference`，並在
   `migration/ground-truth-strategy.md` 裡記下人類同意的理由跟日期——這
   是風險接受的決定，要留痕跡，不能是預設值或事後才承認。

三層擇一寫進 `migration/ground-truth-strategy.md`，測試撰寫 agent 會讀這
份文件決定怎麼做，不會自己判斷、更不會自己修環境。

## 4. 跟人 draft rulebook

從 domain skill 的「語法轉換/library 替換規則」起手當種子——那些已經是決
定好的規則，不用重新討論。只跟人討論**這批程式碼特有、domain skill 沒覆蓋
到**的翻譯決策：讀出 codebase 裡「兩個 agent 可能做出不同選擇」的地方（用
數據佐證，例如「這個模式出現 N 次」），一條一條讓人決定,寫進
`migration/RULEBOOK.md`（保留 Deviation log 區塊給轉換階段回報用）。

Rulebook 完成後在這個 session 裡就是唯讀的——轉換階段的三個 agent 都不能改
它，之後要改也是人類在批次之間手動改。

## 5. Gap inventory

依 `migration/analysis/modules.tsv` 掃描，列出目標語言會強迫你明確決定、
但源語言可以含糊帶過的地方（ownership、nullability、介面契約），寫
`migration/inventory.tsv`。這是攤開讓 agent 查的表，不是要人一條條讀完。

## 6. Domain skill 假設 vs 實際程式碼比對

如果選定的 domain skill 有填 Fingerprint 小節，逐條跟這個 repo 的實際程式
碼核對：

- 落差不大（少數幾個檔案不符合）：當一般 rulebook 修訂處理，寫進
  deviation log 區塊，繼續往下做。
- 落差嚴重（domain skill 的核心假設整個對不上，例如完全找不到假設的私有套
  件）：停下來,回報給人類,問是不是選錯 domain skill 或這個 domain skill 需
  要更新,不要硬套下去。

沒填 Fingerprint 的 domain skill 就跳過這節,不強制。

## 7. 補 target_path、產出完整 manifest

讀 `migration/analysis/manifest-draft.tsv`,依 domain skill 模板專案的命名
慣例,逐列決定 target_path,寫 `migration/manifest.tsv`(欄位:`unit_id,
source_path, target_path`)。

## 8. Scaffold 目標專案

依模板專案把目標路徑的骨架建出來(目錄結構、build 設定檔)。已經存在的部分
不要覆蓋——這個步驟該是幂等的,重跑不該砍掉已經轉換好的東西。

## 9. 產生 pilot 子集

從 `migration/manifest.tsv` 挑 2-3 個 unit,優先挑 `risk-notes.tsv` 標
`high` 的,再搭一個典型/普通的,寫 `migration/pilot-manifest.tsv`。這個子集
是後面轉換階段第一輪要跑的東西——rulebook 沒驗證過就直接對整個批次放,一旦
規則有系統性錯誤,成本會在你發現之前就已經花在全部 unit 上。

## 結束條件

以上九節都做完就**一定要停**,回報完整產物清單(domain skill、
ground-truth-strategy、rulebook、inventory、mismatch 報告如果有、
manifest、pilot-manifest、scaffold 狀態)。
不自動接著呼叫轉換——由人看過這裡的判斷之後,頂層指揮 skill 才會拿
pilot-manifest 去跑 migration-convert。
