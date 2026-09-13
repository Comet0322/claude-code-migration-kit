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

以下七節照「來源 → 轉換規則 → 目標」的順序排列，跟著這個順序讀/填，
自然會先搞清楚舊程式碼長什麼樣、再看兩邊怎麼對應、最後才是目標長什麼樣，
不用在幾節之間來回跳。最後一節「共用知識抽成獨立 skill」是給填寫者看的
authoring 附註，不是內容本身，所以放在最後。

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
`manifest.tsv`，把對應到的 unit 標記成 `excluded`（私有套件本身的實作
不需要逐行翻譯，目標端已經有這裡定義的 library 取代它，只需要轉換呼叫
端）——沒點名就沒有這個自動化，這些 unit 會被當一般應用程式碼硬翻譯一
遍，白白花掉轉換/測試的成本。

如果這個私有套件本身在被遷移的 repo 裡**看不到原始碼**（例如只是一個外
部提供的編譯好的 COM DLL、透過 `Object=` reference 帶進來），就不用點
名任何檔案——呼叫這個套件的程式碼本來就會被 `migration-analyze` 掃進
「呼叫端」那個 unit 裡，沒有獨立的「套件本身」unit 需要排除。]

## UI／範疇慣例（選填）

[如果這批應用通常有 UI 層（`.frm`/`.dfm`、或 `uses`/`import` 子句裡出現
UI 框架 unit），寫下這個部門過去對「UI 要不要跟著遷移」的慣例跟理由（例
如「過去遷移這批應用時，UI 一律不遷、只留核心邏輯，因為新系統統一走另
一套前端」）。

這節寫的是**慣例，不是幫你預先做決定**——UI 保留/捨棄終究是範疇
（scope）決定，`migration-clarify` 偵測到 UI 層 unit 時還是會用
`AskUserQuestion` 問人類這次要不要保留，不會因為這節有寫就跳過確認；差
別只在於：有寫，這裡的慣例跟理由會被當成推薦選項附進那個問題，讓人類確
認的是「要不要比照過去慣例」而不是從零開始盲猜；沒寫，跟原本一樣單純
問，不列推薦值。

沒有 UI 層、或不確定過去慣例是什麼，就留白——不要為了填而編一個從沒發
生過的「慣例」。]

## 來源語言執行環境（選填）

[如果知道怎麼在一般環境裡取得這個來源語言的編譯器/直譯器，寫下確切方
式（例如指令、Docker image、內部工具連結）。migration-clarify 會依此
判斷「有沒有可用環境」；不確定或這台機器不一定裝得起來，就留白或寫
「未知，需要在 migration-clarify 階段當場確認」——不要為了填而編一個。
沒有可用環境時，migration-clarify 會轉而跟人類要 mock data/snapshot，
不會讓任何 agent 自己安裝這裡沒寫的東西。]

## 語法轉換 / library 替換規則

[舊 library → 新 library 的對照表。這是 rulebook 的種子：只要是「兩個 agent
可能做出不同選擇」的翻譯決策，全部列在這裡，不要等 rulebook 草擬時才臨時
決定。]

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

## 新語言 library 文件

[目標語言那些替代 library 的用法**摘要，直接寫在這裡，不要放外部網
址連結**——agent 沒有瀏覽器可以打開連結，air-gapped 環境更是連不出
去，一個純連結對轉換 agent 來說等於沒有這份文件。內容可以簡短，重點
是自己包含到看得懂怎麼用，不是丟一個路徑要 agent 自己想辦法。]

## 測試 / build 方法

[這批應用怎麼跑測試、怎麼 build——具體指令。給 migration-test-reviewer 用，
也是轉換 skill guardrail 檢查時要確認存在的東西。]

## 共用知識抽成獨立 skill（選填，只適用目標端共用）

domain skill 裡「模板專案」「新語言 library 文件」「測試 / build 方法」
這幾節，只要內容跟其他 domain skill **完全一致**，就不要各自複製貼上，
抽成一個獨立 skill，讓對應節改寫成一句「同 skill `<skill 名稱>`」。

典型情境是**目標端共用**：不同部門、不同來源語言，但轉換到同一種目標語
言、用同一套內部 library/慣例——例如 `python-template`、`java-template`。

抽出來的獨立 skill 要寫清楚可以觸發的 `description`——這類 skill 通常在
migration 情境之外也有用（任何人要寫符合公司規範的這個語言的程式碼），
不是只服務 migration。

