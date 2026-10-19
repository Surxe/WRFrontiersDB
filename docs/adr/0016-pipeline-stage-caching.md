# ADR-0016: Pipeline stage caching with DVC

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 (DVC, shared cache, lockfile kept), 2026-10-12 (lockfile dependency, Steam download, dated folders) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0005 (releases), ADR-0007 (deployment), ADR-0008 (environments), ADR-0012 (state), ADR-0014 (swap gate) |

## Context

The pipeline is a chain: download the game, dump a mapping file by launching the game,
export assets to JSON, parse, convert images, build the database. The early stages are
slow and demanding: on the last patch day the export stage took about 8 minutes of a
14-minute run, launches the game, and needs a GPU (baseline, section 2.5; the old
unit's timeout allows for 30 minutes or more). The late stages take seconds to
minutes.

Most runs do not need most stages:

- A discount week changes only discount data. Nothing before the database build needs
  to run.
- A Parser fix needs parse and everything after it, but not the download or export.
- A staging run of a branch that did not touch the Exporter should reuse production's
  export.

Today this is controlled by hand, with `SHOULD_*` flags on the Orchestrator's command
line and "does the output already exist" checks inside stages (baseline, section 2).
The operator has to know which stages a change affects. Getting it wrong means either a
needless export or, worse, a stale stage output silently reused.

Outputs are kept in dated folders (`exports/2026-10-06/`), with the two most recent
kept (baseline, section 3.2).

The maintainer wanted re-running to be decided by a chain of content hashes, and asked
for an existing tool to do it, not something built in-house.

## Decision

1. **DVC (Data Version Control) decides which stages run.** Stages are declared in
   `dvc.yaml`, each with its command, its dependencies (code folders, upstream outputs,
   parameters) and its outputs. `dvc repro` re-runs only the stages whose inputs
   changed.
2. **Stages** (to be finalised at implementation): Steam download, export, parse
   (including textures), image conversion, database build. Whether the Site build is a
   stage was left open.
3. **Dependencies:**
   - code: the stage's own `apps/<stage>/src` folder and the packages it uses. Folders
     are hashed whole, so any change in them re-runs the stage, even a comment. This
     was accepted. Pointing at `src` and not the app folder keeps README edits from
     triggering runs.
   - `uv.lock`: a dependency of the stages, so a library change re-runs them. Because
     every Python dependency is pinned exactly (ADR-0003), the lockfile only changes
     on a deliberate upgrade.
   - parameters in `params.yaml`: the Steam manifest id, the WRFrontiersDB-CUE4Parse release,
     stage options.
4. **One cache is shared by production and staging.** A branch that has not changed a
   stage gets production's output for it from the cache. A branch that has changed it
   runs it once, after which that result is reusable too. This replaces the manual
   `SHOULD_EXPORT=false`.
5. **Files are shared between the working folders and the cache by hard link**, so
   nothing is stored twice. The data volume's file system has no copy-on-write. The
   rule that follows: **a stage must never edit an existing output in place.**
6. **`dvc.lock` is kept as the record of what produced each output.** It is committed
   with `state/` in each data-release commit (ADR-0012), and a copy is uploaded next to
   each published database (ADR-0015). The maintainer considers this record important.
7. **The Steam download folder is not tracked by DVC. Only its marker file is.**
   - The folder is 15 GB, almost all of it one 12 GB file, and DepotDownloader patches
     it in place: the 2026-10-06 patch downloaded 742 MB.
   - Tracking it normally would delete it before each run (forcing a full download),
     replace its files with read-only links into the cache (which in-place patching
     would either fail on or corrupt), and add about 12 GB to the cache per patch.
   - So the download stage's parameter is the manifest id and its only declared output
     is `manifest.txt`, which the Exporter writes after a successful download. That
     output is marked `persist: true` and `cache: false`.
   - The export stage depends on `manifest.txt`.
   - A Steam manifest id already identifies an exact set of files, so the lockfile
     still records precisely which game build produced a database.
   - The download stage only ever runs when the manifest id changes: on patch days.
8. **Dated output folders go away.** Each stage writes to one fixed path. Older
   versions live in the cache. "Keep the two most recent" becomes a cache clean-up
   rule, to be worked out at implementation: keep what production currently uses plus
   the N most recent.
9. **Escape hatches:** a force flag to re-run a stage regardless, and a parameter that
   can be bumped to invalidate the cache if an input turns out to have been missed.
10. **The archive of databases is not a DVC remote** (ADR-0015). A remote may be added
    later to share the cache with a rented server.
11. **Replacing the Orchestrator with a workflow system (Dagster) is a separate, later
    question.** DVC decides what runs; the Orchestrator still watches for patches,
    runs the gate, promotes and reports.

## Alternatives considered

- **Build the hashing in-house.** Full control and no new dependency. Rejected by the
  maintainer in favour of an existing tool: the hard parts (hashing directories,
  storing outputs by content, restoring them, knowing what is stale) are exactly what
  such tools already do.
- **`make`.** Decides by file timestamps, not content. Rejected: timestamps do not
  survive checkouts, and it cannot store and restore outputs.
- **Snakemake, Nextflow and similar workflow tools.** Capable, but centred on
  scheduling many jobs. Not evaluated in depth. DVC was chosen for its content-keyed
  cache of outputs and its lockfile, which match the two things wanted here.
- **Dagster or another orchestrator** to replace the whole Orchestrator. Recorded as a
  separate later evaluation; too much change at once with the rest of the migration.
- **Keep the flags and the dated folders.** Rejected: they depend on the operator
  knowing what changed.
- **Track the Steam download folder normally**, or with `persist` and no cache on the
  whole folder. Rejected for the reasons in decision 7; the second variant would still
  hash 15 GB after every patch to learn what the manifest id already says.

## Consequences

- What runs is decided by what changed. A discount week costs a database build; a
  Parser fix skips the export; staging pays only for the stages a branch touched.
- Every database has a machine-written record of the exact inputs behind it.
- The pipeline now has a new core dependency with its own concepts (cache, lockfile,
  run cache) that the maintainer and any agent must understand to debug a run.
- Correctness depends on dependencies being declared completely. An undeclared input
  (an environment variable, a file read from outside the declared folders, the version
  of a tool in the image) means a stale output is reused silently. This is the
  characteristic failure of such tools.
- A comment edit in a stage's source re-runs that stage and everything after it. For
  the Exporter that means launching the game again: several minutes at best.
- A Python dependency upgrade anywhere in the workspace re-runs every stage, including
  the export (G-0016-6).
- The folder layout on the data volume changes: no more dated folders to browse.
  Looking at a previous patch's output means asking DVC for it.

## Gaps and open questions

### G-0016-1. Where DVC's project directory is, and what is checked out in it

- **Kind:** design
- **Needed by:** phase 2; blocks the pipeline wiring

DVC works inside a project directory that contains `dvc.yaml`, and it only caches
outputs that are inside that directory (`docs/research/external-facts.md`). With hard
links, the cache and the outputs must also be on the same file system. Together these
mean: **the pipeline's project directory is a copy of this repository placed on the
data volume, with the stage outputs in a git-ignored folder inside it.**

That conflicts with three other statements:

- production "has no code checkout" (ADR-0007, G-0007-1);
- the pipeline runs the code of the deployed tag from an image (ADR-0005), so the
  `dvc.yaml` and `params.yaml` in the project directory must match that image exactly;
- the pipeline needs the latest `state/`, which is not what the tag contains
  (ADR-0012, G-0012-1).

A workable arrangement has to say: how the project directory is created and updated
at each release (and by whom, since nobody is meant to edit production); whether
`dvc.yaml` is taken from the checkout or from inside the image; where `state/` comes
from; and where staging's and dev's project directories are, given that all of them
share one cache.

### G-0016-2. Where DVC runs relative to the containers

- **Kind:** design
- **Needed by:** phase 2

Each stage's command has to run in an environment that has that stage's code and
tools. The Exporter is expected to have its own image, because of Proton and the GPU
(ADR-0007). DVC runs commands as child processes, so:

- if DVC runs **inside the pipeline container**, it cannot start the Exporter's
  container without access to the Docker socket (equivalent to root on the guest) or
  Docker-in-Docker;
- if DVC runs **on the guest itself**, each stage's command can be
  `docker compose run --rm <service> ...`, but then DVC and a checkout must be
  installed on the guest, outside any image, which is the opposite of ADR-0007's
  intent;
- if there is **one large pipeline image** containing everything including the
  Exporter's runtime, the problem disappears, at the cost of every pipeline run
  loading a multi-gigabyte image.

There is a second effect to design for: a stage's real inputs include its image (the
operating-system packages, Proton, WRFrontiersDB-CUE4Parse). Those are not in any dependency
folder, so a changed image would not by itself re-run a stage. The image's identity
may need to be a declared parameter.

