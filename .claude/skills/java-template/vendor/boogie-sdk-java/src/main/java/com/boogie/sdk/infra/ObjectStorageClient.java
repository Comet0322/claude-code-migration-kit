package com.boogie.sdk.infra;

import com.boogie.sdk.core.NotFoundException;

import java.net.URI;
import java.time.Duration;
import java.util.AbstractMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ObjectStorageClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 */
public class ObjectStorageClient {

    private final Map<Map.Entry<String, String>, byte[]> store = new ConcurrentHashMap<>();

    private static Map.Entry<String, String> keyFor(String bucket, String key) {
        return new AbstractMap.SimpleImmutableEntry<>(bucket, key);
    }

    public void upload(String bucket, String key, byte[] data) {
        store.put(keyFor(bucket, key), data);
    }

    public byte[] download(String bucket, String key) {
        byte[] data = store.get(keyFor(bucket, key));
        if (data == null) {
            throw new NotFoundException("object not found: bucket=" + bucket + " key=" + key);
        }
        return data;
    }

    public URI presignUrl(String bucket, String key, Duration ttl) {
        return URI.create("https://objects.invalid/" + bucket + "/" + key + "?ttl=" + ttl.getSeconds());
    }
}
