'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { add, integerAverage } = require('../src/mathutils.js');

// --- add(a, b) ---
// Behavior observed from legacy/mathutils.py: `add` is a plain `a + b`.

test('add: sums two positive integers', () => {
  assert.strictEqual(add(2, 3), 5);
});

test('add: sums a negative and a positive integer', () => {
  assert.strictEqual(add(-2, 3), 1);
});

test('add: sums floats (observed Python result 5.5 for 2.5 + 3)', () => {
  assert.strictEqual(add(2.5, 3), 5.5);
});

// --- integerAverage(nums) ---
// Behavior observed from legacy/mathutils.py: `integer_average` computes
// `sum(nums) // len(nums)`, i.e. Python floor division of the sum by the count.

test('integerAverage: floors an inexact average down (7/4 -> 1)', () => {
  // Python: sum([1,2,3,4]) // len([1,2,3,4]) == 10 // 4 == 2
  assert.strictEqual(integerAverage([1, 2, 3, 4]), 2);
});

test('integerAverage: returns exact average when evenly divisible', () => {
  // Python: sum([7,7,7]) // 3 == 21 // 3 == 7
  assert.strictEqual(integerAverage([7, 7, 7]), 7);
});

test('integerAverage: single-element list returns that element', () => {
  // Python: sum([10]) // 1 == 10
  assert.strictEqual(integerAverage([10]), 10);
});

test('integerAverage: negative numbers, evenly divisible (-8/2 -> -4)', () => {
  // Python: sum([-7,-1]) // 2 == -8 // 2 == -4
  assert.strictEqual(integerAverage([-7, -1]), -4);
});

test('integerAverage: negative numbers, floors toward -Infinity on remainder (-9/2 -> -5)', () => {
  // Python: sum([-7,-2]) // 2 == -9 // 2 == -5 (floor division, not truncation
  // toward zero: -9/2 truncated would be -4). This is a non-negative-input
  // edge case beyond the documented gap-inventory scope (RULEBOOK#2 only
  // commits to non-negative inputs); Math.floor(a/b) happens to reproduce
  // Python's floor-division result here, so this test doubles as a check
  // that the conversion did not (incorrectly) use truncating division.
  assert.strictEqual(integerAverage([-7, -2]), -5);
});

test('integerAverage: empty list raises an error, mirroring Python ZeroDivisionError', () => {
  // Python: sum([]) // len([]) raises ZeroDivisionError: division by zero.
  // The exact error type/message is not part of the observable contract,
  // only that dividing by zero (empty input) is treated as an error rather
  // than silently returning a value like NaN or Infinity.
  assert.throws(() => integerAverage([]));
});
