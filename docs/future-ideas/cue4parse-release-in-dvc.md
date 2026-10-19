# Wire the WRFrontiersDB-CUE4Parse release into the DVC pipeline

| | |
|---|---|
| Recorded | 2026-10-19 |
| State | Idea; not planned for the migration |
| Related | ADR-0002 (what stays outside this repository), ADR-0005 (releases), ADR-0007 (exporter image), ADR-0016 (DVC stages and parameters) |

## Where things stand

- `CUE4P-BatchExport` has been **replaced by `WRFrontiersDB-CUE4Parse`**
  (`Surxe/WRFrontiersDB-CUE4Parse`). The ADRs use the new name; the baseline snapshot
  (`research/2026-10-baseline.md`) still says "BatchExport", for the same component.
- `WRFrontiersDB-CUE4Parse` and the Exporter are maintained in separate repositories.
  `WRFrontiersDB-CUE4Parse` is published as GitHub releases that are cut by hand (first
  stable release `v2.0.0`, 2026-10-17, after three `v2.0.0-test.N` pre-releases).
- The Exporter downloads the release at run time. Its `--batch-export-release` option
  (env `BATCH_EXPORT_RELEASE`, `options_schema.py`) takes either `latest`, which
  resolves to the latest stable release and skips pre-releases, or an exact tag to pin
  (`src/dependency_manager.py`, `install_batch_export`).

## Decision for the migration

The initial migration **keeps the release architecture**: the exporter consumes a
published `WRFrontiersDB-CUE4Parse` release, now in place of `CUE4P-BatchExport`. The
release tag is the pipeline parameter ADR-0016 already lists in `params.yaml`.

**Proposed, not decided:** pin an exact tag in `params.yaml` rather than `latest`. DVC
cannot see what `latest` resolves to, so a new release would not re-run the export;
with a pinned tag, a release bump changes `params.yaml` and DVC re-runs the export
then, and only then.

## The idea

Make the CUE4Parse build part of the pipeline itself, so that a change to its source
re-runs the export without anyone cutting a release and bumping a tag:

- a `cue4parse-build` DVC stage that builds the exporter binary from a pinned source
  revision (a git submodule, a vendored folder, or a commit hash in `params.yaml`), with
  the binary as its output;
- the export stage depends on that output instead of on a release tag, so DVC's
  content hashing decides when the export must re-run.

## Why it is deferred

- ADR-0002 keeps the C# exporter outside this repository and consumes it as a versioned
  release; building it in the pipeline reopens that decision.
- It adds a .NET SDK build to the pipeline (or to the `exporter` image, ADR-0007), and
  a build toolchain is a heavier dependency than a downloaded zip.
- Releases are rare. Bumping one pinned tag in `params.yaml` per release is cheap, and
  it already gives DVC the change signal it needs.
- The migration has enough moving parts without it (ADR-0025).

## What would make it worth doing

- Releases become frequent enough that cutting them by hand is a bottleneck.
- Changes to `WRFrontiersDB-CUE4Parse` routinely need to be tested against a full
  pipeline run before they are released.
- The export stage is split from the mapper (ADR-0016, G-0016-7), so a rebuild of the
  exporter would not also re-launch the game.

## Questions to answer first

- **Where the source lives:** submodule, vendored copy, or fetched by commit hash.
  A submodule or vendored copy reopens ADR-0002, decision 5.
- **Whether the build is deterministic:** if two builds of the same source produce
  different bytes, DVC sees a change every time. Hashing the source revision instead
  of the binary would avoid that.
- **Where the build runs:** in its own stage and image, or inside the `exporter` image
  (ADR-0016, G-0016-2 already asks where stages run relative to containers).
- **What happens to the release workflow:** whether releases are still cut for other
  consumers, or stop entirely.
- **A middle step:** automate the release in `WRFrontiersDB-CUE4Parse` CI (tag on
  merge), keep consuming releases, and let a bot open the `params.yaml` bump here. That
  removes the manual step without bringing a .NET build into this repository.
