#!/usr/bin/env python3
"""Generate the index table in docs/adr/README.md from the ADRs' header tables.

Each ADR's header has a "Status" row and a "Record state" row. A record drafted for
review is `Proposed` / `Draft for maintainer review`; once the maintainer has reviewed
it, it is `Accepted` / `Reviewed`. This script checks the two rows agree, counts how
many of each ADR's gaps are resolved, and rewrites the table between the
`<!-- BEGIN generated: adr index -->` and `<!-- END generated: adr index -->` markers.
The rest of the README is hand-written. Standard library only.

Usually run through tools/docs/build_docs.py, which runs every generator.

Usage:
    python3 tools/docs/gen_adr_index.py           # rewrite the index in docs/adr/README.md
    python3 tools/docs/gen_adr_index.py --check   # exit 1 if it is stale or a header is inconsistent
"""

from __future__ import annotations

import sys

from adr_lib import ADR_DIR, REPO, Adr, Gap, cell, read_adrs, read_gaps

OUT = ADR_DIR / "README.md"
BEGIN = "<!-- BEGIN generated: adr index -->"
END = "<!-- END generated: adr index -->"
DRAFT = "Draft for maintainer review"
REVIEWED = "Reviewed"
REVIEWED_STATUSES = ("Accepted", "Superseded", "Deprecated")


def header_problems(adrs: list[Adr]) -> list[str]:
    problems: list[str] = []
    for adr in adrs:
        if not adr.title:
            problems.append(f"{adr.file}: no '# ADR-{adr.number}: Title' heading")
        if not adr.status:
            problems.append(f"{adr.file}: no 'Status' row")
        if adr.record_state not in (DRAFT, REVIEWED):
            problems.append(f"{adr.file}: record state {adr.record_state!r}; expected {DRAFT!r} or {REVIEWED!r}")
        elif adr.record_state == REVIEWED and not adr.status.startswith(REVIEWED_STATUSES):
            problems.append(f"{adr.file}: reviewed, but status is {adr.status!r}")
        elif adr.record_state == DRAFT and adr.status.startswith("Accepted"):
            problems.append(f"{adr.file}: status is Accepted, but the record is still a draft; use Proposed")
    return problems


def render_index(adrs: list[Adr], gaps: list[Gap]) -> str:
    reviewed = sum(1 for a in adrs if a.record_state == REVIEWED)
    resolved = sum(1 for g in gaps if g.resolved)
    lines = [
        BEGIN,
        "",
        f"Reviewed: {reviewed} of {len(adrs)} ADRs. Questions resolved: {resolved} of {len(gaps)}.",
        "",
        "| ADR | Topic | Status | Reviewed | Questions resolved |",
        "|---|---|---|---|---|",
    ]
    for adr in adrs:
        own = [g for g in gaps if g.adr == adr.number]
        done = sum(1 for g in own if g.resolved)
        state = "Yes" if adr.record_state == REVIEWED else "No"
        lines.append(
            f"| [{adr.number}]({adr.file}) | {cell(adr.title)} | {cell(adr.status)} | {state} | {done} / {len(own)} |"
        )
    lines += ["", END]
    return "\n".join(lines)


def splice(text: str, block: str) -> str | None:
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[:start] + block + text[end + len(END) :]


def main(argv: list[str]) -> int:
    check = "--check" in argv
    adrs = read_adrs()
    gaps, problems = read_gaps()
    problems += header_problems(adrs)
    current = OUT.read_text(encoding="utf-8")
    text = splice(current, render_index(adrs, gaps))
    if text is None:
        problems.append(f"{OUT.relative_to(REPO)}: missing the {BEGIN} / {END} markers")
    for problem in problems:
        print(problem, file=sys.stderr)
    if text is None:
        return 1
    if check:
        if current != text:
            print(f"{OUT.relative_to(REPO)} is stale; run tools/docs/build_docs.py", file=sys.stderr)
            return 1
        return 1 if problems else 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(adrs)} ADRs")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
