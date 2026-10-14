#!/usr/bin/env python3
"""Generate docs/open-questions.md from the gaps listed in the ADRs.

Every ADR lists what it leaves open under headings of the form

    ### G-NNNN-N. Short title

    - **Kind:** decision | verification | design | action
    - **Needed by:** ...

This script collects them into one file, and checks that every gap id mentioned
anywhere under docs/ refers to a gap that exists. Standard library only.

Usage:
    python3 tools/docs/gen_open_questions.py           # rewrite docs/open-questions.md
    python3 tools/docs/gen_open_questions.py --check   # exit 1 if it is stale or a reference is broken
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
ADR_DIR = DOCS / "adr"
OUT = DOCS / "open-questions.md"

ADR_FILE = re.compile(r"^(\d{4})-.+\.md$")
GAP_HEADING = re.compile(r"^### (G-(\d{4})-(\d+))\. (.+)$")
FIELD = re.compile(r"^- \*\*(Kind|Needed by):\*\* (.+)$")
RESOLVED = re.compile(r"^\*\*Resolved (\d{4}-\d{2}-\d{2}):\*\*")
GAP_REF = re.compile(r"\bG-\d{4}-\d+\b")
TITLE = re.compile(r"^# ADR-(\d{4}): (.+)$")
KINDS = ("decision", "verification", "design", "action")


@dataclass
class Gap:
    gap_id: str
    adr: str
    adr_file: str
    adr_title: str
    number: int
    title: str
    kind: str = ""
    needed_by: str = ""
    resolved: str = ""


def read_gaps() -> tuple[list[Gap], list[str]]:
    gaps: list[Gap] = []
    problems: list[str] = []
    for path in sorted(ADR_DIR.iterdir()):
        match = ADR_FILE.match(path.name)
        if not match:
            continue
        adr = match.group(1)
        adr_title = ""
        current: Gap | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            title = TITLE.match(line)
            if title:
                adr_title = title.group(2)
                continue
            heading = GAP_HEADING.match(line)
            if heading:
                if heading.group(2) != adr:
                    problems.append(f"{path.name}: {heading.group(1)} does not match the file's number")
                current = Gap(heading.group(1), adr, path.name, adr_title, int(heading.group(3)), heading.group(4))
                gaps.append(current)
                continue
            if line.startswith("## "):
                current = None
                continue
            if current is None:
                continue
            field = FIELD.match(line)
            if field:
                if field.group(1) == "Kind":
                    current.kind = field.group(2).strip()
                else:
                    current.needed_by = field.group(2).strip()
                continue
            resolved = RESOLVED.match(line)
            if resolved:
                current.resolved = resolved.group(1)
    seen: set[str] = set()
    for gap in gaps:
        if gap.gap_id in seen:
            problems.append(f"{gap.adr_file}: {gap.gap_id} appears twice")
        seen.add(gap.gap_id)
        if gap.kind not in KINDS:
            problems.append(f"{gap.adr_file}: {gap.gap_id} has kind {gap.kind!r}; expected one of {', '.join(KINDS)}")
        if not gap.needed_by:
            problems.append(f"{gap.adr_file}: {gap.gap_id} has no 'Needed by'")
    return gaps, problems


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


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def render(gaps: list[Gap]) -> str:
    open_gaps = [g for g in gaps if not g.resolved]
    done = [g for g in gaps if g.resolved]
    lines = [
        "# Open questions",
        "",
        "Every gap named in the ADRs, in one place. **This file is generated** by",
        "`tools/docs/gen_open_questions.py` from the \"Gaps and open questions\" section of",
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
            print(f"{OUT.relative_to(REPO)} is stale; run tools/docs/gen_open_questions.py", file=sys.stderr)
            return 1
        return 1 if problems else 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(gaps)} gaps")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
