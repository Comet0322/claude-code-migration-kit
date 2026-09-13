---
name: python-corplib-etl
description: >
  公司內部「背景 ETL 批次」形狀的 Python 專案模板——目錄結構、進入點、測
  試/build 方法。跟 `python-corplib-fastapi`（常駐服務）是同一套 corplib
  底下的兩種專案形狀之一，挑這個 skill 前提是這批應用是排程/手動觸發、跑
  完一輪就結束的批次工作，不是常駐 HTTP 服務。DB/logging 用法見
  `python-corplib`（這裡不重複），只講批次骨架跟怎麼跑測試/整合檢查。撰
  寫、審查公司內部任何批次型 Python 工作時都能用，不限於 legacy 遷移場
  景。
---

# ETL 批次模板（corplib）

這裡只講「批次」這個形狀的骨架跟測試/build方法。DB/logging 的用法見
`python-corplib`，這個 skill 不重複貼。

## 專案模板

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
- `corplib`（見 `python-corplib`）。
- 純標準庫以外一般不需要其他套件；如果這批 job 需要排程觸發，排程本身
  (cron/公司內部排程系統) 由部署設定負責，不是這個模板的一部分。

人類要先手動執行：`.venv/bin/python -m pip install -r requirements.txt`
（這台機器用專案層級的 `.venv`，`uv venv` 建的；Homebrew Python 預設不
允許系統層級安裝，PEP 668）。
唯讀確認方式：`.venv/bin/python -m pip show corplib`（或 `uv pip show
--python .venv/bin/python corplib`）——**不要用系統層級的裸 `pip
show`**，查錯地方會誤判成沒裝。查不到就停下來告訴人類要先裝，不要自己
執行安裝指令。

## 測試 / build 方法

- 跑測試：`.venv/bin/python -m pytest tests/ -q`
- 確認整個 app 能被匯入（不牽涉真的連 DB）：
  `.venv/bin/python -c "from app.main import main"`
- 整合檢查（migration-convert 全部 unit pass 後跑一次）：執行
  `.venv/bin/python -m app.main`，確認 process 以 exit code 0 結束、且
  log 裡出現每個 job 的完成訊息，再跑一次完整
  `.venv/bin/python -m pytest tests/ -q`。
