'use strict';

// Ported from legacy/report.py

const { integerAverage } = require('./mathutils.js');

// RULEBOOK#1: legacycorp_normalize.normalize_name has no target module and
// must not be imported anywhere. Call sites inline the replacement instead.
function formatReport(name, scores) {
  const displayName = name !== null ? name.trim().toLowerCase().replace(/\s+/g, ' ') : null;
  const avg = integerAverage(scores);
  // RULEBOOK#3: when name is None/null, the legacy f-string embeds the
  // literal string "None" verbatim. Preserved bug-for-bug, not "fixed".
  const displayText = displayName === null ? 'None' : displayName;
  return `Report for ${displayText}: average score = ${avg}`;
}

module.exports = { formatReport };
