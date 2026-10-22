# G-0006-3: the patch-day pipeline's real memory need (measured 2026-10-21)

**Answer.** The pipeline fits a 2.5 GiB limit, but only with swap. Its real (anonymous)
peak is **about 2.8 GiB**, from one step: the Parser's model extraction (`parse_models`).
Under a 2.5 GiB cap the run finished cleanly (no OOM, outputs identical) but pushed
**0.9 GiB** into swap and the parse took a third longer. Under a 2 GiB cap it also
finished, with 1.2 GiB of swap. Every other stage stays under 1.4 GiB anon.

**Recommendation.** Set the WRF LXC to **2.5 GiB memory with 1.5 GiB swap** now. Then
rework `parse_models` so it writes each model as it goes instead of holding all 265 in
memory. That is a small change and should bring the peak down to about 1.4 GiB (an
estimate, see below). After it, the guest can drop to 2 GiB with 0.5 GiB swap, which
leaves room for Valheim's 4 GiB fallback (G-0006-8).

## Earlier work this builds on

- No report from the earlier G-0006-3 hand-off was found: nothing in `/srv/dev/scratch`,
  `/srv/dev/wrf/logs`, the WRFrontiersDB repository or the memory notes.
- Related and reused: a 2026-10-17 session measured the export tool alone (CUE4Parse
  under caps of 768 to 896 MB). That work led to the export sizing its workers from
  `BATCH_EXPORT_MEMORY_MAX` (memory note `wrf-export`). It did not cover the mapper, the
  parse or the site.
- **The journal figures in baseline 3.1 changed meaning on 2026-10-14.** From then on,
  the Exporter runs the export in its own `systemd-run --user --scope`, which lands in
  the user manager's `app.slice`, outside `wrf-orchestrator@.service`'s cgroup. So
  journal peaks since then leave the export out entirely. The 2026-10-20 production
  run still logged "3.1G memory peak, 1.1G memory swap peak" without the export, which
  matches the parse peak found here.

## Method

- **Tool:** `WRFrontiersDB-Orchestrator/bin/measure-memory` (branch `measure-memory`). It runs the command in a transient systemd user slice. Once a second it
  samples `memory.current`, `memory.stat` (anon, file, shmem, kernel, file_dirty,
  file_writeback, ...), `memory.swap.current`, `memory.events` and `memory.pressure`,
  plus host `/proc/meminfo` and the Valheim VM's (VM 100) QEMU RSS and swap. At the end
  it reads `memory.peak`, `memory.swap.peak` and `memory.events`.
- **Nested scope kept inside.** A PATH shim adds `--slice=<measurement slice>` to the
  Exporter's `systemd-run --user --scope`. The export (with its own
  `MemoryMax=1536M`, `MemorySwapMax=0`) therefore sits inside the measured cgroup and
  under its limit, as it would inside one container. Without this, the export would
  escape the measurement and the cap.
- **Stage stamps** come from the orchestrator's banners plus Exporter and Parser markers
  in its console stream (the per-stage log files are block-buffered and lag by minutes).
- **Run:** `bin/run-pipeline --game-version 2026-10-20 --assume-manifest-confirmed` with
  export on, `--should-download-dependencies false`, **`--should-download-steam-game false`**
  (skipped: the depot is current), `--should-get-mapper true --force-get-mapper true`,
  `--should-batch-export true --force-export true`, textures on,
  **`--batch-export-memory-max 1536M`** (production default), parse with maps on,
  `--should-push-data false`, index on (local only: index commits and pushes only when
  push-data is on and a PAT is set, checked in `src/stages/index.py`), site build on,
  `--should-deploy-site false`. No secrets were in the environment, so no push and no
  email. Script: `/srv/dev/scratch/g-0006-3-runs/run.sh`.
- **Map cooking forced too.** For the forced runs the Parser's `build/map_cook_cache`
  was removed, so all 12 maps were cooked rather than copied (patch-day worst case).
  The original cache was restored afterwards (identical to the rebuilt one).
