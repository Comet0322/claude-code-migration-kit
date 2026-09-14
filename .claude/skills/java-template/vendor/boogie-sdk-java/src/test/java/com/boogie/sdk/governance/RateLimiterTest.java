package com.boogie.sdk.governance;

import com.boogie.sdk.core.RateLimitExceededException;
import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for RateLimiter. See boogie-sdk-api.md section 5.5 (governance).
 *
 * <p>The design doc's method-only sketch ({@code boolean tryAcquire()},
 * {@code void acquire()} // 阻塞直到取得 / "blocks until acquired") gives no
 * constructor and no rate configuration, which isn't testable as-is. This
 * test file pins down the additive, testable conventions invented to make
 * the fake meaningful, mirroring the already-built Python port's {@code
 * RateLimiter}:
 *
 * <ul>
 *   <li><b>Constructor (additive, not in the design doc):</b> {@code
 *       RateLimiter(int maxPerInterval, Duration interval)}, a simple
 *       token bucket that starts full with {@code maxPerInterval} tokens
 *       and refills back to full once {@code interval} has elapsed since
 *       the last refill (a "full refill after the interval elapses"
 *       model, not a continuous trickle, since the design doc does not
 *       specify one).
 *   <li><b>Time source:</b> unlike the Python port (which injects a
 *       {@code Callable[[], float]} clock for deterministic refill
 *       tests), this Java fake does NOT add a clock-injection seam. To
 *       stay consistent with this codebase's existing Java convention for
 *       timing-sensitive fakes (see {@code CacheClientTest}'s TTL tests,
 *       which use a short real TTL plus a short real sleep rather than a
 *       clock seam), refill here is tested with a short real {@code
 *       interval} (tens of milliseconds) plus a short real {@code
 *       Thread.sleep}. This keeps the whole suite comfortably under the
 *       1-second budget while avoiding a testing-only constructor
 *       overload.
 *   <li><b>{@code tryAcquire()}:</b> returns {@code true} and consumes one
 *       token while tokens remain; returns {@code false} (never throws)
 *       once the bucket is empty.
 *   <li><b>{@code acquire()} blocking convention:</b> the design doc's
 *       "阻塞直到取得" (block until acquired) conflicts with fast,
 *       deterministic tests. This fake instead adopts the convention that
 *       {@code acquire()} throws {@link RateLimitExceededException}
 *       immediately if no token is currently available, rather than
 *       sleeping/blocking. When a token is available it behaves like
 *       {@code tryAcquire()} (consumes one token) and returns normally.
 *       This is a deliberate deviation for this fake; the implementer
 *       should follow this test file's behavior exactly.
 * </ul>
 *
 * <p>The constructor, {@code tryAcquire()}, and {@code acquire()}
 * currently throw {@link UnsupportedOperationException} (skeleton stage)
 * — every test below is expected to fail with that exception until the
 * `implementer` stage fills in real bodies; that failure mode is
 * expected/fine per the TDD pipeline.
 */
class RateLimiterTest {

    // -- tryAcquire --------------------------------------------------------

    @Test
    void tryAcquireReturnsTrueWhileTokensRemain() {
        RateLimiter limiter = new RateLimiter(2, Duration.ofSeconds(30));

        assertTrue(limiter.tryAcquire());
        assertTrue(limiter.tryAcquire());
    }

    @Test
    void tryAcquireReturnsFalseOnceExhausted() {
        RateLimiter limiter = new RateLimiter(2, Duration.ofSeconds(30));

        limiter.tryAcquire();
        limiter.tryAcquire();

        assertFalse(limiter.tryAcquire());
    }

    @Test
    void tryAcquireNeverThrowsWhenExhausted() {
        RateLimiter limiter = new RateLimiter(1, Duration.ofSeconds(30));

        limiter.tryAcquire();
        for (int i = 0; i < 5; i++) {
            assertFalse(limiter.tryAcquire());
        }
    }

    // -- acquire -------------------------------------------------------------

    @Test
    void acquireDoesNotThrowWhenATokenIsAvailable() {
        RateLimiter limiter = new RateLimiter(1, Duration.ofSeconds(30));

        limiter.acquire();
    }

    @Test
    void acquireThrowsRateLimitExceededWhenBucketIsEmpty() {
        RateLimiter limiter = new RateLimiter(1, Duration.ofSeconds(30));

        limiter.acquire();

        assertThrows(RateLimitExceededException.class, limiter::acquire);
    }

    @Test
    void acquireConsumesATokenLikeTryAcquire() {
        RateLimiter limiter = new RateLimiter(2, Duration.ofSeconds(30));

        limiter.acquire();
        assertTrue(limiter.tryAcquire());
        assertFalse(limiter.tryAcquire());
    }

    // -- refill over real elapsed time ----------------------------------------

    @Test
    void tokensRefillAfterIntervalElapses() throws InterruptedException {
        RateLimiter limiter = new RateLimiter(2, Duration.ofMillis(20));

        limiter.tryAcquire();
        limiter.tryAcquire();
        assertFalse(limiter.tryAcquire());

        Thread.sleep(60);

        assertTrue(limiter.tryAcquire());
    }

    @Test
    void tokensDoNotRefillBeforeIntervalElapses() {
        RateLimiter limiter = new RateLimiter(1, Duration.ofSeconds(30));

        limiter.tryAcquire();

        assertFalse(limiter.tryAcquire());
    }

    @Test
    void refillDoesNotExceedMaxPerInterval() throws InterruptedException {
        RateLimiter limiter = new RateLimiter(2, Duration.ofMillis(20));

        // Consume only one token, then let plenty of time pass.
        limiter.tryAcquire();
        Thread.sleep(60);

        // Bucket should be capped back at maxPerInterval (2), not unbounded.
        assertTrue(limiter.tryAcquire());
        assertTrue(limiter.tryAcquire());
        assertFalse(limiter.tryAcquire());
    }

    @Test
    void acquireSucceedsAgainAfterRefill() throws InterruptedException {
        RateLimiter limiter = new RateLimiter(1, Duration.ofMillis(20));

        limiter.acquire();
        assertThrows(RateLimitExceededException.class, limiter::acquire);

        Thread.sleep(60);

        limiter.acquire(); // must not throw now that the bucket refilled
    }
}
