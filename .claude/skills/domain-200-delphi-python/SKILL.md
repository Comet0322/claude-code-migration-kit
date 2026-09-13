---
name: domain-200-delphi-python
description: >
  [模擬情境] 涵蓋部門 200 的 Delphi 舊應用，目標語言 Python。來源端知識
  （私有套件、執行環境）共用 skill `legacy-200-delphi`（跟
  domain-200-delphi-java 是同一批來源）。目標端 library 文件跟專案形狀模
  板（FastAPI 服務 / ETL 批次，依實例而定）都在 skill `python-template`
  裡（跟 domain-300-vb-python 共用同一組目標 Python 形狀選項）。
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

這批應用的目標 Python 專案可能是 FastAPI 服務或背景 ETL 批次，兩者擇
一，由 `migration-clarify` 跟人類確認（見「決定目標端專案形狀」節），寫進
`migration/target-shape.txt`：
- 同 skill `python-template` 的「專案形狀：FastAPI 常駐服務」節
- 同 skill `python-template` 的「專案形狀：背景 ETL 批次」節

## 語法轉換 / library 替換規則

來源見 skill `legacy-200-delphi`、目標見 skill `python-template`：

| Delphi（legacy-200-delphi） | Python（python-template） | 備註 |
|---|---|---|
| `TDBConnection.Create(ReadIniConnString('app.ini'))` | `Database.from_env()` | DSN 來源從 `app.ini` 改成環境變數 `CORPLIB_DB_DSN`，由部署設定填入，轉換後不再讀 ini。 |
| `Conn.Query(sql, [...])`（無交易） | `with db.session() as conn: conn.fetch_all(sql, {...})` | 具名參數風格一致，陣列 `['k', v, ...]` 換成 dict `{"k": v, ...}`。 |
| `Conn.Execute` 搭配手動 `BeginTransaction`/`Commit`/`Rollback` | `with db.transaction() as tx: tx.execute(...)` | **行為落差最大的一條**：只有原始碼裡看得到手動交易的路徑才對應 `transaction()`；沒有手動交易包起來的單純 `Execute` 對應 `db.session()` 就好，不要一律升級成交易。 |
| `LogMessage(llInfo, msg, ['k=v', ...])` | `logger.info(msg, extra={"k": "v", ...})` | 舊碼是 `key=value` 字串陣列，要拆成 dict 的 key/value 兩半。 |
| `LogMessage(llError, msg, [...])` | `logger.error(msg, extra={...}, exc_info=True)` | 只有原始碼的 `try/except` 區塊裡呼叫的 `LogMessage(llError, ...)` 才對應 `exc_info=True`；沒有 `except` 包起來的呼叫，`exc_info` 不要加，避免記錄到不存在的例外。 |

## 新語言 library 文件

同 skill `python-template` 的「corplib 使用方式」節。

## 測試 / build 方法

隨模板形狀決定，見 `migration/target-shape.txt` 指到的形狀，對應
`python-template` 的「測試 / build 方法（FastAPI）」或「測試 / build
方法（ETL 批次）」節（不再重複貼）。
