# ADR-0001: Record architecture decisions

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10; this record written 2026-10-12; gaps settled on review, 2026-10-29 |
| Record state | Reviewed |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | every other ADR |

## Context

The rework that produced this repository was designed over several days of
conversation between the maintainer and an AI assistant. About sixty macro-level
decisions came out of it, covering the repository, the database, hosting, deployment,
security and the migration itself. They were kept in a single scratch file outside any
repository, edited in place as decisions changed.

That file worked while the design was moving, but it has three weaknesses as a
permanent record:

1. **It loses reasoning.** When a decision changed, the old text was overwritten. For
   example, a full account-separation design for secrets was proposed, costed and
   rejected in favour of a lighter one. In the scratch file that survives as one
   sentence, kept only because the editor chose to keep it.
2. **It is outside the repository.** A person or an agent starting work in the code has
   no way to find it, and it is not reviewed or versioned with the code it explains.
3. **It mixes decisions with status.** "What we decided and why" sat next to "what is
   still open" and "what was measured", with nothing separating the three.

The maintainer wants the project to hold up over years, with the reasoning preserved
and reviewable, and wants gaps named rather than papered over.

## Decision

1. **Significant decisions are recorded as Architecture Decision Records (ADRs)** in
   `docs/adr/`, as Markdown files named `NNNN-short-title.md`, numbered in the order
   they are added.
2. **One ADR per topic, not per individual choice.** The first set groups the original
   sixty-odd decisions into twenty-five topics. A topic is a set of choices that would
   be reconsidered together.
3. **Every ADR has the same sections**, in this order (see `template.md`):
   - a header table: status, date decided, who decided, related ADRs;
   - **Context**: the situation and the evidence, with dates and methods for anything
     measured;
   - **Decision**: numbered statements of what was decided;
   - **Alternatives considered**: each real alternative and why it was not chosen;
   - **Consequences**: what follows, including the costs that were accepted;
   - **Gaps and open questions**: what is not decided, not verified or not designed
     (see point 6);
   - **References**.
4. **Status values:**
   - `Proposed`: written up but not agreed.
   - `Accepted`: agreed by the maintainer.
   - `Superseded by ADR-NNNN`: replaced by a later ADR.
   - `Deprecated`: no longer applies and nothing replaces it.
5. **An accepted ADR is not rewritten.** When a decision changes, a new ADR is written
   that says what changed and why, and the old ADR's status becomes
   `Superseded by ADR-NNNN`. The old text stays. The only edits allowed to an accepted
   ADR are: its status line, links, typographical fixes, and dated resolution notes
   appended to a gap (point 6).
6. **Gaps are part of the record.** Each ADR lists what it leaves open, under numbered
   headings of the form `G-NNNN-N`. Each gap states its kind (a decision to make, a
   fact to verify, a design to write, or an action to take) and the phase by which it
   must be closed. When a gap is closed, a dated note is appended under it. If closing
   it changes the decision, that goes in a new ADR.
7. **`docs/open-questions.md` lists every gap in one place.** It is generated from the
   ADRs by `tools/docs/gen_open_questions.py` and is never edited by hand.
8. **Supporting documents are separate from ADRs:**
   - `docs/research/` holds evidence: measurements and externally verified facts,
     dated. ADRs cite it. It is a snapshot and is not kept current.
   - `docs/architecture.md` describes the system as it currently is (or is planned to
     be). Unlike an ADR it is edited freely as the system changes.
   - `docs/schema.md` and `docs/migration-plan.md` are working specifications: also
     edited freely, with the reasons for their shape recorded in ADRs.
9. **From now on, a macro-level decision is written as an ADR in the session or pull
   request where it is made.** The scratch file is retired once this first set is
   reviewed and merged.
10. **Facts in an ADR carry their standing**: measured (with date and method), read from
    code, stated by the maintainer, verified against vendor documentation, reported by a
    third party, or assumed. Assumptions are named as assumptions.

## Alternatives considered

- **Keep one living decision log in the repository.** Simple, and it shows the current
  state at a glance. Rejected as the only record because editing in place is exactly
  what destroyed the reasoning in the scratch file. `docs/architecture.md` keeps the
  "current state at a glance" benefit without being the record of why.
