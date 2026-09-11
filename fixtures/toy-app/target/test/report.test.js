'use strict';

// Behavior source: legacy/report.py, legacy/mathutils.py, legacy/legacycorp_normalize.py
// All expected strings below were captured by actually running the legacy Python
// code (python3 -c "from report import format_report; ...") on 2026-09-12, NOT
// derived by reading/guessing from source. See agent notes for the exact
// commands and raw outputs.

const test = require('node:test');
const assert = require('node:assert/strict');

const { formatReport } = require('../src/report.js');

test('formats a normal name: trims, lowercases, and collapses internal whitespace', () => {
  // Legacy: format_report('  Alice   Smith  ', [1,2,3])
  // -> 'Report for alice smith: average score = 2'
  assert.equal(
    formatReport('  Alice   Smith  ', [1, 2, 3]),
    'Report for alice smith: average score = 2'
  );
});

test('formats an already-normalized-looking name', () => {
  // Legacy: format_report('BOB', [1,2])
  // -> 'Report for bob: average score = 1'
  assert.equal(formatReport('BOB', [1, 2]), 'Report for bob: average score = 1');
});

test('name is None/null: literally embeds the string "None" (legacy f-string behavior, preserved verbatim)', () => {
  // Legacy: format_report(None, [1,2,3])
  // -> 'Report for None: average score = 2'
  // NOTE: this looks like a latent bug (leaking the Python "None" token into
  // user-facing text) but per RULEBOOK#3 the exact legacy string must be
  // preserved as-is; not "fixed" here.
  assert.equal(formatReport(null, [1, 2, 3]), 'Report for None: average score = 2');
});

test('integer division uses floor semantics (rounds toward negative infinity), not truncation', () => {
  // Legacy: format_report('bob', [-1,-2]) -> sum=-3, len=2, -3 // 2 == -2 (floor)
  // -> 'Report for bob: average score = -2'
  // A naive JS `Math.trunc(sum / len)` port would incorrectly yield -1 here.
  assert.equal(formatReport('bob', [-1, -2]), 'Report for bob: average score = -2');

  // Legacy: format_report('x', [-7, 0]) -> sum=-7, len=2, -7 // 2 == -4 (floor)
  // -> 'Report for x: average score = -4'
  // A naive truncating division would incorrectly yield -3 here.
  assert.equal(formatReport('x', [-7, 0]), 'Report for x: average score = -4');
});

test('single-element scores list: average equals the sole element', () => {
  // Legacy: format_report('x', [7]) -> 'Report for x: average score = 7'
  assert.equal(formatReport('x', [7]), 'Report for x: average score = 7');
});
