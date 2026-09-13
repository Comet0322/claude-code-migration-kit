---
name: migration-clarify
description: >
  釐清需求跟 Gap skill：由頂層指揮 skill 在 migration/analysis/ 產物齊
  全、但 rulebook 或 manifest 還缺的時候呼叫。結尾一定停下來等人簽核，
  不自動進轉換。
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

如果模板專案/新語言 library 文件/測試build方法這幾節寫的是「同 skill
`<名稱>`」而不是內嵌內容,用 Skill 工具載入那個 skill 取得實際內容——它
是被抽出來獨立維護、可能也服務 migration 之外情境的目標端共用知識(見
`domain-template` 的說明),不是選定的 domain skill 遺漏沒填。載入後當作
這個 domain skill 本來就內嵌了這些內容一樣使用,一併餵給後面每一節跟三
個 subagent。

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

## 7. 決定目標端專案形狀（選填，domain skill 模板專案列出多於一種選項才需要）

有些目標語言的專案模板不是單一慣例——例如同樣目標 Python，公司內部同時
有「FastAPI 服務」跟「背景 ETL 批次」兩種形狀，各自的目錄結構、進入點、
整合檢查方式都不一樣，對應到不同的模板 skill（例如
`python-corplib-fastapi` / `python-corplib-etl`）。

如果選定的 domain skill 的「模板專案」節列出不止一個選項，用
`AskUserQuestion` 跟人類確認**這次遷移（這個 `migration/` 目錄、這份
manifest）**是哪一種形狀——跟第 1 節選 domain skill 一樣，一次遷移裡的
manifest 只會是一種形狀，不是逐 unit 各自判斷。如果人類告訴你這次遷移的
manifest 裡真的混了兩種形狀，把這件事回報給人類：這代表這個 repo 該拆成
兩次獨立的遷移實例（各自一份 `migration/` 目錄），而不是在同一份
manifest 裡混搭。

選定後寫入 `migration/target-shape.txt`（單行，模板 skill 名稱）。第 9
節 scaffold 用哪個模板骨架、`migration-convert` 呼叫三個 subagent 時要
餵哪份模板知識，都由這裡決定。

domain skill「模板專案」節如果只寫了一個「同 skill `<名稱>`」（沒有列出
選項），代表這個目標語言在這批應用裡沒有形狀分歧，跳過這節，不用問人
類，也不用寫 `target-shape.txt`。

## 8. 複製來源到本地、補 target_path、產出完整 manifest

讀 `migration/analysis/manifest-draft.tsv`——它的 `source_path` 是
migration-analyze 掃描時看到的位置，不保證就在這次遷移的執行根目錄底
下（可能是另一個目錄保管的原始碼庫、甚至是唯讀掛載的來源）。**逐一把
每個 unit 的來源檔案複製一份進這次遷移自己的 `legacy/` 目錄**（保留
manifest-draft.tsv 裡的相對路徑結構；來源分散在很多層目錄、彼此關係不
大的情況，攤平成 `legacy/<檔名>` 也可以，只要整個批次裡不會撞名）。

這樣做的理由：這次遷移的整個工作目錄（`migration/`、`legacy/`、
`target/`）要能自成一體、可以整包搬走/封存/跟其他次遷移的結果比較，不
依賴外部那份原始碼庫繼續留在原地、繼續維持同樣的相對路徑——原始碼庫之
後被更新、搬家、甚至刪除，這次遷移已經做的分析跟決策依然完整可信,不會
突然找不到檔案或（更危險）不知不覺對到別的版本。

複製完成後，依模板專案的命名慣例（若第 7 節有決定形狀，以
`target-shape.txt` 指到的模板 skill 為準；沒有形狀分歧就直接用 domain
skill 的模板專案節）逐列決定 target_path，寫 `migration/manifest.tsv`
（欄位：`unit_id, source_path, target_path`，`source_path` 一律指向複製
後的本地 `legacy/...` 路徑，不再指向 manifest-draft.tsv 原本寫的位置）。

### 識別「私有套件本身」的 unit——標記 `excluded`，不進轉換佇列

如果 domain skill（或它引用的來源端共用 skill）的「私有套件文件」節點名
了具體的實作檔案，逐一比對 `modules.tsv` 裡每個 unit 的 `source_path` 檔
名——完全對上的，代表這個 unit 就是私有套件本身的原始碼，不是要被翻譯
的應用程式邏輯：目標端已經有對應的 `corplib` 系列取代它，逐行翻譯這個
unit 沒有意義，只要把其他 unit（呼叫端）裡對它的呼叫改寫成呼叫 corplib
就好。

