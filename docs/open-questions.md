# Open questions

Every gap named in the ADRs, in one place. **This file is generated** by
`tools/docs/gen_open_questions.py` from the "Gaps and open questions" section of
each ADR. Do not edit it; edit the ADR and regenerate.

A gap is one of four kinds:

- **decision**: the maintainer has to choose;
- **verification**: a fact has to be checked or measured;
- **design**: something has to be worked out and written down;
- **action**: something has to be done.

Open: 195. Resolved: 5.

## Counts

| Kind | Open |
|---|---|
| decision | 61 |
| verification | 34 |
| design | 84 |
| action | 16 |

## By ADR

### ADR-0001: Record architecture decisions

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0001-1](adr/0001-record-architecture-decisions.md) | decision | before the first gap is closed | How resolved gaps are recorded |
| [G-0001-2](adr/0001-record-architecture-decisions.md) | action | before phase 0 of the migration | Review and acceptance of this first set |
| [G-0001-3](adr/0001-record-architecture-decisions.md) | decision | before the first ADR written by someone other than the maintainer | Who may accept an ADR |
| [G-0001-4](adr/0001-record-architecture-decisions.md) | design | phase 1 (when CI is set up) | Checking the generated question list in CI |

### ADR-0002: One repository for all WRF code

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0002-4](adr/0002-one-repository.md) | design | phase 1 | Agent skills and per-repository instructions |
| [G-0002-5](adr/0002-one-repository.md) | action | phase 5 (cutover) | Order of archiving against the old DV redirect page |
| [G-0002-6](adr/0002-one-repository.md) | action | phase 5 (cutover) | Open issues and pull requests in the old repositories |
| [G-0002-7](adr/0002-one-repository.md) | action | before the first ADR commit is pushed | Review of what the public repository reveals |
| [G-0002-8](adr/0002-one-repository.md) | verification | phase 1 | Whether Design has other consumers |

### ADR-0003: Repository layout and workspaces

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0003-1](adr/0003-repository-layout.md) | decision | phase 1 | Which Python version |
| [G-0003-2](adr/0003-repository-layout.md) | decision | phase 2 | Two settings systems |
| [G-0003-4](adr/0003-repository-layout.md) | design | phase 2 | How TypeScript types are generated from the models |
| [G-0003-5](adr/0003-repository-layout.md) | decision | phase 2 | Is DVC a workspace dependency or a separate tool |
| [G-0003-6](adr/0003-repository-layout.md) | verification | phase 4 | The published codec file is used from outside |
| [G-0003-7](adr/0003-repository-layout.md) | design | phase 2 | Where the pipeline's working data lives relative to the checkout |
| [G-0003-8](adr/0003-repository-layout.md) | design | phase 3 | The `wrf` command |
| [G-0003-9](adr/0003-repository-layout.md) | decision | phase 1 | Agent instruction files |
| [G-0003-10](adr/0003-repository-layout.md) | design | phase 4 | End-to-end tests are named but not designed |

### ADR-0004: Continuous integration and required checks

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0004-1](adr/0004-continuous-integration.md) | design | phase 1 | The dependency map between paths and jobs |
| [G-0004-2](adr/0004-continuous-integration.md) | decision | phase 4, and earlier for any pull request touching the Site | The Site cannot be built in CI without data |
| [G-0004-3](adr/0004-continuous-integration.md) | decision | phase 3 | When images are built |
| [G-0004-4](adr/0004-continuous-integration.md) | verification | phase 1 | Tests that need real game data or a GPU |
| [G-0004-5](adr/0004-continuous-integration.md) | decision | phase 2 | Pipeline commits against a protected branch |
| [G-0004-6](adr/0004-continuous-integration.md) | decision | after cutover | Keeping exactly pinned dependencies current |
| [G-0004-7](adr/0004-continuous-integration.md) | design | phase 1 | Checks for the documents themselves |
| [G-0004-8](adr/0004-continuous-integration.md) | verification | phase 3 (before any deploy secret is stored) | Workflow security on a public repository |

