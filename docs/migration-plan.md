# Migration plan

**TL;DR:** the migration combines the nine separate WRF repositories (Exporter, Parser,
Orchestrator, Data, Site, Discount Visualizer, Discord bot, Design and News-Scraper)
into this one, and moves the system from a JSON data repository, host units and GitHub
Pages to a database, containers in a guest, Cloudflare and one combined site. It
switches over in a single cutover, with the old pipeline still serving patches and
discount weeks until the new system is complete.

The working plan for moving the WRF ecosystem into this repository. It is a living
document: edit it as work proceeds. The strategy behind it, and the alternatives that
were rejected, are in [ADR-0025](adr/0025-migration-strategy.md).

**State (2026-10-12):** the order of work was agreed on 2026-10-11. Phase -1 is in
progress. Phase 5, the cutover itself, is not yet designed.

Each task lists the gaps that must be closed to do it, by id. The ids resolve in
[`open-questions.md`](open-questions.md).

## Ground rules

1. **One cutover.** The old system serves users until the new one is complete.
2. **Freeze the old code, keep the old data flowing.** The old repositories take only
   critical fixes, which are also made here. The old host pipeline keeps running until
   cutover.
3. **The old and new pipelines never run at the same time.** One lock on the host,
   shared into the guest.
4. **Pipe first, reshape later.** Prove the whole new system on today's data shapes.
   Reshape object types after cutover, one at a time.
5. **The state import is re-runnable**, and runs a final time at cutover.

## Before phase -1: learning

The maintainer worked through the technology the plan depends on: Linux containers
(LXC), rented servers against local virtual machines, uv, DVC, and how services at home
are reached. Completed 2026-10-12.

## Phase -1: decision records

- [x] Research baseline and external facts (`docs/research/`).
- [x] ADR-0001 to ADR-0025.
- [x] `docs/architecture.md`, `docs/schema.md`, this plan, the generated question list.
- [ ] Maintainer review of every ADR (G-0001-2), including what the public repository
      reveals (G-0002-7).
- [ ] Decide the design questions that block phase 2, together (G-0025-4).
- [ ] Decide the cutover procedure, at least in outline (G-0025-1).
- [ ] Rough sizes per phase (G-0025-8).

**Done when:** the ADRs are reviewed and merged, and the blocking questions have
answers recorded as new ADRs.

## Phase 0: preparation

Independent of each other and of everything else.

- [ ] **Agent secrets guard** in the shared machine-configuration repository
      (ADR-0022; G-0022-1). Protects the current server at once.
- [ ] **Account security**: two-factor authentication on the Cloudflare, GitHub and
      registrar accounts (G-0019-8).
- [ ] **DNS move** to Cloudflare (ADR-0019). Email forwarding checked: none in use
      (G-0019-1, resolved); write the record list and the way back (G-0019-2); start
      `docs/cloudflare.md` (G-0023-6).
- [x] **Pipeline memory investigation** (G-0006-3). Done 2026-10-21: fits 2.5 GiB
      with 1.5 GiB of swap; the peak is the Parser's model step (G-0006-11, fixed
      in Parser PR #136: the guest is now 2 GiB with 0.5 GiB of swap)
      (`docs/research/2026-10-pipeline-memory.md`).
- [x] Parser fixes for dangling currency references and a missing localization key
      (done in the old Parser repository, 2026-10-10).
- [x] Valheim VM reduced to 3.5 GiB, not the planned 3 GiB (done outside this project;
      the WRF budget is now about 2.5 GiB; G-0006-8).

## Phase 1: repository skeleton

Code moves. Behaviour does not change.

- [x] Decide: licence (G-0002-2). Apache-2.0; `LICENSE` and `NOTICE` at the root.
- [ ] Decide: Python version (G-0003-1); agent instruction files (G-0003-9).
- [ ] History merge with `git filter-repo`, each repository into its folder
      (ADR-0002). Rewrite pull-request numbers in commit messages (G-0002-1). Data
      repository: `tools/` and `tests/` history only. Exporter: Windows DLLs left out
      of tree and history.
- [ ] Record the commit each old repository was merged at (G-0025-5).
- [ ] Convert loose `src/` modules into `src/wrfdb_<app>/` packages (ADR-0003).
- [ ] uv workspace with exact pins; npm workspaces with exact pins; `packages/design`
      replaces the submodule.
- [ ] Drop the Exporter's Windows-only code.
- [ ] Root lint and format configuration.
- [ ] CI: path-scoped jobs and one aggregate required check (ADR-0004; G-0004-1);
      inventory of tests that cannot run on a hosted runner (G-0004-4); `gitleaks`;
      push protection; branch protection; the generated-question-list check (G-0004-7).
- [ ] Consolidate agent skills and instructions (G-0002-4).

**Done when:** every existing test that can run on a hosted runner passes in CI, and
the rest are marked.

## Phase 2: the data path

Needs the answers from G-0025-4 first.

- [ ] `packages/models`: models mirroring today's Parser output, strict for the fields
      consumers read (inventory first: G-0010-5; generation method: G-0010-6);
      `misc` renamed `detail`; the route table; the data release id.
- [ ] `packages/common`: settings and secret loading (G-0003-2), log redaction
      (G-0022-8), slug rules, the shared name matcher (G-0010-4, G-0017-2).
- [ ] `packages/build-codes`: Python and TypeScript codec with one test-vector file.
- [ ] `packages/types`: generated TypeScript types and OpenAPI (G-0003-4).
- [ ] State import script, re-runnable with a merge rule per file (G-0012-5,
      G-0025-7), seeding slug history from today's slug map (G-0013-5).
