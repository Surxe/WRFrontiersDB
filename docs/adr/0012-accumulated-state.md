# ADR-0012: Accumulated state lives in git

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-08 (`state/` directory), 2026-10-10 (slug history, discounts, news, commit order) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0009 (data store), ADR-0013 (slugs), ADR-0014 (swap gate), ADR-0016 (DVC), ADR-0017 (discounts) |

## Context

ADR-0009 rebuilds the database from scratch on every release. Most of what goes into
it can be rebuilt from the current game files. Some of it cannot: it has accumulated
over time, and the game files no longer contain it. If it were kept only in the
database, the first rebuild would erase it.

What accumulates today, and where it lives (baseline, sections 2 and 4):

| Data | Where today | Why it cannot be rebuilt |
|---|---|---|
| Build-code registry | Data repo `index/build_codes.json` | short build links stay valid only if the registry grows at the end and never reorders |
| Robot release dates | Data repo `index/robot_release_dates.json` | the date a robot first appeared is known only from having seen it appear; some entries are typed in by hand from news posts |
| Patch manifests | Data repo `index/patch_manifests.json` | built up from the update probe's record of each Steam build |
| Mapped discount weeks | DV repo `archive/discounts/` (59 weeks) | announcements are free text; the mapping to object ids was done at the time and cannot be reliably redone |
| News posts | News-Scraper repo `archive/` (298 posts) | scraped over time; the source may change or disappear |
| Slug history | does not exist yet | old page addresses are forgotten the moment a name changes (ADR-0013) |

Other files in the Data repository's `index/` are different in kind. The slug map,
nicknames and aliases are derived from the current data each run. Abbreviations are a
hand-curated table inside the code.

Today the pipeline writes accumulated data by committing to the Data and DV
repositories. Both are going away.

## Decision

1. **Accumulated state lives in a checked-in `state/` directory at the root of this
   repository, as JSON.** It is loaded into its own tables on every database build
   (ADR-0010). The database is never its only home.
2. **Contents:**
   - the build-code registry;
   - robot release dates;
   - patch manifests;
   - `state/slugs.json`: each object's current slug and its previous slugs (ADR-0013);
   - `state/discounts/<week>.json`: mapped discount weeks, stored as object ids
     (ADR-0017);
   - `state/news/`: the scraped news posts, kept as provenance.
3. **Data, not code, lives in `state/`.** A new discount week or news post must not look
   like a code change to CI path filters or to the pipeline's stage cache (ADR-0003).
4. **The pipeline commits `state/` as part of each data release**, together with the
   pipeline lockfile `dvc.lock` (ADR-0016). The order is fixed by ADR-0014: build the
   candidate database, run the checks, upload the candidate, build the Site against it,
   **then commit**, then promote. A failure before the commit changes nothing.
5. **Operational state is not accumulated state and stays out of git.** The discount
   watch's "what have I already seen" file and the update probe's own state live in the
   pipeline's working directory on the server.
6. **The DV's name-pin file (`manual_mapping.json`) goes away.** Its job moves into the
   shared name matcher (ADR-0017). The full extent of what it does is to be confirmed
   when that is implemented.
7. **Existing state is brought over by a re-runnable import**, once early for
   development and once more at cutover to pick up what the old pipeline added in the
   meantime (ADR-0025).

## Alternatives considered

- **Keep accumulated state in the database and carry it forward**: each build reads
  the previous database's state tables. Rejected: it turns the "rebuilt from scratch"
  file into one with a lineage. A corrupted or skipped build would break the chain,
  and state would have no reviewable history.
- **Object storage** (a JSON file per item in a bucket). Rejected: no history, no
  review, no diff, and a second place to back up.
- **A separate small repository for state.** It would keep data commits out of the
  code history entirely. Not chosen; the decision places `state/` in this repository.
  It is listed again under G-0012-1 because the open problems there are exactly the
  ones a separate repository avoids.
- **Keep the old repositories alive just for state.** Rejected: that keeps the
  multi-repository coupling the rework exists to remove.

## Consequences

- Every piece of irreplaceable project data is in git: it has history, it can be
  reviewed and corrected by hand, and it is copied wherever the repository is cloned.
  This is also why WRF needs no off-site backup of its own (ADR-0023).
- The database stays disposable. Any database can be rebuilt from game files plus
  `state/` at the matching commit.
- The repository's history now includes machine-made commits: about 65 a year (one per
  patch and per discount week), plus re-runs.
- The pipeline needs write access to this repository from the server, which is a
  credential to manage (ADR-0022) and a new way for a pipeline bug to damage something
  permanent.
- Hand-edited state (a release date typed in from a news post, a corrected discount
  mapping) and machine-written state share the same files.

## Gaps and open questions

### G-0012-1. Which branch the pipeline commits to, and which state it reads

- **Kind:** decision
- **Needed by:** phase 2; this blocks the pipeline design

This is the most important open question in the data path. Three decisions pull
against each other:

- the pipeline runs the code of the deployed release tag, never `main` (ADR-0005);
- the pipeline reads `state/`, changes it and commits it (this ADR);
- `main` is protected and requires checks (ADR-0004).

