---
name: java-template
description: >
  公司內部 Java 目標端知識大全——corplib all-in-one 套件的使用規範（DB
  存取 + 結構化 logging）跟公司內部目前唯一支援的專案形狀模板（背景 ETL
  批次，用 Spring Boot 的 `CommandLineRunner`，跑完一輪就結束，不是常駐
  web 服務）都放在這裡，避免同一套目標端知識分散成好幾個 skill。撰寫、
  審查任何會連 DB 或需要記 log 的公司內部 Java 批次程式碼時使用——不限於
  legacy 遷移場景。在 legacy 遷移到 Java 的情境中，domain-200-vb-java、
  domain-200-delphi-java 的目標端知識（模板專案、library 文件、測試/build
  方法）都指向這裡，不要重複貼。跟 `python-template` 是同一套公司
  DB/logging 慣例的不同語言綁定——後端都是同一台 MS SQL Server、同一套
  log 收集格式，只是這裡是 Java 側實作。Java 目前只有這一種形狀，不像
  Python 端在同一個 `python-template` 裡還分 FastAPI 服務／ETL 批次兩節；
  如果之後 Java 也需要常駐服務形狀，比照 `python-template` 的做法在這裡
  加一節，不要拆成獨立 skill。
---

# java-template：公司內部 Java 目標端知識（library + 專案形狀模板）

這份技能是公司內部 Java 目標端知識的單一入口，涵蓋兩塊：

1. **corplib 使用方式**（DB + Logging）——不管你把它裝進哪一種專案形狀
   都適用，只講一次，不重複。
2. **專案形狀模板**——Java 目前只有一種：**背景 ETL 批次**。

在 legacy 遷移的情境中，`domain-200-vb-java`、`domain-200-delphi-java`
兩個 domain skill 引用這裡當作「模板專案 / 新語言 library 文件 / 測試
build 方法」三節的內容，不重複維護。

`vendor/corplib-java/` 這個子資料夾放的是 `corplib-java` 的一份真實、可
編譯、可執行的最小實作（後端是 SQLite，不是下面文件描述的正牌 MS SQL
Server，僅供 harness 測試基礎設施驗證整條 pipeline 真的能 compile、能
執行、測試真的能過/不過用，不是公司內部正式套件、也不是這份文件描述行
為的替代品）——跟這份 SKILL.md 放在同一個 skill 資料夾底下維護，不是獨
立的東西。

## 專案形狀：背景 ETL 批次

```
target/<unit群組或app名稱>/
├── src/main/java/com/company/<app>/
│   ├── Application.java              # 進入點：SpringApplication.run，
│   │                                  # 實作 CommandLineRunner，依序執行
│   │                                  # 各 job 後結束（不是常駐服務）
│   ├── job/
│   │   └── <UnitId>Job.java          # 每個遷移 unit 一個批次工作類別，
│   │                                  # 暴露一個 run() 方法
│   ├── config/
│   │   └── CorplibConfig.java        # 讀 application.yml，設定 DB DSN、
│   │                                  # log 等級等
│   └── model/
│       └── <UnitId>Dto.java          # 對應這個 unit 的資料物件
├── src/test/java/com/company/<app>/
│   └── <UnitId>JobTest.java
├── src/main/resources/application.yml
└── pom.xml
```

進入點：`java -jar target/<app>.jar`。成功標準：process 跑完自然結束、
exit code 為 0，且 log 裡看得到每個 `<UnitId>Job` 各自輸出的完成訊息（例
如 `logger.info("job done", Map.of("job", "<unitId>"))`）——**沒有 HTTP
health check**，因為這不是常駐服務；`Application.java` 的
`CommandLineRunner.run()` 裡任何一個 job 拋出未捕捉的例外，要讓整個
process 以非 0 exit code 結束，不要吞掉錯誤讓 process 看起來正常結束。

外部套件（不是純標準庫）：
- `spring-boot-starter`（core，不需要 `spring-boot-starter-web`/
  `actuator`——這不是常駐服務，沒有 HTTP endpoint）。
- `com.company:corplib-java`（公司內部 all-in-one 套件，見下方——不在公
  開 Maven Central，air-gapped 環境要由人類先設定好內部 Nexus/Artifactory
  mirror 或把 jar 放進本地 `.m2` 倉庫）。

人類要先手動設定好 `settings.xml` 的內部 repository mirror，並確認
`corplib-java` 抓得到。
唯讀確認方式：`mvn -q dependency:tree | grep corplib`，或檢查本地
`~/.m2/repository/com/company/corplib-java` 是否存在——查不到就停下來告
訴人類要先設定/安裝，不要自己執行安裝指令。

## corplib 使用方式（DB + Logging）

轉換規則直接引用下面這些介面，不需要另外自己選 DB/logging 方案，也不要
繞過它直接用 JDBC/`java.util.logging` 自己接。

### `com.company.corplib.db.Database`

```java
import com.company.corplib.db.Database;

Database db = Database.fromEnv();
// 讀 CORPLIB_DB_DSN 環境變數，內部走 HikariCP 連線池，指向跟舊系統同一
// 台 MS SQL Server（跟 python-template 的 corplib.db 接同一台）

// 查詢
try (var conn = db.session()) {
    var rows = conn.fetchAll(
        "SELECT id, name FROM users WHERE dept = :dept", Map.of("dept", "200"));
    var row = conn.fetchOne("SELECT * FROM users WHERE id = :id", Map.of("id", 1));
}

// 寫入／交易
try (var tx = db.transaction()) {
    tx.execute(
        "UPDATE users SET name = :name WHERE id = :id",
        Map.of("name", "foo", "id", 1));
    tx.commit(); // 離開 try-with-resources 前沒呼叫 commit() 會自動 rollback
}
```

- 參數一律用具名 `:name` 佔位符，`conn`/`tx` 自己處理轉義，不要自己組字
  串下 SQL。
- 連線池、重試、timeout 都由 `Database.fromEnv()` 內建處理，轉換規則不需
  要重新實作這些。

### `com.company.corplib.logging.Loggers`

```java
import com.company.corplib.logging.Loggers;

var logger = Loggers.get(MyClass.class);
logger.info("fetched user", Map.of("unitId", "u123", "userId", 1));
logger.error("db timeout", Map.of("unitId", "u123"), ex);
```

- 輸出格式固定是一行一筆 JSON（timestamp、level、logger 名稱、message、
  extra 欄位），寫到 stdout，由外部 log 收集器處理，格式跟 `python-template`
  的 `corplib.logging` 一致，不用自己配置 logback/log4j pattern layout。

## 測試 / build 方法

- 跑測試：`mvn test`
- 確認整個 app 能被編譯（不牽涉真的連 DB）：`mvn -q compile`
- 整合檢查（migration-convert 全部 unit pass 後跑一次）：`java -jar
  target/<app>.jar`，確認 process 以 exit code 0 結束、且 log 裡出現每個
  job 的完成訊息，再跑一次完整 `mvn test`。
