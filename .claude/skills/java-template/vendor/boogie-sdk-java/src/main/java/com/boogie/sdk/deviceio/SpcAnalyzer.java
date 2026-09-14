package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.ValidationException;

import java.util.ArrayList;
import java.util.List;

/**
 * SpcAnalyzer stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class SpcAnalyzer {

    private final List<Double> samples = new ArrayList<>();

    public void addSample(double value) {
        samples.add(value);
    }

    public boolean isOutOfControl() {
        if (samples.isEmpty()) {
            throw new ValidationException("no samples added");
        }
        ControlLimits limits = controlLimits();
        double latest = samples.get(samples.size() - 1);
        return latest > limits.upper() || latest < limits.lower();
    }

    public ControlLimits controlLimits() {
        if (samples.isEmpty()) {
            throw new ValidationException("no samples added");
        }
        int n = samples.size();
        double mean = samples.stream().mapToDouble(Double::doubleValue).sum() / n;
        double variance = samples.stream()
                .mapToDouble(v -> (v - mean) * (v - mean))
                .sum() / n;
        double stdev = Math.sqrt(variance);
        return new ControlLimits(mean, mean + 3 * stdev, mean - 3 * stdev);
    }
}
