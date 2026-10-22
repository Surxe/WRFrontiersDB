# Architecture overview

A map of the system this repository is being built into. It is a living document: it
is edited as the system changes, and it may add detail to the ADRs but may not
contradict them. Each section names the ADR that holds the reasoning.

**State of this document (2026-10-12): everything here is the planned target. None of
it is built.** The system that is running today is described in
[`research/2026-10-baseline.md`](research/2026-10-baseline.md). Parts of the target
that are not yet designed are marked "open" and point at the gap that tracks them; the
full list is in [`open-questions.md`](open-questions.md).

## 1. What the system does

War Robots: Frontiers (WRF) is a game. This project extracts its data from the game
files and publishes it:

- a **website** with a page for every robot, module, pilot and related object, a robot
  builder with a 3D viewer, and weekly discount pages with history and predictions;
- a **Discord bot** that answers `[[name]]` with a link to the matching page and
  decodes shared build codes;
- an **API**, at first only a placeholder.

Two kinds of event change what is published: a **game patch** (about fifteen a year)
and a **weekly discount announcement**.

## 2. The parts

```
                         game files (Steam)            news feed
                               |                           |
   home server, WRF guest      v                           v
  +------------------------------------------------------------------+
  |  pipeline (scheduled jobs)                                       |
  |    download -> export -> parse -> convert images -> build DB     |
  |         reads and updates accumulated state (state/)             |
  |                              |                                   |
  |                          swap gate                               |
  |                              |                                   |
  |    current database file  <--+     API (FastAPI)     Discord bot |
  |           ^ read-only by ----------^ ----------------^           |
  +-----------|----------------------|-------------------|-----------+
              |                      | tunnel (outbound) | Discord gateway (outbound)
              v                      v                   v
     object storage (R2)        Cloudflare            Discord
     - images, models (public)   - DNS
     - databases (private)       - the website (static)  <--- built by GitHub Actions
                                 - staging site (login)       from a release tag + a database
```

| Part | Where the code is | Runs | ADR |
|---|---|---|---|
| Exporter | `apps/exporter` | pipeline stage, on patch days | 0016 |
| Parser | `apps/parser` | pipeline stage | 0011, 0016 |
| Image conversion | `apps/textures` | pipeline stage | 0020 |
| Database build | `apps/db-build` | pipeline stage | 0009, 0010 |
| Orchestrator | `apps/orchestrator` | scheduled: update probe, discount watch; runs the pipeline, the gate and promotion; sends reports | 0014, 0017, 0024 |
| API | `apps/api` | always on | 0018 |
| Bot | `apps/bot` | always on | 0018 |
| Site | `apps/site` | built in CI, served by Cloudflare | 0019, 0021 |
| Shared code | `packages/` | imported by the above | 0003 |

## 3. How data flows

### 3.1 A game patch

1. The update probe (every 20 minutes) sees a new Steam build and starts the pipeline.
2. DVC works out which stages need to run: all of them, since the game changed
   ([ADR-0016](adr/0016-pipeline-stage-caching.md)).
3. Download (patches the existing game folder in place), export (launches the game
   once to dump a mapping, then extracts assets to JSON), parse, convert images, build
   the database.
4. The swap gate checks the candidate database
   ([ADR-0014](adr/0014-swap-gate.md)). If a blocking check fails, production is left
   as it was and the report says why.
5. Accumulated state and the pipeline's lockfile are committed
   ([ADR-0012](adr/0012-accumulated-state.md)).
6. Promotion: the database is swapped in, the Site is rebuilt and deployed, the API
   and bot pick up the new file.
7. A run report is emailed ([ADR-0024](adr/0024-observability.md)).

### 3.2 A discount week

The discount watch (four times a day) finds a new announcement, maps the announced
names to objects, and writes one file under `state/discounts/`. Only the database
build re-runs. Then the same gate, commit, promotion and report
([ADR-0017](adr/0017-discount-data.md)).

### 3.3 A code release

`wrf release` on the workstation tags the commit. CI tests it and builds the images.
The same command then runs the deploy script on the server, which pulls the images and
restarts the services ([ADR-0005](adr/0005-versioning-and-releases.md),
[ADR-0007](adr/0007-containers-and-deployment.md)). If the release changes how data is
produced, the pipeline re-runs the affected stages. The order of those steps is open
(ADR-0005, G-0005-3).

