# G-0006-4: file ownership across the container boundary (tested 2026-10-23)

**Answer.** Map user and group 1000 straight through. The data volume is owned by the
host account `dev` (uid and gid 1000), which also runs today's host pipeline. If the
WRF guest maps its own id 1000 to host id 1000 and leaves every other id shifted as
usual, then:

- uid 1000 in the guest, and in any Docker container in it running as 1000, is
  `dev` on the host;
- files written from any layer have the same owner the host pipeline uses, so the old
  and new pipelines can share the volume through cutover (ADR-0025);
- DVC's shared cache works with group permissions, including between two different
  uids that share group 1000.

**The rule this needs.** Every container that writes to the volume runs as `1000:1000`
and its image has a user with that id. A container left as root writes files that the
host sees as uid 100000.

## Setup

A throwaway guest, created for the test and destroyed afterwards:

- Unprivileged Debian 13 LXC, `nesting=1,keyctl=1`, Docker 29.9.2 (as in G-0006-1).
- A test directory on the real data volume (`/srv/dev/wrf/dev/g-0006-4-spike`, owned
  `dev:dev`, mode 2775), bind-mounted into the guest at `/wrf` (`mp0`). The live
  pipeline's folders were not mounted.
- On the host, `root:1000:1` added to `/etc/subuid` and `/etc/subgid` so that root may
  map host id 1000 into a container. Both files were restored afterwards.
- In the guest's config, the custom map:

```
lxc.idmap: u 0 100000 1000
lxc.idmap: g 0 100000 1000
lxc.idmap: u 1000 1000 1
lxc.idmap: g 1000 1000 1
lxc.idmap: u 1001 101001 64535
lxc.idmap: g 1001 101001 64535
```

Guest ids 0 to 999 and 1001 to 65535 are shifted by 100000 as in any unprivileged
container. Only 1000 is the same on both sides.

## Results

Who wrote, and who owns the file on the host:

