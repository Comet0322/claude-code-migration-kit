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

## 共用知識抽成獨立 skill（選填，雙向都適用）

domain skill 裡任何一節，只要內容跟其他已存在的 domain skill **完全一
致**，就不要各自複製貼上，抽成一個獨立 skill，讓對應節改寫成一句「同
skill `<skill 名稱>`」。這件事有兩個方向，不要假設只有其中一種：

- **目標端共用**：不同部門、不同來源語言，但轉換到同一種目標語言、用同
  一套內部 library/慣例——例如 `python-template`、`java-template`，「模
  板專案」「新語言 library 文件」「測試 / build 方法」三節指向它。
- **來源端共用**：同一份來源程式碼（同部門、同來源語言）被規劃/已經遷移
  到不止一種目標語言——例如部門 200 的 Delphi 舊應用同時有
  `domain-200-delphi-java` 跟 `domain-200-delphi-python` 兩個 domain
  skill，「這個 domain skill 涵蓋的應用類型」「私有套件文件」「來源語言
  執行環境」這幾節其實是同一份事實，抽成一個獨立 skill（例如
  `legacy-200-delphi`），兩個 domain skill 都指向它。

抽出來的獨立 skill 都寫清楚可以觸發的 `description`——目標端共用 skill
通常在 migration 情境之外也有用（任何人要寫符合公司規範的這個語言的程式
碼）；來源端共用 skill 則是「要理解/維護這批舊程式碼」時有用（不限於這
次遷移）。

**只有「語法轉換 / library 替換規則」這節天生不能共用**——它是「這個特
定來源 → 這個特定目標」的對照表，換一個目標語言，對照表右欄就完全不
同，一定要留在各自的 domain skill 裡自己填。

命名上避開 `domain-` 開頭——這種 skill 不是「這個舊程式碼庫該套用哪個
domain skill」的候選，`migration-clarify` 掃描 `domain-*` 選 domain
skill 時不該把它列進選項。

`migration-clarify`「載入 domain skill 內容」那步，看到任何一節寫「同
skill `<名稱>`」時（不管是目標端還是來源端共用），都要額外用 Skill 工具
載入那個 skill 取得實際內容，再一併餵給 rulebook 草擬跟轉換階段的三個
subagent——subagent 本身沒有 Skill 工具權限，所以是 clarify/convert 讀
進來後轉述給它們，不是 subagent 自己去呼叫。

### 目標端不是單一慣例時：「模板專案」節列多個選項

同一種目標語言在公司內部可能不是只有一套專案慣例——例如目標 Python 同時
有「FastAPI 服務」跟「背景 ETL 批次」兩種形狀。這種情況下**不要**拆成多
個獨立 skill，而是在同一個目標端共用 skill 裡用不同小節分別放（例如
`python-template` 底下「corplib 使用方式」放真正跨形狀共用的 DB/logging
用法，「專案形狀：FastAPI 常駐服務」跟「專案形狀：背景 ETL 批次」各自一
節放骨架/進入點/測試build方法）——同一套目標端知識放在同一個 skill 裡分
節，不要分散成好幾個 skill，讀的人才不用同時開好幾個 skill 才拼得出完整
的目標端知識。

domain skill 的「模板專案」節這時改寫成列出選項而不是單一「同 skill
`<名稱>`」，指到同一個 skill 底下不同的節，例如：

```
這批應用的目標 Python 專案可能是 FastAPI 服務或背景 ETL 批次，兩者擇一：
- 同 skill `python-template` 的「專案形狀：FastAPI 常駐服務」節
- 同 skill `python-template` 的「專案形狀：背景 ETL 批次」節
```

`migration-clarify` 看到列出多個選項時，會用 `AskUserQuestion` 跟人類確
認這次遷移（這份 manifest）要用哪一種、寫進 `migration/target-shape.txt`
（見 `migration-clarify` 的「決定目標端專案形狀」節）。只有一種形狀就直接寫單一「同 skill
`<名稱>`」，不要為了「以防萬一」硬列多個選項。

## 這個 domain skill 涵蓋的應用類型

[一句話描述哪一批老舊程式適用這份知識。盡量寫出可以拿來自動比對的具體指
紋——常見的私有套件 import 路徑、特定設定檔名稱、特定框架版本——
migration-clarify 會拿這幾行去跟實際程式碼比對，猜出「這個實例大概是哪個
domain skill」當推薦選項。]

## 私有套件文件

[這批應用共用的私有/內部 library 說明。**內嵌實際內容或指向倉庫內部的
檔案路徑，不要放外部網址**——agent 沒有瀏覽器，air-gapped 環境連得到的
話還能救，連不到的話一個外部連結就是廢話。

如果這個私有套件本身的實作是以**原始碼**形式跟著每個 app 一起放在被遷移
的 repo 裡（例如 Delphi 私有 package 常見的做法：`.pas` unit 檔案跟著應
用程式一起放，不是只有編譯好的 `.dll`/`.bpl`），**明確點名這些實作檔案
的檔名**（例如「這個私有套件的實作是 `Dept200Data.pas`／
`Dept200Log.pas`」）。migration-clarify 會拿這個去比對
`modules.tsv`，把對應到的 unit 標記成 `excluded`（私有套件本身的實作
不需要逐行翻譯，目標端已經有這裡定義的 library 取代它，只需要轉換呼叫
端）——沒點名就沒有這個自動化，這些 unit 會被當一般應用程式碼硬翻譯一
遍，白白花掉轉換/測試的成本。

如果這個私有套件本身在被遷移的 repo 裡**看不到原始碼**（例如只是一個外
部提供的編譯好的 COM DLL、透過 `Object=` reference 帶進來），就不用點
名任何檔案——呼叫這個套件的程式碼本來就會被 `migration-analyze` 掃進
「呼叫端」那個 unit 裡，沒有獨立的「套件本身」unit 需要排除。]

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

[目標語言那些替代 library 的用法**摘要，直接寫在這裡，不要放外部網
址連結**——agent 沒有瀏覽器可以打開連結，air-gapped 環境更是連不出
去，一個純連結對轉換 agent 來說等於沒有這份文件。內容可以簡短，重點
是自己包含到看得懂怎麼用，不是丟一個路徑要 agent 自己想辦法。]

## 測試 / build 方法

[這批應用怎麼跑測試、怎麼 build——具體指令。給 migration-test-reviewer 用，
也是轉換 skill guardrail 檢查時要確認存在的東西。]