這種 unit 在 `manifest.tsv` 裡的 `target_path` 欄位留空（或寫
`(excluded — replaced by <skill 名稱>)`），並且立刻寫
`migration/state/<unit_id>.json`，`status` 直接設成 `excluded`（不是
`pending`），`last_note` 寫清楚是被哪個 skill 取代。這個決定要記進
`RULEBOOK.md`（跟其他這批特有的決策一樣，讓人看得到依據），不要默默做
掉，也不要自己發明規則以外的判斷——只有 domain skill 明確點名的檔案才能
這樣標記，不要憑自己的判斷擴大範圍。

domain skill 沒有把私有套件具名到檔案層級（例如只描述一個外部提供的編
譯好的 COM DLL，repo 裡完全沒有對應原始碼檔案）就不會有這種 unit——這種
情況下私有套件的呼叫本來就直接出現在應用程式碼裡，`migration-analyze`
不會把它掃成獨立的 unit，不用特別處理。

### 識別 UI／展示層 unit——問人類要不要保留

有些舊應用有 UI 層（VB6 的 `.frm`、Delphi 的 `.dfm`/表單 unit，或
`uses`/`import` 子句裡出現 `Vcl.Forms`／`Vcl.Controls`／`Forms`／
`Controls` 這類 UI 框架 unit），跟私有套件排除不同——UI 層要不要保留是
**範疇（scope）決定**，不是「目標端已經有等價物」這種技術事實，domain
skill 沒辦法幫你預先決定，一定要問人類。

如果 `migration/analysis/modules.tsv` 裡有 unit 看起來是 UI 層，用
`AskUserQuestion` 問人類這次遷移整批要「保留 UI（連同 UI 一起轉換——這
代表選定的 domain skill 要有對應的目標端 UI 框架知識，模板專案/新語言
library 文件都要涵蓋，沒有的話跟第 6 節一樣：回報給人類，domain skill
需要補強或選錯了）」還是「捨棄 UI，只轉核心邏輯」。跟第 7 節的目標端形
狀決定一樣，一次遷移整批只問一次，不是逐 unit 各自判斷。

**捨棄 UI**：這些 unit 標記 `excluded`（跟私有套件排除用同一個機制，
`last_note` 寫「UI 層，人類決定不遷移，見 RULEBOOK.md」），並在
`RULEBOOK.md` 記一條這個決定（含日期跟理由）——這是範疇縮減的決定，跟
規則決策一樣要留痕跡，不能是預設值、更不能是你自己看順眼就決定。**UI
事件處理常式裡混了商業邏輯的 unit（例如一個 `ButtonClick` 事件同時更新
畫面跟寫 DB）不能直接整個標 `excluded`**——這種要在 `RULEBOOK.md` 記一
條，讓轉換 agent 知道只抽出商業邏輯部分轉換、UI 觸發的部分捨棄，不是整
個 unit 二選一。

沒有偵測到任何 UI 層 unit（例如這批本來就是純批次/CLI 工具，像部門
200/300 這批模擬情境）就跳過這節，不用問人類。

## 9. Scaffold 目標專案

依模板專案（同第 8 節，若有 `target-shape.txt` 就用它指到的模板 skill）
把目標路徑的骨架建出來(目錄結構、build 設定檔)。已經存在的部分不要覆
蓋——這個步驟該是幂等的,重跑不該砍掉已經轉換好的東西。

如果模板專案小節宣告了目標語言側需要的外部套件：用唯讀方式確認(`test -d
node_modules`、`pip show <pkg>` 之類)是不是已經裝好。沒裝好就**停下來告
訴人類要先手動執行哪個安裝指令**，不要自己執行安裝——這條跟第 3 節「取
得 ground truth 的方式」裡「不能自己裝東西」是同一條紅線，只是換成目標
語言側。人類裝好之後你再重跑這一節確認。

## 10. 產生 pilot 子集

從 `migration/manifest.tsv` 挑 2-3 個 unit,優先挑 `risk-notes.tsv` 標
`high` 的,再搭一個典型/普通的,寫 `migration/pilot-manifest.tsv`。這個子集
是後面轉換階段第一輪要跑的東西——rulebook 沒驗證過就直接對整個批次放,一旦
規則有系統性錯誤,成本會在你發現之前就已經花在全部 unit 上。

## 結束條件

以上十節都做完就**一定要停**,回報完整產物清單(domain skill、
ground-truth-strategy、target-shape（如果有做這節）、rulebook、
inventory、mismatch 報告如果有、manifest、pilot-manifest、scaffold 狀
態)。
不自動接著呼叫轉換——由人看過這裡的判斷之後,頂層指揮 skill 才會拿
pilot-manifest 去跑 migration-convert。

回報裡順便提醒一句：`migration-convert` 開跑前會檢查
`.claude/settings.json` 有沒有裝好 deny 規則(見 `migration` 第一節「開
始之前」跟 `migration-convert` 的 Red Flags)，如果這是第一次在這個 repo
上跑，趁現在簽核的空檔弄好，不要等 convert 卡住才處理——你自己不會去檢
查或建立這個檔案，這只是提醒，不是你的工作範圍。
