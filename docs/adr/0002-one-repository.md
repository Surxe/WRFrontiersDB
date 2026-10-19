# ADR-0002: One repository for all WRF code

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-09 (new repository, history merge), 2026-10-10 (monorepo confirmed) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0003 (layout), ADR-0004 (CI), ADR-0005 (releases), ADR-0025 (migration) |

## Context

The WRF data ecosystem is nine repositories that only work together (see
`docs/research/2026-10-baseline.md`, section 1): Exporter, Parser, Orchestrator, Data,
Site, Discount Visualizer (DV), Discord bot, Design and News-Scraper. One person
maintains all of them, with AI agents doing much of the editing.

The problems the maintainer raised with this arrangement:

1. **Chains of pull requests.** A change to the data shape needs a Parser PR, then a
   Data change, then a Site PR and often a bot PR, each merged in order. A "parent"
   repository has to be merged before the "child" can even be tested against it.
2. **CI is duplicated and uneven.** Five repositories have their own workflows, written
   at different times to different standards. Four have none. There is no check that a
   change in one repository breaks another.
3. **Two machines to keep in step.** Each repository is cloned on the workstation and
   on the server. Keeping nine clones, nine virtual environments and their settings
   matched on two machines is manual work that goes wrong.
4. **Coupling is by convention.** The bot keeps a hand-copied table of the Site's
   routes. The Site and DV vendor Design as a submodule and read data through a symlink
   to a Data checkout. The Orchestrator finds sibling repositories by directory name.
   The Site and bot both depend on the Data repository's exact JSON layout with no
   shared type definitions.
5. **No end-to-end test.** Nothing runs the whole chain against a change before it is
   live.

The repositories have no outside contributors. Pull requests were squash-merged, so
each repository's history is a clean line of commits.

## Decision

1. **All WRF code moves into one repository, `Surxe/WRFrontiersDB`.** It was created on
   2026-10-10: public, default branch `main`.
2. **The existing repositories' histories are merged in**, each rewritten into its
   destination folder with `git filter-repo`, so `git log` and `git blame` keep working
   across the move. Two exceptions:
   - `WRFrontiersDB-Data` (346 MB of history, almost all of it data) contributes only
     the history of its `tools/` and `tests/` folders.
   - The Exporter's committed Windows DLLs (Oodle and Detex) are left out of both the
     tree and the history. Oodle is proprietary, and the Linux path already downloads
     it at run time.
3. **The Site and the Discount Visualizer become one site.** In the maintainer's words,
   "they should have been one in the first place". (This also removes the limit of one
   GitHub Pages site per repository, although hosting moves anyway: ADR-0019.)
4. **The old repositories are archived** after cutover, each with a README that points
   here.
5. **Staying outside this repository:**
   - `WRFrontiersDB-CUE4Parse` (replaced `CUE4P-BatchExport`): C#, consumed as a versioned
     release.
   - `OptionsConfig`: the maintainer's general-purpose library, used as an ordinary
     dependency.
   - `CUE4Parse` and `WRF-Compat-Tools`: other people's projects.
6. **The Exporter no longer supports Windows.** Windows-only code paths and binaries
   are dropped. (Decided 2026-10-10.)

The accepted costs, stated when the decision was made:

- Outside contribution becomes harder: a contributor to the Site now clones and
  navigates the whole system. There are no outside contributors today.
- The migration itself is a large one-time cost (ADR-0025).
- Two toolchains live side by side (Python and Node).
- Deployment has to be smarter, because one release tag now covers every app
  (ADR-0005, ADR-0007).

## Alternatives considered

- **Keep nine repositories and add tooling** (a meta-repository with submodules, or
  scripts that open linked pull requests). This keeps contribution simple per
  repository. Rejected: it treats the symptom. The coupling between the repositories is
  real, so changes will keep spanning them, and every cross-repository tool adds one
  more thing to keep in step on two machines.
- **Two or three repositories** (for example "pipeline" and "frontends"). Rejected: the
  most common painful change, a data shape change, crosses exactly that boundary.
- **A monorepo with a build system** (Nx, Turborepo, Bazel, Pants). These add task
  graphs and remote caching. Judged overkill for eight apps and one maintainer;
  path-scoped CI jobs give most of the benefit (ADR-0004). Can be revisited if CI time
  becomes a problem.
- **A fresh repository without history.** Simpler to create. Rejected because the
  history is clean and useful, especially the Parser's 181 commits explaining how game
  data is interpreted.

## Consequences

- A data shape change, its type definitions and every consumer change in one pull
  request, tested together.
- One CI configuration, one set of required checks, one place for agent instructions.
- One version number for everything deployed (ADR-0005). An app that did not change
  still gets a new version when another one does.
