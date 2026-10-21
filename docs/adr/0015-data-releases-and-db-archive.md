# ADR-0015: Data release ids and the database archive

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0005 (versions), ADR-0009 (data store), ADR-0014 (swap gate), ADR-0016 (DVC), ADR-0023 (backups) |

## Context

ADR-0009 makes each data release a complete database file, and says history between
patches comes from keeping old files. That raised three questions: what a file is
called, where old files live, and for how long.

Measured on 2026-10-10 (baseline, sections 2.4 and 4):

- A database built from today's objects and all localization strings, with a text
  index, is about 27 MB (9 MB gzipped). With the reference and state tables, about
  30 MB.
- New databases are built for game patches (about 15 a year), for discount weeks
  (about 52 a year, each one a data release under ADR-0017), and for re-runs after a
  fix. About 70 a year, or roughly 2 GB if every one were kept.
- Object storage has a free allowance of 10 GB (ADR-0019). Images and models already
  use about 0.6 GB of it.

A naming problem surfaced while working this out. The original name was
`wrfdb-<version>.sqlite`, where the version is the game build's date, such as
`2026-10-06`. But a discount week or a re-run produces a different database for the
same game version, and the two files would have the same name.

What old databases are for:

1. **Rolling back**: swapping the previous file in. Needs the last few.
2. **History**: comparing one game patch with the next. Needs one good file per patch,
   indefinitely. This data cannot be recovered cheaply later.
3. **Debugging**: looking at exactly what was live. Needs recent files.

## Decision

1. **Every published database has a data release id: `<game version>.<n>`.** `n` counts
   the databases built for that game version: the patch-day build is `2026-10-06.1`,
   the next discount week `2026-10-06.2`, a re-run after a fix `2026-10-06.3`.
2. **The file is named `wrfdb-<release>.sqlite`.** The id is also stored in the
   database's `meta` table and reported by `/data/deploy.json` and `/v1/meta`.
3. **The swap gate's "not older than production" check** compares the game version
   first, then `n`.
4. **Databases are stored in a private object-storage bucket**, separate from the
   public bucket that holds images and models. The API host reads with a read-only
   credential; the pipeline writes with a read-write one.
5. **Retention is set by storage lifecycle rules, per folder:**
   - `dbs/releases/`: every published database and a copy of its `dvc.lock`. Deleted
     automatically after **90 days**.
   - `dbs/patches/`: one database per game patch, **kept indefinitely**. When a new
     game patch is promoted, the outgoing database is copied here (a copy within
     storage, not an upload), so that the last build of each patch is the one kept.
   - Staging: its own location, deleted after 14 days.
6. **The server keeps the current database and the previous two on its own disk**, so
   that a rollback works without object storage or an internet connection.
7. **The archive is not a DVC remote** (ADR-0016).
8. **Old patches are not back-filled.** History before the migration stays in the
   archived Data repository's git history, in the old shape. The archive starts with
   the first patch after cutover.
9. **There is no second copy elsewhere.** The maintainer decided against copying patch
   databases to the backup provider.

Expected storage: about 0.45 GB a year in `patches/`, plus about 0.5 GB in the rolling
90-day window. Within the free allowance for many years.

## Alternatives considered

- **GitHub release assets.** Free and versioned. Rejected: assets on a public
  repository are public, which contradicts "no public dataset" (ADR-0009).
- **The same bucket as the images**, under a folder. Rejected: public access is
  granted per bucket, so the databases would be public too.
- **A DVC remote** in object storage, with the database as a tracked output. It would
  tie each file to a commit. Rejected: files are named by content hash, so they are
  unreadable without DVC; retention is by git commit, not age, so lifecycle rules
  cannot apply; and it risks pushing the whole 25 GB export cache by accident. A named
  file with its lockfile beside it gives the same traceability and stays readable.
- **Keep everything forever.** About 2 GB a year. Rejected as unnecessary: a
  discount-week database differs from its neighbour only in discount rows, and every
  database already contains the full discount history from `state/`.
- **Keep only the last few, no per-patch archive.** Rejected: it gives up patch-to-patch
  history, which cannot be recovered later without re-downloading and re-exporting
  each old game build.
- **A timestamp or a global counter as the id.** Unique and simple. Rejected in favour
  of `<game version>.<n>` because the game version is what people recognise, and the
  id then sorts and reads sensibly.
- **A second copy at the backup provider.** Declined by the maintainer. A patch
  database can in principle be rebuilt from the Steam manifest id, the release tag and
  the lockfile, at the cost of a full download and export.

