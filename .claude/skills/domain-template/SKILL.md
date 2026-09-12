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
migration-clarify 會照這個幫每個 unit 決定 target_path，並把骨架建出來。]

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
