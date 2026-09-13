# Rulebook: dept200-delphi → Java (dept200-delphi-java)

來源：`fixtures/dept200-delphi/legacy/`　目標語言：Java
Domain skill：`domain-200-delphi-java`（來源端 `legacy-200-delphi`，目標端 `java-corplib`）
Ground truth tier：`inference`（見 `migration/ground-truth-strategy.md`）

## 種子規則（承襲自 domain skill，唯讀，不重新討論）

| Delphi | Java (corplib-java) | 備註 |
|---|---|---|
| `TDBConnection.Create(ReadIniConnString('app.ini'))` | `Database.fromEnv()` | DSN 來源改成環境變數 `CORPLIB_DB_DSN`，轉換後不再讀 ini。 |
| `Conn.Query(sql, [...])`（無交易） | `try (var conn = db.session()) { conn.fetchAll(sql, Map.of(...)); }` | 陣列 `['k', v, ...]` 換成 `Map.of("k", v, ...)`。 |
| `Conn.Execute` 搭配手動 `BeginTransaction`/`Commit`/`Rollback` | `try (var tx = db.transaction()) { tx.execute(...); tx.commit(); }` | 只有原始碼裡看得到手動交易的路徑才對應 `transaction()`；沒包交易的單純 `Execute` 對應 `db.session()`，不要一律升級成交易。 |
| `LogMessage(llInfo, msg, ['k=v', ...])` | `logger.info(msg, Map.of("k", "v", ...))` | `key=value` 字串陣列拆成 Map 的 key/value。 |
| `LogMessage(llError, msg, [...])` | `logger.error(msg, Map.of(...), ex)` | 只有 `try/except` 區塊裡才抓得到例外物件時才傳 `ex`；沒有 `except` 包起來的呼叫，`ex` 傳 `null`，不要編造例外。 |

## 這批程式碼特有的決策（人類已確認）

### 1. Dept200Data / Dept200Log 是「被 library 取代」的 unit，不產生目標檔案

**數據佐證**：語法轉換規則表裡的 5 條規則全部是轉換「呼叫端」（都出現在
`UserSync.pas`，共 9 處呼叫：2 次 `Query`、1 次 `Execute`、3 次交易方法呼
叫、3 次 `LogMessage`）。`Dept200Data.pas`（69 行）跟 `Dept200Log.pas`
（33 行）本身的內部實作（`TDBConnection` class body、`LogMessage`
procedure body）沒有任何一條規則要求翻譯成對應 Java class——它們的角色完
全由 `corplib-java` 的 `Database` / `Loggers` 取代。

**決定**：`dept200_data`、`dept200_log` 兩個 unit 在 `manifest.tsv` 裡標
記為 `library-replaced`，`target_path` 留空，轉換階段（`migration-convert`）
跳過這兩個 unit，不產生目標程式碼、不寫測試。只有 `user_sync`、`app` 兩
個 unit 需要實際轉換。

**影響範圍**：manifest 產出的 4 個 unit 裡，2 個進轉換 pipeline
（`user_sync`, `app`），2 個標記為 replaced 直接視為完成。

### 2. Package / app 命名

沒有需要人類抉擇的替代方案（模板佔位符 `<app>` 必須填一個值，只有唯一
合理選項），直接採用：

- Package base：`com.company.dept200`
- App 名稱（模板路徑 `target/<app>/`）：`dept200`

對應這批「部門 200」的批次應用；同批次其他部門的實例各自用自己的部門代
號，不共用同一個 target 目錄。

### 3. Unit → Java 類別對應（依模板慣例，無爭議，列出備查）

| unit_id | 角色 | Java 對應 |
|---|---|---|
| `user_sync` | 批次工作本體（`RunNightlySync`） | `job/UserSyncJob.java`，暴露 `run()` |
| `app` | 進入點（`App.dpr` 呼叫 `UserSync.RunNightlySync`） | `Application.java`，`CommandLineRunner` 依序呼叫各 Job |

## Deviation log

（轉換階段發現的規則缺口/偏差回報寫在這裡，目前為空）
