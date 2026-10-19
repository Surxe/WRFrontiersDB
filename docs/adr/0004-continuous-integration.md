# ADR-0004: Continuous integration and required checks

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-09 (CI builds images, no self-hosted runner), 2026-10-10 (scoping, secret scanning) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0002, ADR-0003, ADR-0005 (releases), ADR-0007 (deployment), ADR-0019 (site deploys), ADR-0022 (secrets) |

## Context

Today five of the nine repositories have GitHub Actions workflows and four have none
(baseline, section 1). The existing ones were written separately: the Parser runs
`unittest` on pull requests; the Site lints, tests, builds and deploys; the DV has six
workflows that also carry its weekly data flow. No repository requires a check to pass
before merging, and no check crosses a repository boundary.

One repository changes what CI has to do:

- Running every app's checks on every change would be slow and wasteful. The Site's
  tests and build have nothing to say about a Parser change.
- But "only run what changed" collides with GitHub's required checks: a required job
  that is skipped never reports, and the pull request waits forever.
- CI also becomes part of the release path: images are built there and pulled by the
  server (ADR-0007), and the Site is deployed from there (ADR-0019).

The server is at home behind the router and cannot be reached from GitHub.

## Decision

1. **One CI configuration, written once, with required checks.** The maintainer's
   stated aim is to invest in real CI/CD once, in one repository.
2. **Jobs are scoped by path** with `dorny/paths-filter` (or equivalent): a change under
   `apps/bot/` runs the bot's jobs; a change under `packages/` runs every job that
   depends on that package.
3. **One aggregate job is the only required check.** It runs always, after the others,
   and fails if any job that ran has failed. Branch protection requires that one job, so
   skipped jobs never block a merge.
4. **No monorepo build system** (Nx, Turborepo). Judged overkill at this size.
5. **CI builds the container images** and pushes them to GitHub's container registry.
   The server only pulls. Nothing is built on the server.
6. **No self-hosted runner.** Reasons given: the maintenance it needs, and the risk of
   attaching a machine on the home network to a public repository's workflows.
7. **GitHub never connects into the home network.** Deployments to the server are
   started from inside it (ADR-0007).
8. **Secrets are kept out of the repository by two checks:** a `gitleaks` pre-commit
   hook, and GitHub's push protection.
9. **`main` is protected:** the aggregate check is required and force-pushes are
   blocked (which also protects the rule that ADR history is permanent).
10. **Generated files are checked for staleness:** the TypeScript types in
    `packages/types/` (ADR-0003) fail CI when they do not match the models.
11. **The local check for the Site is a real build** (`npm run build && npm run
    preview`), not the development server, because the development server hides
    build-time failures.
12. **Per-pull-request preview deployments of the Site are not built now.** They can be
    added later without infrastructure changes (ADR-0019).

## Alternatives considered

- **Run everything on every change.** Simple and always correct. Rejected for cost in
  time: the Site alone lints, runs 55 test files and builds about 700 pages.
- **A separate workflow file per app, each with its own `paths:` trigger.** This is
  the common first attempt. Rejected because of the required-check problem described
  above: a workflow that does not trigger cannot satisfy a required check.
- **A build system that works out affected projects** (Nx, Turborepo). It would also
  cache task outputs. Rejected as overkill for now; path filters are a few lines.
- **A self-hosted runner on the server.** It would let CI deploy directly and build
  with the game data to hand. Rejected (decision 6). The cost is that deployment needs
  a command run from home (ADR-0007).
- **Building images on the server.** Rejected: the server is a small laptop whose
  memory is the tightest constraint in the system (ADR-0006).

## Consequences

- A pull request runs only the jobs its paths call for, and one green check means
  "everything relevant passed".
- The path filter map is itself a thing to keep correct. A missing entry means a change
  goes untested without anyone noticing. This is the main risk of the approach.
- Images exist for every commit CI builds, which is what lets staging run any commit
  (ADR-0008).