## Consequences

- Every database that was ever live has a unique name, and what is live can be named
  exactly.
- Rolling back to either of the two previous releases is local and immediate.
- Patch-to-patch history accumulates from cutover onward at negligible cost.
- The only copy of each patch database is in one provider's bucket. Losing that
  account loses the history (though not the ability to rebuild it, slowly).
- The pipeline and the deploy script gain storage housekeeping duties: uploading,
  copying to `patches/`, and pruning local copies.
- Anything that needs the database outside the server needs a credential for a private
  bucket. That includes the Site's build in GitHub Actions (ADR-0019) and any work on
  the workstation (ADR-0008, G-0008-9).

## Gaps and open questions

### G-0015-1. A quiet period can lose a patch database

- **Kind:** design
- **Needed by:** phase 2

Decision 5 copies the outgoing database to `patches/` when the *next* game patch is
promoted, and deletes everything in `releases/` after 90 days. If the game goes more
than 90 days without a patch and without any other data release, the current
database's only stored copy expires before it is ever copied. Recent patches came one
to three weeks apart and discount weeks are weekly, so this would need both to stop.
But if the game is ever wound down, that is exactly when it would happen, and that
last patch is the one most worth keeping.

**Proposed default:** write to `patches/` at every promotion, not at the next patch:
each promoted release overwrites `patches/wrfdb-<game version>.sqlite`. The last build
of a patch is then always the one kept, with no dependence on a later event.

### G-0015-2. Where the counter `n` comes from

- **Kind:** design
- **Needed by:** phase 2

`n` must increase for each database built for a game version and never repeat. The
source of truth is not chosen: the highest existing name in storage, a value in
`state/`, or the previous database's `meta`. It must behave sensibly when a build
fails the gate (is the number reused?), when the same inputs are built twice, and in
staging (ADR-0008, G-0008-6).

### G-0015-3. What a rollback restores

- **Kind:** design
- **Needed by:** phase 3

Decision 6 makes the file available. A complete rollback also has to: redeploy the
Site built against the older database; leave `state/` alone (the build-code registry
and slug history only ever grow, so an older database simply lacks the newest
entries); and stop the next scheduled run from immediately re-promoting the release
that was rolled back. None of this is specified. See ADR-0005, G-0005-4.

### G-0015-4. The claim that a patch database can be rebuilt

- **Kind:** verification
- **Needed by:** not scheduled

Decision 9 rests on being able to rebuild an old database from the Steam manifest id,
the release tag and the lockfile. That depends on things outside the project's
control: Steam continuing to serve old builds to the account, the pinned WRFrontiersDB-CUE4Parse
release remaining downloadable, and the old code still running on a current system.
It has never been tried. One rebuild of a previous patch, done once, would turn the
claim into a fact or show that the single copy is more precious than assumed.

### G-0015-5. Storage rules to confirm at set-up

- **Kind:** verification
- **Needed by:** phase 3

Assumed and not yet checked against the provider's documentation: that lifecycle rules
can target a key prefix with an age in days; that a server-side copy within a bucket
exists and what it costs; and that a bucket with no public domain attached is not
reachable anonymously. Whether staging uses a prefix or its own bucket is G-0008-2.

### G-0015-6. Comparing two archived databases

- **Kind:** design
- **Needed by:** after cutover

The purpose of `patches/` is comparison. `sqldiff` is not installed anywhere yet and
shows whole changed documents, not changed fields (ADR-0009, G-0009-3). The comparison
tool, and the first use for it (a patch-notes page, or a section of the run report),
are not designed. Until one exists the archive is kept on trust.

**Resolved 2026-10-20:** Comparing two archived databases is not needed for now. The
archive is kept for rollback and future use; the comparison tool and its consumers are
recorded as a future idea
([`../future-ideas/field-level-patch-diff.md`](../future-ideas/field-level-patch-diff.md)).

### G-0015-7. Local copies and the stage cache

- **Kind:** design
- **Needed by:** phase 3

The database is also a pipeline stage output (ADR-0016), so a copy sits in the stage
cache, another is the promoted file, and two more are the previous releases. On a
volume with 39 GB free this is small, but which copy is "the" file the services read,
and who deletes what, should be decided in one place so that a cache clean-up cannot
remove the file production is serving.

## References

- `docs/research/2026-10-baseline.md`, sections 2.4 and 4.
- `docs/research/external-facts.md`, "Cloudflare R2".
