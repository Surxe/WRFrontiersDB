#!/usr/bin/env python3
"""Generate docs/open-questions.md from the gaps listed in the ADRs.

Every ADR lists what it leaves open under headings of the form

    ### G-NNNN-N. Short title

    - **Kind:** decision | verification | design | action
    - **Needed by:** ...

This script collects them into one file, and checks that every gap id mentioned
anywhere under docs/ refers to a gap that exists. Standard library only.

Usually run through tools/docs/build_docs.py, which runs every generator.

Usage:
    python3 tools/docs/gen_open_questions.py           # rewrite docs/open-questions.md
    python3 tools/docs/gen_open_questions.py --check   # exit 1 if it is stale or a reference is broken
"""

from __future__ import annotations

import sys

from adr_lib import DOCS, GAP_REF, KINDS, REPO, Gap, cell, read_gaps

OUT = DOCS / "open-questions.md"


def broken_references(known: set[str]) -> list[str]:
    problems: list[str] = []
    for path in sorted(DOCS.rglob("*.md")):
        if path == OUT or path.name == "template.md":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for ref in GAP_REF.findall(line):
                if ref not in known:
                    problems.append(f"{path.relative_to(REPO)}:{number}: {ref} is not defined in any ADR")
    return problems


def render(gaps: list[Gap]) -> str:
    open_gaps = [g for g in gaps if not g.resolved]
    done = [g for g in gaps if g.resolved]
    lines = [
        "# Open questions",
        "",
        "Every gap named in the ADRs, in one place. **This file is generated** by",
        "`tools/docs/build_docs.py` from the \"Gaps and open questions\" section of",
        "each ADR. Do not edit it; edit the ADR and regenerate.",
        "",
        "A gap is one of four kinds:",
        "",
        "- **decision**: the maintainer has to choose;",
        "- **verification**: a fact has to be checked or measured;",
        "- **design**: something has to be worked out and written down;",
        "- **action**: something has to be done.",
        "",
        f"Open: {len(open_gaps)}. Resolved: {len(done)}.",
        "",
        "## Counts",
        "",
        "| Kind | Open |",
        "|---|---|",
    ]
    for kind in KINDS:
        lines.append(f"| {kind} | {sum(1 for g in open_gaps if g.kind == kind)} |")
    lines += ["", "## By ADR", ""]
    current = ""
    for gap in open_gaps:
        if gap.adr != current:
            current = gap.adr
            lines += [
                f"### ADR-{gap.adr}: {gap.adr_title}",
                "",
                "| Gap | Kind | Needed by | Question |",
                "|---|---|---|---|",
            ]
        link = f"[{gap.gap_id}](adr/{gap.adr_file})"
        lines.append(f"| {link} | {gap.kind} | {cell(gap.needed_by)} | {cell(gap.title)} |")
        following = open_gaps[open_gaps.index(gap) + 1 :]
        if not following or following[0].adr != gap.adr:
            lines.append("")
    if done:
        lines += ["## Resolved", "", "| Gap | Resolved | Question |", "|---|---|---|"]
        for gap in done:
            lines.append(f"| [{gap.gap_id}](adr/{gap.adr_file}) | {gap.resolved} | {cell(gap.title)} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    gaps, problems = read_gaps()
    problems += broken_references({g.gap_id for g in gaps})
    for problem in problems:
        print(problem, file=sys.stderr)
    text = render(gaps)
    if check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"{OUT.relative_to(REPO)} is stale; run tools/docs/build_docs.py", file=sys.stderr)
            return 1
        return 1 if problems else 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(gaps)} gaps")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
