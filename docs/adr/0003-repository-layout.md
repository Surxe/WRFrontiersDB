# ADR-0003: Repository layout and workspaces

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 (layout, workspaces), 2026-10-12 (uv installed on the workstation), 2026-10-19 (JavaScript pins, Astro version, browser tools), 2026-10-29 (Python version), 2026-10-30 (settings) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0002 (one repository), ADR-0004 (CI), ADR-0010 (schema), ADR-0012 (state), ADR-0016 (DVC) |

## Context

ADR-0002 puts nine repositories into one. Their current shapes differ (baseline,
sections 1.1 and 1.2):

- Four Python projects keep loose modules directly under `src/`, with generic names
  that repeat across projects (`config`, `options`, `utils`, `stages`). Two are proper
  packages.
- Each Python project has its own virtual environment and a `requirements.txt` that
  pins only some direct dependencies. The same library is pinned to different versions
  in different projects. Nothing pins indirect dependencies.
- The two front ends are on different major versions of Astro and share CSS through a
  git submodule.
- The build-code codec exists twice, in Python and in JavaScript, both inside the Data
  repository.
- Linting is configured per repository, in two cases through a custom
  `.wrf-lint.json`.

The layout has to serve three mechanical consumers besides people: CI path filters
(ADR-0004), pipeline stage dependencies (ADR-0016), and Docker build contexts
(ADR-0007). All three work on directories.

## Decision

### 1. Top-level layout

```
WRFrontiersDB/
  apps/                things that run; each has a README, tests/, and a Dockerfile if deployed
    exporter/          Steam download, mapper, CUE4Parse export driver (from WRFrontiers-Exporter)
    parser/            exported JSON -> parsed JSON + textures         (from WRFrontiersDB-Parser)
    textures/          PNG -> WebP plus 128 px and 512 px copies       (new pipeline stage)
    db-build/          parsed JSON + state/ -> SQLite; swap-gate checks (new; absorbs Data tools/wrfdb_data)
    orchestrator/      update probe, discount watch, runs the pipeline, gate, promotion, reports
                       (from Orchestrator + News-Scraper + DV backend)
    api/               FastAPI service                                  (new)
    bot/               Discord bot                                      (from WRFrontiersDB-Discord-Bot)
    site/              Astro site; DV pages under src/pages/discounts/  (from Site + DV frontend)
  packages/            libraries imported by apps; never run on their own
    models/            Pydantic models (the single source of truth for types),
                       the type -> route table, the data release id
    common/            settings and secret loading, log redaction, slug rules, name matcher
    build-codes/       the build-code codec in Python and TypeScript, with one shared test-vector file
    types/             TypeScript types and OpenAPI schema generated from models/ (committed)
    design/            CSS tokens, fonts, style guide                   (from WRFrontiersDB-Design)
  state/               accumulated project state, checked in (ADR-0012)
  deploy/              compose.yml, deploy script, guest systemd timer units, secrets.example
  tools/               developer-side scripts, including the `wrf` command
  docs/                adr/, research/, architecture.md, schema.md, migration-plan.md, cloudflare.md, runbooks
  tests/e2e/           tests that cross app boundaries
  dvc.yaml  dvc.lock  params.yaml
  pyproject.toml  uv.lock            uv workspace: the Python members of apps/ and packages/
  package.json  package-lock.json    npm workspaces: apps/site, packages/design, packages/types, packages/build-codes
  AGENTS.md
  .github/workflows/
```

### 2. Rules behind the layout

1. **Split by role, not by language.** `apps/` holds things that run; `packages/` holds
   things that are imported. A change under `packages/` can affect any app; a change
   under `apps/<x>/` affects only `<x>`.
2. **Directory names are kebab-case** (`db-build`, `build-codes`). Python import names
   use underscores and a common prefix (`wrfdb_db_build`, `wrfdb_build_codes`).
3. **Every Python app becomes a real package**, `apps/<app>/src/wrfdb_<app>/`. This is
   required, not cosmetic: the workspace shares one virtual environment, so four
   different modules named `config` would collide.
4. **One uv workspace for all Python.** One `uv.lock` at the root, committed. Each app
   and package keeps its own `pyproject.toml` listing its own dependencies. Members
   refer to each other by name and are installed in editable mode, so a change to
   `packages/models` is seen at once by every app.
5. **Every Python dependency is pinned to an exact version** (decided 2026-10-12, in
   connection with ADR-0016). Upgrades are deliberate edits.
6. **npm workspaces for the JavaScript side.** `packages/design` replaces the Design
   submodule. The symlinks to a Data checkout disappear with the Data repository
   (ADR-0009). As on the Python side, every JavaScript dependency is pinned to an
   exact version (no `^` or `~` ranges), one root `package-lock.json` is committed,
   and all workspaces use the same version of each library (decided 2026-10-19).
7. **Generated TypeScript types are committed** in `packages/types/`, with a CI check
   that fails when they are stale. The Site then builds without Python, and a change to
   the data contract shows up as a reviewable diff.
