# Simulated internal shared library ("legacycorp" private package).
# This module is NOT meant to be translated line-by-line during migration —
# see the domain skill's replacement rule for what the new language must do
# instead of porting this implementation.

def normalize_name(s):
    return " ".join(s.strip().lower().split())
