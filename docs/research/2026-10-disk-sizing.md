# G-0006-5: the guest's disk and the data volume's growth (measured 2026-10-23)

**Answer.** Both fit with room to spare.

- **Guest root disk: 32 GB, thin-provisioned on `local-lvm`.** The expected use is about
  12 GB at worst. The thin pool has about 315 GB free, and a thin disk only uses what is
  written.
- **Data volume: keep the existing 68 GB volume.** After cutover it holds about 24 GB.
  It grows by a few hundred megabytes per patch, and by up to a few gigabytes when a
  code release rewrites a stage's output. That leaves about two years before it is
  full without a clean-up rule. ADR-0016's rule is needed within the first year, as
  that ADR already says.
- **Leave Docker's storage out of the daily dump** with
  `--exclude-path '/var/lib/docker/?*' --exclude-path '/var/lib/containerd/?*'`. That
  exact form matters: the trailing-slash form excluded nothing. With it the dump is
  552 MB. Without it, about 3 GB.

## The machine's disks

| | Size | Free | Notes |
|---|---|---|---|
| volume group `pve` | 476 GB | 4 GB unallocated | |
| thin pool `data` (`local-lvm`) | 350 GB | about 315 GB (9.8% used) | Valheim VM, `lxc-lab` |
| `root` (host) | 40 GB | 15 GB | |
| `wrf` (the data volume) | 68 GB, thick | 39 GB | ext4, `/srv/dev/wrf` |

The data volume is a plain (thick) volume, not in the thin pool. With 4 GB free in the
volume group, it can only grow by moving the data to a thin volume.

## Guest root disk

Built in a throwaway guest (Debian 13, Docker 29.9.2) from stand-ins for the planned
images (ADR-0007 decision 4):

| Image | Contents | On disk | Compressed |
|---|---|---|---|
| `exporter` | G-0006-4's mapper stack (Debian, i386, Mesa 26.1.6, gamescope, umu) + the Exporter with WRFrontiersDB-CUE4Parse, UE4SS and DepotDownloader | 2.54 GB | 643 MB |
| `pipeline` | `python:3.13-slim`, git, Parser and Orchestrator requirements | 514 MB | 132 MB with `bot` |
| `bot` (and API, similar) | `python:3.13-slim` + the bot's requirements | 236 MB | |
| `site` (if the Site build stays in the pipeline) | `node:22-slim` + the Site's `npm ci` | 689 MB | |
| `cloudflared` | official image | 99 MB | |

Proton (1.4 GB) is not in the exporter image. It stays on the data volume, as
G-0007-7 leaves open. Putting it in the image would make the image about 4 GB.
DepotDownloader and WRFrontiersDB-CUE4Parse are self-contained, so no .NET runtime is
needed.

The guest's root file system:

| | GB |
|---|---|
| Debian + Docker packages | 1.5 |
| one set of all images (layers shared between images are stored once) | 3.7 |
| build cache, if images are built on the server (dev Compose project, ADR-0007 decision 7) | 3.0 |
| a second exporter version during a deploy, or staging on another tag, when the base layers changed | 2.5 |
| logs, operational state, local database copies (estimate) | 1 |
| **worst case** | **about 12** |

32 GB gives room for a third image version and an unpruned build cache. Two prune
rules keep it bounded: after a successful deploy, keep the current and previous tag
of each image (the previous one for rollback); and cap the build cache
(`docker builder prune --keep-storage`). Thin provisioning means the unused part costs
nothing.

**Pull time.** A pull of `python:3.13` (415 MB compressed) took 38 s, about 86 Mbit/s
over the server's wifi. So the exporter image takes about a minute when its base
layers change, and seconds when only its code layer does (G-0007-10).

## Backup size

ADR-0023 decision 2 leaves Docker's storage out of the guest's daily dump and expects
"well under 1 GB". Docker 29 keeps images in containerd's store (`/var/lib/containerd`,
3.7 GB here) as well as `/var/lib/docker`.

| Dump | Size |
|---|---|
| with images | 2.90 GB (also when excluded with `--exclude-path /var/lib/docker/`) |
| with `--exclude-path '/var/lib/docker/?*' --exclude-path '/var/lib/containerd/?*'` | **552 MB** |

The guest restored from the 552 MB dump started Docker and containerd with no images,
then pulled and ran a container. That is the recovery path ADR-0023 describes. The
trailing-slash form left everything in. Only the `?*` form, the one Proxmox documents,
excluded the contents.

## Data volume

### What it holds after cutover

| | GB | Notes |
|---|---|---|
| Steam download | 15 | one copy, not in the DVC cache (ADR-0016 decision 7) |
| DVC cache, first fill | about 5.5 | exports 3.8, parsed 1.1, textures 0.3, mapper files |
| Stage workspaces | about 0 | `cache.type hardlink`, shared with the cache |
| Proton, Wine prefix, umu runtime | 2.9 | 1.4 + 0.7 + 0.8 |
| logs | 0.1 | |
| **total** | **about 24** | of 67 usable |

Today the volume also holds `dev/` (2.3 GB of development copies and spike backups) and
`tools/` (0.9 GB, .NET and NuGet). Neither is used by the pipeline: both export tools
are self-contained.

During cutover, the old pipeline's dated folders (about 5 GB per version, two
versions) sit beside the new cache. That is about 34 GB at most, still within the
volume.

### Growth per patch

The Data repository's history holds the published parse output (`current/`) and
textures for ten game versions, 2026-04-14 to 2026-10-22. Git stores each distinct
file once, as DVC's cache does. Counting the bytes each commit added that no earlier
commit had:

| Version | New content | What drove it |
|---|---|---|
| 2026-06-23 to 2026-08-25 | 19 to 23 MB each | the patch |
| 2026-09-15 | 815 MB | models added to the output (417 MB of JSON), then reworked |
| 2026-09-29 | 569 MB | model output rewritten twice by Parser changes |
| 2026-10-06 | 122 MB | 85 MB of it from a Parser change on 2026-10-15 |
| 2026-10-20 | 39 MB | the patch |
| 2026-10-22 | 13 MB | the patch |

So a patch adds tens of megabytes of parse output and textures. A Parser change that
rewrites a large output adds hundreds. All distinct content over six months was
1.8 GB. The volume's `parsed/` folder (1.1 GB) is about twice the published `current/`
(516 MB), so double these figures for the cache.

The export was not re-measured. The baseline's pair of patches added 208 MB of new
export content (G-0016-4). A WRFrontiersDB-CUE4Parse change that rewrites every file
would add up to 3.8 GB.

**Estimate.** About 0.3 GB per patch (export about 0.2, the rest under 0.1), at 15 patches a year, is about 5 GB a year. Code
releases that rewrite outputs add perhaps 5 to 10 GB more. That is roughly 10 to 15 GB
a year without clean-up, against about 33 GB free after cutover: two years or more.
Clean-up (ADR-0016 decision 8) is needed within the first year, as G-0016-4 says, but
not on day one.

## Not measured

- The database, converted images and models from the new pipeline (they do not exist
  yet).
- The export's per-patch growth on a fresh pair of patches. The 2026-10-20 export
  folder was deleted on 2026-10-23, after G-0006-4's test overwrote it.
- Real images, which may differ from the stand-ins: the API's dependencies, and
  whether the Site build lives in the pipeline image.