### ADR-0005: Versioning and release model

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0005-1](adr/0005-versioning-and-releases.md) | decision | phase 3 | The exact form of the version string |
| [G-0005-2](adr/0005-versioning-and-releases.md) | decision | phase 3 | A tag whose build fails |
| [G-0005-3](adr/0005-versioning-and-releases.md) | design | phase 3 | A code release that changes the data |
| [G-0005-4](adr/0005-versioning-and-releases.md) | design | phase 3 | Rolling back |
| [G-0005-5](adr/0005-versioning-and-releases.md) | design | phase 3 | How the pipeline knows which release is deployed |
| [G-0005-6](adr/0005-versioning-and-releases.md) | design | phase 2 (schema), the API phase (API) | Schema and API version rules |
| [G-0005-7](adr/0005-versioning-and-releases.md) | decision | after cutover | Urgent fixes |

### ADR-0006: Hosting topology

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0006-1](adr/0006-hosting-topology.md) | verification | the start of phase 3; this is the first thing to try | Docker inside an unprivileged container on this Proxmox version |
| [G-0006-2](adr/0006-hosting-topology.md) | verification | phase 3, before anything depends on the guest for patch days | The Exporter's mapper inside Docker inside the guest |
| [G-0006-3](adr/0006-hosting-topology.md) | verification | phase 3 | Whether the pipeline fits in the limit |
| [G-0006-4](adr/0006-hosting-topology.md) | design | phase 3 | File ownership across the container boundary |
| [G-0006-5](adr/0006-hosting-topology.md) | design | phase 3 | Where the guest's disk lives and how big it is |
| [G-0006-6](adr/0006-hosting-topology.md) | decision | phase 3 | One mechanism for a service to get its database |
| [G-0006-7](adr/0006-hosting-topology.md) | design | phase 3 | Starting again after a power cut |
| [G-0006-8](adr/0006-hosting-topology.md) | verification | before the WRF guest's limit is finalised | Valheim's memory under load |
| [G-0006-9](adr/0006-hosting-topology.md) | decision | not scheduled | When to move the API and bot to a rented server |
| [G-0006-10](adr/0006-hosting-topology.md) | decision | after cutover | Host upgrades |

### ADR-0007: Containers, images and deployment

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0007-1](adr/0007-containers-and-deployment.md) | design | phase 2, before the pipeline is wired | "No code checkout" against what the pipeline needs |
| [G-0007-2](adr/0007-containers-and-deployment.md) | design | phase 2 | Stages that live in different images |
| [G-0007-3](adr/0007-containers-and-deployment.md) | decision | phase 3 | Three environments, two names |
| [G-0007-4](adr/0007-containers-and-deployment.md) | decision | phase 3 | How selective a deployment must be |
| [G-0007-5](adr/0007-containers-and-deployment.md) | design | phase 3 | The deploy script is unspecified |
| [G-0007-6](adr/0007-containers-and-deployment.md) | decision | phase 3 | How `wrf release` reaches the guest |
| [G-0007-7](adr/0007-containers-and-deployment.md) | decision | phase 3 | Are the images public |
| [G-0007-8](adr/0007-containers-and-deployment.md) | design | phase 3 | Logs |
| [G-0007-9](adr/0007-containers-and-deployment.md) | design | phase 3 | Non-secret configuration per environment |
| [G-0007-10](adr/0007-containers-and-deployment.md) | verification | phase 3 | Image size and pull time |

### ADR-0008: Environments: local, staging and production

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0008-1](adr/0008-environments.md) | decision | phase 3 | Is "dev" on the server a third environment |
| [G-0008-2](adr/0008-environments.md) | decision | phase 3 | Staging storage: a prefix or separate buckets |
| [G-0008-3](adr/0008-environments.md) | design | phase 2 | What staging does with accumulated state |
| [G-0008-4](adr/0008-environments.md) | decision | phase 3 | The scheduled jobs in staging |
| [G-0008-5](adr/0008-environments.md) | verification | phase 2 | Staging's shared write access to the stage cache |
| [G-0008-6](adr/0008-environments.md) | design | phase 2 | Data release ids in staging |
| [G-0008-7](adr/0008-environments.md) | decision | phase 3 | Credentials that staging shares with production |
| [G-0008-8](adr/0008-environments.md) | design | phase 4 | How the staging Site gets built and deployed |
| [G-0008-9](adr/0008-environments.md) | design | phase 2 | What can be done on the workstation |
| [G-0008-10](adr/0008-environments.md) | design | phase 2 | Protection against a staging run writing to production |

