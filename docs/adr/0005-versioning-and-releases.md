# ADR-0005: Versioning and release model

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-09 (release model), 2026-10-10 (data release id) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0004 (CI), ADR-0007 (deployment), ADR-0014 (swap gate), ADR-0015 (data release ids), ADR-0019 (site deploys) |

## Context

Two different things change what users see:

- **Code**: a fix to the Parser, a new page on the Site, a new bot command.
- **Data**: a new game patch (about fifteen a year) or a new weekly discount
  announcement (about fifty a year). Neither involves a code change.

Today there is no version for the system as a whole. Each repository deploys from its
own default branch, in its own way: the Site's CI deploys on every push; the bot runs
from a working copy on the server; the pipeline runs whatever is checked out in each
sibling repository at that moment. The only version users see is the data version (the
date of the game build, such as `2026-10-06`), and the Site and DV each publish a
`deploy.json` naming the Data commit they were built from.

Two failure modes follow from that. A half-merged change can go live because the
pipeline happens to run against a default branch mid-change. And when something breaks,
there is no single answer to "what exactly is running".

With one repository (ADR-0002), one version for the code becomes possible.

## Decision

### Code releases

1. **One code version for the whole repository, by calendar date** (CalVer):
   `2026.10.09`, and `2026.10.09.2` for a second release the same day. It is a git tag.
2. **Merging to `main` never deploys anything.** Deploying is a separate, manual act.
3. **A release is made with one local command, `wrf release`**, which creates and
   pushes the tag. CI then runs the tests and builds the images for that tag, and the
   same command goes on to run the deployment on the server (ADR-0007).
4. **Images carry two tags**: the release version and the commit hash. The deploy
   script accepts either, so a branch can be tried in production-like conditions.

### Data releases

5. **A data release does not change the code version.** A new patch or discount week is
   published by the pipeline on its own.
6. **The pipeline always runs the deployed release**, never `main`. Unreleased code
   cannot affect a patch day.
7. **Each published database has a data release id**, `<game version>.<n>`: the game
   build's date plus a counter of databases built for that game version (ADR-0015).
8. **There are exactly two release paths**: code (manual) and data (automatic, on a
   patch or a discount week).

### What is built from what

9. **The Site is always built from a release tag plus a published database**, never
   from a working copy. Both kinds of release trigger a Site build at the deployed tag.
10. **Four versions are kept distinct and all are shown**: code version, data release
    id, database schema version, API version. The bot's `/about` command, the Site's
    `/data/deploy.json` and the API's `/v1/meta` each report code and data versions.
11. **The database records the schema version it was built with**, and a service checks
    it when opening the file (ADR-0009).

## Alternatives considered

- **Semantic versioning** (`1.4.2`). It communicates compatibility to consumers of a
  library. Nothing here is consumed as a library, and deciding "major or minor" for a
  website adds a judgement with no reader. A date answers the question people actually
  ask: how old is what is running.
- **A version per app.** Precise, but it brings back the compatibility matrix the
  monorepo was meant to remove ("which bot works with which models").
- **Continuous deployment from `main`.** Fewer steps. Rejected by the maintainer: a
  merge should not be able to change production, and the patch-day pipeline must not
  pick up whatever happens to be on `main`.
- **Bumping the code version on data releases**, so one number identifies everything.
  Rejected: it would create about sixty-five releases a year with no code change and
  blur the two questions "what code" and "what data".
- **Building the Site from a working copy on the server**, as the Orchestrator can
  today. Rejected: what is deployed would then depend on the state of a directory.

## Consequences

- "What is running" always has an exact answer: a tag and a data release id.
- A release is deliberate and repeatable; rolling back code is deploying the previous
  tag.
- A fix to one app releases all of them under a new version, changed or not.
- Releasing needs the maintainer (or an agent acting for them) at a machine on the home
  network (ADR-0007).
- A Parser fix reaches users only after a release, and then only when the pipeline next
  runs or is run by hand. The current "merge the Parser fix, then republish" habit
  becomes "merge, release, and the deploy rebuilds the data" (see G-0005-3).

