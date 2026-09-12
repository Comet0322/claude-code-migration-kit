---
name: domain-template
description: >
  [模板，不要直接用] 領域知識包裝的骨架。複製這個資料夾、改名成
  domain-<你的app類型>（例如 domain-legacy-billing），把下面每一節換成這批
  老舊程式實際的內容。migration-clarify skill 會掃描 .claude/skills/domain-*
  列出所有已包裝好的領域知識供你選。這個 template 本身不該被選到——內容都是
  佔位符。
---

# Domain skill 模板

這份文件本身不是拿來執行的，是拿來填的。填完、改名之後，它才是一個真正可以
在 migration-clarify 選單裡出現的 domain skill。

## 這個 domain skill 涵蓋的應用類型

[一句話描述哪一批老舊程式適用這份知識。盡量寫出可以拿來自動比對的具體指
紋——常見的私有套件 import 路徑、特定設定檔名稱、特定框架版本——
migration-clarify 會拿這幾行去跟實際程式碼比對，猜出「這個實例大概是哪個
domain skill」當推薦選項。]

## 私有套件文件

[這批應用共用的私有/內部 library 說明，或指向文件的路徑/連結。]

## 來源語言執行環境（選填）

[如果知道怎麼在一般環境裡取得這個來源語言的編譯器/直譯器，寫下確切方
式（例如指令、Docker image、內部工具連結）。migration-clarify 會依此
判斷「有沒有可用環境」；不確定或這台機器不一定裝得起來，就留白或寫
「未知，需要在 migration-clarify 階段當場確認」——不要為了填而編一個。
沒有可用環境時，migration-clarify 會轉而跟人類要 mock data/snapshot，
不會讓任何 agent 自己安裝這裡沒寫的東西。]

## 模板專案

[轉換後預期的目標專案骨架——目錄結構、進入點、build 設定檔案該長怎樣。
migration-clarify 會照這個幫每個 unit 決定 target_path，並把骨架建出來。

進入點不只要寫「檔案在哪」，也要寫**怎麼執行它、怎樣算成功**——全部 unit
轉換完成後，migration-convert 會做一次整合檢查：組完整個 target 專案跑一
次全部測試，並執行這裡描述的進入點一次，確認組起來的整個程式真的能跑，
不是每個檔案各自過測試就好。寫法例如「進入點
`target/src/main.py`，執行 `python3 target/src/main.py --help`，能印出用
法說明就算成功」。這批應用沒有一個天然的單一進入點（例如是一堆各自獨立
的 library 函式）就明講「沒有進入點」，migration-convert 那步會跳過「跑
進入點」，只做「全部測試一起跑」。

如果目標語言需要外部套件（不是純標準庫）：列出套件清單、**人類要先手動
安裝好**的指令（例如 `npm install`、`pip install -r requirements.txt`），
跟怎麼**唯讀確認**已經裝好的方式（例如 `test -d node_modules`、
`pip show <pkg>`）。migration-clarify scaffold 那步、跟 migration-convert
開跑前都會用這個唯讀確認方式檢查——沒裝好就停下來告訴人類，任何 agent 都
不會自己執行安裝指令（這條跟「來源語言執行環境」那節是對稱的紀律，只是
換成目標語言側）。純標準庫、不需要額外套件就明講「無」。]

## 語法轉換 / library 替換規則

[舊 library → 新 library 的對照表。這是 rulebook 的種子：只要是「兩個 agent
可能做出不同選擇」的翻譯決策，全部列在這裡，不要等 rulebook 草擬時才臨時
決定。]

## 新語言 library 文件

[目標語言那些替代 library 的用法文件連結/摘要，給轉換 agent 查。]

## 測試 / build 方法

[這批應用怎麼跑測試、怎麼 build——具體指令。給 migration-test-reviewer 用，
也是轉換 skill guardrail 檢查時要確認存在的東西。]

## Fingerprint（選填，給落差比對用）

[列出這個 domain skill 假設成立的具體事實，例如「應該找得到 import
'legacypkg/foo'」「build 設定檔應該是 xxx.cfg」。migration-clarify 會拿實際
程式碼逐條比對，落差記錄到 migration/domain-mismatch.md，不會默默忽略。沒
填這節就跳過比對，不強制。]
