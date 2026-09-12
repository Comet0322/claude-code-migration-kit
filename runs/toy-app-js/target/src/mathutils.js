'use strict';

// Ported from legacy/mathutils.py

function add(a, b) {
  return a + b;
}

function integerAverage(nums) {
  // Python: sum(nums) // len(nums) (RULEBOOK#2: // -> Math.floor(a / b),
  // scope limited to non-negative inputs per gap inventory).
  if (nums.length === 0) {
    // Python raises ZeroDivisionError for sum([]) // len([]); mirror that
    // with an explicit throw rather than silently producing NaN.
    throw new Error('integerAverage: division by zero (empty input)');
  }
  const sum = nums.reduce((total, n) => total + n, 0);
  return Math.floor(sum / nums.length);
}

module.exports = { add, integerAverage };