- Releasing depends on GitHub Actions being up.
- Because deployments are started from home, releasing is impossible while away. This
  was accepted (ADR-0007).

## Gaps and open questions

### G-0004-1. The dependency map between paths and jobs

- **Kind:** design
- **Needed by:** phase 1

The filter map has to encode which app depends on which package, and that `uv.lock`,
`package-lock.json`, the root lint configuration and the workflow files themselves
affect everything. Written by hand it will drift from the real dependency graph in
`pyproject.toml` and `package.json`. Options: generate the map from the workspace
metadata, or add a test that compares the two.

### G-0004-2. The Site cannot be built in CI without data

- **Kind:** decision
- **Needed by:** phase 4, and earlier for any pull request touching the Site

Today the Site's CI checks out the public Data repository. Under ADR-0009 the data is a
SQLite file in a private bucket and there is no public dataset. A pull-request build of
the Site therefore needs a database from somewhere. Options:

- a small **fixture database** built in CI from fixture JSON committed to the
  repository: needs no secret and works for forks, but tests a toy data set;
- **the real database**, fetched with a read-only token stored as a GitHub secret:
  realistic, but exposes that token to workflow code and is unavailable to forks;
- both: fixtures on pull requests, the real database on `main` and at release.

The same question applies to the bot's tests and to `tests/e2e/`. It also decides
whether a contributor without credentials can build the Site at all.

### G-0004-3. When images are built

- **Kind:** decision
- **Needed by:** phase 3

Staging deploys "any commit" by its hash (ADR-0008), so an image must exist for that
commit. Building on every push to every branch is simple but builds many images nobody
uses; building on demand (a manually triggered workflow) adds a wait before each
staging deploy. Related: container packages are private when first pushed and have to
be made public once by hand, and commit-tagged images accumulate without a clean-up
rule.

### G-0004-4. Tests that need real game data or a GPU

- **Kind:** verification
- **Needed by:** phase 1

The exit condition for phase 1 is "every existing test passes in CI". Some existing
tests may depend on game exports, a Data checkout, Proton or a GPU (the Site has a
`HEAVY_TESTS` switch; the Exporter has 21 test files around a step that launches the
game). Which tests can run on a hosted runner has not been inventoried. Those that
cannot need a marker and a place to run (staging).

### G-0004-5. Pipeline commits against a protected branch

- **Kind:** decision
- **Needed by:** phase 2

The pipeline commits accumulated state on every data release (ADR-0012). If those
commits go to `main`, they must either bypass branch protection or go through it, and
each one would trigger CI. ADR-0012, gap G-0012-1, covers the options; the CI side
(what a state-only commit should run) follows from that choice.

### G-0004-6. Keeping exactly pinned dependencies current

- **Kind:** decision
- **Needed by:** after cutover

Every dependency is pinned exactly (ADR-0003). Nothing updates them unless someone
does. An automated updater (Dependabot or Renovate) would propose upgrades; note that a
Python dependency change re-runs the long export stage on the next pipeline run
(ADR-0016, G-0016-6). No routine is defined.

### G-0004-7. Checks for the documents themselves

- **Kind:** design
- **Needed by:** phase 1

`docs/open-questions.md` is generated from the ADRs (ADR-0001). A CI step should
regenerate it and fail on any difference. Broken links between documents could be
checked the same way.

### G-0004-8. Workflow security on a public repository

- **Kind:** verification
- **Needed by:** phase 3 (before any deploy secret is stored)

The repository will hold secrets for Cloudflare and possibly for the data bucket. The
workflows need the usual hardening: least-privilege `permissions`, no secret-bearing
jobs on pull requests from forks, deploy jobs limited to release tags through a
protected environment, and third-party actions pinned to commit hashes. None of this
is written down yet.

## References

- `docs/research/2026-10-baseline.md`, section 1.
- `dorny/paths-filter`: https://github.com/dorny/paths-filter
