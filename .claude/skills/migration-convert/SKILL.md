---
name: migration-convert
description: >
  轉換指揮 skill：由頂層指揮 skill 在釐清需求跟 Gap 完成後呼叫，接受一個
  manifest 路徑。不要在 migration/ 目錄的前置產物（rulebook、inventory、
  domain skill 選定、目標專案骨架）不齊全時使用。
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
   `migration/domain-skill.txt`（選定的 domain skill 名稱）、
   `migration/ground-truth-strategy.md` 都存在。
3. 如果選定的 domain skill 的「模板專案」節列出不止一種形狀選項（例如目
   標 Python 同時有 FastAPI 服務跟 ETL 批次兩種模板 skill），
   `migration/target-shape.txt` 必須存在且指到其中一個——這決定要載入哪
   份模板知識餵給三個 subagent。只有一種形狀（沒有分歧）的 domain skill
   不需要這個檔案。缺了就停下來，告訴人類要先跑 migration-clarify 決
   定，不要自己猜一個形狀。
4. domain skill 描述的模板專案骨架已經在目標路徑上（你不負責生成骨架）。
5. domain skill 如果宣告了目標語言側需要的套件（見模板專案小節），用唯
   讀方式確認已經裝好（例如 `test -d node_modules`、`pip show
   <pkg>`）——**只查詢，不安裝**。沒裝好就停下來告訴人類要先裝什麼，不
   要自己執行安裝指令（這條跟第 6 項是同一條紅線，只是查的東西不同）。
6. `.claude/settings.json` 裡已經有擋 `git commit` / `git push` 跟套件安
   裝指令（`brew install`/`pip install`/`npm install` 等）的 deny 規則。
   **沒有就停下來，告訴人類要加什麼規則（可以指給人類看
   `templates/settings.json` + `templates/settings.README.md`），不要自
   己去編輯 settings.json**——這條紅線不可以因為省事而繞過。就算 Claude
   Code 平台自己的自我修改防護剛好擋下了你的編輯嘗試，也不代表可以換個
   方式繞（例如透過腳本間接寫檔）——正確的下一步永遠是停下來，讓人類自
   己編輯，或人類自己執行被擋掉的那個指令。

任何一項不齊全，回報缺什麼、STOP，不要嘗試自己生成或跳過。

## Red Flags

下面這些念頭出現時代表你正在把自己說服繞過某條紅線——停下來，照規則做，
不要照這個念頭做：

| 念頭 | 事實 |
|---|---|
| 「這只是測試/準備工作，不算真的繞過」 | 沒有「這次是測試所以不算」這種例外——這條規則本身就發生過一次真實案例：有人為了讓測試跑得過去，自己動手建了 `.claude/settings.json`。任何情境下都不要自己裝套件、不要自己編輯 `settings.json`。 |
| 「反正被擋下的操作，我換個方式（腳本、間接寫檔）繞過去就好」 | 被 deny 擋下就是設計在運作，不是要你想辦法達成同樣效果——連平台自己的自我修改防護擋下編輯嘗試都不是繞過的理由，正確反應永遠是停下來讓人類決定，不是找別條路徑。 |
| 「反正遲早要裝，先裝了省事」 | 決定裝什麼、什麼時候裝是人類的權限，不是效率問題——省下來的是你的麻煩，不是你的決定範圍。 |
| 「前置產物大概率沒問題，先跑跑看」 | 開跑前檢查清單缺哪一項就照樣停，不要用「大概率對」取代「confirmed」。 |
| 「這個 unit 看起來已經因為之前的規則修訂解決了，重試看看」 | 沒有人類明確把狀態改回 `pending`，這個 unit 永遠算失敗，不會自己重試。 |
| 「domain skill 沒寫進入點，隨便挑一個檔案當進入點跑跑看」 | 沒描述進入點就跳過整合檢查裡「跑進入點」那一步，不要自己發明一個。 |
| 「規則缺口才出現一兩次，先套用一個看起來合理的規則接著做」 | 累積到 3 次以上才停是門檻，不是「先套用比較有效率」的空間——同一 category 沒到 3 次可以繼續跑，但不代表你可以自己臨時決定一條規則去補 domain skill/rulebook 沒覆蓋到的空白。 |
| 「reviewer 的審查結論看起來太嚴格/不合理，我照自己的判斷來」 | 你自己不對翻譯對不對下判斷——reviewer 的裁決就是裁決，全盤採信，不做二次判斷。 |

