---
name: domain-200-delphi-java
description: >
  [模擬情境] 涵蓋部門 200 的 Delphi 舊應用，目標語言 Java。來源端知識（私
  有套件、執行環境）共用 skill `legacy-200-delphi`（跟
  domain-200-delphi-python 是同一批來源）。目標端知識共用 skill
  `java-template`（跟 domain-200-vb-java 共用同一套目標 Java library）。
---

# Domain skill 模板

這份文件本身不是拿來執行的，是拿來填的。填完、改名之後，它才是一個真正可以
在 migration-clarify 選單裡出現的 domain skill。

## 這個 domain skill 涵蓋的應用類型

同 skill `legacy-200-delphi`。

## 私有套件文件

同 skill `legacy-200-delphi`。

## 來源語言執行環境（選填）

同 skill `legacy-200-delphi`。

## 模板專案

同 skill `java-template`。

## 語法轉換 / library 替換規則

來源見 skill `legacy-200-delphi`、目標見 skill `java-template`：

| Delphi（legacy-200-delphi） | Java（java-template） | 備註 |
|---|---|---|
| `TDBConnection.Create(ReadIniConnString('app.ini'))` | `Database.fromEnv()` | DSN 來源從 `app.ini` 改成環境變數 `CORPLIB_DB_DSN`，由部署設定填入，轉換後不再讀 ini。 |
| `Conn.Query(sql, [...])`（無交易） | `try (var conn = db.session()) { conn.fetchAll(sql, Map.of(...)); }` | 具名參數風格一致，陣列 `['k', v, ...]` 換成 `Map.of("k", v, ...)`。 |
| `Conn.Execute` 搭配手動 `BeginTransaction`/`Commit`/`Rollback` | `try (var tx = db.transaction()) { tx.execute(...); tx.commit(); }` | **行為落差最大的一條**：只有原始碼裡看得到手動交易的路徑才對應 `transaction()`；沒有手動交易包起來的單純 `Execute` 對應 `db.session()` 就好，不要一律升級成交易。 |
| `LogMessage(llInfo, msg, ['k=v', ...])` | `logger.info(msg, Map.of("k", "v", ...))` | 舊碼是 `key=value` 字串陣列，要拆成 Map 的 key/value 兩半。 |
| `LogMessage(llError, msg, [...])` | `logger.error(msg, Map.of(...), ex)` | 舊碼的 `try/except` 區塊裡才抓得到例外物件；沒有 `except` 包起來的 `LogMessage(llError, ...)` 呼叫，`ex` 參數傳 `null`，不要編一個假的例外。 |

## 新語言 library 文件

同 skill `java-template`。

## 測試 / build 方法

同 skill `java-template`。
