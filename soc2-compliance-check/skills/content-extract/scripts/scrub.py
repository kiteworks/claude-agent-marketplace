#!/usr/bin/env python3
"""Compatibility entrypoint; truncation requires ownership AND explicit consent.

Canonical source: scratch-foundation, component 1.0.0.
Legacy --path-only invocations fail closed. Truncation is not deletion or erasure.
"""

import sys

from scratch_lifecycle import main

if __name__ == "__main__":
    raise SystemExit(main(["release", "--mode", "truncate", *sys.argv[1:]]))
