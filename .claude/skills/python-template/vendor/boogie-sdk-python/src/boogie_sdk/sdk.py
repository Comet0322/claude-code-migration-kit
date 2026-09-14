"""BoogieSdk: single facade entry point over every boogie_sdk module.

See boogie-sdk-api.md (this skill's library doc) section 3 (Facade 與生命週期).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable, TypeVar

from boogie_sdk.config.config import BoogieConfig
from boogie_sdk.config.config_client import ConfigClient
from boogie_sdk.crypto.cert_manager import CertManager
from boogie_sdk.crypto.crypto_client import CryptoClient
from boogie_sdk.crypto.secret_client import SecretClient
from boogie_sdk.crypto.token_client import TokenClient
from boogie_sdk.deviceio.batch_tracker import BatchTracker
from boogie_sdk.deviceio.device_protocol_client import DeviceProtocolClient
from boogie_sdk.deviceio.file_polling_client import FilePollingClient
from boogie_sdk.deviceio.flat_file_parser import FlatFileParser
from boogie_sdk.deviceio.report_generator import ReportGenerator
from boogie_sdk.deviceio.shift_calendar import ShiftCalendar
from boogie_sdk.deviceio.spc_analyzer import SpcAnalyzer
from boogie_sdk.governance.audit_logger import AuditLogger
from boogie_sdk.governance.feature_flag_client import FeatureFlagClient
from boogie_sdk.governance.health_check import HealthCheck
from boogie_sdk.governance.id_generator import IdGenerator
from boogie_sdk.governance.notification_client import NotificationClient
from boogie_sdk.governance.rate_limiter import RateLimiter
from boogie_sdk.infra.cache_client import CacheClient
from boogie_sdk.infra.db_client import DbClient
from boogie_sdk.infra.http_client import HttpClient
from boogie_sdk.infra.object_storage_client import ObjectStorageClient
from boogie_sdk.infra.queue_client import QueueClient
from boogie_sdk.infra.scheduler_client import SchedulerClient
from boogie_sdk.infra.service_discovery_client import ServiceDiscoveryClient
from boogie_sdk.observability.logger import Logger
from boogie_sdk.observability.metrics_client import MetricsClient
from boogie_sdk.observability.tracer import Tracer

T = TypeVar("T")


class _LazyRegistry:
    """Shared lazy-singleton cache used by BoogieSdk and its sub-namespaces."""

    def __init__(self) -> None:
        self._instances: dict[str, Any] = {}

    def get(self, key: str, factory: Callable[[], T]) -> T:
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    def clear(self) -> None:
        self._instances.clear()


class _DeviceIoNamespace(_LazyRegistry):
    """Groups the deviceio module's several clients under `sdk.deviceio.*()`."""

    def protocol_client(self) -> DeviceProtocolClient:
        return self.get("protocol_client", DeviceProtocolClient)

    def file_polling(self) -> FilePollingClient:
        return self.get("file_polling", FilePollingClient)

    def flat_file_parser(self) -> FlatFileParser:
        return self.get("flat_file_parser", FlatFileParser)

    def report_generator(self) -> ReportGenerator:
        return self.get("report_generator", ReportGenerator)

    def batch_tracker(self) -> BatchTracker:
        return self.get("batch_tracker", BatchTracker)

    def shift_calendar(self) -> ShiftCalendar:
        return self.get("shift_calendar", ShiftCalendar)

    def spc_analyzer(self) -> SpcAnalyzer:
        return self.get("spc_analyzer", SpcAnalyzer)


class BoogieSdk(_LazyRegistry):
    """Single entry point exposing every boogie_sdk module as a lazily-built client.

    Usage::

        config = BoogieConfig.load()
        sdk = BoogieSdk.init(config)
        sdk.crypto.encrypt_aes(data, key_id="key-1")
        sdk.close()
    """

    def __init__(self, config: BoogieConfig):
        super().__init__()
        self._config = config

    @classmethod
    def init(cls, config: BoogieConfig | None = None) -> "BoogieSdk":
        return cls(config or BoogieConfig.load())

    # -- config ---------------------------------------------------------
    @property
    def config(self) -> ConfigClient:
        return self.get("config", lambda: ConfigClient(self._config))

    # -- crypto -----------------------------------------------------------
    @property
    def crypto(self) -> CryptoClient:
        return self.get("crypto", CryptoClient)

    @property
    def secret(self) -> SecretClient:
        return self.get("secret", SecretClient)

    @property
    def token(self) -> TokenClient:
        return self.get("token", TokenClient)

    @property
    def cert(self) -> CertManager:
        return self.get("cert", CertManager)

    # -- infra ------------------------------------------------------------
    @property
    def http(self) -> HttpClient:
        return self.get("http", HttpClient)

    @property
    def db(self) -> DbClient:
        return self.get("db", DbClient)

    @property
    def cache(self) -> CacheClient:
        return self.get("cache", CacheClient)

    @property
    def queue(self) -> QueueClient:
        return self.get("queue", QueueClient)

    @property
    def object_storage(self) -> ObjectStorageClient:
        return self.get("object_storage", ObjectStorageClient)

    @property
    def service_discovery(self) -> ServiceDiscoveryClient:
        return self.get("service_discovery", ServiceDiscoveryClient)

    @property
    def scheduler(self) -> SchedulerClient:
        return self.get("scheduler", SchedulerClient)

    # -- deviceio -----------------------------------------------------------
    @property
    def deviceio(self) -> _DeviceIoNamespace:
        return self.get("deviceio", _DeviceIoNamespace)

    # -- observability ------------------------------------------------------
    @property
    def logger(self) -> Logger:
        return self.get("logger", Logger)

    @property
    def metrics(self) -> MetricsClient:
        return self.get("metrics", MetricsClient)

    @property
    def tracer(self) -> Tracer:
        return self.get("tracer", Tracer)

    # -- governance -----------------------------------------------------------
    @property
    def id_generator(self) -> IdGenerator:
        return self.get("id_generator", IdGenerator)

    @property
    def feature_flag(self) -> FeatureFlagClient:
        return self.get("feature_flag", FeatureFlagClient)

    @property
    def rate_limiter(self) -> RateLimiter:
        return self.get(
            "rate_limiter",
            lambda: RateLimiter(max_per_interval=100, interval=timedelta(seconds=1)),
        )

    @property
    def notification(self) -> NotificationClient:
        return self.get("notification", NotificationClient)

    @property
    def health(self) -> HealthCheck:
        return self.get("health", HealthCheck)

    @property
    def audit(self) -> AuditLogger:
        return self.get("audit", AuditLogger)

    def close(self) -> None:
        self.clear()
