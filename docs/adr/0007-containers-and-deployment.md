# ADR-0007: Containers, images and deployment

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-09 (Docker, images, deploy path), 2026-10-10 (scheduled jobs, tunnel, staging through the deploy script) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0004 (CI), ADR-0005 (releases), ADR-0006 (hosting), ADR-0008 (environments), ADR-0016 (DVC), ADR-0022 (secrets) |

## Context

ADR-0006 puts every WRF workload in one container guest at home and asks that
production differ from local development as little as possible. This ADR covers how
the workloads are packaged, how a release reaches the server, and how recurring jobs
run.

What exists today (baseline, sections 2 and 3):

- Services are systemd units on the host that run Python straight from a git working
  copy, in a virtual environment built by hand on that machine.
- "Deploying" a change means pulling the repository on the server. The bot runs
  whatever is checked out.
- Recurring work (the update probe every 20 minutes, the discount watch four times a
  day) is systemd timers.
- The server cannot be reached from the internet, and guests cannot be reached from
  the home network except through the host.

## Decision

### Packaging

1. **Docker and Docker Compose, both locally and in production.**
2. **CI builds the images** and pushes them to GitHub's container registry, tagged with
   the release version and the commit hash (ADR-0004, ADR-0005). The server only pulls.
3. **An image holds code. Data is mounted.** The database file is mounted read-only
   into the services that read it, so the same image runs locally, at home and on a
   rented server against the same file. (Recorded as a leaning on 2026-10-08; nothing
   since has contradicted it.)
4. **One Dockerfile per deployed app, in that app's folder.** The expected images are
   `api`, `bot`, a Python `pipeline` image (orchestrator, parser, textures, db-build)
   and an `exporter` image (Proton, WRFrontiersDB-CUE4Parse, GPU libraries). The grouping is to be
   settled at implementation.
5. **Long-running services are Compose services**: the API, the bot, and the tunnel
   client (`cloudflared`, one per Compose stack; ADR-0019).

### What is on the server

6. **Production runs CI-built images named by release tag.** It has no working copy of
   the code: only a root-owned `compose.yml`, the deploy script, configuration and
   secret files, and the data volume. Nobody edits these by hand; they are copied from
   this repository's `deploy/` by the deploy script.
7. **Development runs beside it as a second Compose project**
   (`docker compose -p wrfdb-dev --profile dev`), from an ordinary clone.
8. **Staging is deployed with the same deploy script as production**
   (`deploy --env staging <ref>`), never started by hand, so every staging run also
   tests the deployment itself (ADR-0008).

### How a release reaches the server

9. **`wrf release`, run on the workstation, does the whole thing**: it creates and
   pushes the tag; waits while GitHub Actions tests and builds the images; then
   connects to the server over the home network and runs the deploy script inside the
   guest (through the host, since guests are not directly reachable).
10. **GitHub never connects into the home network**, and there is no self-hosted runner
    (ADR-0004).
11. **Accepted limitation: releases can only be made from home.**
12. **The deploy script checks the API's `/v1/meta` endpoint** to confirm that the new
    version is up and which data it is serving (ADR-0018).

### Recurring jobs

13. **Schedules are systemd timers inside the guest**, each running
    `docker compose run --rm pipeline <command>` under a lock (ADR-0008). The unit
    files live in `deploy/` and are installed by the deploy script. Locally, the same
    commands are run by hand.

## Alternatives considered

- **Podman with Quadlet** (containers managed directly by systemd, no daemon). It fits
  a server well. Rejected because of the principle in ADR-0006: local work would use
  `docker compose up` and production would not. Docker is also already in use on the
  workstation and inside the Valheim VM. The maintainer's position was that Podman
  would only make sense if it were used locally too.
- **Keep running from a git working copy.** Nothing to build. Rejected: what runs
  depends on the state of a directory and of a hand-built virtual environment, and it
  cannot be reproduced elsewhere.
- **Build images on the server.** Rejected: memory (ADR-0006).
- **Let CI deploy**, through a self-hosted runner or an inbound connection. Rejected in
  ADR-0004.
- **A scheduler container inside the Compose stack** (cron or a similar image) instead
  of systemd timers. It would move with the stack to any host. Rejected: it would also
  fire on the workstation unless switched off there, and it gives up the journal and
  `systemctl list-timers` visibility that every other job on this server already has.
- **A remote-access mesh (Tailscale)** to allow releasing from anywhere. Raised and
  declined; releasing only from home was accepted instead.
- **Kubernetes (k3s)** was not seriously considered: far more machinery than four
  containers on one small machine need.

## Consequences

- What runs in production is an image built from a tagged commit, the same image that
  was tested, and the same one staging ran.
- Local, staging and production differ in configuration and credentials, not in how
  things are started.
- A release takes as long as CI plus an image pull over home wifi. Image size now
  matters; the Exporter image in particular will be large.
- Every release produces a new image tag for every app. As designed, a deployment
  therefore restarts every service, changed or not. The maintainer accepted "a smarter
  deploy script (restart only what changed)" as a cost of the monorepo; how smart it
  has to be is G-0007-4.
