package com.boogie.sdk.governance;

import com.boogie.sdk.core.RateLimitExceededException;

import java.time.Duration;

/**
 * RateLimiter stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 *
 * <p>Additive constructors beyond the design doc's method-only sketch,
 * needed for the governance test suite (and the existing {@code
 * BoogieSdk.rateLimiter()} facade / {@code BoogieSdkSmokeTest}, which
 * construct every module through a no-arg factory reference) to keep
 * compiling — see RateLimiterTest for the full behavioral conventions
 * these establish, mirroring the already-built Python port's {@code
 * RateLimiter}:
 *
 * <ul>
 *   <li>{@link #RateLimiter(int, Duration)} configures a token bucket
 *       that starts full with {@code maxPerInterval} tokens and refills
 *       back to full once {@code interval} has elapsed since the last
 *       refill (a "full refill after the interval elapses" model, not a
 *       continuous trickle, since the design doc does not specify one).
 *   <li>{@link #RateLimiter()} is a no-arg convenience constructor kept
 *       only so the pre-existing {@code BoogieSdk.rateLimiter()} facade
 *       method (which predates this module having a real configuration
 *       story) still compiles and constructs successfully; it stands in
 *       for an effectively-unconfigured limiter and is not exercised by
 *       RateLimiterTest, which always uses the two-arg constructor.
 * </ul>
 *
 * <p>Unlike the throwing behavioral methods below, neither constructor
 * throws {@link UnsupportedOperationException} — they only store the
 * given configuration — so that merely constructing a {@code RateLimiter}
 * (as the facade and {@code BoogieSdkSmokeTest} already do today) keeps
 * succeeding exactly as it did when the class had only an implicit no-arg
 * constructor.
 *
 * <p>Deliberate deviation from the design doc's "{@code acquire()} 阻塞直到
 * 取得" (blocks until acquired) comment: for fast, deterministic tests this
 * fake instead makes {@code acquire()} raise {@link
 * com.boogie.sdk.core.RateLimitExceededException} immediately when no
 * token is available, rather than blocking — see RateLimiterTest.
 */
public class RateLimiter {

    private final int maxPerInterval;
    private final Duration interval;

    private int tokens;
    private long lastRefillMillis;

    public RateLimiter() {
        this(Integer.MAX_VALUE, Duration.ofDays(1));
    }

    public RateLimiter(int maxPerInterval, Duration interval) {
        this.maxPerInterval = maxPerInterval;
        this.interval = interval;
        this.tokens = maxPerInterval;
        this.lastRefillMillis = System.currentTimeMillis();
    }

    public synchronized boolean tryAcquire() {
        refillIfDue();
        if (tokens > 0) {
            tokens--;
            return true;
        }
        return false;
    }

    public synchronized void acquire() {
        if (!tryAcquire()) {
            throw new RateLimitExceededException("rate limit exceeded");
        }
    }

    private void refillIfDue() {
        long now = System.currentTimeMillis();
        if (now - lastRefillMillis >= interval.toMillis()) {
            tokens = maxPerInterval;
            lastRefillMillis = now;
        }
    }
}
