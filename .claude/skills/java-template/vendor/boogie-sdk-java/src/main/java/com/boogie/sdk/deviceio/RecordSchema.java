package com.boogie.sdk.deviceio;

import java.util.Map;

public interface RecordSchema<T> {
    T parseRow(Map<String, String> raw);
}