### G-0016-3. Cleaning a cache that several workspaces share

- **Kind:** design
- **Needed by:** phase 2

DVC's clean-up keeps what the chosen git commits and workspace reference and deletes
the rest. The documentation warns that with a shared cache, a clean-up run in one
project breaks the others' data unless they are named with `--projects`
(`docs/research/external-facts.md`). Production, staging and dev share one cache
(decision 4). So the clean-up rule in decision 8 needs: one place it runs from; every
workspace listed; a way to express "what production currently uses" (which depends on
where lockfiles are committed, G-0012-2); and confirmation of whether the run cache's
own records are ever pruned, which the documentation does not say. Group write
permissions on the shared cache across three sets of container users are part of the
same design (ADR-0006, G-0006-4).

### G-0016-4. How fast the cache grows

- **Kind:** verification
- **Needed by:** phase 2

The cache stores each distinct file once, so growth per patch depends on how many
files differ between patches. For the export stage this was measured on 2026-10-12 by
comparing the two dated export folders on the server (baseline, section 3.3): of
30,496 files, 30,161 were identical, and new or changed files came to about 208 MB.
On that evidence the export adds a few hundred megabytes per patch, not gigabytes.

Still unmeasured: the parsed output (0.8 GB, a few large JSON files per type, which
probably change in full on most patches), textures, converted images, models and the
database itself. A rough upper bound for those together is 1.5 GB per patch. With
39 GB free on the volume, the clean-up rule is needed within the first year but not
on day one. One pair of patches is thin evidence; a content update larger than a
balance patch will change more.

