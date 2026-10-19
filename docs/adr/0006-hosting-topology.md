# ADR-0006: Hosting topology

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-09; boundary between repositories settled 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0007 (containers and deployment), ADR-0008 (environments), ADR-0019 (Cloudflare), ADR-0022 (secrets), ADR-0023 (backups) |

## Context

Everything except the websites already runs on one machine at home: an old laptop
running Proxmox (baseline, section 3). The pipeline, the update probe, the discount
watch and the bot run directly on the Proxmox host as systemd units, next to one
virtual machine that hosts a Valheim game server.

The constraints that shaped the decision:

- **Memory is the scarce resource.** The machine has 7.1 GiB. The Valheim VM holds a
  fixed share whether it uses it or not. The patch-day pipeline has peaked at 2.6 to
  4.2 GB plus up to 1.7 GB of swap (baseline, section 3.1), and today nothing limits
  it. If the host runs out, the kernel kills the largest process, which is the Valheim
  VM.
- **The pipeline needs a GPU.** The Exporter's mapper step launches the game under
  Proton and needs a working Vulkan driver (baseline, section 2.3). The laptop has one
  integrated GPU.
- **The pipeline is bursty.** It runs for minutes, about once a week. The bot and the
  API are tiny and always on.
- **Nothing at home can be reached from the internet.** The machine is behind the home
  router, and guests are a further layer in, behind the host. Everything that looks
  like "the internet reaching the server" must be the server connecting out
  (ADR-0019).
- **The workstation's copy of the game data is stale.** Patch processing only happens
  on the server now, so pipeline development has to happen there too.
- The maintainer wants to learn server and container technology through this project,
  and asked what renting capacity would cost.

A principle was agreed first, and used to settle several later questions:

> **Minimise the differences between local and production.** Any tool choice that makes
> local work differently from production needs a strong reason.

## Decision

1. **All WRF workloads move into one Proxmox guest**: the API, the bot, the pipeline and
   its scheduled jobs. The host becomes hypervisor and backups only.
2. **That guest is an unprivileged Linux container (LXC), not a virtual machine**,
   with a memory limit of about 3 GiB. The exact figure waits for the pipeline memory
   investigation (G-0006-3).
3. **Inside the guest, the workloads run as Docker containers under Docker Compose**
   (ADR-0007), the same way they run on the workstation.
4. **The Valheim VM is reduced from 4 GiB to a fixed 3 GiB**, keeping its swap file.
   (This is being applied separately from this project.)
5. **The design must not depend on being at home or on Proxmox.** The same Compose file
   runs anywhere; the pipeline publishes each database to object storage and the API
   can fetch it from there. A likely later split is: the pipeline stays at home, and
   the API and bot move to a small rented server.
6. **The home machine is never on the path of a page view.** Pages and images are
   served from Cloudflare (ADR-0019, ADR-0020). Once the API exists, some site features
   may depend on it; even then the laptop must not be needed to load a page or an icon.
7. **Order of arrival:** the API goes into the guest first; the bot and the pipeline
   move in at cutover. The Exporter's Proton step is to be trialled inside the guest
   before cutover.
8. **Which repository owns what:** `home-server` owns host-level configuration (creating
   the guest, the backup timer for it). This repository's `deploy/` owns everything
   inside the guest (the Compose file, the deploy script, the scheduled-job units).

Memory budget behind points 2 and 4: 7.1 GiB total, less 3 GiB for Valheim, less about
1 GiB for the host, leaves about 3 GiB for WRF.

## Alternatives considered

- **A virtual machine for WRF.** Stronger isolation and the form Proxmox recommends
  for running Docker. Rejected on memory: a VM's memory belongs to the VM whether used
  or not, so fitting the pipeline's burst would mean reserving about 3 GiB around the
  clock on a 7 GiB machine. A container's limit is a cap, not a reservation; idle, the
  WRF guest is estimated to use a few hundred megabytes (the bot alone uses about
  65 MB today; the Docker daemon and the API are not yet measured).
- **Stay on the host as systemd units.** No new technology. Rejected: no memory
  limit protects Valheim, production differs completely from local development, and it
  cannot move to a rented server.
- **A privileged container.** Fewer problems with file ownership and devices.
  Rejected as the default: root inside a privileged container is root on the host.
- **Two guests, production and development.** Proposed during the secrets discussion so
  that the AI agent could have full access to one and none to the other. Rejected with
  the rest of that design as too much to manage at personal scale (ADR-0022).
- **Rent a server now for everything.** Removes the dependence on home power and wifi.
  Rejected for the pipeline: it needs about 3 GB of memory in bursts, tens of gigabytes
  of disk and a GPU, which is far beyond the cheapest tier. For the API and bot it is
  affordable (about 5 US dollars a month) but solves a problem nobody has yet reported.
- **Move the Valheim server out instead**, freeing the laptop for WRF. Discussed and
  not pursued.
- **Podman instead of Docker inside the guest.** See ADR-0007.

## Consequences

- A runaway pipeline is killed inside its own guest instead of taking down Valheim.
- Production and local development run the same containers from the same Compose file.
- The WRF guest can be backed up, restored and eventually moved as a unit (ADR-0023).
- Docker inside a container is a less-travelled path than Docker inside a VM. Proxmox's
  own guidance prefers the VM for isolation, and there is a current, reported breakage
  on this exact combination (G-0006-1).
- The Exporter, the hardest thing to containerise in the whole system, now has to run
  inside two layers of containers with GPU access (G-0006-2).
