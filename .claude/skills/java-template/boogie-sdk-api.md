# boogie-sdk (Java) — 設計文件

## 1. 目的

`boogie-sdk` 是模擬公司內部 all-in-one library 的訓練用套件。所有「連接 infra」
的元件底層都是**記憶體內假實作(in-memory fake)**,不連真實外部服務 —— 目的不是
真的可用於生產,而是讓 migration skill 在讀到舊語言程式碼時,能認出「這段邏輯
應該轉換成呼叫 boogie-sdk 的哪個 API」。因此每個 client 的方法簽章、生命週期、
例外處理都刻意模仿真實企業 SDK 的樣子。

- 建置工具:**Maven**(單一 module,單一 jar)
- groupId: `com.boogie.sdk`
- artifactId: `boogie-sdk`
- Java 版本:17
- 版本號:`0.1.0`(單一版本,不分模組獨立版號)

## 2. 專案結構

實際套件現在 vendor 在 `.claude/skills/java-template/vendor/boogie-sdk-java/`
底下(這份文件本身也在同一個 skill 目錄裡),讓 migration skill 不用另外去
repo 根目錄找:

```
.claude/skills/java-template/vendor/boogie-sdk-java/
├── pom.xml
└── src/
    ├── main/java/com/boogie/sdk/
    │   ├── BoogieSdk.java              # 入口 facade
    │   ├── config/
    │   │   ├── BoogieConfig.java
    │   │   └── ConfigClient.java
    │   ├── core/                       # 共用例外、基礎型別
    │   │   ├── PlatformException.java
    │   │   ├── InfraException.java
    │   │   ├── CryptoException.java
    │   │   ├── ValidationException.java
    │   │   ├── DeviceIoException.java
    │   │   ├── NotFoundException.java
    │   │   └── RateLimitExceededException.java
    │   ├── crypto/
    │   │   ├── CryptoClient.java
    │   │   ├── SecretClient.java
    │   │   ├── TokenClient.java
    │   │   ├── CertManager.java
    │   │   └── MaskUtil.java
    │   ├── infra/
    │   │   ├── HttpClient.java
    │   │   ├── DbClient.java
    │   │   ├── CacheClient.java
    │   │   ├── QueueClient.java
    │   │   ├── ObjectStorageClient.java
    │   │   ├── ServiceDiscoveryClient.java
    │   │   └── SchedulerClient.java
    │   ├── deviceio/
    │   │   ├── DeviceProtocolClient.java
    │   │   ├── FilePollingClient.java
    │   │   ├── FlatFileParser.java
    │   │   ├── ReportGenerator.java
    │   │   ├── BatchTracker.java
    │   │   ├── ShiftCalendar.java
    │   │   └── SpcAnalyzer.java
    │   ├── observability/
    │   │   ├── Logger.java
    │   │   ├── MetricsClient.java
    │   │   └── Tracer.java
    │   └── governance/
    │       ├── IdGenerator.java
    │       ├── FeatureFlagClient.java
    │       ├── RateLimiter.java
    │       ├── NotificationClient.java
    │       ├── HealthCheck.java
    │       └── AuditLogger.java
    └── test/java/com/boogie/sdk/...    # JUnit5,對假實作的行為做斷言
```

## 3. Facade 與生命週期

所有模組都透過單一入口取得,模仿真實企業 SDK「一個物件、各種 `xxx()` 取子模組」
的慣例,方便 migration skill 辨識固定進入點:

```java
BoogieConfig config = BoogieConfig.load();      // 讀 boogie-sdk.yaml + 環境變數
BoogieSdk sdk = BoogieSdk.init(config);

sdk.crypto().encryptAes(data, "key-1");
sdk.db().query("SELECT ...", params);
sdk.logger().info("done", Map.of("batchId", id));

sdk.close();                                    // 釋放所有底層假資源
```

## 4. 共用慣例

- **例外階層**:所有例外繼承 `PlatformException`(unchecked)。各模組拋出對應子類
  (`CryptoException`、`InfraException`、`DeviceIoException`、`ValidationException`、
  `NotFoundException`、`RateLimitExceededException`)。
- **設定**:`BoogieConfig.load()` 讀取 `boogie-sdk.yaml`,環境變數可覆蓋(`BOOGIE_*` 前綴)。
- **命名**:client 類別一律 `XxxClient`(除了少數工具類如 `MaskUtil`、`ShiftCalendar`)。
- **Builder**:需要多個可選參數的操作用 builder,例如 `HttpClient.request()...build()`。

## 5. 模組 API 參考

### 5.1 crypto

```java
class CryptoClient {
    byte[] encryptAes(byte[] plaintext, String keyId);
    byte[] decryptAes(byte[] ciphertext, String keyId);
    byte[] sign(byte[] data, String keyId);
    boolean verify(byte[] data, byte[] signature, String keyId);
    byte[] hash(byte[] data, HashAlgo algo);           // SHA256, SHA512
    byte[] hmac(byte[] data, String keyId);
}

class SecretClient {
    Secret getSecret(String path);                     // 內建 TTL 快取
    void putSecret(String path, Map<String, String> data);
}

class TokenClient {
    String issueToken(Map<String, Object> claims);
    Claims verifyToken(String token);
}

class CertManager {
    Certificate loadCert(Path path);
    Instant getExpiryDate(String certId);
    boolean isRotationDue(String certId);
}

class MaskUtil {
    static String maskIdNumber(String id);
    static String maskPhone(String phone);
    static String maskCardNumber(String card);
}
```