### ADR-0009: Data store: a SQLite file, rebuilt and swapped

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0009-1](adr/0009-data-store.md) | decision | phase 2 | Which SQLite versions must be supported |
| [G-0009-2](adr/0009-data-store.md) | decision | phase 2 | Binary JSON or text JSON for stored documents |
| [G-0009-3](adr/0009-data-store.md) | verification | phase 2 | What `sqldiff` can and cannot show |
| [G-0009-4](adr/0009-data-store.md) | design | phase 3 | How the swap works, and how readers notice |
| [G-0009-5](adr/0009-data-store.md) | design | phase 3 | The swap is not atomic across consumers |
| [G-0009-6](adr/0009-data-store.md) | design | phase 4 | Data the browser fetches at run time |
| [G-0009-7](adr/0009-data-store.md) | decision | phase 4 | What "no public dataset" means |
| [G-0009-8](adr/0009-data-store.md) | decision | phase 2 | How long the intermediate JSON is kept |

### ADR-0010: Database schema: documents plus generic relations

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0010-1](adr/0010-database-schema.md) | design | phase 2 | The actual table definitions |
| [G-0010-2](adr/0010-database-schema.md) | decision | phase 2 | What identifies an object |
| [G-0010-3](adr/0010-database-schema.md) | design | phase 2 | What a `refs` row contains |
| [G-0010-4](adr/0010-database-schema.md) | design | phase 4 | Text search does not cover what the bot does today |
| [G-0010-5](adr/0010-database-schema.md) | design | phase 2 | Which fields the models must get right first |
| [G-0010-6](adr/0010-database-schema.md) | design | phase 2 | Generating models from current JSON |
| [G-0010-7](adr/0010-database-schema.md) | design | phase 4 | How localization is exposed |
| [G-0010-8](adr/0010-database-schema.md) | design | phase 2 | The contents of `meta` |
| [G-0010-9](adr/0010-database-schema.md) | decision | phase 2 | Whether promoted columns duplicate or replace document fields |

### ADR-0011: Object shape: three tiers

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0011-1](adr/0011-object-shape-three-tiers.md) | decision | phase 2 | "Above WARNING blocks" is new behaviour, and one level sits in between |
| [G-0011-2](adr/0011-object-shape-three-tiers.md) | decision | phase 6 (when the first type is reshaped) | The tier 2 split was the assistant's reading |
| [G-0011-3](adr/0011-object-shape-three-tiers.md) | design | phase 6 | The format of the lifting map |
| [G-0011-4](adr/0011-object-shape-three-tiers.md) | design | phase 6 | When a sub-structure deserves to be an object |
| [G-0011-5](adr/0011-object-shape-three-tiers.md) | verification | the API phase | How much `detail` weighs, and who can see it |
| [G-0011-6](adr/0011-object-shape-three-tiers.md) | design | phase 2 | Validating twice |

### ADR-0012: Accumulated state lives in git

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0012-1](adr/0012-accumulated-state.md) | decision | phase 2; this blocks the pipeline design | Which branch the pipeline commits to, and which state it reads |
| [G-0012-2](adr/0012-accumulated-state.md) | design | phase 2 | What a committed `dvc.lock` means |
| [G-0012-3](adr/0012-accumulated-state.md) | design | phase 2 | Two writers |
| [G-0012-4](adr/0012-accumulated-state.md) | design | phase 2 | State written by one release and read by another |
| [G-0012-5](adr/0012-accumulated-state.md) | design | phase 2 (the import) | Which existing files are state |
| [G-0012-6](adr/0012-accumulated-state.md) | design | phase 2 | Committed state that never went live |
| [G-0012-7](adr/0012-accumulated-state.md) | decision | after cutover | Reviewing what the pipeline commits |

### ADR-0013: Slugs and link stability

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0013-1](adr/0013-slugs-and-link-stability.md) | design | phase 4 | On Cloudflare, a redirect wins over a real page |
| [G-0013-2](adr/0013-slugs-and-link-stability.md) | verification | phase 4 | The redirect limit |
| [G-0013-3](adr/0013-slugs-and-link-stability.md) | design | phase 4 | Chains and loops |
| [G-0013-4](adr/0013-slugs-and-link-stability.md) | decision | phase 4 | A reused name silently points somewhere else |
| [G-0013-5](adr/0013-slugs-and-link-stability.md) | design | phase 2 (the import) | Seeding the history at migration |
| [G-0013-6](adr/0013-slugs-and-link-stability.md) | verification | phase 4 (on staging) | Redirect sources and trailing slashes |
| [G-0013-7](adr/0013-slugs-and-link-stability.md) | decision | after cutover | An object that changes type |
| [G-0013-8](adr/0013-slugs-and-link-stability.md) | verification | not scheduled | The evidence window is short |

