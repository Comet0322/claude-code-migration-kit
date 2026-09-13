---
name: domain-200-vb-java
description: >
  [模擬情境] 涵蓋部門 200 的 VB6 舊應用（私有套件是單一封裝好的 COM
  library `Dept200Common.dll`，DB 連線跟 logging 都從這一個 library
  來，不是兩個各自獨立的套件），目標語言 Java。目標端知識（模板專案、
  library 文件、測試/build 方法）共用 skill `java-template`（跟
  domain-200-delphi-java 共用同一套目標 Java library）。
---

# Domain skill 模板

這份文件本身不是拿來執行的，是拿來填的。填完、改名之後，它才是一個真正可以
在 migration-clarify 選單裡出現的 domain skill。

## 這個 domain skill 涵蓋的應用類型

部門 200 的 VB6 應用。特徵：`.vbp` 專案檔裡有 `Dept200Common.dll` 的 COM
reference（`Object=` 那行）——這是一個封裝好的**單一** library，`clsDBConn`
（DB）跟 `clsLogger`（logging）都從同一個 DLL 來，不是分開的兩個套件。跟
`domain-300-vb-python` 涵蓋的部門 300 VB6 應用是不同的私有套件生態，不能
共用彼此的私有套件文件（同樣是 VB6，但兩個部門各自維護一套私有
library）。

## 私有套件文件

`Dept200Common.dll`（早期繫結 COM component，一個 DLL 裡有 `clsDBConn` 跟
`clsLogger` 兩個 class，對應到 `java-template` 的 `com.company.corplib.db`
/ `com.company.corplib.logging` 這種「一個 library、兩個子模組」的形
狀）：

```vb
Dim Conn As New clsDBConn
Dim Logger As New clsLogger

Conn.Open App.Path & "\app.ini"
Set rs = Conn.Query("SELECT id, name FROM users WHERE dept = ?", Array("200"))
Conn.Execute "UPDATE users SET name = ? WHERE id = ?", Array("foo", 1)
Conn.Close

Logger.LogInfo "fetched user", "unit_id=u123;user_id=1"
Logger.LogError "db timeout", "unit_id=u123"
```

- `clsDBConn`：底層是 ADO 連到 MS SQL Server（跟 `corplib` 系列連的是同
  一台）。參數是**位置**佔位符 `?` + `Array(...)`，不是具名參數——順序
  要跟 SQL 裡 `?` 出現順序對應，轉換時不能只照抄字串。沒有自己包交易，
  呼叫端直接用 ADODB Connection 內建的 `Conn.BeginTrans` /
  `Conn.CommitTrans` / `Conn.RollbackTrans`。
- `clsLogger`：寫到 `App.Path & "\logs\" & Format(Now, "yyyymmdd") &
  ".log"`，格式 `[時間] [等級] message key=value;key=value`——**用分號分
  隔多個 key=value**，跟部門 300 用逗號分隔不同，兩邊的語法轉換規則不能
  互相套用。

## 來源語言執行環境（選填）

未知，需要在 migration-clarify 階段當場確認——VB6 IDE/`vb6.exe /make` 大
概率這台機器裝不起來（VB6 已停產），優先假設要走 snapshot 或 inference
層級。

## 模板專案

同 skill `java-template`。

## 語法轉換 / library 替換規則

| VB6（`Dept200Common`） | Java（`java-template`） | 備註 |
|---|---|---|
| `Conn.Query(sql, Array(...))`（位置參數 `?`） | `conn.fetchAll(sql, Map.of(...))`（具名 `:param`） | SQL 裡的 `?` 要依序換成 `:paramN`，並補上對應的 key 名稱——不是單純照抄 SQL 字串。 |
| `Conn.BeginTrans` / `CommitTrans` / `RollbackTrans` | `try (var tx = db.transaction()) { ...; tx.commit(); }` | 只有原始碼裡看得到手動呼叫 `BeginTrans` 的路徑才對應 `transaction()`；沒有交易包起來的單純 `Query`/`Execute` 對應 `db.session()`。 |
| `Logger.LogInfo msg, "k=v;k2=v2"` | `logger.info(msg, Map.of("k", "v", "k2", "v2"))` | 先用 `;` 拆多組，再用 `=` 拆單組 key/value。 |
| `Logger.LogError msg, kv`（`On Error GoTo` 區塊內） | `logger.error(msg, Map.of(...), ex)` | `Err.Description` 的內容包成 `new RuntimeException(errDescription)` 當 `ex` 傳入；不在 `On Error` 區塊內的 `LogError` 呼叫，`ex` 傳 `null`，不要編一個假的例外物件。 |

## 新語言 library 文件

同 skill `java-template`。

## 測試 / build 方法

同 skill `java-template`。
