---
name: python-template
description: >
  公司內部 Python 目標端知識大全——corplib all-in-one 套件的使用規範（DB
  存取 + 結構化 logging）跟公司內部目前支援的兩種專案形狀模板（FastAPI
  常駐服務 / 背景 ETL 批次）都放在這裡，避免同一套目標端知識分散成好幾
  個 skill。撰寫、審查任何會連 DB、需要記 log，或要建立這兩種專案形狀的
  公司內部 Python 程式碼時使用——不限於 legacy 遷移場景。在 legacy 遷移
  到 Python 的情境中，domain-200-delphi-python、domain-300-vb-python 的
  目標端知識（library 文件、專案形狀模板、測試/build 方法）都指向這裡，
  不要重複貼。跟 `java-template` 是同一套公司 DB/logging 慣例的不同語言
  綁定——後端都是同一台 MS SQL Server、同一套 log 收集格式，只是這裡是
  Python 側實作。
---

# python-template：公司內部 Python 目標端知識（library + 專案形狀模板）

這份技能是公司內部 Python 目標端知識的單一入口，涵蓋兩塊：

1. **corplib 使用方式**（DB + Logging）——不管你把它裝進哪一種專案形狀
   都適用，只講一次，不在每個形狀底下重複。
2. **專案形狀模板**——公司內部目前有兩種：**FastAPI 常駐服務**、**背景
   ETL 批次**。先確認這批應用屬於哪一種形狀（由 `migration-clarify` 跟
   人類確認，見「Decide target project shape」節），再看對應那節的目錄結構/進入
   點/測試build方法，不要兩節都套用。

在 legacy 遷移的情境中，`domain-200-delphi-python`、`domain-300-vb-python`
兩個 domain skill 的目標端知識（模板專案、library 文件、測試/build 方
法）都指向這裡，不要重複貼。

`vendor/corplib-python/` 這個子資料夾放的是 `corplib` 的一份真實、可安
裝、可執行的最小實作（後端是 SQLite，不是下面文件描述的正牌 MS SQL
Server，僅供 harness 測試基礎設施驗證整條 pipeline 真的能 import、能執
行、測試真的能過/不過用，不是公司內部正式套件、也不是這份文件描述行為
的替代品）——跟這份 SKILL.md 放在同一個 skill 資料夾底下維護，不是獨立
的東西。

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

## 專案形狀：FastAPI 常駐服務

這個形狀的前提是這批應用要跑成常駐 HTTP 服務，不是跑完就結束的批次工
作。DB/logging 的用法見上面「corplib 使用方式」節，這裡不重複。

```
target/<unit群組或app名稱>/
├── app/
│   ├── __init__.py
│   ├── main.py                  # 進入點：建立 FastAPI app、掛路由、掛
│   │                             # corplib 的 logging middleware
│   ├── api/
│   │   └── routes_<unit_id>.py  # 每個遷移 unit 一個 router 檔
│   ├── core/
│   │   └── config.py            # pydantic BaseSettings，讀環境變數
│   │                             # （DB DSN、log 等級等）
│   └── models/
│       └── <unit_id>.py         # 對應這個 unit 的 pydantic schema
├── tests/
│   └── test_<unit_id>.py
└── requirements.txt
```

進入點：`uvicorn app.main:app --host 0.0.0.0 --port 8000`。成功標準：能啟
動且 `GET /healthz` 回 200（`main.py` 自己掛一個回傳 `{"status": "ok"}` 的
`/healthz` route，不對應任何一個 legacy unit，純粹是進入點健康檢查）。

外部套件（不是純標準庫）：
- `fastapi`、`uvicorn`、`pydantic`（公開套件）。
- `corplib`（見上面「corplib 使用方式」節）。