- [ ] `apps/db-build`: the tables in `docs/schema.md` (G-0010-1, G-0010-2, G-0009-1,
      G-0009-2); the checks it owns (G-0014-3); the predictions step (G-0017-5); what
      `shoulder_profiles.json` gave the Site, so that the Parser's Analysis stage can
      be dropped.
- [ ] `apps/textures`: WebP and resized copies (G-0020-5, G-0020-6); upload
      (G-0020-9, G-0020-1).
- [ ] DVC: stage definitions (G-0016-7), project directory and checkout (G-0016-1),
      where it runs (G-0016-2), shared cache and its clean-up (G-0016-3), determinism
      check (G-0016-5), tool set-up (G-0016-9).
- [ ] Exporter: stop passing the Steam password on a command line; decide where the
      remembered login is kept (G-0022-2).
- [ ] Orchestrator: profiles and configurable sinks (ADR-0008; G-0008-10); release ids
      (G-0015-2); the gate (ADR-0014; G-0014-4, G-0014-5, G-0014-6); promotion
      (G-0014-2); state commits (G-0012-1 to G-0012-4, G-0012-6); the new run report
      (G-0024-2); the discount watch and mapping (G-0017-1, G-0017-3, G-0017-4,
      G-0017-7).
- [ ] Classify every existing error-level log call as blocking or not (G-0011-1).

**Done when:** the pipeline, run on the server, produces a database that passes the
gate, with assets in staging storage.

## Phase 3: infrastructure and deployment

Mostly in parallel with phase 2. **The three spikes come first** (G-0025-3).

- [x] **Spike 1:** create the guest; run a Docker container in it (G-0006-1). Done
      2026-10-21: Docker and Compose work in an unprivileged container with nesting,
      AppArmor left on; the reported breakage does not occur on these versions.
- [ ] **Spike 2:** run the Exporter's mapper inside it (G-0006-2).
- [ ] **Spike 3:** run the pipeline under the memory limit (G-0006-3).
- [ ] In the `home-server` repository: the guest (unprivileged, memory limit, start on
      boot: G-0006-7), GPU access, the shared data volume and its ownership mapping
      (G-0006-4), disk sizing (G-0006-5), the shared lock (G-0025-6), the daily dump
      timer (ADR-0023; G-0023-1, G-0023-2).
- [ ] Decide: environments on the server (G-0008-1); staging storage (G-0008-2);
      how the guest is reached (G-0007-6); whether images are public (G-0007-7).
- [ ] Here: Dockerfiles; `deploy/compose.yml`; per-environment settings (G-0007-9);
      secret files and their permissions (G-0022-3, G-0022-5); logs (G-0007-8,
      G-0024-3); the deploy script, written to a specification (G-0007-5, G-0007-4,
      G-0005-3, G-0005-4); scheduled-job units; `wrf release` (G-0003-8, G-0005-1,
      G-0005-2); image builds in CI (G-0004-3, G-0004-8).
- [ ] Placeholder API with `/v1/meta` (ADR-0018; G-0018-1, G-0018-2); database pickup
      (G-0009-4, G-0018-3); the tunnel.
- [ ] Cloudflare: storage buckets and lifecycle rules (G-0015-1, G-0015-5), asset
      hostname and cross-origin access (G-0019-5), staging login, `docs/cloudflare.md`.

**Done when:** `deploy --env staging <commit>` brings up the staging stack and
`/v1/meta` answers through the staging tunnel. Then the restore drill (ADR-0023).

## Phase 4: consumers

- [ ] Site: upgrade to Astro 6 (G-0003-3); reads the database
      at build; the files it generates under `/data/` (G-0009-6, G-0021-4, G-0020-3,
      G-0010-7); discount pages under `/discounts/`; kebab-case routes; generated
      redirects (G-0013-1, G-0013-2, G-0013-3, G-0021-8); trailing slashes; the image
      component; legal pages (G-0021-5); sitemap and robots file (G-0021-7);
      staging-only test pages (G-0021-6).
- [ ] Site deployment workflow for production and staging (G-0019-3, G-0019-4,
      G-0008-8); a database for CI builds (G-0004-2).
- [ ] Bot: reads the database; the shared route table; image addresses; the test bot.
- [ ] The old DV redirect page, prepared and not deployed.
- [ ] Everything on the staging checklist (G-0019-6, G-0021-1, G-0013-6, G-0020-4,
      G-0020-7, G-0020-8).
- [ ] A parity check of the new site and bot against the old (G-0025-2).

**Done when:** a full staging run works from the deploy script: pipeline, database,
staging site, test bot; and the parity check has been read.

## Phase 5: cutover

Not designed. See G-0025-1 for what the runbook must settle. Items already collected
for it:

- final state import (G-0025-7);
- move the bot (G-0025-9);
- deploy the old DV redirect page, then archive (G-0002-5, G-0019-7);
- update the Discord developer portal's links (G-0021-5);
- `www` and canonical host (G-0019-10);
- retire old secrets and tokens (G-0022-6);
- close or move open issues; archive the old repositories, including the old API
  repository (G-0002-3, G-0002-6);
- rewrite the patch-day runbook (G-0014-9).

## Phase 6: after cutover

Nothing here blocks the switch.

- Three-tier reshaping, one type per pull request (ADR-0011; G-0011-2 to G-0011-4).
- API waves 2 and 3 (ADR-0018; G-0018-4).
- Housekeeping decisions deferred until the system is running: dependency updates
  (G-0004-6), token rotation (G-0022-7), upgrade policy for the host (G-0006-10),
  asset clean-up (G-0020-2), silent-failure monitoring (G-0024-1).
- Parked ideas, tracked outside this repository: a binary format for models; an
  observability service; Terraform for Cloudflare; evaluating Dagster.
