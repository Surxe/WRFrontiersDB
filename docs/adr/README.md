# Architecture decision records

How these records work is itself a decision: see
[ADR-0001](0001-record-architecture-decisions.md). In short: one record per topic; an
accepted record is not rewritten, it is superseded by a new one; and every record
lists what it leaves open.

**Records marked "Draft for maintainer review" have not been reviewed yet.** The
decisions were agreed in conversation between 2026-10-08 and 2026-10-12; for a draft,
the write-up, and in particular the gaps it names, may still change. Once a record is
reviewed, its "Record state" row changes to "Reviewed", so
`grep -l '| Record state | Reviewed |' docs/adr/0*.md` lists the reviewed ones.

## Index

| ADR | Topic | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-one-repository.md) | One repository for all WRF code | Accepted |
| [0003](0003-repository-layout.md) | Repository layout and workspaces | Accepted |
| [0004](0004-continuous-integration.md) | Continuous integration and required checks | Accepted |
| [0005](0005-versioning-and-releases.md) | Versioning and release model | Accepted |
| [0006](0006-hosting-topology.md) | Hosting topology | Accepted |
| [0007](0007-containers-and-deployment.md) | Containers, images and deployment | Accepted |
| [0008](0008-environments.md) | Environments: local, staging and production | Accepted |
| [0009](0009-data-store.md) | Data store: a SQLite file, rebuilt and swapped | Accepted |
| [0010](0010-database-schema.md) | Database schema: documents plus generic relations | Accepted |
| [0011](0011-object-shape-three-tiers.md) | Object shape: three tiers | Accepted |
| [0012](0012-accumulated-state.md) | Accumulated state lives in git | Accepted |
| [0013](0013-slugs-and-link-stability.md) | Slugs and link stability | Accepted |
| [0014](0014-swap-gate.md) | The swap gate | Accepted |
| [0015](0015-data-releases-and-db-archive.md) | Data release ids and the database archive | Accepted |
| [0016](0016-pipeline-stage-caching.md) | Pipeline stage caching with DVC | Accepted |
| [0017](0017-discount-data.md) | Discount data | Accepted |
| [0018](0018-api-rollout.md) | API rollout in waves | Accepted |
| [0019](0019-cloudflare-dns-hosting-tunnel.md) | Cloudflare for DNS, site hosting and the tunnel | Accepted |
| [0020](0020-assets-images-and-models.md) | Assets: object storage, image formats and models | Accepted |
| [0021](0021-site-url-structure.md) | URL structure of the merged site | Accepted |
| [0022](0022-secrets-and-agent-access.md) | Secrets and the AI agent's access | Accepted |
| [0023](0023-backups-and-recovery.md) | Backups and recovery | Accepted |
| [0024](0024-observability.md) | Observability: email reports only, for now | Accepted |
| [0025](0025-migration-strategy.md) | Migration strategy | Accepted, except the cutover procedure |

## Suggested reading order

For someone new to the project:

1. [`../architecture.md`](../architecture.md): what the system is meant to be.
2. [`../research/2026-10-baseline.md`](../research/2026-10-baseline.md): what exists
   today.
3. ADR-0002 (why one repository), ADR-0009 (why a database), ADR-0006 (where it runs).
4. ADR-0025 and [`../migration-plan.md`](../migration-plan.md): how to get there.
5. [`../open-questions.md`](../open-questions.md): what is not settled.

For reviewing the gaps, the ones that block work soonest are collected in ADR-0025,
G-0025-3 (assumptions to test first) and G-0025-4 (design questions that block
phase 2).

## By area

| Area | ADRs |
|---|---|
| Repository and process | 0001, 0002, 0003, 0004, 0005 |
| Where and how things run | 0006, 0007, 0008 |
| Data | 0009, 0010, 0011, 0012, 0013, 0014, 0015, 0016, 0017 |
| What users reach | 0018, 0019, 0020, 0021 |
| Operations | 0022, 0023, 0024 |
| Getting there | 0025 |

## Writing a new ADR

Copy [`template.md`](template.md) to the next free number. Leave its status as
`Proposed` until the maintainer accepts it. After adding or changing any gap, run
`python3 tools/docs/gen_open_questions.py` to regenerate the question list.