A tag is a fixed commit. If the pipeline works in a checkout of the tag, it reads the
state as it was when the tag was made, not the state as last written, and a commit made
on top of a tag belongs to no branch. So code and state have to come from different
places: code from the tag, state from wherever the latest state is. And the commit has
to go somewhere that exists, can accept it, and can be read again by the next run.

Options:

1. **State on `main`.** The pipeline uses the tag's code (from the image) and a
   separate checkout of `main` containing only `state/`. It commits there and pushes to
   `main`, retrying on top of any new commits. It needs permission to bypass branch
   protection, and each push triggers CI (which the path filter can reduce to almost
   nothing).
2. **State on a dedicated branch** that only the pipeline writes to, for example
   `data-releases`. `main` stays protected and human-only. Code releases never touch
   it. Hand corrections to state become pull requests against that branch. The
   `state/` directory on `main` would then be either absent or a stale copy, which
   contradicts the layout in ADR-0003 unless stated.
3. **State in a separate repository.** Same properties as option 2 with a harder
   boundary and one more repository.

Whichever is chosen also decides G-0012-2, G-0008-3 (what staging does) and
G-0004-5 (what CI does on a state commit).

### G-0012-2. What a committed `dvc.lock` means

- **Kind:** design
- **Needed by:** phase 2

`dvc.lock` records the hashes of each stage's inputs, including the code folders, as
they were at the release tag the pipeline ran. Committed to `main`, where the code may
have moved on, it describes a different commit's code. Anyone running a status check
on `main` would see every stage reported as changed, and a developer's own pipeline
run would rewrite the file. The maintainer considers keeping this file important as
the record of what produced each database. Options: commit it only where the state is
committed (G-0012-1, options 2 or 3); or store each release's lockfile as a plain,
named file (`state/releases/<release>.dvc.lock`) so that it is a record and not a live
DVC file. A copy is uploaded next to each database in any case (ADR-0015).

### G-0012-3. Two writers

- **Kind:** design
- **Needed by:** phase 2

A person corrects a release date while a discount week is being committed by the
pipeline. With one writer at a time per file this is a normal rebase; with both editing
the same JSON file it is a conflict the pipeline has to handle unattended. The pipeline
should make the smallest possible edits (one file per discount week already helps),
and needs a defined behaviour when its push is rejected.

### G-0012-4. State written by one release and read by another

- **Kind:** design
- **Needed by:** phase 2

State outlives code. A file written by release A will be read by release B, and after
a rollback by A again. Each state file therefore needs a format version, and a rule for
what a reader does with a newer format than it knows.

### G-0012-5. Which existing files are state

- **Kind:** design
- **Needed by:** phase 2 (the import)

The table in the Context is the assistant's classification from reading the code. To
confirm for each file in the Data repository's `index/`, the Orchestrator's `data/`
directory, the DV repository and the scraper: accumulated (goes to `state/`), derived
(rebuilt by `db-build`), curated in code (stays in a package), or operational (stays on
the server). Known unclear cases:

- the update probe's registry of Steam build to version id, which feeds patch
  manifests: is the manifest file enough, or is the registry itself state?
- hand-entered pending robot entries inside the release-dates file;
- the DV's prediction accuracy history and per-week prediction history, which the
  prediction builder appends to on each run. If the prediction formula changes, old
  rows cannot be regenerated as they were.

### G-0012-6. Committed state that never went live

- **Kind:** design
- **Needed by:** phase 2

Decision 4 commits after the checks and before promotion. If promotion then fails,
the committed state describes a release that is not live. For grow-only data that is
harmless, but the next run must not treat that release as published. The commit could
record its outcome, or promotion could be made safe to retry until it succeeds.

**Resolved 2026-10-20:** Both, as decided in ADR-0014, G-0014-2: promotion is
idempotent and retried until it succeeds, and the pipeline records each promotion's
outcome outside git, so the next run knows whether the last committed release is live.

### G-0012-7. Reviewing what the pipeline commits

- **Kind:** decision
- **Needed by:** after cutover

Machine-made commits to permanent state are unreviewed by design. The swap gate checks
some of it (the build-code registry only grows, slug history is consistent). Whether
anything else should be checked, or summarised in the run report, is open.

### G-0012-8. The probe marks a patch handled when the run starts

- **Kind:** design
- **Needed by:** cutover

The update probe saves a patch as handled once its hand-off command exits 0
(Orchestrator `src/probe.py`, `main`). On the server that command is
`systemctl start --no-block wrf-orchestrator@{version}.service`, which returns once the
job is queued. So the patch is recorded as handled when the run starts, not when it
finishes. A run that fails, or is cut off by a power cut or a reboot (G-0006-7), is
not retried. Nothing reports it, either, unless the run itself sends an email. Options:
advance the probe's state only when the run succeeds (the run writes the state, or
the probe checks the run's last outcome); or keep the current behaviour, and have the
boot report or the run report name any patch that has no successful run.

## References

- `docs/research/2026-10-baseline.md`, sections 2 and 4.
- The Data repository's `docs/build-codes.md` for the registry's growth rule.
