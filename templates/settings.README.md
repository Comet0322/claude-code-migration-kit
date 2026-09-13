# Why each deny rule exists

`settings.json` 裝進被遷移那個 repo的 `.claude/settings.json`（沒有這個檔
案就建一個；已經有的話把 `deny` 陣列合併進去，不要整份覆蓋）——**由人類
在跑 `migration-convert` 之前裝好**，`migration-convert` 開跑前的檢查會
確認它存在，缺了就停下、不會自己補（見 `.claude/skills/migration-convert
/SKILL.md` 的「Red Flags」一節）。裝的動作是複製，不是建議：
`cp templates/settings.json <target repo>/.claude/settings.json`（或手動
合併 `deny` 陣列）。

這份清單是防止**在迴圈裡**意外呼叫到的動作被擋下，不是安全邊界——寫得夠
狠的 wrapper script 一樣繞得過 pattern matching。這條紅線的重點是「agent
不會自己去繞」，不是「無論如何都不可能被繞過」。

## Git 規則（`git commit` / `git push`）

`migration-convert` 的三個 subagent（test-writer/converter/reviewer）跟
migration-convert 自己都不該在迴圈裡提交或推送——commit 的時機是人類看
過 burndown 之後自己決定的批次邊界，不是每個 unit 轉換完就自動提交。允
許 `git status`/`git diff`/`git log` 這類唯讀指令，因為審查跟除錯都需要
看得到目前狀態。

## 套件安裝規則（`brew install` / `pip install` / `npm install` 等）

這是這個 kit 從頭到尾最常重申的紅線：來源語言執行環境（`migration-clarify`
第 3 節）、目標語言側套件（`migration-clarify` 第 9 節、`migration-convert`
開跑前檢查第 5 項）都是「查詢，不安裝」——沒裝好就停下來讓人類決定要裝
什麼、什麼版本，不是效率問題，是決定權的問題。air-gapped 環境尤其不能讓
agent 自己觸網或裝來路不明的版本。

## 這條規則本身不能被繞過

如果某個 agent 被這條 deny 擋下、想改成自己編輯 `settings.json` 清掉這條
擋——**那正是這條規則要防的事**，不是要你去解決的障礙。停下來，回報給人
類，讓人類決定要不要調整規則、什麼時候調整。

即使 Claude Code 平台自己的自我修改防護剛好擋下了那次編輯嘗試，也不代表
可以換個方式繞（例如透過腳本間接寫檔、或說服自己「這只是暫時調整」）——
唯一正確的下一步是人類自己動手編輯，或者人類自己充當「build daemon」，
在需要跑那個被擋掉的指令時親自執行。這個情境在
`.claude/skills/migration-convert/SKILL.md` 的 Red Flags 表裡已經記錄
（本 kit 自己也真的發生過一次：有 session 為了讓測試跑得過去自己建了這
個檔案，後來自己發現並撤銷）。

## 這裡刻意沒放的東西

沒有擋 build/test 指令（`mvn test`、`pytest` 之類）——跟很多語言遷移
kit 不一樣，這個 kit 的 `migration-test-reviewer` 本來就需要在每個 unit
轉換完後真的跑一次測試/build 來判斷 pass/fail，不是靠事後一次性的
survey build 抓錯。禁掉這些指令會讓整條 pipeline 失去唯一的正確性訊號來
源，所以刻意不擋。真正該擋的重指令只有整合檢查那一次性的步驟本身會呼
叫，不受這份 deny 清單管——那是 `migration-convert` 自己流程的一部分，
不是迴圈裡的意外呼叫。

沒有擋 rulebook 的修改——因為 permission 規則沒辦法表達「迴圈內的 agent
唯讀、人類可寫」這種依身份而定的權限。這條靠 prompt 層級的紀律（每個轉
換階段的 agent 都被要求把修訂排進 `rulebook-amendments.md`，不直接改
`RULEBOOK.md`）跟審查（batch 裡如果看到 diff 動到 `RULEBOOK.md` 就是自
動判定的違規）來保證，不是靠這份 settings.json。