## 4. Where things run

| Place | What | ADR |
|---|---|---|
| Home server, one container guest (2 GiB memory limit, 0.5 GiB swap) | the pipeline, API, bot, tunnel client, and staging copies of each, as Docker Compose projects | 0006, 0007 |
| Cloudflare | DNS; the website and its staging copy; object storage; the front door of the tunnel | 0019, 0020 |
| GitHub | the code, accumulated state, CI, container images, the Site's deployment workflow | 0002, 0004 |
| Discord | the bot connects out to it | 0018 |
| Workstation | development, and where releases are started | 0007, 0008 |

Nothing at home accepts connections from the internet. The bot and the tunnel client
connect outwards and keep the connection open. The home server is never needed to load
a web page or an image.

## 5. Environments

| | Code comes from | Data | Outputs go to | Started by |
|---|---|---|---|---|
| Local | working copy on the workstation | open (ADR-0008, G-0008-9) | nowhere public | hand |
| Staging | CI-built image of any commit | production's game files, read-only; its own database | staging storage, staging site (behind a login), test bot | the deploy script |
| Production | CI-built image of a release tag | everything | production storage, the public site, the bot | the deploy script; scheduled jobs |

Staging and production share one guest, one stage cache and one lock, so their
pipelines never run at the same time ([ADR-0008](adr/0008-environments.md)). Whether a
separate "dev" environment exists on the server is open (ADR-0008, G-0008-1).

## 6. Where each kind of data lives

| Data | Home | Rebuildable | ADR |
|---|---|---|---|
| Code | this repository | n/a | 0002 |
| Accumulated state: build-code registry, release dates, patch manifests, slug history, discount weeks, news posts | `state/` in this repository | no | 0012 |
| Game download, exports, parsed JSON, the stage cache | the data volume on the server | yes | 0016 |
| The live database, and the two before it | the server | yes | 0009, 0015 |
| Every published database (90 days), one per game patch (kept) | private object storage | yes, slowly | 0015 |
| Images (PNG originals, WebP, resized copies) and models | public object storage | yes | 0020 |
| Secrets | one root-only directory per machine; the maintainer's password manager | n/a | 0022 |
| Operational state: what the probe and the watch have already seen; logs | the guest | partly | 0023 |

## 7. Versions

Four are kept apart ([ADR-0005](adr/0005-versioning-and-releases.md)):

- **code version**: the release tag, a date such as `2026.10.09`;
- **data release id**: the game build's date and a counter, such as `2026-10-06.2`
  ([ADR-0015](adr/0015-data-releases-and-db-archive.md));
- **schema version**: recorded in each database;
- **API version**: in the path, `/v1`.

The bot's `/about`, the Site's `/data/deploy.json` and the API's `/v1/meta` report what
is running.

## 8. Terms

| Term | Meaning |
|---|---|
| Candidate | a database that has been built and not yet promoted |
| Data release | publishing a new database, for a patch, a discount week or a re-run |
| DV | the Discount Visualizer, the former separate discount site |
| Guest | the Linux container on the home server that holds all WRF workloads |
| Promote | make a candidate the live database and deploy the Site built from it |
| Slug | the last part of a page's address, made from the object's name |
| Stage | one step of the pipeline, with declared inputs and outputs |
| State | accumulated data that cannot be rebuilt from game files; lives in `state/` |
| Swap gate | the checks a candidate must pass before promotion |
| Tier 1 / 2 / 3 | the stable, semi-stable and raw parts of an object ([`schema.md`](schema.md)) |
| Wave 1 / 2 / 3 | the steps by which consumers move to the API |

## 9. The largest unknowns

For a reader deciding where to look first. Each is a gap in an ADR.

1. Whether the Exporter's game-launching step works inside the container guest
   (ADR-0006, G-0006-2). Docker itself was verified there (G-0006-1).
2. Whether the pipeline fits in the guest's memory limit (ADR-0006, G-0006-3).
3. How the pipeline can run a release tag's code while reading and committing the
   latest state (ADR-0012, G-0012-1; ADR-0016, G-0016-1 and G-0016-2).
4. How a code release that changes the data is deployed (ADR-0005, G-0005-3).
5. The cutover procedure (ADR-0025, G-0025-1).