- One clone per machine instead of nine. The submodules and the data symlinks
  disappear (ADR-0003).
- The repository becomes the home of accumulated project state as well as code
  (ADR-0012), which the old layout kept in the Data repository.
- Every old commit gets a new hash. Links to old commits and pull requests keep
  working only because the old repositories stay up, archived.
- The public repository now contains the whole system's design, including its
  security model (ADR-0022). The `home-server` and `dev-env` repositories that
  describe the machines are already public, so this adds little new exposure, but it
  was checked rather than assumed (see G-0002-7).

## Gaps and open questions

### G-0002-1. Commit messages will link to the wrong pull requests

- **Kind:** design
- **Needed by:** phase 1 (before the history merge)

Squash-merge commit messages end in the pull request number, for example
`Resolve module-level currencies to real Currency refs (#131)`. On GitHub, `#131` in a
commit links to issue or pull request 131 of the repository the commit is in. After the
merge those links would point at unrelated items in this repository, or at nothing.

**Proposed default:** during the `git filter-repo` pass, rewrite `(#N)` in each
repository's messages to the full form `(Surxe/<old-repo>#N)`, which GitHub links to
the original pull request for as long as the archived repository exists.

### G-0002-2. Licence

- **Kind:** decision
- **Needed by:** phase 1

No WRF repository has a licence file. A public repository without one is "all rights
reserved" by default: others may read it but have no permission to reuse it. That may
be the intent, but it has never been decided. The Data repository's `NOTICE`
(attribution to the game's publisher for extracted assets) also needs a new home, since
the data it covers moves to object storage and the website (ADR-0020).

### G-0002-3. The old `WRFrontiersDB-API` repository

- **Kind:** decision
- **Needed by:** phase 5 (cutover)

A sample API repository from June 2025 exists and was not part of the planning (see the
baseline, section 1.3). It has a `render.yaml`, so a hosted copy may still be running.
It should be archived with the others, and any hosted deployment shut down. Its name is
also the obvious name for the new API, which will instead live in `apps/api` here.

**Resolved 2026-10-19:** The maintainer confirmed the repository is obsolete and has no
remaining deployments, so there is nothing to shut down. It is ignored by the
migration: not merged, not archived as part of cutover, and not a constraint on the
new API, which lives in `apps/api`.

### G-0002-4. Agent skills and per-repository instructions

- **Kind:** design
- **Needed by:** phase 1

The old repositories carry working agent material that the patch-day process depends
on: the `patch-warnings` skill (Parser), the `republish` and `send-test-email` skills
(Orchestrator), `CLAUDE.md` files (Parser, bot), `STANDARDS.md` files (Exporter,
Parser, Orchestrator) and `PATCH_DAY.md`. A history merge moves the files but not their
meaning: paths inside them change, and `republish` describes a flow (push to the Data
repository) that will no longer exist. They need to be consolidated into this
repository's `AGENTS.md` and `.claude/skills/`, and the patch-day runbook rewritten for
the new pipeline (ADR-0014).

### G-0002-5. Order of archiving against the old DV redirect page

- **Kind:** action
- **Needed by:** phase 5 (cutover)

The old DV address is on GitHub's domain and will be replaced by a "this site has
moved" page (ADR-0019). An archived repository is read-only, so that page must be
deployed before the DV repository is archived. Whether GitHub Pages keeps serving an
archived repository is reported but not confirmed by GitHub's documentation
(`docs/research/external-facts.md`); if it does not, the DV repository must stay
unarchived.

### G-0002-6. Open issues and pull requests in the old repositories

- **Kind:** action
- **Needed by:** phase 5 (cutover)

Any open issues or pull requests in the nine repositories at cutover need to be closed,
moved or re-created here. Their number was not counted.

### G-0002-7. Review of what the public repository reveals

- **Kind:** action
- **Needed by:** before the first ADR commit is pushed

These documents describe infrastructure and a security model in a public repository.
They were written to leave out addresses, account names and ids, and the machines'
own repositories are already public. The maintainer should confirm on review that
nothing here says more than intended, in particular ADR-0006, ADR-0022 and ADR-0023.

### G-0002-8. Whether Design has other consumers

- **Kind:** verification
- **Needed by:** phase 1

`WRFrontiersDB-Design` becomes a package inside this repository. If anything outside
the Site and DV uses it as a submodule, that consumer would be left on a frozen copy.
None is known; it was not searched for.

## References

- `docs/research/2026-10-baseline.md`, sections 1 and 4.
- ADR-0003 for where each old repository's code lands.
- ADR-0025 for the order in which the move happens.