## Unit 狀態

每個 unit 的狀態記在 `migration/state/<unit_id>.json`：

```json
{
  "status": "pending | pass | fail-conversion | fail-test | rule-gap | excluded",
  "attempts": { "test_writer": 0, "converter": 0, "reviewer": 0 },
  "last_note": ""
}
```

**只處理 `status: pending` 的 unit（狀態檔不存在也視為 `pending`）。**
`pass`、`fail-conversion`、`fail-test`、`rule-gap`、`excluded` 都是**終
止狀態**，跳過、不重跑，只計入最終 burndown——這是刻意的：不這樣做的
話，每次重新呼叫你，永久失敗的 unit 會被重新跑一輪（再花一次三個 agent
的成本），即使人類什麼都還沒修。

`excluded` 是唯一一個**不是由你產生**的終止狀態——它是 migration-clarify
在補 manifest 那步就直接寫好的（這個 unit 是私有套件本身的實作、已經被
目標端 library 取代，不需要也不會被轉換，只有呼叫它的其他 unit 需要轉
換）。你不需要判斷哪些 unit 該是 `excluded`，也不會自己把任何 unit 標成
`excluded`——看到就跳過，當作跟其他終止狀態一樣處理即可。

**人類要重試一個終止狀態的 unit**，做法是明確把它的狀態檔改回
`status: "pending"`、`attempts` 歸零（代表用修好之後的規則重新給一次完
整的重試預算），或者乾脆刪掉那個 unit 的狀態檔（等同於 `pending`）。**你
不會自己判斷「這個看起來修好了，我重試看看」**——沒有人類明確把狀態改回
`pending`，這個 unit 就一直算失敗，寫在 burndown 裡等人類處理。這條特別
適用於「規則缺口累積 3 次暫停」之後：人類修完 `RULEBOOK.md`，要記得把
`rulebook-amendments.md` 裡那個項目標成已解決、並把所有因此暫停的 unit
狀態改回 `pending`，你才會在下次呼叫時重新處理它們——你不會自己去對照
「這個修訂解決了哪些 unit」，這是人類要做的事。

## 每個 unit 的 pipeline

依 manifest 順序（不並行跨 unit，除非呼叫者明確要求平行跑），對每個
`status: pending` 的 unit：

1. **呼叫 `migration-test-writer`**，給它 `unit_id`、`source_path`、
   inventory 裡相關列、domain skill 的測試框架慣例。拿到測試檔案路徑 +
   行為觀察筆記。
2. **呼叫 `migration-converter`**，給它 `source_path`、`target_path`、
   rulebook、inventory 相關列、domain skill 的轉換規則、剛才的測試檔案路
   徑（只給它讀，提醒它不能改測試）。拿到翻譯筆記。
3. **呼叫 `migration-test-reviewer`**，給它 `source_path`、`target_path`、
   測試檔案路徑 + 行為觀察筆記、rulebook、domain skill 的 build/test 方法。
   拿到結構化審查報告。

**每次呼叫上面任何一個 agent，不管結果是通過還是要重跑，都要把它回傳的
usage 統計附加一行到 `migration/cost-log.tsv`**（欄位：`timestamp,
unit_id, agent, attempt, tokens, tool_uses, duration_ms, outcome`，例如：
`2026-09-12T18:20:00Z	user_sync	migration-converter	1	48213	9	62000	pass`
——tab 分隔，八個欄位都要有值，`outcome` 用跟 unit 狀態一致的字
（`pass`/`fail-conversion`/`fail-test`/`rule-gap`），不要自己發明別的用
詞）。這不是只在成功時才記——重跑的呼叫一樣花資源，budget 要算進去，不
然「這次 pilot 實際花了多少」會低估。這份紀錄是給人類做容量規劃用的
（air-gapped、固定內部算力的環境沒有「加錢買更多算力」這個選項，pilot
要不要放大到完整批次，靠的是這份數字，不是感覺）。