### ADR-0014: The swap gate

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0014-1](adr/0014-swap-gate.md) | design | phase 2 | Assets are uploaded before the gate has passed |
| [G-0014-2](adr/0014-swap-gate.md) | design | phase 3 | Promotion is several steps, and the Site is built twice |
| [G-0014-3](adr/0014-swap-gate.md) | design | phase 2 | Where the gate's code lives and what runs it |
| [G-0014-4](adr/0014-swap-gate.md) | design | phase 2 | The count threshold on small types |
| [G-0014-5](adr/0014-swap-gate.md) | design | phase 2 | Canaries that name game objects |
| [G-0014-6](adr/0014-swap-gate.md) | design | phase 2 | Which localization keys are checked |
| [G-0014-7](adr/0014-swap-gate.md) | decision | phase 3 | The override when nobody is awake |
| [G-0014-8](adr/0014-swap-gate.md) | design | phase 2 | What exactly the discount-week release re-checks |
| [G-0014-9](adr/0014-swap-gate.md) | action | phase 5 (cutover) | The patch-day runbook |

### ADR-0015: Data release ids and the database archive

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0015-1](adr/0015-data-releases-and-db-archive.md) | design | phase 2 | A quiet period can lose a patch database |
| [G-0015-2](adr/0015-data-releases-and-db-archive.md) | design | phase 2 | Where the counter `n` comes from |
| [G-0015-3](adr/0015-data-releases-and-db-archive.md) | design | phase 3 | What a rollback restores |
| [G-0015-4](adr/0015-data-releases-and-db-archive.md) | verification | not scheduled | The claim that a patch database can be rebuilt |
| [G-0015-5](adr/0015-data-releases-and-db-archive.md) | verification | phase 3 | Storage rules to confirm at set-up |
| [G-0015-6](adr/0015-data-releases-and-db-archive.md) | design | after cutover | Comparing two archived databases |
| [G-0015-7](adr/0015-data-releases-and-db-archive.md) | design | phase 3 | Local copies and the stage cache |

### ADR-0016: Pipeline stage caching with DVC

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0016-1](adr/0016-pipeline-stage-caching.md) | design | phase 2; blocks the pipeline wiring | Where DVC's project directory is, and what is checked out in it |
| [G-0016-2](adr/0016-pipeline-stage-caching.md) | design | phase 2 | Where DVC runs relative to the containers |
| [G-0016-3](adr/0016-pipeline-stage-caching.md) | design | phase 2 | Cleaning a cache that several workspaces share |
| [G-0016-4](adr/0016-pipeline-stage-caching.md) | verification | phase 2 | How fast the cache grows |
| [G-0016-5](adr/0016-pipeline-stage-caching.md) | verification | phase 2 | Whether stages are deterministic |
| [G-0016-6](adr/0016-pipeline-stage-caching.md) | decision | phase 2 | Every dependency upgrade re-runs the export |
| [G-0016-7](adr/0016-pipeline-stage-caching.md) | design | phase 2 | Stage boundaries |
| [G-0016-8](adr/0016-pipeline-stage-caching.md) | verification | phase 2 | A failed stage leaves its output missing |
| [G-0016-9](adr/0016-pipeline-stage-caching.md) | action | phase 2 | Tool housekeeping |

### ADR-0017: Discount data

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0017-1](adr/0017-discount-data.md) | decision | phase 2 | What happens when an announced item cannot be mapped |
| [G-0017-2](adr/0017-discount-data.md) | design | phase 2 | The matcher, and Jev's place in it |
| [G-0017-3](adr/0017-discount-data.md) | verification | phase 2 | What exactly `manual_mapping.json` does |
| [G-0017-4](adr/0017-discount-data.md) | design | phase 2 | Robot expansion and what a discount item is |
| [G-0017-5](adr/0017-discount-data.md) | decision | phase 2 | Prediction history as state |
| [G-0017-6](adr/0017-discount-data.md) | design | phase 4 | The link-preview screenshot |
| [G-0017-7](adr/0017-discount-data.md) | verification | phase 2 | Detection depends on a third party's page |
| [G-0017-8](adr/0017-discount-data.md) | decision | phase 3 | How often the watch runs and when it reports |

