# boogie-sdk (Python) — 設計文件

## 1. 目的

與 skill `java-template` 底下的 [`boogie-sdk-api.md`](../java-template/boogie-sdk-api.md) 完全對稱:所有「連接 infra」的元件底層都是
**記憶體內假實作(in-memory fake)**,方法簽章、生命週期、例外階層刻意跟 Java 版
一一對應,差別只在命名慣例(snake_case)與語言慣用寫法。目的是讓 migration skill
不管目標語言選 Java 還是 Python,對照邏輯都一致。

- 建置工具:**uv**(單一 package,`src/` layout)
- 套件名稱:`boogie_sdk`(發布名 `boogie-sdk`)
- Python 版本:>= 3.11
- 版本號:`0.1.0`

## 2. 專案結構

實際套件現在 vendor 在 `.claude/skills/python-template/vendor/boogie-sdk-python/`
底下(這份文件本身也在同一個 skill 目錄裡),讓 migration skill 不用另外去
repo 根目錄找:

```
.claude/skills/python-template/vendor/boogie-sdk-python/
├── pyproject.toml
└── src/boogie_sdk/
    ├── __init__.py          # 匯出 BoogieSdk
    ├── sdk.py                # BoogieSdk facade
    ├── config/
    │   ├── config.py          # BoogieConfig
    │   └── config_client.py
    ├── core/                  # 共用例外
    │   ├── errors.py          # PlatformError 及子類
    ├── crypto/
    │   ├── crypto_client.py
    │   ├── secret_client.py
    │   ├── token_client.py
    │   ├── cert_manager.py
    │   └── mask_util.py
    ├── infra/
    │   ├── http_client.py
    │   ├── db_client.py
    │   ├── cache_client.py
    │   ├── queue_client.py
    │   ├── object_storage_client.py
    │   ├── service_discovery_client.py
    │   └── scheduler_client.py
    ├── deviceio/
    │   ├── device_protocol_client.py
    │   ├── file_polling_client.py
    │   ├── flat_file_parser.py
    │   ├── report_generator.py
    │   ├── batch_tracker.py
    │   ├── shift_calendar.py
    │   └── spc_analyzer.py
    ├── observability/
    │   ├── logger.py
    │   ├── metrics_client.py
    │   └── tracer.py
    └── governance/
        ├── id_generator.py
        ├── feature_flag_client.py
        ├── rate_limiter.py
        ├── notification_client.py
        ├── health_check.py
        └── audit_logger.py
└── tests/...                  # pytest,對假實作行為斷言
```

## 3. Facade 與生命週期

```python
from boogie_sdk import BoogieConfig, BoogieSdk

config = BoogieConfig.load()          # 讀 boogie_sdk.yaml + 環境變數
sdk = BoogieSdk.init(config)

sdk.crypto.encrypt_aes(data, key_id="key-1")
sdk.db.query("SELECT ...", params)
sdk.logger.info("done", batch_id=id)

sdk.close()                            # 釋放所有底層假資源
```

Java 版用 `sdk.crypto()`(方法呼叫);Python 版用 `sdk.crypto`(屬性存取,回傳
lazily-constructed 的 client 實例)—— 這是兩語言唯一刻意保留的慣用差異,其餘一致。

## 4. 共用慣例

- **例外階層**:所有例外繼承 `PlatformError`。子類:`CryptoError`、`InfraError`、
  `DeviceIoError`、`ValidationError`、`NotFoundError`、`RateLimitExceededError`。
- **設定**:`BoogieConfig.load()` 讀取 `boogie_sdk.yaml`,環境變數可覆蓋(`BOOGIE_*` 前綴)。
  用 `@dataclass(frozen=True)` 實作,不可變。
- **命名**:client 類別一律 `XxxClient`(工具類例外:`mask_util`、`shift_calendar` 用模組函式)。
- **型別提示**:全面使用 type hints,搭配 `dataclass`/`TypedDict` 描述回傳結構。

## 5. 模組 API 參考

### 5.1 crypto

```python
class CryptoClient:
    def encrypt_aes(self, plaintext: bytes, key_id: str) -> bytes: ...
    def decrypt_aes(self, ciphertext: bytes, key_id: str) -> bytes: ...
    def sign(self, data: bytes, key_id: str) -> bytes: ...
    def verify(self, data: bytes, signature: bytes, key_id: str) -> bool: ...
    def hash(self, data: bytes, algo: HashAlgo) -> bytes: ...   # SHA256, SHA512
    def hmac(self, data: bytes, key_id: str) -> bytes: ...

class SecretClient:
    def get_secret(self, path: str) -> Secret: ...              # 內建 TTL 快取
    def put_secret(self, path: str, data: dict[str, str]) -> None: ...

class TokenClient:
    def issue_token(self, claims: dict) -> str: ...
    def verify_token(self, token: str) -> Claims: ...

class CertManager:
    def load_cert(self, path: Path) -> Certificate: ...
    def get_expiry_date(self, cert_id: str) -> datetime: ...
    def is_rotation_due(self, cert_id: str) -> bool: ...

# mask_util.py — 模組層級函式
def mask_id_number(id_no: str) -> str: ...
def mask_phone(phone: str) -> str: ...
def mask_card_number(card: str) -> str: ...
```

### 5.2 infra