## Gaps and open questions

### G-0005-1. The exact form of the version string

- **Kind:** decision
- **Needed by:** phase 3

Three details are open:

- **Leading zeros.** Python's version rules treat `2026.10.09` and `2026.10.9` as the
  same version and normalise to the second (`docs/research/external-facts.md`). If the
  code version is ever written into Python package metadata, the tag and the reported
  version would differ. The workspace packages could simply not carry the release
  version (stay at `0.0.0`) and read it from a file or variable set at build time.
- **A prefix.** `v2026.10.09` or bare `2026.10.09`. Tag-pattern rules in CI and
  GitHub environments are easier to write against a prefix.
- **Which clock.** The data version uses the UTC day. A release made late in the
  evening, local time, lands on a different date in UTC. The code version should name
  its clock.

### G-0005-2. A tag whose build fails

- **Kind:** decision
- **Needed by:** phase 3

`wrf release` pushes the tag before CI has built anything. If tests or an image build
then fail, a tag exists that can never be deployed. Options: delete the tag and reuse
the number; leave it and release `.2`; or have `wrf release` wait for a green run on the
commit before tagging at all.

**Proposed default:** refuse to tag a commit whose CI run on `main` is not green, and
never move or delete a pushed tag.

### G-0005-3. A code release that changes the data

- **Kind:** design
- **Needed by:** phase 3

The production database was built by the previous release. If the new release changes
the Parser, the models or the database schema, the running database no longer matches
the new code. So a code deployment cannot just restart containers: it must also re-run
the pipeline (ADR-0016 will re-run only the stages whose code changed), pass the swap
gate (ADR-0014), and switch the database and the services together. This raises
questions the decisions do not answer:

- In what order do the new images, the new database and the Site go live, and what do
  users see in between?
- If the rebuilt database fails the gate, is the code deployment rolled back?
- A release that changes the Exporter triggers the export stage, which launches the
  game under Proton. It took about 8 minutes on the last patch day (baseline, section
  2.5); the old unit allows for 30 or more. Is that acceptable inside a deployment?
- What does a service do when it opens a database whose schema version it does not
  expect: refuse to start, or keep serving the old file?

This is the least specified part of the release model and should be designed before
the deploy script is written.

### G-0005-4. Rolling back

- **Kind:** design
- **Needed by:** phase 3

"Deploy the previous tag" is only half of a rollback when the schema changed: the
previous code needs the previous database too. ADR-0015 keeps the last two databases on
the server for this. What happens to state already committed by the newer release
(ADR-0012), and to the Site, is not defined. A `deploy rollback` command is named in
the plan but not specified.

### G-0005-5. How the pipeline knows which release is deployed

- **Kind:** design
- **Needed by:** phase 3

Decision 6 says the pipeline runs the deployed release. Something on the server must
record which tag that is, and the scheduled jobs must use it. With images this is
natural (the Compose file names the tag), but the pipeline also needs the repository's
`dvc.yaml`, `params.yaml` and `state/` at matching versions. See ADR-0016, G-0016-1.

### G-0005-6. Schema and API version rules

- **Kind:** design
- **Needed by:** phase 2 (schema), the API phase (API)

Decision 10 names a schema version and an API version without saying what they look
like, who changes them or when. For the schema: is it an integer bumped by hand on
any incompatible change, or derived from the models (a hash)? A derived value cannot be
forgotten but changes on every edit, compatible or not.

### G-0005-7. Urgent fixes

- **Kind:** decision
- **Needed by:** after cutover

With one version for everything, a fix needed now must be released together with
whatever else is on `main`. If `main` holds unfinished work, the choices are to release
from a branch cut at the last tag, or to always keep `main` releasable. Neither is
stated. The commit-hash image tag (decision 4) makes a branch release mechanically
possible.

## References

- ADR-0015 for the data release id and its counter.
- CalVer: https://calver.org/
