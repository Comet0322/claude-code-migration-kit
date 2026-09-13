---
name: domain-300-vb-python
description: >
  [模擬情境] 涵蓋部門 300 的 VB6 舊應用（私有套件是單一封裝好的 COM
  library `CorpUtil300.dll`，DB 連線跟 logging 都從這一個 library 來，
  logging 走 Windows Event Log），目標語言 Python。目標端 library 文件跟
  專案形狀模板（FastAPI 服務 / ETL 批次，依實例而定）都在 skill
  `python-template` 裡（跟 domain-200-delphi-python 共用同一組目標
  Python 形狀選項）。
---

# Domain skill 模板

這份文件本身不是拿來執行的，是拿來填的。填完、改名之後，它才是一個真正可以
在 migration-clarify 選單裡出現的 domain skill。

## 這個 domain skill 涵蓋的應用類型

部門 300 的 VB6 應用。特徵：`.vbp` 專案檔裡有 `CorpUtil300.dll` 的 COM
reference——這是一個封裝好的**單一** library，`clsConn`（DB）跟
`clsEventLogger`（logging）都從同一個 DLL 來。程式碼裡會出現存取
`HKLM\Software\Dept300\DB` 這把 registry key。跟 `domain-200-vb-java` 涵
蓋的部門 200 VB6 應用是不同的私有套件生態（同樣是 VB6，但兩個部門各自維
護一套私有 library），不能共用彼此的私有套件文件。

## 私有套件文件

`CorpUtil300.dll`（早期繫結 COM component，一個 DLL 裡有 `clsConn`
（ODBC）跟 `clsEventLogger` 兩個 class，對應到 `python-template` 的
`corplib.db` / `corplib.logging` 這種「一個 library、兩個子模組」的形
狀）：

```vb
Dim Conn As New clsConn
Dim Logger As New clsEventLogger

Conn.Connect  ' 內部從 registry HKLM\Software\Dept300\DB\ConnString 讀取
Set rs = Conn.Exec("SELECT id, name FROM users WHERE dept = ?", Array("300"))
Conn.Run "UPDATE users SET name = ? WHERE id = ?", Array("foo", 1)
Conn.Disconnect

Logger.Write evtInformation, "fetched user", "unit=u456,user=2"
Logger.Write evtError, "db timeout", "unit=u456"
```

- `clsConn`：底層是 **ODBC**（不是 ADO）連到 MS SQL Server（跟 `corplib`
  系列連的是同一台，但存取方式跟部門 200 的 `Dept200Common`／ADO 不
  同）。參數同樣是位置佔位符 `?` + `Array(...)`。**沒有交易 API**——
  `Conn.Run` 每次呼叫內部就地 commit，沒有 `BeginTrans` 這類方法可以呼
  叫，跟部門 200 不一樣，不要假設兩個部門的 VB6 私有庫行為對稱。
- `clsEventLogger`：寫進 **Windows Event Log**（Application log，來源
  名稱 `Dept300App`），不是本機文字檔——跟部門 200 的 `clsLogger` 寫本
  機 txt 完全不同機制。key=value 用**逗號**分隔（部門 200 是分號），兩
  邊的語法轉換規則不能互相套用。`evtInformation`/`evtError` 是這個 DLL
  的 COM type library 暴露的列舉值。

## 來源語言執行環境（選填）

未知，需要在 migration-clarify 階段當場確認——VB6 IDE 大概率這台機器裝不
起來，優先假設要走 snapshot 或 inference 層級。

## 語法轉換 / library 替換規則

| VB6（`CorpUtil300`） | Python（`python-template`） | 備註 |
|---|---|---|
| `Conn.Connect`（讀 registry） | `Database.from_env()` | DSN 來源從 registry 改成環境變數 `CORPLIB_DB_DSN`。 |
| `Conn.Exec(sql, Array(...))` | `with db.session() as conn: conn.fetch_all(sql, {...})` | 位置 `?` 依序換成具名 `:param`，順序要對應轉換。 |
| `Conn.Run(sql, ...)`（單次呼叫內自動 commit，無交易 API） | `with db.session() as conn: conn.execute(...)`（**不要用** `transaction()`） | 這個私有庫本來就沒有交易語意，不要因為部門 200 的案例有 `transaction()` 就對稱套用——沒有交易概念的呼叫直接對應 `session()`。 |
| `Logger.Write evtInformation, msg, "k=v,k2=v2"` | `logger.info(msg, extra={"k": "v", "k2": "v2"})` | 逗號分隔的 key=value（注意跟部門 200 的分號不同，不要套錯規則）。 |
| 寫進 Windows Event Log | 寫 stdout JSON，交給外部 log 收集器 | **這是刻意的架構調整**（遷移到 air-gapped/跨平台環境後不再有 Windows Event Log 可寫），不是遺漏；rulebook 要記一條「行為改變，已由人類確認」。 |

## 模板專案

這批應用的目標 Python 專案可能是 FastAPI 服務或背景 ETL 批次，兩者擇
一，由 `migration-clarify` 跟人類確認（見「Decide target project shape」節）：
- 同 skill `python-template` 的「專案形狀：FastAPI 常駐服務」節
- 同 skill `python-template` 的「專案形狀：背景 ETL 批次」節

## 新語言 library 文件

同 skill `python-template` 的「corplib 使用方式」節。

## 測試 / build 方法

隨 `migration-clarify` 已確認的模板形狀決定，對應 `python-template` 的
「測試 / build 方法（FastAPI）」或「測試 / build 方法（ETL 批次）」節
（不再重複貼）。
