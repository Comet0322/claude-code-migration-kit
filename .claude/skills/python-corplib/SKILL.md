---
name: python-corplib
description: >
  公司內部 Python all-in-one 套件 corplib 的使用規範（DB 存取 + 結構化
  logging）。撰寫、審查任何會連 DB 或需要記 log 的公司內部 Python 程式碼
  時使用——不限於 legacy 遷移場景。這裡**只放 library 本身怎麼用**，不含
  專案骨架——公司內部同一個 corplib 會被裝進不止一種專案形狀（例如
  FastAPI 服務用 `python-corplib-fastapi`、背景 ETL 批次用
  `python-corplib-etl`），那兩個 skill 才決定目錄結構/進入點/測試build方
  法，並且都引用這裡的 DB/logging 用法，不要在這裡重複維護。
---

# corplib：公司內部 Python DB + Logging 規範

這份技能只講 `corplib` 這個 library 本身怎麼用，不管你把它裝進哪一種專
案形狀。要看專案骨架、進入點、測試/build 方法，去對應的形狀 skill（見
`description`）。

## corplib 使用方式（DB + Logging）

轉換規則直接引用下面這些介面，不需要另外自己選 DB/logging 方案，也不要
繞過它直接用 `sqlite3`/`logging` 標準庫自己接。

### `corplib.db`

```python
from corplib.db import Database

db = Database.from_env()  # 讀 CORPLIB_DB_DSN 環境變數，內部走 pyodbc 連線
                           # 池，指向跟舊系統同一台 MS SQL Server

# 查詢
with db.session() as conn:
    rows = conn.fetch_all(
        "SELECT id, name FROM users WHERE dept = :dept", {"dept": "200"}
    )
    row = conn.fetch_one("SELECT * FROM users WHERE id = :id", {"id": 1})

# 寫入／交易
with db.transaction() as tx:
    tx.execute(
        "UPDATE users SET name = :name WHERE id = :id",
        {"name": "foo", "id": 1},
    )
    # with 區塊正常結束才 commit，發生例外會自動 rollback
```

- 參數一律用具名 `:name` 佔位符，`conn`/`tx` 自己處理轉義，不要自己組字
  串下 SQL。
- 連線池、重試、timeout 都由 `Database.from_env()` 內建處理，轉換規則不
  需要重新實作這些。

### `corplib.logging`

```python
from corplib.logging import get_logger

logger = get_logger(__name__)
logger.info("fetched user", extra={"unit_id": "u123", "user_id": 1})
logger.error("db timeout", extra={"unit_id": "u123"}, exc_info=True)
```

- 輸出格式固定是一行一筆 JSON（timestamp、level、logger 名稱、message、
  extra 欄位），寫到 stdout，由外部 log 收集器處理，不用自己配置
  handler/formatter。
- 套件需要人類先手動安裝好（不在公開 PyPI，air-gapped 環境要由人類先從
  內部套件庫/vendored wheel 裝好）；唯讀確認方式：這台機器用專案層級的
  `.venv`（`uv venv` 建的），查 `.venv/bin/python -m pip show corplib`
  或 `uv pip show --python .venv/bin/python corplib`——**不要用系統層級
  的裸 `pip show corplib`**，這台機器的 Homebrew Python 預設不允許系統
  層級安裝（PEP 668），裸指令查不到不代表沒裝，是查錯地方。查不到就停
  下來告訴人類要先裝，不要自己執行安裝指令。
