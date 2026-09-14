package com.boogie.sdk;

import com.boogie.sdk.config.BoogieConfig;
import com.boogie.sdk.config.ConfigClient;
import com.boogie.sdk.crypto.CertManager;
import com.boogie.sdk.crypto.CryptoClient;
import com.boogie.sdk.crypto.SecretClient;
import com.boogie.sdk.crypto.TokenClient;
import com.boogie.sdk.governance.AuditLogger;
import com.boogie.sdk.governance.FeatureFlagClient;
import com.boogie.sdk.governance.HealthCheck;
import com.boogie.sdk.governance.IdGenerator;
import com.boogie.sdk.governance.NotificationClient;
import com.boogie.sdk.governance.RateLimiter;
import com.boogie.sdk.infra.CacheClient;
import com.boogie.sdk.infra.DbClient;
import com.boogie.sdk.infra.HttpClient;
import com.boogie.sdk.infra.ObjectStorageClient;
import com.boogie.sdk.infra.QueueClient;
import com.boogie.sdk.infra.SchedulerClient;
import com.boogie.sdk.infra.ServiceDiscoveryClient;
import com.boogie.sdk.observability.Logger;
import com.boogie.sdk.observability.MetricsClient;
import com.boogie.sdk.observability.Tracer;

/**
 * Single entry point exposing every boogie-sdk module as a lazily-built client.
 * See boogie-sdk-api.md section 3 (Facade 與生命週期).
 *
 * <pre>
 * BoogieConfig config = BoogieConfig.load();
 * BoogieSdk sdk = BoogieSdk.init(config);
 * sdk.crypto().encryptAes(data, "key-1");
 * sdk.close();
 * </pre>
 */
public final class BoogieSdk implements AutoCloseable {
    private final BoogieConfig config;
    private final LazyRegistry registry = new LazyRegistry();

    private BoogieSdk(BoogieConfig config) {
        this.config = config;
    }

    public static BoogieSdk init() {
        return init(null);
    }

    public static BoogieSdk init(BoogieConfig config) {
        return new BoogieSdk(config != null ? config : BoogieConfig.load());
    }

    // -- config ---------------------------------------------------------
    public ConfigClient config() {
        return registry.get("config", () -> new ConfigClient(config));
    }

    // -- crypto -----------------------------------------------------------
    public CryptoClient crypto() {
        return registry.get("crypto", CryptoClient::new);
    }

    public SecretClient secret() {
        return registry.get("secret", SecretClient::new);
    }

    public TokenClient token() {
        return registry.get("token", TokenClient::new);
    }

    public CertManager cert() {
        return registry.get("cert", CertManager::new);
    }

    // -- infra ------------------------------------------------------------
    public HttpClient http() {
        return registry.get("http", HttpClient::new);
    }

    public DbClient db() {
        return registry.get("db", DbClient::new);
    }

    public CacheClient cache() {
        return registry.get("cache", CacheClient::new);
    }

    public QueueClient queue() {
        return registry.get("queue", QueueClient::new);
    }

    public ObjectStorageClient objectStorage() {
        return registry.get("objectStorage", ObjectStorageClient::new);
    }

    public ServiceDiscoveryClient serviceDiscovery() {
        return registry.get("serviceDiscovery", ServiceDiscoveryClient::new);
    }

    public SchedulerClient scheduler() {
        return registry.get("scheduler", SchedulerClient::new);
    }

    // -- deviceio -----------------------------------------------------------
    public DeviceIoNamespace deviceIo() {
        return registry.get("deviceIo", DeviceIoNamespace::new);
    }

    // -- observability ------------------------------------------------------
    public Logger logger() {
        return registry.get("logger", Logger::new);
    }

    public MetricsClient metrics() {
        return registry.get("metrics", MetricsClient::new);
    }

    public Tracer tracer() {
        return registry.get("tracer", Tracer::new);
    }

    // -- governance -----------------------------------------------------------
    public IdGenerator idGenerator() {
        return registry.get("idGenerator", IdGenerator::new);
    }

    public FeatureFlagClient featureFlag() {
        return registry.get("featureFlag", FeatureFlagClient::new);
    }

    public RateLimiter rateLimiter() {
        return registry.get("rateLimiter", RateLimiter::new);
    }

    public NotificationClient notification() {
        return registry.get("notification", NotificationClient::new);
    }

    public HealthCheck health() {
        return registry.get("health", HealthCheck::new);
    }

    public AuditLogger audit() {
        return registry.get("audit", AuditLogger::new);
    }

    @Override
    public void close() {
        registry.clear();
    }
}