### ADR-0018: API rollout in waves

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0018-1](adr/0018-api-rollout.md) | decision | phase 3 | A hostname is needed now |
| [G-0018-2](adr/0018-api-rollout.md) | decision | phase 3 | Who can reach the placeholder |
| [G-0018-3](adr/0018-api-rollout.md) | design | phase 3 | Picking up a new database |
| [G-0018-4](adr/0018-api-rollout.md) | decision | not scheduled | What triggers waves 2 and 3 |
| [G-0018-5](adr/0018-api-rollout.md) | design | wave 2 | The bot's query rules as an API |
| [G-0018-6](adr/0018-api-rollout.md) | design | wave 2 | Versioning the API |

### ADR-0019: Cloudflare for DNS, site hosting and the tunnel

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0019-2](adr/0019-cloudflare-dns-hosting-tunnel.md) | design | phase 0 | The DNS move, step by step |
| [G-0019-3](adr/0019-cloudflare-dns-hosting-tunnel.md) | decision | phase 4 | How the data bucket is read from GitHub Actions |
| [G-0019-4](adr/0019-cloudflare-dns-hosting-tunnel.md) | design | phase 4 | Two things can deploy the Site |
| [G-0019-5](adr/0019-cloudflare-dns-hosting-tunnel.md) | design | phase 3 | Image and model domains, and cross-origin requests |
| [G-0019-6](adr/0019-cloudflare-dns-hosting-tunnel.md) | verification | phase 4 | Things to confirm on staging |
| [G-0019-7](adr/0019-cloudflare-dns-hosting-tunnel.md) | verification | phase 5 | The old DV stub and archiving |
| [G-0019-8](adr/0019-cloudflare-dns-hosting-tunnel.md) | action | phase 0 | Account security |
| [G-0019-9](adr/0019-cloudflare-dns-hosting-tunnel.md) | verification | phase 4 | Limits to keep in view |
| [G-0019-10](adr/0019-cloudflare-dns-hosting-tunnel.md) | decision | phase 5 | `www` and other names |

### ADR-0020: Assets: object storage, image formats and models

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0020-1](adr/0020-assets-images-and-models.md) | decision | phase 2 | Stable names mean uploads overwrite live files |
| [G-0020-2](adr/0020-assets-images-and-models.md) | decision | after cutover | Nothing deletes assets |
| [G-0020-3](adr/0020-assets-images-and-models.md) | design | phase 4 | How code in the browser gets hashes and copies |
| [G-0020-4](adr/0020-assets-images-and-models.md) | verification | phase 4 (on staging) | Model files: caching, compression and cross-origin access |
| [G-0020-5](adr/0020-assets-images-and-models.md) | design | phase 2 | Details the encoding rule leaves open |
| [G-0020-6](adr/0020-assets-images-and-models.md) | verification | phase 2 | The encoder is an input to the hash |
| [G-0020-7](adr/0020-assets-images-and-models.md) | verification | phase 4 | Quality was judged on one kind of image |
| [G-0020-8](adr/0020-assets-images-and-models.md) | verification | phase 4 | WebP in Discord embeds |
| [G-0020-9](adr/0020-assets-images-and-models.md) | design | phase 2 | Upload mechanics |

### ADR-0021: URL structure of the merged site

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0021-1](adr/0021-site-url-structure.md) | verification | phase 4 (on staging) | Redirects, real pages and trailing slashes on the host |
| [G-0021-2](adr/0021-site-url-structure.md) | decision | phase 4 | Which address is canonical for the latest week |
| [G-0021-3](adr/0021-site-url-structure.md) | verification | phase 4 | Outside users of files that are moving |
| [G-0021-4](adr/0021-site-url-structure.md) | design | phase 4 | What generates the files under `/data/` |
| [G-0021-5](adr/0021-site-url-structure.md) | action | phase 5 (cutover) | Legal pages and the Discord application |
| [G-0021-6](adr/0021-site-url-structure.md) | design | phase 4 | How staging-only pages are kept out of production |
| [G-0021-7](adr/0021-site-url-structure.md) | action | phase 4 | Sitemap and robots file |
| [G-0021-8](adr/0021-site-url-structure.md) | verification | phase 4 | `/shoulder_profiles` and other existing redirects |

