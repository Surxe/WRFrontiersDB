#!/usr/bin/env python3
"""Run every documentation generator in tools/docs/.

Regenerates docs/open-questions.md and the index in docs/adr/README.md from the ADRs.
Run it after adding or changing an ADR, a gap, or an ADR's status. Standard library
only.

Usage:
    python3 tools/docs/build_docs.py           # regenerate everything
    python3 tools/docs/build_docs.py --check   # exit 1 if anything is stale or inconsistent
"""

from __future__ import annotations

import sys

import gen_adr_index
import gen_open_questions

GENERATORS = (gen_open_questions, gen_adr_index)


def main(argv: list[str]) -> int:
    failed = [g.__name__ for g in GENERATORS if g.main(argv) != 0]
    if failed:
        print(f"failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