### G-0016-5. Whether stages are deterministic

- **Kind:** verification
- **Needed by:** phase 2

The cache assumes that the same inputs give the same outputs. If a stage writes
anything that varies between runs (timestamps, unordered keys, absolute paths), then a
forced re-run produces "different" outputs, every later stage re-runs, and a new
database is published that differs from the last one only by noise.

For the export there is indirect evidence that it is deterministic: 99% of files were
byte-identical between two exports made a week apart from different game builds
(baseline, section 3.3). The parse, the image conversion (encoder output can vary
between library versions) and the database build have not been tested. Running each
twice on the same inputs and comparing would settle it.

### G-0016-6. Every dependency upgrade re-runs the export

- **Kind:** decision
- **Needed by:** phase 2

Decision 3 makes the single workspace lockfile a dependency of every stage. The
maintainer accepted the cost given exact pinning. The practical effect is still worth
stating: upgrading a library that only the API or the bot uses re-runs the download
check, the export (several minutes, launching the game under Proton), parse, and the rest,
on the next pipeline run. A narrower alternative is a per-stage dependency list
exported from the lockfile, so a stage only re-runs when its own libraries change.
That is more moving parts for less waiting.

### G-0016-7. Stage boundaries

- **Kind:** design
- **Needed by:** phase 2

Not settled: whether the mapper (which launches the game) is its own stage or part of
export, which decides whether a WRFrontiersDB-CUE4Parse upgrade re-launches the game; where model
files are produced; whether texture extraction stays inside parse while conversion is
separate; and whether the Site build is a stage (decision 2 left it open, and ADR-0014,
G-0014-2, bears on it).

### G-0016-8. A failed stage leaves its output missing

- **Kind:** verification
- **Needed by:** phase 2

DVC removes a stage's outputs before running it. If the stage then fails, the working
folder has no output for it. That must never affect what production is serving: the
live database has to be a separate promoted copy, not the stage's output path
(ADR-0015, G-0015-7).

### G-0016-9. Tool housekeeping

- **Kind:** action
- **Needed by:** phase 2

Pin the DVC version (ADR-0003, G-0003-5); switch off its anonymous usage reporting;
set the cache location, link type and shared-group mode in checked-in configuration;
and decide whether DVC's own lock is enough or the machine-wide pipeline lock
(ADR-0008) wraps every invocation.

## References

- `docs/research/2026-10-baseline.md`, sections 2 and 3.2.
- `docs/research/external-facts.md`, "DVC".
- DVC pipelines: https://doc.dvc.org/user-guide/pipelines
