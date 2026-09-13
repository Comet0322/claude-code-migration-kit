# What's in settings.json, and why

`settings.json` 裝進被遷移那個 repo 的 `.claude/settings.json`（沒有這個
檔案就建一個；已經有的話把 `hooks` 合併進去，不要整份覆蓋）——**由人類
在跑 `migration-convert` 之前裝好**。裝的動作是複製，`hooks/` 資料夾也
要一起複製過去（`settings.json` 裡的 hook 指令用
`${CLAUDE_PROJECT_DIR}/.claude/hooks/syntax-check.sh` 這個路徑，指的是複
製過去之後在目標 repo 裡的位置，不是這裡）：

```
cp .claude/skills/migration/templates/settings.json <target repo>/.claude/settings.json
cp -r .claude/skills/migration/templates/hooks <target repo>/.claude/hooks
```

（或手動合併 `hooks` 內容，`hooks/` 資料夾一樣要複製過去。）

## Hook：`migration-translator`/`migration-test-writer` 結束前的語法檢查

`hooks.SubagentStop` 那段設定，`migration-translator`（負責寫轉換後程式
碼）跟 `migration-test-writer`（負責寫新語言的測試檔——同樣是要跑在
Python/Java 上的真實程式碼，一樣可能語法錯，不是只有 converter 端會出這
種問題）這兩個 subagent 每次要結束、把結果交回去之前，都會先跑一次
`.claude/hooks/syntax-check.sh`：找到 `target/` 底下的 `pom.xml`（跑
`mvn -q compile`）或 `requirements.txt`（跑 `ruff check .`），非 0 結果
就用 exit code 2 擋下這次結束，把錯誤內容丟回去讓它自己修，不是每次
Write/Edit 就觸發，而是「準備回傳結果前」才觸發一次，也不是每個檔案分開
檢查，是對整個 target 專案跑一次（hook 本身拿不到「這次改了哪些檔案」的
清單，反正 `mvn compile`/`ruff check` 本來就是掃全專案，沒必要另外去
猜)。`migration-test-reviewer` 沒有寫入權限（read-only + execute
only），不需要掛這個 hook。

這是加分檢查，不是硬性關卡：`mvn`/`ruff` 這台機器沒裝，script 會直接放
行（exit 0），不會因為缺工具就卡住 subagent——跟這個 kit 其他地方「不裝
好的東西不能成為擋人的理由」是同一條紀律。真正的正確性把關還是在
`migration-test-reviewer`（跑實際測試），這個 hook 只是把最便宜、最明顯
的語法錯誤提前攔在更早、更便宜的一關。

## 為什麼這裡沒有 git commit/push、套件安裝的 `permissions.deny`

早期版本這裡放過一份 `deny` 清單（擋 `git commit`/`git push`/
`pip install` 等指令），後來拿掉了，原因不是這些規則不重要，是**這個技
術手段的副作用比想像中大**：

- `permissions.deny` 是**整個 repo 層級**生效，沒辦法只在「migration 自
  己的自動化迴圈裡」才生效。裝上之後，人類自己在同一個 Claude Code
  session 裡開口說「幫我 commit 這個」——即使跟 migration workflow 完全
  無關，一樣會被擋，而且會一直擋到人類自己想起來去 `.claude/settings.json`
  手動移除為止。對不了解這條規則背景的人來說，這種「莫名其妙被擋」的體
  驗容易被誤判成 kit 壞掉，變成不必要的支援負擔。
- 這條規則從設計上就從來不是安全邊界（寫得夠狠的 wrapper script 一樣繞
  得過 pattern matching），只是防「agent 自己不小心在迴圈裡順手做了不該
  做的事」——既然只是防意外，不是防蓄意繞過，那麼技術上硬擋所有人、包括
  人類自己的直接請求，換來的代價（誤傷、需要事後手動清理）就不太划算。

**現在完全靠 prompt 層級的紀律**：`migration-convert`、三個轉換 subagent
的說明文件裡都明確寫著「不裝套件」「不 commit/push」，`migration-convert`
的 Red Flags 表也把這兩條列成不能妥協的紅線——跟這個 kit 另一個本來就沒
被 `settings.json` 管到的規則（rulebook 在迴圈內唯讀）用的是同一種機
制：靠說明文件的明確指示 + 事後審查（batch 裡如果看到不該有的 commit/
安裝紀錄，就是要回報給人類的違規），不是靠技術上讓它做不到。這比較弱，
但換到的是這個 repo 平常的使用不會被無差別擋住。

`migration-clarify`（來源語言執行環境、目標語言側套件章節）跟
`migration-convert` 的 pre-flight check 仍然會**查詢，不安裝**——沒裝好
就停下來讓人類決定，這件事本身沒有變，變的只是「有沒有一份 permission
規則技術上擋住安裝指令」這一層。

## `mvn test`/`pytest` 這類 build/test 指令沒有被擋

`migration-test-reviewer` 本來就需要在每個 unit 轉換完後真的跑一次測試/
build 來判斷 pass/fail，不是靠事後一次性的 survey build 抓錯——擋掉這些
指令會讓整條 pipeline 失去唯一的正確性訊號來源，所以從一開始就沒被列進
任何 deny 清單過。