4. 依審查結論分派：
   - **通過** → 狀態寫 `pass`，繼續下一個 unit。
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

## 全部 unit 通過後的整合檢查

每次跑完這次拿到的 manifest（不管是 pilot 還是完整批次）之後，檢查
`migration/manifest.tsv`（**完整清單**，不是你這次跑的那份，可能只是
pilot 子集）裡是不是每一列都已經是 `pass` 或 `excluded`——`excluded` 的
unit 沒有目標檔案，不需要也不會變成 `pass`，不能因為它們卡在非 `pass`
狀態就永遠不觸發整合檢查。還沒全部 `pass`/`excluded` 就跳過這節,直接
進「結束條件」。

全部 `pass`/`excluded` 才做，而且只做一次（用
`migration/state/_integration.json` 存不存在判斷有沒有做過；有 unit 的
狀態事後被改回 `pending` 或失敗狀態就要重做這一節）：

呼叫一次 `migration-test-reviewer`，但這次審查範圍從「一個 unit」換成
「整個 target/ 專案」：

1. 跑 domain skill 的 build 方法，對 `target/` 底下**全部**檔案一次跑
   過，不是逐一 unit 分開跑。
2. 跑 `target/` 底下**全部**測試一次（整個測試目錄一起跑），不是逐一
   unit 的測試檔案分開跑——這裡要抓的是「單獨看沒問題、合在一起才會爆」
   的問題（例如兩個 unit 各自的命名衝突、循環 import 在整合時才炸開）。
3. domain skill 的「模板專案」小節有描述進入點的執行方式就執行一次，
   確認整個組起來的程式真的能跑，不是每個檔案自己過測試就好。沒描述
   （或明講沒有進入點）就跳過這一項，不要自己發明一個進入點。

這次呼叫的 usage 統計一樣附加一行到 `migration/cost-log.tsv`
（`unit_id` 欄位寫 `_integration`）。

寫入 `migration/state/_integration.json`：`{"status": "pass"|"fail",
"note": "..."}`。**失敗不自動重試**——問題可能橫跨多個 unit，不像單一
unit 失敗那樣能明確退回哪個 agent，在最終報告裡列出具體症狀，交給人類
判斷要退回哪個 unit 重做。

這一節做的事，份量對應原始 code-migration-kit 的 Step 4（compile）+
Step 5（run it），但用一次性檢查取代那邊整套錯誤佇列+獨立 fixer 的機
械——這個規模的批次用不到那麼重的機制。

## 結束條件

manifest 跑完（或因規則缺口暫停）就停，回報一份 burndown：總數 / pass /
fail-conversion / fail-test / rule-gap / excluded，加上整合檢查的結果
（如果有跑的話），以及待人類決定的 rulebook 修訂項目列表。`excluded` 單
獨列一項，不要跟失敗狀態混在一起算，也不要漏掉不提——它不是失敗，是
「這個 unit 本來就不用轉換」，人類要看得到這批 unit 被明確交代過，不是
不見了。連同這次跑下來
`migration/cost-log.tsv` 的總計（總 token 數、總耗時、依 agent 角色分開
的小計）一起附在報告裡——這是人類決定「pilot 這樣的花費，放大到完整批
次大概要多少」的依據。終止狀態的 unit 明確提醒一句「要重試請把狀態改回
pending 再重新呼叫我」，不要假設人類記得這件事。**不要自己決定要不要放
大 pilot 到完整批次、要不要進下一個階段**——那是呼叫者看完這份報告後才
做的事。