8. **Data is not code.** Anything accumulated or curated as data lives in `state/`, not
   inside an app folder. Otherwise a new discount week would look like a code change to
   CI and to the pipeline's stage cache.
9. **One Dockerfile per deployed app, inside that app's folder.** Which apps share an
   image is settled at implementation (ADR-0007).
10. **Tests live with their code** (`apps/<x>/tests/`, `packages/<y>/tests/`).
    Cross-app tests go in `tests/e2e/`.
11. **One lint and format configuration at the root**: ruff and pyright for Python,
    eslint and prettier for TypeScript. The per-repository configurations and both
    `.wrf-lint.json` files go.
12. **The Orchestrator keeps its name** but gets thinner: DVC runs the stages
    (ADR-0016). If Dagster is ever adopted (a parked idea), only this folder changes.

### 3. Where the old code goes

| Old location | New location |
|---|---|
| Exporter | `apps/exporter` |
| Parser | `apps/parser` |
| Orchestrator | `apps/orchestrator` |
| News-Scraper (code) | `apps/orchestrator` (the discount watch) |
| News-Scraper `archive/` (298 posts) | `state/news/` |
| DV backend (name mapping, grid generation) | `apps/orchestrator` (mapping), `packages/common` (name matcher) |
| DV prediction builder | `apps/db-build` (a step writing a predictions table; decided 2026-10-11) |
| DV `archive/discounts/` | `state/discounts/` |
| DV frontend | `apps/site/src/pages/discounts/` and its components |
| Data `tools/wrfdb_data` | `apps/db-build` (index and registry building), `packages/common` (slug rules), `packages/build-codes` (codec) |
| Data `tools/js` (codec) | `packages/build-codes` |
| Data `index/` | `state/` for what accumulates; the rest is rebuilt by `db-build` (ADR-0012) |
| Data `current/`, `textures/`, `Models/` | retired; produced by the pipeline into the database and object storage |
| Bot | `apps/bot` |
| Site | `apps/site` |
| Design | `packages/design` |

## Alternatives considered

- **Split by language** (`python/`, `web/`). Rejected: a data contract change touches
  both, and the split would cut across every CI filter and stage dependency.
- **Flat top level** (`exporter/`, `parser/`, `models/`, ...). Rejected: it hides the
  one distinction that matters to CI, namely "can this change affect other things".
- **Separate lockfile and environment per Python app.** Keeps apps free to disagree on
  versions. Rejected: disagreement between apps that exchange data is the problem being
  removed, and it would keep nine environments to maintain.
- **One shared virtual environment without uv** (a `.venv` at the root, `pip install`
  into it). Raised by the maintainer. It gives the shared environment but none of the
  rest: no lockfile, no resolver that considers all apps at once, no record of which
  app needs which package, no automatic wiring of local packages, no check that the
  environment matches what is declared. Reproducing those by hand amounts to rebuilding
  a workspace.
- **Poetry or PDM** in place of uv. Both can do workspaces of a kind. uv was chosen for
  first-class workspaces, speed, and replacing the Python-version manager too. This was
  not compared in depth.
- **Generate TypeScript types at build time and do not commit them.** Rejected: every
  Site build would need Python, and contract changes would be invisible in review.

## Consequences

- The Parser, Exporter, Orchestrator and DV backend all need their imports rewritten as
  part of the move. This is the largest mechanical task in phase 1.
- All apps share one version of each library. If two apps genuinely need versions that
  cannot both be satisfied, locking fails and says so. That constraint was accepted.
- Shared code is live across apps with no publishing step.
- A docs-only or data-only change can be told apart from a code change by path.
- The repository root carries two ecosystems' files (`pyproject.toml` and
  `package.json`); newcomers have to learn which tool owns which folder.

## Gaps and open questions

### G-0003-1. Which Python version

- **Kind:** decision
- **Needed by:** phase 1

The projects declare floors from 3.8 to 3.11, the DV README says 3.12, CI uses 3.11 and
both machines run 3.13.5. A workspace has one interpreter version. It also fixes the
SQLite version Python links against, which matters to ADR-0009 (the database's JSON
format needs SQLite 3.45 or newer).

**Proposed default:** 3.13, the version already running everywhere, pinned in
`.python-version` and installed by uv.

**Resolved 2026-10-29:** The proposed default is accepted: Python 3.13, pinned in
`.python-version` and installed by uv. It matches the `python:3.13-slim-trixie` images
already chosen in ADR-0009, G-0009-1. The SQLite concern above no longer applies:
G-0009-2 stores documents as JSON text, so the minimum is SQLite 3.38 (G-0009-1), which
any 3.13 build meets.

### G-0003-2. Two settings systems

- **Kind:** decision
- **Needed by:** phase 2

