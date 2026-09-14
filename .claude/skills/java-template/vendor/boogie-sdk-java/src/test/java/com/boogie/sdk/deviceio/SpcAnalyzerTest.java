package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.ValidationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for SpcAnalyzer. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>Standard X-bar 3-sigma control limits, with the following conventions
 * invented and pinned down here (the implementer must match them exactly),
 * mirroring the already-built Python port's {@code SpcAnalyzer}:
 *
 * <ul>
 *   <li><b>{@code center}</b> = arithmetic mean of all samples added so
 *       far.
 *   <li><b>Spread = population standard deviation</b> (divide by N, <i>not</i>
 *       N-1) of all samples added so far. {@code upper}/{@code lower} =
 *       {@code center ± 3 * populationStdev}.
 *   <li><b>{@code isOutOfControl()}</b> evaluates the <i>most recently
 *       added</i> sample against control limits computed from <b>all
 *       samples added so far, including that most recent sample itself</b>
 *       (not limits computed from prior samples only — that is a
 *       defensible alternative, but this fake picks "include the current
 *       sample" and documents it here).
 *   <li>A sample exactly equal to {@code upper} or {@code lower} counts as
 *       <b>in control</b> (boundary is inclusive of the control limits;
 *       only strictly outside counts as out of control).
 *   <li><b>Zero samples</b>: both {@code controlLimits()} and {@code
 *       isOutOfControl()} throw {@link ValidationException} — there is no
 *       meaningful center/spread with no data.
 *   <li><b>One sample</b>: {@code controlLimits()} returns a degenerate
 *       result where {@code center == upper == lower == that sample's
 *       value} (population stdev of a single value is 0). {@code
 *       isOutOfControl()} is {@code false} in this case since the single
 *       sample sits exactly on (not outside) its own limits.
 * </ul>
 */
class SpcAnalyzerTest {

    private static final double EPSILON = 1e-6;

    private SpcAnalyzer analyzer;

    @BeforeEach
    void setUp() {
        analyzer = new SpcAnalyzer();
    }

    // -- zero / one sample edge cases ---------------------------------------------

    @Test
    void controlLimitsWithZeroSamplesThrowsValidationException() {
        assertThrows(ValidationException.class, () -> analyzer.controlLimits());
    }

    @Test
    void isOutOfControlWithZeroSamplesThrowsValidationException() {
        assertThrows(ValidationException.class, () -> analyzer.isOutOfControl());
    }

    @Test
    void controlLimitsWithOneSampleIsDegenerate() {
        analyzer.addSample(7.0);

        ControlLimits limits = analyzer.controlLimits();

        assertEquals(7.0, limits.center(), EPSILON);
        assertEquals(7.0, limits.upper(), EPSILON);
        assertEquals(7.0, limits.lower(), EPSILON);
    }

    @Test
    void isOutOfControlWithOneSampleIsFalse() {
        analyzer.addSample(7.0);
        assertFalse(analyzer.isOutOfControl());
    }

    // -- controlLimits: known dataset --------------------------------------------

    @Test
    void controlLimitsForClassicPopulationStdevDataset() {
        // Dataset [2, 4, 4, 4, 5, 5, 7, 9]: mean = 5, population stdev = 2
        // (a well-known textbook example that gives exact integers).
        for (double value : new double[] {2, 4, 4, 4, 5, 5, 7, 9}) {
            analyzer.addSample(value);
        }

        ControlLimits limits = analyzer.controlLimits();

        assertEquals(5.0, limits.center(), EPSILON);
        assertEquals(11.0, limits.upper(), EPSILON);
        assertEquals(-1.0, limits.lower(), EPSILON);
    }

    @Test
    void controlLimitsUpdateAsSamplesAreAdded() {
        analyzer.addSample(10.0);
        analyzer.addSample(10.0);
        ControlLimits firstLimits = analyzer.controlLimits();
        assertEquals(10.0, firstLimits.center(), EPSILON);
        assertEquals(10.0, firstLimits.upper(), EPSILON);
        assertEquals(10.0, firstLimits.lower(), EPSILON);

        analyzer.addSample(20.0);
        ControlLimits secondLimits = analyzer.controlLimits();
        // Adding a different value changes the center and widens the spread.
        assertEquals(40.0 / 3.0, secondLimits.center(), EPSILON);
        assertNotEquals(firstLimits.upper(), secondLimits.upper());
    }

    // -- isOutOfControl ---------------------------------------------------------

    @Test
    void isOutOfControlFalseForIdenticalSamples() {
        for (int i = 0; i < 5; i++) {
            analyzer.addSample(100.0);
        }

        assertFalse(analyzer.isOutOfControl());
    }

    @Test
    void isOutOfControlTrueForClearOutlierAmongStableBaseline() {
        // Ten identical baseline samples, then one outlier. With population
        // stdev computed over all 11 samples (including the outlier itself),
        // this specific baseline size/outlier combination is large enough
        // that the outlier still falls outside its own 3-sigma limits —
        // verified by hand below (mean ~= 104.545, stdev ~= 14.374,
        // upper ~= 147.667).
        for (int i = 0; i < 10; i++) {
            analyzer.addSample(100.0);
        }
        analyzer.addSample(150.0);

        ControlLimits limits = analyzer.controlLimits();
        assertEquals(104.545454545, limits.center(), 1e-6);
        // The Python reference test used a *relative* tolerance here
        // (pytest.approx(147.667364, rel=1e-5), i.e. an absolute delta of
        // roughly 0.0015); the true population-stdev value for this dataset
        // is 147.66742263865973, so an absolute delta of 1e-5 is ~150x too
        // tight and fails against a mathematically correct implementation.
        assertEquals(147.667364, limits.upper(), 1e-3);

        assertTrue(analyzer.isOutOfControl());
    }

    @Test
    void isOutOfControlOnlyReflectsMostRecentlyAddedSample() {
        // After adding the outlier, add one more in-baseline sample: the
        // analyzer should now report false again, because the *latest*
        // sample (back to baseline) is what's being judged, not the
        // earlier outlier.
        for (int i = 0; i < 10; i++) {
            analyzer.addSample(100.0);
        }
        analyzer.addSample(150.0);
        assertTrue(analyzer.isOutOfControl());

        analyzer.addSample(100.0);
        assertFalse(analyzer.isOutOfControl());
    }
}