人類要先手動執行：`.venv/bin/python -m pip install -r requirements.txt`
（這台機器用專案層級的 `.venv`，`uv venv` 建的；Homebrew Python 預設不
允許系統層級安裝，PEP 668）。
唯讀確認方式：`.venv/bin/python -m pip show fastapi`、
`.venv/bin/python -m pip show uvicorn`（或 `uv pip show --python
.venv/bin/python <pkg>`）——**不要用系統層級的裸 `pip show`**，查錯地方
會誤判成沒裝。查不到就停下來告訴人類要先裝，不要自己執行安裝指令。

`main.py` 要掛 `from corplib.logging import RequestLoggingMiddleware` 並
`app.add_middleware(RequestLoggingMiddleware)`——每個 request 會自動記一
筆含 trace_id 的 log，轉換規則不需要在每個 router 自己重複記 request 層
級的 log。

### 測試 / build 方法（FastAPI）

- 跑測試：`.venv/bin/python -m pytest tests/ -q`
- 確認整個 app 能被匯入（不牽涉真的連 DB）：
  `.venv/bin/python -c "from app.main import app"`
- 整合檢查（migration-convert 全部 unit pass 後跑一次）：啟動
  `.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`，
  `curl -sf http://localhost:8000/healthz` 回 200 即算入口點檢查通過，
  再跑一次完整 `.venv/bin/python -m pytest tests/ -q`。

## 專案形狀：背景 ETL 批次

這個形狀的前提是這批應用是排程/手動觸發、跑完一輪就結束的批次工作，不
是常駐 HTTP 服務。DB/logging 的用法見上面「corplib 使用方式」節，這裡不
重複。

```
target/<unit群組或app名稱>/
├── app/
│   ├── __init__.py
│   ├── main.py                  # 進入點：依序執行各 job，跑完就結束、
│   │                             # 不常駐
│   ├── jobs/
│   │   └── job_<unit_id>.py     # 每個遷移 unit 一個批次工作模組，暴露
│   │                             # 一個 run() 函式
│   └── core/
│       └── config.py            # 讀環境變數（DB DSN、log 等級等）
├── tests/
│   └── test_<unit_id>.py
└── requirements.txt
```

進入點：`python -m app.main`。成功標準：process 跑完自然結束、exit code
為 0，且 log 裡看得到每個 job 各自輸出的完成訊息（例如
`logger.info("job done", extra={"job": "<unit_id>"})`）——**沒有 HTTP
health check**，因為這不是常駐服務；`main.py` 裡任何一個 job 拋出未捕捉
的例外就要讓整個 process 以非 0 exit code 結束，不要吞掉錯誤讓 process
看起來正常結束。

外部套件（不是純標準庫）：
- `corplib`（見上面「corplib 使用方式」節）。
- 純標準庫以外一般不需要其他套件；如果這批 job 需要排程觸發，排程本身
  (cron/公司內部排程系統) 由部署設定負責，不是這個模板的一部分。

人類要先手動執行：`.venv/bin/python -m pip install -r requirements.txt`
（這台機器用專案層級的 `.venv`，`uv venv` 建的；Homebrew Python 預設不
允許系統層級安裝，PEP 668）。
唯讀確認方式：`.venv/bin/python -m pip show corplib`（或 `uv pip show
--python .venv/bin/python corplib`）——**不要用系統層級的裸 `pip
show`**，查錯地方會誤判成沒裝。查不到就停下來告訴人類要先裝，不要自己
執行安裝指令。

### 測試 / build 方法（ETL 批次）

- 跑測試：`.venv/bin/python -m pytest tests/ -q`
- 確認整個 app 能被匯入（不牽涉真的連 DB）：
  `.venv/bin/python -c "from app.main import main"`
- 整合檢查（migration-convert 全部 unit pass 後跑一次）：執行
  `.venv/bin/python -m app.main`，確認 process 以 exit code 0 結束、且
  log 裡出現每個 job 的完成訊息，再跑一次完整
  `.venv/bin/python -m pytest tests/ -q`。
