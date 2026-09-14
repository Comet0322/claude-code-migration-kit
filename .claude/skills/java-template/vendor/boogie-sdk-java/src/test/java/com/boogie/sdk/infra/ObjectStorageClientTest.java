package com.boogie.sdk.infra;

import com.boogie.sdk.core.NotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.URI;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for ObjectStorageClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * method shapes):
 *
 * - Backing store: an in-memory map keyed by the pair {@code (bucket,
 *   key)} -> bytes; the same key in two different buckets is stored and
 *   retrieved independently.
 * - {@code download} on a key that was never uploaded throws
 *   {@link NotFoundException}.
 * - {@code presignUrl} returns a deterministic {@link URI} containing the
 *   bucket and key (the exact scheme/query format is an implementation
 *   choice — this file only pins down "bucket and key are recoverable
 *   from the string form" and "same inputs -> same URI", not an exact
 *   string).
 */
class ObjectStorageClientTest {

    private ObjectStorageClient client;

    @BeforeEach
    void setUp() {
        client = new ObjectStorageClient();
    }

    @Test
    void uploadThenDownloadReturnsTheSameBytes() {
        client.upload("bucket", "key", "data".getBytes());
        assertArrayEquals("data".getBytes(), client.download("bucket", "key"));
    }

    @Test
    void downloadOnAMissingKeyThrowsNotFound() {
        assertThrows(NotFoundException.class, () -> client.download("bucket", "missing"));
    }

    @Test
    void uploadOverwritesAnExistingObjectAtTheSameBucketAndKey() {
        client.upload("bucket", "key", "v1".getBytes());
        client.upload("bucket", "key", "v2".getBytes());

        assertArrayEquals("v2".getBytes(), client.download("bucket", "key"));
    }

    @Test
    void theSameKeyInDifferentBucketsIsStoredIndependently() {
        client.upload("bucket-a", "key", "a".getBytes());
        client.upload("bucket-b", "key", "b".getBytes());

        assertArrayEquals("a".getBytes(), client.download("bucket-a", "key"));
        assertArrayEquals("b".getBytes(), client.download("bucket-b", "key"));
    }

    @Test
    void downloadingFromAWrongBucketForAnExistingKeyThrowsNotFound() {
        client.upload("bucket-a", "key", "a".getBytes());
        assertThrows(NotFoundException.class, () -> client.download("bucket-b", "key"));
    }

    @Test
    void presignUrlContainsTheBucketAndKey() {
        URI uri = client.presignUrl("my-bucket", "path/to/file.txt", Duration.ofMinutes(5));

        assertNotNull(uri);
        String asString = uri.toString();
        assertTrue(asString.contains("my-bucket"), () -> "expected bucket in presigned URL: " + asString);
        assertTrue(asString.contains("file.txt"), () -> "expected key in presigned URL: " + asString);
    }

    @Test
    void presignUrlIsDeterministicForTheSameInputs() {
        URI first = client.presignUrl("bucket", "key", Duration.ofMinutes(5));
        URI second = client.presignUrl("bucket", "key", Duration.ofMinutes(5));

        assertEquals(first, second);
    }
}