- Availability of the bot and the API is that of one laptop on home wifi. This was
  accepted; the websites do not share it.
- Guests cannot be reached directly from the workstation, only through the host. This
  shapes how deployments are started (ADR-0007).

## Gaps and open questions

### G-0006-1. Docker inside an unprivileged container on this Proxmox version

- **Kind:** verification
- **Needed by:** the start of phase 3; this is the first thing to try

Since about November 2025 there are reports that Docker fails to start containers
inside LXC guests on Proxmox 9, after a security fix in `containerd`
(`docs/research/external-facts.md`). The reported workarounds remove AppArmor
confinement from the guest, which weakens the isolation the unprivileged container was
chosen for. The server runs Proxmox 9.2. Whether it is affected, and whether a proper
fix has shipped since, is unknown.

A short spike decides it: create the guest, install Docker, run a container. If it
fails without the workaround, the choices are: accept the workaround; use a virtual
machine after all and solve memory differently (for example by starting the pipeline
VM only on demand); or run the services without Docker inside the guest, at the cost
of the "same as local" principle.

### G-0006-2. The Exporter's mapper inside Docker inside the guest

- **Kind:** verification
- **Needed by:** phase 3, before anything depends on the guest for patch days

The mapper needs `gamescope` in headless mode, a Vulkan driver for the integrated GPU,
32-bit libraries, `umu-launcher`, a custom Proton build, a persistent Wine prefix, GPU
group membership and a runtime directory (baseline, section 2.3). On the host this took
a dedicated install script to get right. Inside a Docker container inside an
unprivileged LXC, each of those is a separate thing that may not work: passing the GPU
device through two layers, mapping the `render` group's id through both, running a
nested compositor without a login session.

The decision already calls for a trial before cutover. It should be planned as a
risk, with fallbacks named in advance: run the Exporter directly in the guest (not in
Docker), or leave the Exporter on the host and let the rest of the pipeline run in the
guest. Either fallback changes ADR-0007 and ADR-0016.

### G-0006-3. Whether the pipeline fits in the limit

- **Kind:** verification
- **Needed by:** phase 3

The largest measured run used 4.2 GB plus 1.7 GB of swap, against a planned limit of
about 3 GiB. The measured figure includes file cache, which the kernel can give back,
so the true requirement is lower, but by how much is not known. An investigation was
handed off to a separate session and has not reported. Until it does, the limit, the
guest's swap allowance, and whether any stage needs rework are all open. If the
pipeline cannot fit, the options include raising the limit only while it runs, or
moving the heaviest stage to the workstation.

### G-0006-4. File ownership across the container boundary

- **Kind:** design
- **Needed by:** phase 3

In an unprivileged container, user ids are shifted on the host. The WRF data volume is
owned by an ordinary host account; mounted into the guest it would appear to belong to
nobody. Docker containers inside the guest add a third set of user ids. A mapping has
to be chosen so that the pipeline's containers, staging's containers and the old host
pipeline (which keeps running until cutover, ADR-0025) can all read and write what they
need on the same volume, and so that DVC's shared cache works with group permissions.

### G-0006-5. Where the guest's disk lives and how big it is

- **Kind:** design
- **Needed by:** phase 3

Not yet sized: the guest's root disk (Docker images, including a large Exporter image),
and the growth of the pipeline's cache on the 68 GB data volume, which has 39 GB free
today. Each patch adds whatever changed in the stage outputs: about 200 MB for the
export on the one pair of patches measured, with the other stages still unmeasured
(ADR-0016, G-0016-4).

### G-0006-6. One mechanism for a service to get its database

- **Kind:** decision
- **Needed by:** phase 3

Decision 5 says the API can fetch the database from object storage, so that it can run
anywhere. ADR-0014 describes promotion at home as flipping a local pointer to a file
already on the server's disk. Those are two mechanisms. Running one at home and the
other on a rented server later would mean the rented-server path is untested until the
day it is needed. Options: always fetch from object storage, even at home; or keep the
local pointer and accept that the remote path is future work.

### G-0006-7. Starting again after a power cut

- **Kind:** design
- **Needed by:** phase 3

The guest and its containers must come back on their own after the laptop restarts:
guest start-on-boot, Docker restart policies, the scheduled jobs, and the tunnel. Not
specified. The host's wifi comes up through a custom service, which the guest's network
depends on.

### G-0006-8. Valheim's memory under load

- **Kind:** verification
- **Needed by:** before the WRF guest's limit is finalised

The reduction to 3 GiB rests on a measurement with two players (about 2.0 GB peak). Six
players was not measured. If Valheim needs more, the WRF budget shrinks.

### G-0006-9. When to move the API and bot to a rented server

- **Kind:** decision
- **Needed by:** not scheduled

The later split is described as likely but has no trigger. A useful trigger would be a
stated tolerance, for example "the bot being unavailable for more than N hours in a
month". Without monitoring (ADR-0024) there is currently no way to know that number.

### G-0006-10. Host upgrades

- **Kind:** decision
- **Needed by:** after cutover

G-0006-1 exists because a routine package update changed behaviour. After cutover, a
Proxmox or Docker upgrade can break production. No policy says when upgrades are
applied or how they are tested first (staging runs in the same guest, so it shares the
same Docker).

## References

- `docs/research/2026-10-baseline.md`, sections 2.3 and 3.
- `docs/research/external-facts.md`, "Proxmox, LXC and Docker".
- Proxmox container documentation: https://pve.proxmox.com/pve-docs/pct.1.html