### 5.2 infra

```java
class HttpClient {
    HttpResponse get(String url, Map<String, String> headers);
    HttpResponse post(String url, byte[] body, Map<String, String> headers);
    // 內建 trace-id 注入、retry/backoff、timeout
}

class DbClient {
    List<Row> query(String sql, Map<String, Object> params);
    int execute(String sql, Map<String, Object> params);
    <T> T transaction(Function<DbSession, T> work);
}

class CacheClient {
    Optional<byte[]> get(String key);
    void set(String key, byte[] value, Duration ttl);
    void delete(String key);
    byte[] getOrCompute(String key, Duration ttl, Supplier<byte[]> loader);
}

class QueueClient {
    void publish(String topic, byte[] message);
    Subscription subscribe(String topic, Consumer<Message> handler);
}

class ObjectStorageClient {
    void upload(String bucket, String key, byte[] data);
    byte[] download(String bucket, String key);
    URI presignUrl(String bucket, String key, Duration ttl);
}

class ServiceDiscoveryClient {
    Endpoint resolve(String serviceName);
}

class SchedulerClient {
    Lock lock(String name, Duration ttl);
    void scheduleCron(String cronExpr, Runnable task);
}
```

### 5.3 deviceio

```java
class DeviceProtocolClient {
    void connect(String endpoint);
    void sendCommand(DeviceCommand cmd);
    void onEvent(Consumer<DeviceEvent> handler);
    void disconnect();
}

class FilePollingClient {
    void watch(Path dir, String pattern, Consumer<Path> handler);
    List<Path> pollOnce(Path dir, String pattern);
}

class FlatFileParser {
    <T> List<T> parse(Path file, RecordSchema<T> schema);
}

class ReportGenerator {
    void generateExcel(List<Map<String, Object>> data, Path template, Path outFile);
    void generatePdf(List<Map<String, Object>> data, Path template, Path outFile);
}

class BatchTracker {
    void createBatch(String batchId);
    void updateStatus(String batchId, String status);
    List<BatchEvent> getHistory(String batchId);
}

class ShiftCalendar {
    Shift currentShift(Instant time);
    ShiftBoundary boundariesFor(LocalDate date);
}

class SpcAnalyzer {
    void addSample(double value);
    boolean isOutOfControl();
    ControlLimits controlLimits();
}
```

### 5.4 observability

```java
class Logger {
    void info(String msg, Map<String, Object> fields);
    void warn(String msg, Map<String, Object> fields);
    void error(String msg, Throwable t, Map<String, Object> fields);
}

class MetricsClient {
    Counter counter(String name);
    Gauge gauge(String name);
    Timer timer(String name);
}

class Tracer {
    Span startSpan(String name);   // span.end() 結束
}
```

### 5.5 governance

```java
class IdGenerator {
    long nextId();                 // Snowflake-style
}

class FeatureFlagClient {
    boolean isEnabled(String flagKey, Map<String, Object> context);
}

class RateLimiter {
    boolean tryAcquire();
    void acquire();                 // 阻塞直到取得
}

class NotificationClient {
    void sendEmail(String to, String subject, String body);
    void sendIm(String channel, String message);
    void sendSms(String phone, String message);
}

class HealthCheck {
    void register(String name, Supplier<Boolean> check);
    HealthReport status();
}

class AuditLogger {
    void record(String actor, String action, String resource, String result);
}
```

## 6. 測試慣例

- JUnit5,一律針對假實作的**可觀察行為**斷言(例如 `CacheClient.set` 後 `get` 拿得回來、
  `QueueClient.publish` 後訂閱者收到訊息、`SpcAnalyzer` 超出管制界限時回傳 `true`)。
- 不需要 Testcontainers / 真實服務,因為底層全是 in-memory fake。

## 7. Migration 對照速查表

給 migration skill 用:舊語言常見寫法 → 應該轉成哪個 boogie-sdk 呼叫。

| 舊程式碼常見模式 | 對應 boogie-sdk API |
|---|---|
| 自製 XOR / 簡易加密函式 | `sdk.crypto().encryptAes(...)` / `decryptAes(...)` |
| 讀寫 `.ini`(`TIniFile`、`GetPrivateProfileString`) | `sdk.config().get(...)` |
| 直接組 SQL 字串操作 `ADODB.Connection` / `TADOConnection` | `sdk.db().query(...)` / `execute(...)` |
| Socket/TCP 直連機台(`TIdTCPClient`、WinSock) | `sdk.deviceIo().protocolClient()` |
| 用 `TStringList.SaveToFile` 寫純文字 log | `sdk.logger()` |
| `CDO.Message` / Indy SMTP 寄信 | `sdk.notification().sendEmail(...)` |
| `FindFirst`/`FindNext` 輪詢共用資料夾 | `sdk.deviceIo().filePolling()` |
| 手刻 retry/重試迴圈呼叫外部 API | `sdk.http()`(內建 retry/backoff) |
| 全域變數存設定值 | `sdk.config()` |
| `CreateMutex` / 檔案鎖做單例執行保護 | `sdk.scheduler().lock(...)` |
| 手算管制圖界限、異常判定 | `sdk.deviceIo().spcAnalyzer()` |
| Excel COM 自動化(`TExcelApplication`)產報表 | `sdk.deviceIo().reportGenerator()` |