- **One ADR per individual decision.** Closer to how some teams use ADRs. Rejected
  because it would produce about sixty short files, most of them meaningless without
  their neighbours (a cache header rule means little without the hosting choice beside
  it).
- **Decisions recorded only in pull-request descriptions and commit messages.** No extra
  files. Rejected because they are hard to find later, cannot hold the alternatives and
  evidence at this length, and the first set of decisions predates any pull request.
- **A wiki or an external document.** Rejected for the same reason as the scratch file:
  it is not versioned or reviewed with the code.
- **An ADR tool (`adr-tools`, Log4brains).** Not needed. Plain Markdown files and one
  small script are enough, and add nothing to install.

## Consequences

- The reasons behind the system, including rejected designs, stay readable in the
  current tree without reading git history.
- A new session, human or AI, can orient itself from `docs/adr/README.md` and
  `docs/architecture.md`.
- Changing a decision costs a new file. That friction is intended: it forces the change
  to be stated.
- The first set was written after the decisions were made, from the scratch file and
  the conversation. Where the write-up adds analysis that was not discussed (most of
  the gaps), it says so. The maintainer has agreed the decisions but has not yet
  reviewed these write-ups; each one is marked "Draft for maintainer review" until that
  happens.
- Two kinds of text now exist that must not be confused: ADRs (stable) and the living
  documents (`architecture.md`, `schema.md`, `migration-plan.md`). The risk is that the
  living documents drift from the ADRs. The rule is that a living document may add
  detail but may not contradict an accepted ADR; a contradiction means a new ADR is
  owed.

## Gaps and open questions

### G-0001-1. How resolved gaps are recorded

- **Kind:** decision
- **Needed by:** before the first gap is closed

Point 6 lets a dated resolution note be appended under a gap in an accepted ADR. That
is a small exception to "accepted ADRs are not rewritten". The alternative is to leave
ADR text untouched and record resolutions only in a separate living file.

**Proposed default:** allow appended notes, as written in point 6. A reader of an ADR
then sees at once which of its gaps are still open.

**Resolved 2026-10-29:** The proposed default is accepted. Resolution notes are
appended under the gap, as point 6 says.

### G-0001-2. Review and acceptance of this first set

- **Kind:** action
- **Needed by:** before phase 0 of the migration

The decisions were agreed in conversation; the write-ups were not. The maintainer
needs to read each ADR, correct anything that misstates a decision, and remove the
"Draft for maintainer review" line. Where a write-up turns out to be wrong about what
was decided, it should be corrected before merge, since nothing has been published yet.

**Resolved 2026-10-29:** Accepted. The review goes one ADR at a time. When the
maintainer has reviewed an ADR, its "Record state" row changes to "Reviewed" (see
`README.md`); the ADRs still marked "Draft for maintainer review" are the ones left.

### G-0001-3. Who may accept an ADR

- **Kind:** decision
- **Needed by:** before the first ADR written by someone other than the maintainer

Today the maintainer is the only decider, and AI sessions draft. The rule is not
written down. If it stays "only the maintainer accepts", an agent must leave new ADRs
as `Proposed`.

**Proposed default:** only the maintainer changes a status to `Accepted`.

**Resolved 2026-10-29:** The proposed default is accepted. Only the maintainer
changes a status to `Accepted`; an ADR drafted by an agent stays `Proposed` until then.

### G-0001-4. Checking the generated question list in CI

- **Kind:** design
- **Needed by:** phase 1 (when CI is set up)

`docs/open-questions.md` is generated. Nothing yet fails when it is stale. A CI step
that regenerates it and fails on a difference would keep it honest. See ADR-0004.

**Resolved 2026-10-29:** Rejected. CI does not check the file. It is regenerated
with `tools/docs/gen_open_questions.py` in the same change as the ADR edit, as is done
today. ADR-0004's G-0004-7 asks for the same check, plus a link check; it is
left open for that ADR's review.

## References

- Michael Nygard, "Documenting Architecture Decisions" (2011), the origin of the format.
- `docs/adr/template.md`.
- `tools/docs/gen_open_questions.py`.
