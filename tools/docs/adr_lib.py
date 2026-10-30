"""Shared parsing of the ADRs under docs/adr/, used by the generators in tools/docs/.

Every ADR starts with a header table and lists what it leaves open under headings of
the form

    ### G-NNNN-N. Short title

    - **Kind:** decision | verification | design | action
    - **Needed by:** ...

Standard library only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
ADR_DIR = DOCS / "adr"

ADR_FILE = re.compile(r"^(\d{4})-.+\.md$")
GAP_HEADING = re.compile(r"^### (G-(\d{4})-(\d+))\. (.+)$")
FIELD = re.compile(r"^- \*\*(Kind|Needed by):\*\* (.+)$")
RESOLVED = re.compile(r"^\*\*Resolved (\d{4}-\d{2}-\d{2}):\*\*")
HEADER_ROW = re.compile(r"^\| (Status|Record state) \| (.+) \|$")
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


@dataclass
class Adr:
    number: str
    file: str
    title: str = ""
    status: str = ""
    record_state: str = ""


def adr_paths() -> list[tuple[str, Path]]:
    paths = []
    for path in sorted(ADR_DIR.iterdir()):
        match = ADR_FILE.match(path.name)
        if match:
            paths.append((match.group(1), path))
    return paths


def read_adrs() -> list[Adr]:
    adrs: list[Adr] = []
    for number, path in adr_paths():
        adr = Adr(number, path.name)
        for line in path.read_text(encoding="utf-8").splitlines():
            title = TITLE.match(line)
            if title and not adr.title:
                adr.title = title.group(2)
                continue
            row = HEADER_ROW.match(line)
            if row:
                if row.group(1) == "Status" and not adr.status:
                    adr.status = row.group(2).strip()
                elif row.group(1) == "Record state" and not adr.record_state:
                    adr.record_state = row.group(2).strip()
            if line.startswith("## "):
                break
        adrs.append(adr)
    return adrs


def read_gaps() -> tuple[list[Gap], list[str]]:
    gaps: list[Gap] = []
    problems: list[str] = []
    for adr, path in adr_paths():
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


def cell(text: str) -> str:
    return text.replace("|", "\\|")
