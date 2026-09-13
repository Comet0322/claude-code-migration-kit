---
name: domain-200-delphi-java
description: >
  [模擬情境] 涵蓋部門 200 的 Delphi 舊應用，目標語言 Java（來源跟
  domain-200-delphi-python 是同一批，來源端知識各自內嵌，不抽共用
  skill）。目標端知識共用 skill `java-template`（跟 domain-200-vb-java
  共用同一套目標 Java library）。
---

# Domain skill 模板

這份文件本身不是拿來執行的，是拿來填的。填完、改名之後，它才是一個真正可以
在 migration-clarify 選單裡出現的 domain skill。

## 這個 domain skill 涵蓋的應用類型

部門 200 的 Delphi 舊應用。特徵：`uses` 子句裡有 `Dept200Data`、
`Dept200Log`——這兩個私有套件的原始碼跟著應用程式一起放在 repo 裡（不是
外部編譯好的套件），檔名就是 `Dept200Data.pas`／`Dept200Log.pas`。跟
`domain-200-delphi-python` 是同一批來源，純看程式碼證據沒辦法判斷這個
repo 該選 java 還是 python 這個 domain skill——目標語言是人類決定的範
疇，不是能從舊程式碼本身推斷出來的線索，遇到這種情況 `migration-clarify`
第 1 節本來就該停下來問人類，不要嘗試用程式碼特徵自動分辨兩者。

## 私有套件文件

`Dept200Data.pas`（DB 連線）+ `Dept200Log.pas`（logging），原始碼跟著
應用程式放在同一個 repo：

```pascal
Conn := TDBConnection.Create(ReadIniConnString('app.ini'));
try
  Result := Conn.Query('SELECT id, name FROM users WHERE dept = :dept', ['dept', '200']);
  Conn.Execute('UPDATE users SET name = :name WHERE id = :id', ['name', 'foo', 'id', 1]);

  Conn.BeginTransaction;
  try
    ...
    Conn.Commit;
  except
    Conn.Rollback;
  end;
finally
  Conn.Free;
end;

LogMessage(llInfo, 'fetched user', ['dept=200']);
LogMessage(llError, 'db timeout', ['unit_id=user_sync']);
```

- `TDBConnection`：底層走 BDE 連 MS SQL Server（跟 `corplib` 系列連的是
  同一台）。連線字串來自 `ReadIniConnString('app.ini')`（讀 `app.ini` 的
  `[DB]` 區段 `ConnString`）。查詢/寫入參數用具名 `:param` 佔位符，但傳
  遞方式是**攤平的陣列**（`['dept', '200']`、`['name', 'foo', 'id',
  1]`——key、value 交錯排列，不是 array of pair），轉換時要注意這個攤平
  結構，不能直接照抄成 key=value 陣列的轉法。沒有自動交易，呼叫端要手動
  呼叫 `BeginTransaction`/`Commit`/`Rollback` 才有交易語意，單純的
  `Query`/`Execute` 沒有交易包裝。
- `LogMessage`：寫到 `<exe 所在目錄>\logs\<yyyymmdd>.log`，格式 `[時間]
  [等級] message k=v k2=v2`——**`KeyValues` 參數本身就是已經拆好的
  `k=v` 字串陣列**（例如 `['unit_id=user_sync', 'rows=12']`），不需要
  再對單一字串做二次拆分（跟部門 200/300 的 VB6 版本不同，那邊是塞在同
  一個字串裡用分號/逗號分隔，這裡 Delphi 版本本來就是陣列）。

私有套件本身的實作就是 `Dept200Data.pas`／`Dept200Log.pas` 這兩個檔
案——`migration-analyze` 掃出對應 unit 後，`migration-clarify` 會標記為
`excluded`，不逐行翻譯。

## 來源語言執行環境（選填）

未知，需要在 migration-clarify 階段當場確認——舊版 Delphi/Borland/
Embarcadero IDE 這台機器大概率裝不起來（授權/版本都難取得），優先假設要
走 snapshot 或 inference 層級。

## 語法轉換 / library 替換規則

目標見 skill `java-template`：

| Delphi（見上方「私有套件文件」節） | Java（java-template） | 備註 |
|---|---|---|
| `TDBConnection.Create(ReadIniConnString('app.ini'))` | `Database.fromEnv()` | DSN 來源從 `app.ini` 改成環境變數 `CORPLIB_DB_DSN`，由部署設定填入，轉換後不再讀 ini。 |
| `Conn.Query(sql, [...])`（無交易） | `try (var conn = db.session()) { conn.fetchAll(sql, Map.of(...)); }` | 具名參數風格一致，陣列 `['k', v, ...]` 換成 `Map.of("k", v, ...)`。 |
| `Conn.Execute` 搭配手動 `BeginTransaction`/`Commit`/`Rollback` | `try (var tx = db.transaction()) { tx.execute(...); tx.commit(); }` | **行為落差最大的一條**：只有原始碼裡看得到手動交易的路徑才對應 `transaction()`；沒有手動交易包起來的單純 `Execute` 對應 `db.session()` 就好，不要一律升級成交易。 |
| `LogMessage(llInfo, msg, ['k=v', ...])` | `logger.info(msg, Map.of("k", "v", ...))` | 舊碼是 `key=value` 字串陣列，要拆成 Map 的 key/value 兩半。 |
| `LogMessage(llError, msg, [...])` | `logger.error(msg, Map.of(...), ex)` | 舊碼的 `try/except` 區塊裡才抓得到例外物件；沒有 `except` 包起來的 `LogMessage(llError, ...)` 呼叫，`ex` 參數傳 `null`，不要編一個假的例外。 |

## 模板專案

同 skill `java-template`。

## 新語言 library 文件

同 skill `java-template`。

## 測試 / build 方法

同 skill `java-template`。