### ADR-0022: Secrets and the AI agent's access

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0022-1](adr/0022-secrets-and-agent-access.md) | action | phase 0 | The guard does not exist yet |
| [G-0022-2](adr/0022-secrets-and-agent-access.md) | decision | phase 2 | The Steam password is passed on a command line |
| [G-0022-3](adr/0022-secrets-and-agent-access.md) | design | phase 3 | File permissions for secrets inside containers |
| [G-0022-4](adr/0022-secrets-and-agent-access.md) | decision | phase 3 | Secrets in backups |
| [G-0022-5](adr/0022-secrets-and-agent-access.md) | action | phase 3 | The list of secrets |
| [G-0022-6](adr/0022-secrets-and-agent-access.md) | action | phase 5 (cutover) | Retiring the old secrets |
| [G-0022-7](adr/0022-secrets-and-agent-access.md) | decision | after cutover | Rotation |
| [G-0022-8](adr/0022-secrets-and-agent-access.md) | verification | phase 2 | What the log filter cannot catch |
| [G-0022-9](adr/0022-secrets-and-agent-access.md) | action | phase 0 | Account security outside the machines |

### ADR-0023: Backups and recovery

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0023-1](adr/0023-backups-and-recovery.md) | verification | phase 3 | What the dump includes and excludes, exactly |
| [G-0023-2](adr/0023-backups-and-recovery.md) | decision | phase 3 | Secrets in an unencrypted dump |
| [G-0023-3](adr/0023-backups-and-recovery.md) | decision | after cutover | A backup that silently stops |
| [G-0023-4](adr/0023-backups-and-recovery.md) | decision | not scheduled | The drill covers one failure, not the worst one |
| [G-0023-5](adr/0023-backups-and-recovery.md) | design | phase 3 | Where operational state lives |
| [G-0023-6](adr/0023-backups-and-recovery.md) | action | phase 0 (it should be started with the DNS move) | `docs/cloudflare.md` does not exist yet |

### ADR-0024: Observability: email reports only, for now

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0024-1](adr/0024-observability.md) | decision | after cutover | Which silent failures are worth closing first |
| [G-0024-2](adr/0024-observability.md) | design | phase 2 | What the new run report contains |
| [G-0024-3](adr/0024-observability.md) | design | phase 3 | Logs: where they go and how long they are kept |
| [G-0024-4](adr/0024-observability.md) | decision | phase 3 | Reports from staging |
| [G-0024-5](adr/0024-observability.md) | decision | before any decision to rent a server | Knowing how available the bot and API are |

### ADR-0025: Migration strategy

| Gap | Kind | Needed by | Question |
|---|---|---|---|
| [G-0025-1](adr/0025-migration-strategy.md) | decision | before phase 5; ideally sketched before phase 3, since it shapes the deploy script | The cutover procedure and rollback are not decided |
| [G-0025-2](adr/0025-migration-strategy.md) | design | phase 4 | How to know the new system matches the old one |
| [G-0025-3](adr/0025-migration-strategy.md) | action | the start of phase 3, and before phase 2 goes far | The risky assumptions should be tested before the work that depends on them |
| [G-0025-4](adr/0025-migration-strategy.md) | decision | the start of phase 2 | Design questions that block phase 2 |
| [G-0025-5](adr/0025-migration-strategy.md) | decision | phase 1 | Keeping the freeze honest |
| [G-0025-6](adr/0025-migration-strategy.md) | design | phase 3 (as soon as anything runs in the guest) | The shared lock between the old and new pipelines |
| [G-0025-7](adr/0025-migration-strategy.md) | design | phase 2 (the script), phase 5 (its last run) | The final state import |
| [G-0025-8](adr/0025-migration-strategy.md) | action | phase -1 | No estimate |
| [G-0025-9](adr/0025-migration-strategy.md) | design | phase 5 | Moving the bot |

## Resolved

| Gap | Resolved | Question |
|---|---|---|
| [G-0002-1](adr/0002-one-repository.md) | 2026-10-19 | Commit messages will link to the wrong pull requests |
| [G-0002-2](adr/0002-one-repository.md) | 2026-10-19 | Licence |
| [G-0002-3](adr/0002-one-repository.md) | 2026-10-19 | The old `WRFrontiersDB-API` repository |
| [G-0003-3](adr/0003-repository-layout.md) | 2026-10-19 | One Astro version, one screenshot tool |
| [G-0019-1](adr/0019-cloudflare-dns-hosting-tunnel.md) | 2026-10-19 | The domain has email forwarding records |
