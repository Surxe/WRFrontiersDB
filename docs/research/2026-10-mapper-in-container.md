# G-0006-2: the Exporter's mapper in Docker inside the WRF container (tested 2026-10-21)

**Answer.** It works. The Exporter's Linux mapper ran inside a Docker container inside
an unprivileged LXC guest on the server: `gamescope --backend headless` on the
integrated GPU, `umu-run`, the WRF-TLS Proton build, UE4SS. It produced a mapping file
for the 2026-10-20 patch with the same content as the production one. The mapper took
14 to 20 s (the host's runs take 14 to 46 s).

**One thing it needs.** Steam's runtime (`pressure-vessel`, through `bwrap`) creates
user and mount namespaces, which Docker's default seccomp profile blocks. The container
needs a seccomp profile that allows six more system calls (below). Nothing else had to
be loosened: no privileged container, no extra capabilities, AppArmor left on for the
LXC guest, and no changes to the Exporter.

## Setup

A throwaway guest, created for the test and destroyed afterwards:

- Unprivileged Debian 13 LXC, `nesting=1,keyctl=1`, **2 GiB memory and 0.5 GiB swap**
  (ADR-0006, decision 2), 4 cores.
- GPU: `dev0: /dev/dri/renderD128,gid=992,mode=0660` and
  `dev1: /dev/dri/card1,gid=44,mode=0660` (992 and 44 are `render` and `video` inside
  the Debian 13 guest; on the host `render` is 993). No `lxc.*` raw options.
- A separate 30 GB volume at `/wrf`, holding copies of the game download (15 GB), the
  Wine prefix and the Proton build. The live `/srv/dev/wrf` was not mounted. The copies
  were owned by the guest's uid 1000 (host uid 101000).
- Docker 29.9.2 from Docker's repository, as in G-0006-1.

The image (`2026-10-mapper-in-container/Dockerfile`) mirrors `home-server`'s
`wrf-gpu/install.sh`: Debian 13, i386 multiarch, RADV, `gamescope` from backports,
umu-launcher 1.4.4, Python with the Exporter's requirements, a `wrf` user with uid 1000.
The Exporter is the current `main` (0ab66aa) with its downloaded UE4SS.

Mesa: the image resolved 26.1.6 from backports, while the host runs 25.0.7 from Debian
main. umu-launcher's 32-bit Mesa dependencies would not resolve against main once
`gamescope` came from backports. **Decision (2026-10-22): pin 26.1.6 from backports**,
the version the spike ran on. The Dockerfile pins it explicitly. The pin was added
after the spike, at the version the spike had resolved. An `apt-get install -s` of the
pinned set resolves cleanly, but the image has not been rebuilt with it.

The run:

```
docker run --rm --security-opt seccomp=seccomp-bwrap.json \
  --device /dev/dri/renderD128 --device /dev/dri/card1 --group-add 992 --group-add 44 \
  --tmpfs /run/user/1000:uid=1000,gid=1000,mode=700 \
  -v /wrf:/wrf -v /wrf/home:/home/wrf wrf-mapper-spike \
  python src/run.py --should-download-dependencies false --should-download-steam-game false \
    --should-get-mapper true --force-get-mapper true --should-batch-export false \
    --headless true --steam-game-download-dir /wrf/steam-download \
    --output-mapper-file /wrf/out/2026-10-20.usmap ... \
    --wine-prefix /wrf/prefix --proton-path /wrf/proton/GE-Proton10-34-WRF-TLS
```

## What happened, in order

1. **The GPU through both layers.** `vulkaninfo` in the Docker container listed
   `AMD Radeon Graphics (RADV RENOIR)`. gamescope chose it and started its headless
   backend and Xwayland without a login session or logind. Its PipeWire warning
   (no screen capture) is harmless.
2. **First run failed** after 42 s: `bwrap: No permissions to create a new namespace`.
   The host allows unprivileged user namespaces (`kernel.unprivileged_userns_clone=1`,
   `kernel.apparmor_restrict_unprivileged_userns=0`). `unshare -Ur` fails in a default
   container and works with `seccomp=unconfined`, so the block is Docker's seccomp
   profile.
3. **With `seccomp=unconfined`** the mapper succeeded in 20 s.
4. **With a narrowed profile** it succeeded in 14 s. The profile is Docker's default
   (`moby/profiles`, `seccomp/default.json`) plus one rule allowing `unshare`, `setns`,
   `mount`, `umount2`, `pivot_root` and `clone` without conditions. In the default
   profile these are allowed only with `CAP_SYS_ADMIN`, which the container does not
   get. That is the configuration to use.

On first use, umu-launcher downloaded Steam's runtime (`steamrt3`, 797 MB) into
`~/.local/share/umu`. In production that directory must be on a persistent volume, or
every run downloads it again. No ADR places it yet. It is a re-downloadable cache like
Proton and the Wine prefix, so the data volume fits (ADR-0007 decision 3; ADR-0023
decision 4, not backed up). It must not share a volume with DepotDownloader's remembered
Steam login, which also sits in the home directory but is a secret (G-0022-2). So mount
the umu directory alone, not the whole home directory.

## Is the output the same?

The mapper does not produce the same bytes twice: two runs in the container differed
from each other and from production, at the same size (2,477,625 bytes). The file is an
uncompressed usmap (version 4) and the difference is ordering. UE4SS writes enums and
structs in the order the engine happens to list them.

`2026-10-mapper-in-container/usmap_canon.py` decodes every byte of the file, including
UE4SS's two extensions (`PPTH`, object paths; `EATR`, enum, struct and property flags).
It resolves every name reference, re-keys each record by name and hashes the result.
Production and all three container runs gave the same hash, `5457cd6787f3a019`: 56,623
names, 2,289 enums, 13,203 structs, identical.

## Memory

The Docker container's control group peaked at 1.66 GiB, including file cache. The
whole guest peaked at 2.0 GiB under its 2 GiB limit, which includes Docker's daemon and
the image build earlier in the session. There were no out-of-memory events. This agrees
with the mapper's 1.45 GiB of anonymous memory measured on the host (G-0006-3).

## Not tested

- The rest of the Exporter in the container: the Steam download (DepotDownloader) and
  the export (CUE4Parse, .NET).
- The live data volume with its real ownership mapping (G-0006-4). The test used
  copies on a volume owned by the guest.
- Repeated runs over weeks, and what a Proxmox, kernel or Docker update does to this
  (G-0006-10).