**「這個 domain skill 涵蓋的應用類型」「私有套件文件」「來源語言執行環
境」「語法轉換 / library 替換規則」這幾節不要抽成獨立 skill**——即使同
一份來源程式碼被規劃/已經遷移到不止一種目標語言（例如同時有
`domain-<app>-java` 跟 `domain-<app>-python` 兩個 domain skill），這幾
節內容還是各自留在對應的 domain skill 裡直接填，允許重複貼上兩份：同一
批來源事實通常份量不大，抽成獨立 skill 換來的維護成本（多一層要跟著同步
更新的間接層）大於重複貼上省下來的量；「語法轉換 / library 替換規則」本
來就天生不能共用（是「這個特定來源 → 這個特定目標」的對照表，換一個目
標語言，對照表右欄就完全不同），硬把其他幾節抽出來只會讓一個 domain
skill 的內容分散在兩個檔案，讀的人要先去查另一個 skill 才拼得出完整的來
源端知識。

命名上避開 `domain-` 開頭——這種 skill 不是「這個舊程式碼庫該套用哪個
domain skill」的候選，`migration-clarify` 掃描 `domain-*` 選 domain
skill 時不該把它列進選項。

`migration-clarify`「Load domain skill content」那步，看到「模板專案」「新
語言 library 文件」「測試 / build 方法」這幾節寫「同 skill `<名稱>`」
時，要額外用 Skill 工具載入那個 skill 取得實際內容，再一併餵給 rulebook
草擬跟轉換階段的三個 subagent——subagent 本身沒有 Skill 工具權限，所以
是 clarify/convert 讀進來後轉述給它們，不是 subagent 自己去呼叫。

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
認這次遷移（這份 manifest）要用哪一種（見 `migration-clarify` 的「決定
目標端專案形狀」節）——**決定之後記在哪個檔案、用什麼格式，是
migration-clarify 自己的實作細節，domain skill 這裡不用管，也不要寫死
具體檔名/欄位名稱**：那是 migration 那條線自己維護的儲存機制，寫死在
domain skill 裡只會造成 migration-clarify 之後想換儲存方式時，要跟著回
頭改每一個已經寫好的 domain skill。只有一種形狀就直接寫單一「同 skill
`<名稱>`」，不要為了「以防萬一」硬列多個選項。

## 單一 domain skill 內容太大時：拆成同資料夾底下的參考檔案（選填）

跟上面「共用知識抽成獨立 skill」不同——那節解決的是「這份知識還有其他
skill 也要用，值得抽出來獨立維護」；這裡講的是「這份知識就是只有這個
domain skill 自己要用，純粹是內容太多，不適合全部塞進單一
`SKILL.md`」。判斷依據不一樣，不要混為一談：前者看「有沒有其他 skill 共
用」，後者看「份量會不會讓 `SKILL.md` 太肥」。

真實部門的 domain skill，以下幾節常常比本 repo 這批模擬情境肥很多：

- **私有套件文件**——真實私有 library 常常不只一兩個 class、幾個方法，
  完整 API 列出來可能好幾頁。
- **語法轉換 / library 替換規則**——這是 rulebook 的種子，真實老舊程式
  碼庫的翻譯決策常常遠遠不只幾條，可能是幾十條。
- **新語言 library 文件**——如果這個 domain skill 沒有共用的目標端模板
  skill、自己內嵌完整文件，份量也可能很大。

太大的時候，把實際內容搬到這個 domain skill 自己資料夾底下的
`references/<描述性檔名>.md`（例如
`.claude/skills/domain-<app>/references/private-package.md`），對應的
`SKILL.md` 小節改寫成一句指到這個相對路徑、外加一句話說裡面是什麼（例如
「私有套件完整 API 見 `references/private-package.md`（含全部
class/方法簽章跟範例）」）。

這跟「同 skill `<名稱>`」的差別：那是指到**另一個 skill**，要用 Skill
工具載入；這裡指到的是**同一個 skill 自己資料夾裡的檔案**，是一個相對
路徑（不是 skill 名稱），用 Read 工具直接讀，不要誤當成另一個 skill 名
稱去呼叫 Skill 工具（也讀不到，這種路徑本來就不是註冊過的 skill）。
`migration-clarify`「Load domain skill content」那步看到小節內容是這種相對
路徑（有 `/`、副檔名通常是 `.md`，跟「同 skill `<名稱>`」那種純 skill
名稱明顯不同），就直接用 Read 工具讀進來，當作這節本來就內嵌了這些內容
一樣使用。

份量不大就不要為了「以防萬一」先拆——`SKILL.md` 本身在 skill 被觸發時是
整份載入的，拆檔案是為了不要讓不常用到的大段內容平白佔掉每次都要載入的
`SKILL.md`，不是格式上的規定；只有一兩段的私有套件文件、四五條的對照
表，留在 `SKILL.md` 裡就好。