- **Conditions:** Valheim VM up, 0 players (last disconnect 2026-10-20 19:23). Host
  7.1 GiB RAM and 7.1 GiB swap, about 2.8 GiB of that swap already in use (about
  1.5 GiB of it the Valheim VM's).
- **Integrity:** `parsed/2026-10-20` and `textures/2026-10-20` were backed up to
  `/srv/dev/wrf/dev/g-0006-3-backup/`. After each forced run, `diff -rq` against the
  backup showed **0 differences**, and the export's file list with sizes
  (59,450 files) matched. Data, Parser, Site and Exporter checkouts are clean.
  Nothing was published.

## Results

All figures MiB. "anon+file" is the peak of the sum at one sample. Sub-stage
durations come from marker times. Stage totals from the orchestrator are listed under
each table.

### Run 1: uncapped, forced (the true profile)

689 s, exit 0. `memory.peak` 3,259, `memory.swap.peak` 523. Events: oom 0, oom_kill 0.
(`max` 20,539 is the export's own 1536M scope reclaiming file cache.)

| Stage | Duration (s) | Peak anon | Peak anon+file | Peak swap |
|---|---|---|---|---|
| export: mapper (game under Proton) | 44 | 928 | 1,843 | 522 |
| export: CUE4Parse assets | 77 | 383 | 2,173 | 37 |
| export: CUE4Parse meshes | 271 | 951 | 2,114 | 37 |
| export: CUE4Parse maps | 149 | 1,004 | 1,844 | 37 |
| **parse: objects (incl. models)** | 51 | **2,772** | **3,197** | 18 |
| parse: maps (12 cooked) | 46 | 1,118 | 2,172 | 18 |
| parse: enrich | 4 | 683 | 2,083 | 18 |
| index | 1 | 6 | 1,701 | 18 |
| site (install, slugs, build) | 43 | 611 | 3,126 | 18 |

Stage totals: export 542 s, parse 102 s, site 38 s. Host MemAvailable fell to
**953 MiB** at the parse peak.

### Run 2: MemoryHigh=2.5G (2560M), MemoryMax=2.75G (2816M), forced

708 s (**+3%**), exit 0. `memory.peak` 2,562, `memory.swap.peak` **895**. Events:
high 7,535, oom 0, oom_kill 0. Outputs identical.

| Stage | Duration (s) | Peak anon | Peak anon+file | Peak swap |
|---|---|---|---|---|
| export: mapper | 12 | 1,362 | 2,217 | 0 |
| export: CUE4Parse assets | 77 | 437 | 2,403 | 0 |
| export: CUE4Parse meshes | 279 | 905 | 2,330 | 0 |
| export: CUE4Parse maps | 157 | 1,111 | 2,168 | 0 |
| **parse: objects** | 81 | 2,406 | 2,539 | **889** |
| parse: maps | 49 | 1,150 | 1,992 | 293 |
| parse: enrich + images | 5 | 674 | 2,137 | 289 |
| site | 44 | 890 | 2,473 | 18 |

Stage totals: export 526 s, parse **135 s (+33%)**, site 36 s. Memory PSI "some"
avg10 peaked at 7.3%.

### Run 3: MemoryHigh=2G (2048M), MemoryMax=2.25G (2304M), forced

751 s (**+9%**), exit 0. `memory.peak` 2,050, `memory.swap.peak` **1,203**. Events:
high 9,867, oom 0, oom_kill 0. Outputs identical.

| Stage | Duration (s) | Peak anon | Peak anon+file | Peak swap |
|---|---|---|---|---|
| export: mapper | 13 | 1,385 | 1,921 | 0 |
| export: CUE4Parse assets | 79 | 467 | 1,901 | 0 |
| export: CUE4Parse meshes | 302 | 828 | 1,902 | 0 |
| export: CUE4Parse maps | 179 | 1,103 | 1,830 | 0 |
| **parse: objects** | 81 | 2,026 | 2,032 | **1,198** |
| parse: maps | 49 | 1,093 | 1,903 | 333 |
| parse: enrich | 4 | 677 | 1,798 | 325 |
| site | 40 | 608 | 1,987 | 18 |

Stage totals: export 574 s (+6%), parse 134 s (+32%), site 36 s. PSI "some" avg10
peaked at 8.5%.

### Run 4: ordinary re-run, no forces, uncapped (the weekly probe-triggered case)

110 s, exit 0. Mapper and export skipped (outputs exist), maps copied from the cook
cache. `memory.peak` 3,517 (mostly file cache), swap 0.

| Stage | Duration (s) | Peak anon | Peak anon+file | Peak swap |
|---|---|---|---|---|
| **parse: objects** | 58 | **2,786** | 3,075 | 0 |
| parse: maps (cached) | 7 | 714 | 1,826 | 0 |
| parse: enrich + images | 4 | 708 | 2,217 | 0 |
| site | 40 | 580 | 3,406 | 0 |

The cheap run has the same 2.8 GiB peak. The heavy step runs every time, not only on
patch days.

## The heaviest stage: Parser `parse_models`

In run 1, anon climbs about 140 MiB/s for 20 s to 2,772 MiB and holds there for about
28 s. It then drops to 696 MiB the moment the map parse starts, which is when
`parse_models()` returns. The code
(`WRFrontiersDB-Parser/src/parse/parsers/model.py`) builds a `models` dict for all 265
character modules before writing any file. Each model carries LOD0 vertex positions
and triangle indices converted with `.tolist()` into Python lists of floats and ints.
On disk that is 417 MB of JSON (`parsed/<v>/Models`). In memory it is about 2.1 GiB,
because a Python float in a list costs about 32 bytes. The 28 s plateau is the
write-out loop.

The rest of the parse needs about 0.7 GiB, and map cooking peaks at about 1.15 GiB. If
each model is written as soon as it is extracted (and not kept, since `main()` discards
the return value anyway), the parse should peak at about 0.8 to 1.2 GiB. The run's
peak would then be the mapper (about 1.4 GiB anon) or the export (bounded by its own
1.5 GiB cap). **This is an estimate from the curve, not a measurement.** The change
belongs in the `WRFrontiersDB-Parser-dev` worktree, and `bin/measure-memory` can
confirm it.

The export is **not** the problem. Its anon stays at or below 1.1 GiB inside its own
1536M scope. Its high memory.current is page cache from the 13 GB pak set, and the
kernel reclaims that freely.

## Valheim and the host during the runs

- Valheim VM RSS: 1.9 to 2.2 GiB with 0 players. Its host-side swap grew from 1.43 to
  1.65 GiB over the four runs. The host paged the idle VM's memory out under the
  pipeline's pressure. Nothing was killed and the server stayed up.
- Host MemAvailable minimum: 953 MiB uncapped, 1.49 GiB at 2.5G, 1.85 GiB at 2G.
  Host SwapFree minimum: 3.3 GiB.
- With the cap, the pipeline gives way instead of the host: its overflow goes to its
  own swap, and the host's free memory stayed higher than in the uncapped run.

## Recommended LXC limit and swap allowance

| | Memory | Swap | Why |
|---|---|---|---|
| **Now (code as is)** | **2.5 GiB** | **1.5 GiB** | Measured: finishes with 0.9 GiB swap, about +35 s. 1.5 GiB leaves about 0.6 GiB of margin for a patch that adds models (the step grows with the model count). |
| If Valheim goes to 4 GiB first | 2 GiB | 1.5 GiB | Measured: finishes with 1.2 GiB swap, +9%. Tight margin; do the Parser rework first. |
| **After the `parse_models` rework** | **2 GiB** | **0.5 GiB** | Estimated peak about 1.4 GiB anon (mapper). Remeasure before relying on it. |

Which of the ADR's options this points to: **rework that stage.** It is a small,
local change and removes the only step over 1.4 GiB. "Raise the limit only while it
runs" and "move the heaviest stage to the workstation" are not needed. Both would be
heavier answers to a problem that comes down to one data structure.

Swap is not free. The guest's swap is the host's swap, which already holds about
2.8 GiB, 1.5 GiB of it Valheim's. A 1.5 GiB allowance still fits the 7.1 GiB swap
device.

## What was not measured

- **The Steam download** (DepotDownloader). Skipped: the depot is current. It moved
  742 MB on 2026-10-06; its memory use is unknown, though it runs before the mapper,
  not alongside the parse.
- **Valheim with players.** All runs had 0 players. Several players add VM memory
  (G-0006-8) and host pressure. The VM is a fixed 3.5 GiB, so that pressure lands on
  the host and its swap, not on this limit.
- **Proxmox's exact cgroup settings.** The runs used systemd's `MemoryHigh` (throttle)
  with `MemoryMax` above it. A Proxmox LXC sets `memory.max` (hard) and
  `memory.swap.max`; with a hard limit the kernel reclaims and swaps at the limit
  instead of throttling first. Expected to behave the same as long as swap is allowed,
  but check it in spike 3 (migration plan).
- **Docker and the other services inside the guest** (Docker daemon, API, bot at about
  65 MB), and the mapper and export running inside Docker inside the LXC (G-0006-2).
  Running there also needs a user systemd for the export's own scope, or another way to
  apply its cap.
- **Variance.** One run per configuration, one patch. Export times varied ±5% between
  runs with no cap effect. The mapper step took 44 s in run 1 and 12 to 13 s after
  (first-launch warm-up). 1 s sampling can miss sub-second spikes; `memory.peak`
  (3,259 MiB) and the highest sampled current (3,255 MiB) agree in run 1.
- **The parse rework's effect** (an estimate only, above).

## Files

- Raw samples (one row a second): `g-0006-3-pipeline-memory-uncapped.csv`,
  `-capped-2.5G.csv`, `-capped-2G.csv`, `-noforce.csv`, in `/srv/dev/scratch/` on the server (not checked in).
- Per-run summary, console log and orchestrator logs:
  `/srv/dev/scratch/g-0006-3-runs/<run>/summary.{md,json}`, `<run>.console.log`,
  `logs/<run>/`.
- Backups of the overwritten outputs: `/srv/dev/wrf/dev/g-0006-3-backup/` (safe to
  delete; the re-run reproduced them).