- The files in `deploy/` are production configuration. A wrong edit there is a
  production change at the next deployment.

## Gaps and open questions

### G-0007-1. "No code checkout" against what the pipeline needs

- **Kind:** design
- **Needed by:** phase 2, before the pipeline is wired

Decision 6 says production has no working copy. But the pipeline, as designed
elsewhere, needs three things that live in the repository: the stage definitions
(`dvc.yaml`, `params.yaml`), the accumulated state it reads and then commits
(`state/`, ADR-0012), and a place inside a project directory for stage outputs, because
DVC only caches outputs inside its project (ADR-0016). The API and bot can run from
images alone; the pipeline cannot, as currently described. Either the pipeline gets a
managed checkout on the data volume (a deliberate exception to decision 6), or the
stage definitions are baked into the pipeline image and only `state/` is checked out.
ADR-0016, G-0016-1, discusses the options.

### G-0007-2. Stages that live in different images

- **Kind:** design
- **Needed by:** phase 2

Decision 13 runs the pipeline as `docker compose run --rm pipeline <command>`, and
decision 4 gives the Exporter its own image. Then the pipeline container, which runs
DVC, has to start a stage that lives in another image. From inside a container that
means handing it the Docker socket (which is equivalent to root on the guest) or
running Docker inside Docker. The alternatives are to run DVC on the guest itself, with
each stage's command being a `docker compose run`, or to build one large pipeline
image that includes the Exporter's dependencies. See ADR-0016, G-0016-2.

### G-0007-3. Three environments, two names

- **Kind:** decision
- **Needed by:** phase 3

The decisions use "dev" and "staging" for things on the server that may or may not be
the same: a Compose project run from a working copy (decision 7), and an environment
deployed by script from CI-built images (decision 8). ADR-0008 proposes treating them
as two distinct environments and names the open points.

### G-0007-4. How selective a deployment must be

- **Kind:** decision
- **Needed by:** phase 3

Options, from simple to complex: restart everything on every release (a few seconds of
bot downtime, a few times a month); let Compose recreate only services whose image
content actually changed (requires image builds to be reproducible enough that an
unchanged app yields an identical image, which is not guaranteed); or have the deploy
script decide from the changed paths between two tags.

**Proposed default:** restart everything. Revisit only if the downtime is noticed.

### G-0007-5. The deploy script is unspecified

- **Kind:** design
- **Needed by:** phase 3

It is the most safety-critical piece of new code and has only been named. It needs a
written behaviour for: installing or updating the Compose file and timer units;
pulling images; running or triggering the pipeline when the release changes the data
(ADR-0005, G-0005-3); health checking; what it does when a step fails half-way;
`rollback`; refusing to run while a pipeline run holds the lock; and what `--env`
changes.

### G-0007-6. How `wrf release` reaches the guest

- **Kind:** decision
- **Needed by:** phase 3

Two routes were mentioned: run a command in the guest from the host (Proxmox's
`pct exec`, which needs root on the host), or SSH into the guest through the host
(which needs an SSH server and keys in the guest). The first reuses access that already
exists; the second works the same on a rented server later.

### G-0007-7. Are the images public

- **Kind:** decision
- **Needed by:** phase 3

Public images need no pull credential on the server and the code is public anyway.
This was proposed as part of a larger design that was otherwise rejected (ADR-0022) and
then carried into the plan without being confirmed on its own. It comes with a rule
that must then always hold: an image never contains a secret or game data. The Exporter
image raises a further question: whether a third party's custom Proton build may be
redistributed inside a public image, or should instead be mounted from the data volume
as it is today.

### G-0007-8. Logs

- **Kind:** design
- **Needed by:** phase 3

Container logs default to JSON files that grow without limit. The pipeline today writes
one log file per stage and attaches them to the report email (baseline, section 2.1).
Where service logs and pipeline logs go in the new layout, how long they are kept, and
how they stay readable from the host, is not designed. See ADR-0024.

### G-0007-9. Non-secret configuration per environment

- **Kind:** design
- **Needed by:** phase 3

Secrets have a design (ADR-0022). Ordinary settings that differ between production and
staging (hostnames, bucket names, Discord guild ids, which sinks to write to) do not
yet have a home. They should be checked in, per environment, under `deploy/`.

### G-0007-10. Image size and pull time

- **Kind:** verification
- **Needed by:** phase 3

The Exporter's runtime today includes about 2 GB of Proton and Wine prefix on the data
volume plus system packages. How large its image is, and how long a pull takes on the
server's wifi, should be measured once, because it sets the minimum duration of any
release that touches it.

Measured 2026-10-23 with a stand-in image (`docs/research/2026-10-disk-sizing.md`): the
exporter image is 2.54 GB, 643 MB compressed, with Proton kept on the data volume.
Pulls run at about 86 Mbit/s, so about a minute when its base layers change, seconds
when only the code layer does. The image must set `BATCH_EXPORT_MEMORY_SCOPE=none`
(WRFrontiers-Exporter PR #35).

## References

- `docs/research/2026-10-baseline.md`, sections 2 and 3.
- ADR-0008 for the environments and the lock.