| Writer | Host owner | Notes |
|---|---|---|
| host `dev` (today's pipeline) | `1000:1000` | readable and appendable from the guest |
| guest user 1000 | `1000:1000` | |
| Docker, `-u 1000:1000` | `1000:1000` | the same as the host pipeline |
| Docker, `-u 1001:1000` | `101001:1000` | group from the setgid directory; group-writable |
| Docker as root (no `-u`) | `100000:1000` | still group 1000 through setgid, but an unmapped owner |

Host `dev` could append to files written by 1000 and by 1001, create directories
inside ones 1001 had made, and delete the whole mixed-owner tree, including the root-
written file. That works because the directories are group-writable (2775) and the
writers used `umask 002`. A `444` file from another uid can still be deleted, because
deletion depends on the directory.

**DVC.** DVC 3.67.1 in a Python image, with the project and its cache on the mount and
`cache.shared group`, `cache.type hardlink,copy`:

1. As 1000: `dvc init`, `dvc add`, commit.
2. As 1001 (standing in for staging): `dvc checkout` from 1000's cache, then add a file.
3. As 1000 again: `dvc status` clean, `dvc add`, then `dvc gc -w -f`, which removed
   objects 1001 had written.

All three passed. Cache directories were 2775 with group 1000 whichever uid created
them. One failure on the way: DVC (through `getpass`) stops with `getpwuid(): uid not
found: 1000` when the running uid has no passwd entry. That is why each image must
define its user.

**GPU together with the map.** The same guest with `dev0: /dev/dri/renderD128,gid=992`
(G-0006-2) still opened the render node from a Docker container running as
`1000:1000` with `--group-add 992`. Guest gid 992 is in the shifted range (host
100992). Proxmox gives the node to that gid, so the custom map does not interfere.

## What the design is

1. **Host (`home-server`):** `root:1000:1` in `/etc/subuid` and `/etc/subgid`. When the
   guest is created, add the six `lxc.idmap` lines to its config and bind-mount the
   data volume. Proxmox's own options cannot express a custom map, so these are raw
   `lxc.*` lines, which only `root@pam` may set. That fits, because the guest is
   created by `home-server`'s scripts (ADR-0006 decision 8).
2. **Guest:** a user and group with id 1000. It owns the deploy directories and is
   the identity the containers use.
3. **Images and Compose:** every service that writes to the volume sets
   `user: "1000:1000"`, and its image creates that user. Containers that only read
   (the API reading a database) may use other ids. They still need read permission,
   which the current modes give everyone.
4. **Volume modes:** keep what is there. Directories are setgid group `dev` (2775 or
   2755), processes use `umask 002`, and DVC uses `cache.shared group`. Those modes
   let a second uid work if one is ever wanted.
5. **Staging uses the same uid as production** (decided 2026-10-23). Staging and production are separated
   by Compose project, paths and secrets (ADR-0008), not by uid. A separate uid buys
   little at this scale, as with the two-guest design ADR-0022 rejected. The test shows
   that it would work, through the group, if that changes.

## Follow-up tests (2026-10-23)

Three items left open above were then tested, in a second throwaway guest built to the
design: 2 GiB memory and 0.5 GiB swap, the id-1000 map, the GPU, and the real data
volume, the repositories and `dev`'s `~/.nvm` (read-only) bind-mounted at their host
paths. Everything was destroyed afterwards and the host's id files restored.

### The full pipeline on the real volume

Today's pipeline code (the checkouts, bind-mounted) ran in one Docker container as
`1000:1000`. The image had G-0006-2's mapper stack with Mesa pinned to 26.1.6, plus git
and the export tool's native libraries. The flags were the G-0006-3 forced run's:
mapper and export forced, map cooking forced, textures, parse with maps, index, site
build, no push, no deploy, no secrets in the environment.

- **It completed:** 827 s in all, the export 643 s. The container's peak was 1.82 GiB
  with 351 MiB of swap, inside the guest's limit. The host was short of memory at the
  time (about 2.4 GiB available), so this is not a clean memory measurement (spike 3).
- **Ownership:** the run wrote 78,271 files, every one `dev:dev` on the host. Before and
  after, no file on the volume or in the five repositories was owned by anything but
  1000:1000. All repositories were left clean.
- **Same output as the host:** the game download had moved on to the 2026-10-22 patch
  (processed on the host on 2026-10-22), so this run exported that game. Its `parsed/`
  output was byte-identical to the host pipeline's own `parsed/2026-10-22`. The
  export's file list and sizes matched (59,450 files). The mapping file decoded to
  the same schema as the host's.

Two things failed on the way. Neither is about ownership:

1. **A cold umu cache fails the mapper.** With an empty `~/.local/share/umu`, umu-
   launcher starts downloading Steam's runtime (about 800 MB) inside the mapper's 120 s
   window, and the Exporter kills it. In G-0006-2 the runtime happened to be downloaded
   by an earlier failed attempt. So the cache placed on the data volume (G-0006-2) has
   to be **filled at deploy time**, before any mapper run, for example by one
   `umu-run` against a throwaway prefix. That is what was done here.
2. **`systemd-run` in the image breaks the export.** The Exporter caps the export with
   `systemd-run --user --scope` whenever `systemd-run` is on the PATH. Debian's
   packages put it in the image, and in a container there is no user session bus, so
   the export failed after 0.06 s. Without the binary the Exporter skips the scope and
   the container's own limit applies. For the test it was masked
   (`-v /dev/null:/usr/bin/systemd-run:ro`). The real fix belongs in the Exporter: an
   explicit option to not use the scope. That is a change for ADR-0007's exporter
   image, not for ownership.

Also seen: the mapper rewrote parts of the Wine prefix's registry. The container has no
host fonts, so the font list changed, and Wine's user id changed. Wine rebuilds both at
every launch, and the host pipeline rewrites them the same way. While host and guest
share one prefix during cutover, each side will rewrite them; nothing breaks, but the
prefix is not byte-stable across the two.

### A shared lock across the boundary

A lock file on the volume, held on one side and tried without waiting on the other:

| Held by | Tried from | `flock` | POSIX `fcntl` lock |
|---|---|---|---|
| host `dev` | guest user 1000 | blocked | blocked |
| guest user 1000 | host `dev` | blocked | |
| host `dev` | Docker container in the guest | blocked | blocked |
| Docker container in the guest | host `dev` | blocked | |

Locks are kernel objects on the file, and all layers see the same file through the bind
mount, so one lock file serves G-0025-6 whichever kind the old pipeline adopts.

### Backup and restore with the custom map

`vzdump --mode snapshot` of the running guest (as ADR-0023's daily dump would run)
excluded all three bind mounts ("not a volume"), as ADR-0023 wants. The archive was
1.9 GB, most of it the spike's Docker images, which production pulls again instead.
`pct restore` to a new id kept the six `lxc.idmap` lines, the bind mounts (with
`ro=1`), the GPU devices and the limits. The restored guest started with the same id
map. Docker and its images came back, the image's user was still 1000, a container
wrote to the real volume as `1000:1000`, and the GPU was visible.

## Not tested

- A clean memory measurement of the containerised run (spike 3).
- Some folders on the volume are 2755, not 2775: `data`, `data/mapper`,
  `data/steam-download`, `prefix` and `discount-logs`. That is fine with a single uid. A
  second uid would need them made group-writable.
