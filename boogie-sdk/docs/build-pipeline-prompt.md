# boogie-sdk 實作流程 Prompt Template

給之後(Python 現在跑一次、Java 之後跑一次)貼給 Claude Code 用的完整指令。
每次使用時把方括號 `[...]` 換成該語言對應的值即可,其餘文字保持原樣。

---

## 參數對照表

最終產出**不是**放在 repo 根目錄的 `boogie-sdk/`,而是直接放進對應語言的
`*-template` skill 底下(`.claude/skills/<language>-template/vendor/
boogie-sdk-<language>/`),這樣 migration skill 才能直接發現、不用另外接線
——見階段 4。Python/Java 這兩欄是已經跑過、實際落地的值;之後如果要做新語言
port(例如 C#),先照 `<language>-template` 的既有 skill 命名慣例建立
`.claude/skills/<language>-template/`(可以參考 `domain-template` 的做法),
再類推對照表。

| 佔位符 | Python 值 | Java 值 |
|---|---|---|
| `[LANGUAGE]` | Python | Java |
| `[TEMPLATE_SKILL]` | `.claude/skills/python-template/` | `.claude/skills/java-template/` |
| `[DESIGN_DOC]` | `[TEMPLATE_SKILL]/boogie-sdk-api.md` | `[TEMPLATE_SKILL]/boogie-sdk-api.md` |
| `[PROJECT_ROOT]` | `[TEMPLATE_SKILL]/vendor/boogie-sdk-python/` | `[TEMPLATE_SKILL]/vendor/boogie-sdk-java/` |
| `[BUILD_TOOL]` | uv | Maven |
| `[TEST_CMD]` | `uv run --package boogie-sdk pytest [PROJECT_ROOT]/tests -q` | `mvn -f [PROJECT_ROOT]/pom.xml test` |
| `[BUILD_CMD]` | `uv sync --all-packages`(**絕對不要**在 `[PROJECT_ROOT]` 底下跑裸的 `uv sync`——會把 repo 根目錄 workspace 其他成員的依賴洗掉,見階段 0 的提醒) | `mvn -q -f [PROJECT_ROOT]/pom.xml -DskipTests package` |
| `[TEST_FRAMEWORK]` | pytest | JUnit5 |

---

## Prompt 本體

我要實作 boogie-sdk 的 [LANGUAGE] 版本,設計文件在 `[DESIGN_DOC]`。這是訓練用
的模擬 library,所有 infra 連線都是記憶體內假實作,不接真實外部服務 —— 重點是
API 形狀要跟設計文件完全一致,之後才能拿去給 migration skill 對照舊語言程式碼。

請照下面的階段執行,**每個階段做完先跟我確認結果再進下一階段**:

### 階段 0:骨架 + 編譯執行測試環境

在 `[PROJECT_ROOT]` 建立專案骨架([BUILD_TOOL]),包含:
- 依設計文件的「專案結構」章節建立目錄與空模組檔案(先放最小可編譯的殼,例如
  類別/介面簽章 + `raise NotImplementedError` / `throw new UnsupportedOperationException()`)
- `core`/`config` 基礎模組(例外階層、`BoogieConfig`、`BoogieSdk` facade)要先有
  可運作的最小實作,因為其他模組都依賴它
- Python 專屬:`[PROJECT_ROOT]` 要註冊進 repo 根目錄 `pyproject.toml` 的
  `[tool.uv.workspace] members`,之後才能用 `uv run --package boogie-sdk`
  執行——**絕對不要**在 `[PROJECT_ROOT]` 底下直接跑裸的 `uv sync`,會把 repo
  根目錄 workspace 其他成員(例如 `migration-test-harness` 自己的
  `claude-agent-sdk` 依賴)從共用 venv 洗掉;要嘛在 repo 根目錄跑
  `uv sync --all-packages`,要嘛在 `[PROJECT_ROOT]` 底下用 `uv add <pkg>`
  加單一套件依賴。
- 確認 `[BUILD_CMD]` 跟 `[TEST_CMD]`(即使 0 個測試)都能成功跑完,沒有編譯錯誤
- 確認完成後回報:目錄樹、`[TEST_CMD]` 的輸出

不要在這階段寫任何模組的真實邏輯或單元測試,只要「骨架能編譯、能跑測試指令」。

### 階段 1:逐模組 TDD 迴圈(每模組派 3 個 agent)

依設計文件「模組 API 參考」章節,依序處理每個模組(建議順序:`core`/`config` →
`crypto` → `infra` → `observability` → `governance` → `deviceio`,因為後面模組
可能依賴前面模組的例外類別或 client 慣例)。

對**每一個模組**,依序執行 3 個 agent(用 Agent tool 各自獨立派工,不要讓同一個
agent 兼兩個角色):

1. **測試撰寫 agent**:只讀設計文件裡該模組的 API 簽章與說明,寫出 [TEST_FRAMEWORK]
   單元測試,涵蓋每個 public method 的正常情境、邊界情況、例外情境。此時模組還沒
   實作,測試應該是紅燈(compile 可能會失敗,因為方法還沒實作 —— 沒關係,先確保
   骨架有殼)。這個 agent **不能看到、也不能寫**實作程式碼。
2. **實作撰寫 agent**:讀設計文件該模組章節 + 上一步寫好的測試,寫出讓測試全部
   通過的實作(純記憶體假實作,不接真實外部服務)。**不能修改測試檔案**,只能
   改動 method 內部邏輯讓測試通過;如果認為測試本身有誤,要回報給我而不是直接改測試。
3. **驗收 agent**:跑 `[TEST_CMD]`(或至少該模組的測試)+ 對照設計文件檢查
   API 是否忠實(方法名稱、簽章、例外型別是否一致)、程式碼品質是否合理。若不通過,
   給出具體修正指示並回到步驟 2 重跑,直到通過為止。

一個模組的 3-agent 迴圈完成、驗收 agent 給過之後,才進下一個模組。全部模組跑完後
回報:哪些模組完成、測試總數、是否有已知的取捨或簡化。

### 階段 2:整合檢查

所有模組完成後,跑一次完整的 `[TEST_CMD]`,確認 `BoogieSdk` facade 能正確組裝
所有子模組(`sdk.crypto`、`sdk.db`... 等都能正常取得並互不干擾)。這階段不用再拆
3 個 agent,你自己跑完整測試 + 檢查 facade 接線即可。

### 階段 3:文件 + ETL 範例專案(派 1 個 subagent)

派一個 subagent 做兩件事:
1. 幫 `[PROJECT_ROOT]` 寫使用文件(README:安裝方式、`[BUILD_CMD]`/`[TEST_CMD]`、
   每個模組的簡短使用範例)。
2. 在 `[PROJECT_ROOT]/examples/etl-demo` 建一個可執行的 ETL 範例專案,情境是
   「從某個來源讀資料 → 轉換 → 寫入另一處」,盡量吃到多個模組(例如:
   `config` 讀設定 → `http` 或 `db` 抓資料 → `crypto` 做欄位加解密/遮罩 →
   `queue` 或 `object-storage` 輸出 → `logger`/`metrics` 記錄過程 →
   `notification` 在失敗時通知)。這個範例專案就是給新人 onboarding 用的 template。

   **檔案結構固定為 4 個檔案,不管哪個語言都一律照這個切法**(main 之外三個對應
   ETL 的 Extract/Transform/Load 三階段,用更貼近「資料搬移」情境的命名):
   - `main`(`main.py` / `Main.java` / 對應語言的進入點檔名):組裝 `BoogieSdk`、
     跑 batch/shift 追蹤、logger/tracer/metrics 這些橫跨全流程的可觀測性、依序呼叫
     download → process → upload、最後印出總結(batch 歷史、metrics snapshot、
     tracer spans、已發通知、audit trail)。
   - `download`(`download.py` / `Download.java`):對應 Extract——準備/讀取來源
     資料(例如建表 + seed + query,或呼叫 `http`)。
   - `process`(`process.py` / `Process.java`):對應 Transform——欄位加解密/遮罩、
     資料驗證,單筆失敗要能被攔截(記 audit + 發 notification)但不中斷整批。
   - `upload`(`upload.py` / `Upload.java`):對應 Load——把結果寫到
     `object-storage`/`queue`,以及產出報表(Excel/PDF)這類「輸出」動作都歸在這裡。

   不要把這四個檔案的職責混在一起(例如不要把 transform 邏輯寫進 main),
   也不要為了湊檔案數而拆出第 5 個檔案——恰好 4 個檔案,職責照上面對應。

   **只有真的碰資料庫(SQL)的那個檔案才需要外部化 SQL**:通常是
   `download`(從來源表讀資料)。這個檔案不要把 SQL 字串寫死在程式碼裡,改成
   在旁邊放一個 `sql/`(Python 放同目錄下的 `sql/*.sql`;Java 放
   `src/main/resources/.../sql/*.sql` 用 classloader 讀)資料夾,每個語句一個
   `.sql` 檔,由該檔案讀進來執行。`main` 負責跟 `BoogieSdk` 拿到 db
   連線(`sdk.db`/`sdk.db()`)再傳給該檔案——該檔案本身不該再去碰整個 `sdk`
   facade。如果 `process`/`upload` 這兩個階段在這個範例的劇本裡本來就不碰資料庫
   (例如 transform 是純記憶體運算、load 是寫 object storage/queue),就不用為了
   湊「三個都要有 SQL」而硬塞資料庫操作進去——SQL 外部化只套用在真的有 SQL 的
   那個檔案上。

完成後回報範例專案怎麼跑(執行指令 + 預期輸出)。

### 階段 4:接進 `[TEMPLATE_SKILL]` 的 SKILL.md

因為 `[PROJECT_ROOT]` 本來就直接落在 `[TEMPLATE_SKILL]/vendor/` 底下(見
「參數對照表」),這步只剩下把 `[TEMPLATE_SKILL]/SKILL.md` 的內容改成描述
boogie-sdk 本身,不用再搬檔案:

1. 把設計文件(`[DESIGN_DOC]`)當成這個 skill 的「library 文件」參考檔——
   保留完整內容,只需要修正裡面的相對路徑(專案結構那段的路徑要指到
   `[TEMPLATE_SKILL]/vendor/boogie-sdk-<language>/`)。
2. 改寫 `[TEMPLATE_SKILL]/SKILL.md`:
   - frontmatter `description` 提到「boogie-sdk」而不是舊的假 library 名稱。
   - 「How to use boogie-sdk」章節:每個模組簡短範例 + 一個模組總表(可以照
     `[DESIGN_DOC]` 第 5 節濃縮),註明方法呼叫風格(Java 是方法呼叫
     `sdk.db()`,Python 是屬性存取 `sdk.db`)。
   - 「Project shape」章節:换成階段 3 那個 4 檔案 ETL 模板的實際目錄結構跟
     檔案職責說明,並附上真的能跑的指令(從 repo 根目錄呼叫
     `[TEST_CMD]`/例外的執行指令)。如果這個語言原本就有多個 project shape
     (例如 Python 的 FastAPI service),**只換掉跟這次 ETL 範例對應的那個
     shape 章節**,其他 shape 維持原樣——不要因為換了 library 就連帶砍掉
     用不到 boogie-sdk 這部分功能的章節。
3. 全文找一次舊 library 名稱(例如前一版的 `corplib`)有沒有殘留引用,一併
   換成 boogie-sdk 對應的 API,避免文件裡留著解析不到的死引用。
4. 改完後重新用 `[TEST_CMD]` 跑一次(新路徑),並且真的執行一次 ETL 範例
   模板,確認從 repo 根目錄呼叫都正常——路徑改動最容易在這裡出現筆誤。

---

## 使用方式

- **這次(Python)**:把 `[LANGUAGE]`→Python 等代入上面表格,整段貼給我開始執行。
- **之後(Java)**:同一份 prompt,把表格換成 Java 那一欄再貼一次即可,不用重寫描述。