The Exporter, Parser and Orchestrator read settings through `optionsconfig`
(environment variables, command-line arguments, generated README sections). ADR-0022
requires secrets to be read from files through pydantic-settings and typed so they
cannot be printed. As written, an app would use both libraries for overlapping jobs.
Options: keep `optionsconfig` for non-secret options and pydantic-settings for secrets
only; move everything to pydantic-settings; or teach `optionsconfig` to read secret
files.

**Resolved 2026-10-30:** Option 2, all settings through pydantic-settings; `optionsconfig`
is not used in this repository. There are no per-app `.env` files. Settings are sorted
by kind:

- run-control flags (`SHOULD_*`) are dropped, because DVC decides what runs (ADR-0016);
- paths are fixed by the layout;
- options that change a stage's output go in `params.yaml`;
- settings that differ by environment go in `deploy/` (ADR-0007, G-0007-9);
- secrets are files under `/run/secrets` (ADR-0022).

`common/settings.py` holds one small class per concern (Steam, storage, Discord, run
report, ...), and each stage or service creates only the ones it uses. A single class
would require every secret in every container. A generator writes a README section from
those classes, listing each setting and each secret with its file and the services that
read it; this becomes the list G-0022-5 asks for. `depends_on` is not carried over: it
existed to tie options to the `SHOULD_*` flags.

### G-0003-3. One Astro version, one screenshot tool

- **Kind:** design
- **Needed by:** phase 4

The Site is on Astro 5 with Playwright; the DV frontend is on Astro 6 with Puppeteer.
One site means one version of each. Upgrading the Site to Astro 6 is probably the
smaller change, but it was not assessed. Its cost belongs in the phase 4 estimate.

**Resolved 2026-10-19:** One Astro version: the Site moves up to the DV's Astro 6,
pinned exactly like everything else (decision 6). The two browser tools are not
duplicates and both stay, each with one role: Puppeteer for screenshots taken by the
pipeline (the DV's, and the discount link preview, G-0017-6), and Playwright for
browser debugging through MCP while developing the Site, so it is a development
dependency only and not part of any pipeline or image. The cost of the Astro upgrade
still belongs in the phase 4 estimate.

### G-0003-4. How TypeScript types are generated from the models

- **Kind:** design
- **Needed by:** phase 2

Decision 7 fixes that types are generated and committed, not how. The path is Pydantic
to JSON Schema to TypeScript, but the generator, the handling of open dictionaries
(`detail`, ADR-0011) and of optional fields are not chosen. The staleness check also
means the Site's CI job needs Python after all, even though the Site's build does not.

### G-0003-5. Is DVC a workspace dependency or a separate tool

- **Kind:** decision
- **Needed by:** phase 2

DVC brings a large dependency tree of its own. As a workspace dependency it would share
the single lockfile, and its requirements could conflict with the apps' (for example
over shared libraries). Installing it as a standalone tool (`uv tool install`) keeps it
out of the lockfile but then its version is pinned somewhere else.

**Proposed default:** a standalone tool with its version pinned in the pipeline image
and in `deploy/`, unless a trial shows the lockfile resolves cleanly with it.

### G-0003-6. The published codec file is used from outside

- **Kind:** verification
- **Needed by:** phase 4

The Site serves the JavaScript codec at a public address (`/build-code.js`), and the
bot's README invites other sites to use it. ADR-0021 moves it under `/data/`. If anyone
outside uses the current address, it needs a redirect. Whether anyone does is unknown.

### G-0003-7. Where the pipeline's working data lives relative to the checkout

- **Kind:** design
- **Needed by:** phase 2

`dvc.yaml` sits at the repository root and refers to stage outputs by path. DVC only
caches outputs that are inside the project directory
(`docs/research/external-facts.md`). So the pipeline's working directory has to be a
checkout of this repository placed on the data volume, with a `data/` folder inside it
that is ignored by git. That collides with the earlier statement that production "has
no code checkout" (ADR-0007). ADR-0016, gap G-0016-1, treats this in full.

### G-0003-8. The `wrf` command

- **Kind:** design
- **Needed by:** phase 3

`tools/` is to hold a `wrf` command (`wrf release`, deploy wrappers). Its language,
whether it is a workspace package, and how it is put on the path on each machine are
not designed.

### G-0003-9. Agent instruction files

- **Kind:** decision
- **Needed by:** phase 1

The layout names one `AGENTS.md`. The old repositories have `CLAUDE.md` files and
tool-specific folders (`.claude`, `.cursor`, `.windsurf`, `.agents`). Which files the
agents in use actually read, and whether `CLAUDE.md` is a link to `AGENTS.md` or
generated from it, needs settling so there is one source. See also G-0002-4.

### G-0003-10. End-to-end tests are named but not designed

- **Kind:** design
- **Needed by:** phase 4

`tests/e2e/` exists in the layout. What runs there, against what data, and whether in
CI or only on staging, is undefined. ADR-0004 (G-0004-2) and ADR-0008 cover the data
problem.

## References

- `docs/research/2026-10-baseline.md`, sections 1.1 and 1.2.
- uv workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/