```python
class HttpClient:
    def get(self, url: str, headers: dict | None = None) -> HttpResponse: ...
    def post(self, url: str, body: bytes, headers: dict | None = None) -> HttpResponse: ...
    # 內建 trace-id 注入、retry/backoff、timeout

class DbClient:
    def query(self, sql: str, params: dict | None = None) -> list[Row]: ...
    def execute(self, sql: str, params: dict | None = None) -> int: ...
    def transaction(self, work: Callable[[DbSession], T]) -> T: ...

class CacheClient:
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes, ttl: timedelta) -> None: ...
    def delete(self, key: str) -> None: ...
    def get_or_compute(self, key: str, ttl: timedelta, loader: Callable[[], bytes]) -> bytes: ...

class QueueClient:
    def publish(self, topic: str, message: bytes) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> Subscription: ...

class ObjectStorageClient:
    def upload(self, bucket: str, key: str, data: bytes) -> None: ...
    def download(self, bucket: str, key: str) -> bytes: ...
    def presign_url(self, bucket: str, key: str, ttl: timedelta) -> str: ...

class ServiceDiscoveryClient:
    def resolve(self, service_name: str) -> Endpoint: ...

class SchedulerClient:
    def lock(self, name: str, ttl: timedelta) -> Lock: ...
    def schedule_cron(self, cron_expr: str, task: Callable[[], None]) -> None: ...
```

### 5.3 deviceio

```python
class DeviceProtocolClient:
    def connect(self, endpoint: str) -> None: ...
    def send_command(self, cmd: DeviceCommand) -> None: ...
    def on_event(self, handler: Callable[[DeviceEvent], None]) -> None: ...
    def disconnect(self) -> None: ...

class FilePollingClient:
    def watch(self, directory: Path, pattern: str, handler: Callable[[Path], None]) -> None: ...
    def poll_once(self, directory: Path, pattern: str) -> list[Path]: ...

class FlatFileParser:
    def parse(self, file: Path, schema: RecordSchema[T]) -> list[T]: ...

class ReportGenerator:
    def generate_excel(self, data: list[dict], template: Path, out_file: Path) -> None: ...
    def generate_pdf(self, data: list[dict], template: Path, out_file: Path) -> None: ...

class BatchTracker:
    def create_batch(self, batch_id: str) -> None: ...
    def update_status(self, batch_id: str, status: str) -> None: ...
    def get_history(self, batch_id: str) -> list[BatchEvent]: ...

class ShiftCalendar:
    def current_shift(self, at: datetime) -> Shift: ...
    def boundaries_for(self, day: date) -> ShiftBoundary: ...

class SpcAnalyzer:
    def add_sample(self, value: float) -> None: ...
    def is_out_of_control(self) -> bool: ...
    def control_limits(self) -> ControlLimits: ...
```

### 5.4 observability

```python
class Logger:
    def info(self, msg: str, **fields) -> None: ...
    def warn(self, msg: str, **fields) -> None: ...
    def error(self, msg: str, exc: BaseException | None = None, **fields) -> None: ...

class MetricsClient:
    def counter(self, name: str) -> Counter: ...
    def gauge(self, name: str) -> Gauge: ...
    def timer(self, name: str) -> Timer: ...

class Tracer:
    def start_span(self, name: str) -> Span: ...   # span.end() 結束,或用 with 語法
```

### 5.5 governance

```python
class IdGenerator:
    def next_id(self) -> int: ...                   # Snowflake-style

class FeatureFlagClient:
    def is_enabled(self, flag_key: str, context: dict | None = None) -> bool: ...

class RateLimiter:
    def try_acquire(self) -> bool: ...
    def acquire(self) -> None: ...                   # 阻塞直到取得

class NotificationClient:
    def send_email(self, to: str, subject: str, body: str) -> None: ...
    def send_im(self, channel: str, message: str) -> None: ...
    def send_sms(self, phone: str, message: str) -> None: ...

class HealthCheck:
    def register(self, name: str, check: Callable[[], bool]) -> None: ...
    def status(self) -> HealthReport: ...

class AuditLogger:
    def record(self, actor: str, action: str, resource: str, result: str) -> None: ...
```

## 6. 測試慣例

- pytest,一律針對假實作的**可觀察行為**斷言(例如 `cache_client.set` 後 `get` 拿得回來、
  `queue_client.publish` 後訂閱者收到訊息、`spc_analyzer` 超出管制界限時回傳 `True`)。
- 不需要真實服務或 Docker,底層全是 in-memory fake。

## 7. Migration 對照速查表

與 Java 版共用同一份對照邏輯(舊程式碼型態相同,只是目標語言不同):

| 舊程式碼常見模式 | 對應 boogie-sdk API |
|---|---|
| 自製 XOR / 簡易加密函式 | `sdk.crypto.encrypt_aes(...)` / `decrypt_aes(...)` |
| 讀寫 `.ini`(`TIniFile`、`GetPrivateProfileString`) | `sdk.config.get(...)` |
| 直接組 SQL 字串操作 `ADODB.Connection` / `TADOConnection` | `sdk.db.query(...)` / `execute(...)` |
| Socket/TCP 直連機台(`TIdTCPClient`、WinSock) | `sdk.deviceio.protocol_client()` |
| 用 `TStringList.SaveToFile` 寫純文字 log | `sdk.logger` |
| `CDO.Message` / Indy SMTP 寄信 | `sdk.notification.send_email(...)` |
| `FindFirst`/`FindNext` 輪詢共用資料夾 | `sdk.deviceio.file_polling()` |
| 手刻 retry/重試迴圈呼叫外部 API | `sdk.http`(內建 retry/backoff) |
| 全域變數存設定值 | `sdk.config` |
| `CreateMutex` / 檔案鎖做單例執行保護 | `sdk.scheduler.lock(...)` |
| 手算管制圖界限、異常判定 | `sdk.deviceio.spc_analyzer()` |
| Excel COM 自動化(`TExcelApplication`)產報表 | `sdk.deviceio.report_generator()` |
