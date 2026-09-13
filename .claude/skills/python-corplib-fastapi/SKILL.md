---
name: python-corplib-fastapi
description: >
  公司內部「FastAPI 服務」形狀的 Python 專案模板——目錄結構、進入點、測
  試/build 方法。跟 `python-corplib-etl`（背景 ETL 批次）是同一套
  corplib 底下的兩種專案形狀之一，挑這個 skill 前提是這批應用要跑成常駐
  HTTP 服務，不是跑完就結束的批次工作。DB/logging 用法見 `python-corplib`
  （這裡不重複），只講服務骨架跟怎麼跑測試/整合檢查。撰寫、審查公司內部
  任何 FastAPI 服務時都能用，不限於 legacy 遷移場景。
---

# FastAPI 服務模板（corplib）

這裡只講「服務」這個形狀的骨架跟測試/build方法。DB/logging 的用法見
`python-corplib`，這個 skill 不重複貼。

## 專案模板

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
- `corplib`（見 `python-corplib`）。

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

## 測試 / build 方法

- 跑測試：`.venv/bin/python -m pytest tests/ -q`
- 確認整個 app 能被匯入（不牽涉真的連 DB）：
  `.venv/bin/python -c "from app.main import app"`
- 整合檢查（migration-convert 全部 unit pass 後跑一次）：啟動
  `.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`，
  `curl -sf http://localhost:8000/healthz` 回 200 即算入口點檢查通過，
  再跑一次完整 `.venv/bin/python -m pytest tests/ -q`。
