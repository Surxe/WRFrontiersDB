# ADR-0014: The swap gate

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0008 (environments), ADR-0009 (data store), ADR-0011 (tiers), ADR-0012 (state), ADR-0013 (slugs), ADR-0015 (archive), ADR-0019 (site deploys) |

## Context

Under ADR-0009 a data release is a new database file swapped in to replace the old
one. Something has to decide whether a candidate file is fit to go live.

Today there is almost no such decision. A parse that finishes is published, whatever
it logged (baseline, section 2.1). The only checks that stop a run are inside the
`INDEX` stage: a slug collision, and a change that would break existing build codes.
Problems reach users first and the maintainer second, through the report email.

Two things found while designing the gate show what is currently getting through. A
trial of the proposed checks against live data on 2026-10-10 found that 9,214 of
28,188 references pointed at ids that do not exist (two currency ids hard-coded
without a suffix), and that one localization key used by an object did not exist in
the game's files. Both were Parser bugs, both were live, and nobody had noticed. Both
have since been fixed.

The Site is a further source of failure: it can fail to build on data the Parser
accepts. And the bot must never link to a page that has not been deployed.

## Decision

### Order of a data release

1. Build the candidate database.
2. Run the checks below.
3. Upload the candidate to object storage as `wrfdb-<release>.sqlite`. Nothing points
   at it yet.
4. Build the Site against the candidate, at the deployed release tag.
5. Commit `state/` and `dvc.lock` (ADR-0012).
6. Promote: repoint the server's `current` database, deploy the Site, and let the API
   and bot pick up the new file.

**A failure before step 5 changes nothing.** Production keeps the previous database.

The Site build is inside the gate because the Site can fail on data the Parser
accepts, and because the bot must never link to a page that is not deployed.

### Checks that block

| Check | What it catches |
|---|---|
| Model validation: tier 1 strict, tier 2 shape (ADR-0011) | a game change that breaks a field consumers rely on |
| Every reference resolves | links to objects that do not exist |
| Every localization key used exists in English | missing names and descriptions |
| Every icon, image and model path exists in object storage, including resized copies (ADR-0020) | broken images |
| Slugs: no collision within a type; history consistent; no slug equal to a fixed page name under the same route (ADR-0013) | unreachable or overwritten pages |
| Build codes: the registry only grows; no existing code changes meaning | published build links silently decoding to something else |
| Database health: integrity check, declared foreign keys, schema version matches the code | a corrupt or mismatched file |
| Object count per type against production: block if any type drops by more than about 10% or to zero | a stage that silently produced a fraction of its output |
| Data version is not older than production's | publishing a stale run over a newer one |
| Canary queries: search finds the robot Alpha; a known module, pilot and build code resolve | the database works for real lookups |
| The Site builds | data the Site cannot render |

The 10% threshold is a starting value and may change.

### Reported, not blocking

Objects added and removed (with detection of a robot that looks renamed); new raw keys
in `detail` and changes to tier 2 key sets; missing non-English translations; objects
that should have a page but have no slug; nickname collisions; anomalies in release
dates or patch manifests.

### Override

`--accept <check>` lets one named check through for one run. Every use is recorded in
the run report and in the data-release commit message.

### Staging

Staging runs the same gate with the same thresholds, comparing against production's
current database. Its report, with a summary of the differences between the two files,
doubles as a description of what a branch changes (ADR-0008).

## Alternatives considered

- **Publish first, report after** (today's behaviour). Players get new data fastest.
  Rejected: it is how 9,214 dangling references went live unnoticed.
- **Commit state before the checks**, as an earlier draft had it. Rejected: a failed
  release would leave permanent state describing something that never went live.
- **Leave the Site out of the gate** and deploy it after promotion. Simpler and faster.
  Rejected: the bot would be able to link to pages that do not exist yet, and a Site
  build failure would be discovered after the data was already live.
- **Warnings that block.** Rejected: a typical patch produces warnings (1,500 on
  2026-09-29); every patch would stop. The maintainer was clear that unknown game data
  must not block.
- **No override.** Rejected: some failures will be known and acceptable (a type that
  really did shrink), and the alternative to an override is editing the check.

## Consequences

- Users never see a database that failed these checks.
- **A patch can now be withheld.** Before, a patch always went out, sometimes with
  gaps. Now a blocking failure at three in the morning means the site stays on the
  previous patch until a person fixes the cause or accepts the check. Stale but
  consistent was chosen over current but broken. The cost is time-to-publish on the
  days it happens, and it puts weight on the report email being read (ADR-0024).
- Each release takes longer: checks plus a full Site build before anything goes live.
- The gate needs production's current database to compare against, and the list of
  objects in object storage.
- The checks are code that can itself be wrong. A check that blocks wrongly on a
  patch day is an outage of freshness; the override exists for that.

## Gaps and open questions

### G-0014-1. Assets are uploaded before the gate has passed

- **Kind:** design
- **Needed by:** phase 2

One blocking check is that every image and model path exists in object storage. So
images and models must be uploaded before the checks run. ADR-0020 stores them at
stable names, with a version marker in the address rather than in the name. Uploading
a candidate's assets therefore overwrites production's live files before the gate has
decided anything, and a candidate that then fails has already changed what users are
served. For images that rarely change this is mostly harmless, but it breaks the
promise that "a failure before step 5 changes nothing".

Options: name objects by their content hash, so an upload can never overwrite anything
and old and new files coexist (this also makes the address marker unnecessary); upload
to a candidate location and copy into place at promotion; or accept the overwrite and
say so.

### G-0014-2. Promotion is several steps, and the Site is built twice

- **Kind:** design
- **Needed by:** phase 3

Step 6 bundles three actions on three systems: repoint the database on the server,
deploy the Site on Cloudflare, and have services reload. They cannot happen at the
same instant, and any of them can fail after the state commit in step 5. Not defined:
the order within step 6; what "promoted" means if the Site deployment fails; whether
promotion can simply be retried; and what the bot does in between.

Separately, step 4 builds the Site on the server to prove that it builds, while
ADR-0019 deploys the Site from a GitHub Actions run at the release tag. That is a
second build, on a different machine, and it is the second one that goes live. The
gate has then tested a build that is not the one deployed. Options: deploy the output
of the gate's build (hand it to the workflow as a file, or deploy from the server);
or drop the server-side build and treat the workflow's build as the gate step, waiting
for it before promoting.

**Resolved 2026-10-20:**

- **The Site is built once.** Step 4 runs the deploy workflow in upload-only mode: it
  builds the Site against the candidate and uploads it as a new Worker version with
  `wrangler versions upload`, tagged with the release id. An uploaded version serves no
  traffic, so a failure here is still before the commit and changes nothing. The
  server-side build is dropped. Promotion deploys that exact version with
  `wrangler versions deploy`, an atomic switch. The Cloudflare token stays in GitHub
  (ADR-0019). Staging and production are separate Workers, so each uploads its own
  version in its own gate run.
- **The order within step 6** is ADR-0009, G-0009-4: deploy the Site version and wait
  until it is live, repoint `current`, call the internal reload endpoints and confirm
  the new release, then purge the API cache. That also answers what the bot does in
  between: it keeps serving the previous release, which never links to an undeployed
  page.
- **The state commit stays before promotion** (step 5). Committing after would risk a
  live release whose state exists nowhere in git, so the next run could reassign build
  codes or slugs that users already have.
- **Promotion is idempotent and is retried until it succeeds.** Every action in it is
  safe to repeat: deploying the same version, repointing `current` to the same file,
  calling reload. Requirements that make this hold:
  - the pipeline records the outcome of each promotion ("release N promoted") as
    operational state outside git (ADR-0012, decision 5). A retry acts only on the last
    committed release without that record, so a manual rollback is never undone by a
    retry;
  - a retry finds the Site version by its release tag and deploys it; it never builds
    again. Cloudflare keeps the last 100 versions, far more than a retry needs;
  - a run that starts while a promotion is pending finishes it first, under the
    machine-wide pipeline lock (ADR-0008), and the gate's "not older than
    production" check still stops an older release from being promoted over a newer
    one;
  - a promotion that stops part-way (for example, Site live, `current` not repointed)
    leaves the bot and the API one release behind the Site until the retry. The run
    report says so prominently (ADR-0024).

### G-0014-3. Where the gate's code lives and what runs it

- **Kind:** design
- **Needed by:** phase 2

The layout puts "swap-gate checks" in `apps/db-build` and "gate, promotion" in
`apps/orchestrator`. Some checks need only the candidate file; others need
production's database, object storage, or a Site build. A clear split would be:
`db-build` validates what it builds; the orchestrator runs everything that compares or
reaches outside.

### G-0014-4. The count threshold on small types

- **Kind:** design
- **Needed by:** phase 2

A 10% drop is a sensible alarm for 6,142 scrap rewards. For a type with five objects,
losing one is 20% and would block. The rule needs a floor, for example "more than 10%
and more than N objects", or per-type settings. It also needs a defined result for a
type that is new in the candidate or absent in production.

### G-0014-5. Canaries that name game objects

- **Kind:** design
- **Needed by:** phase 2

"Search finds the robot Alpha" fails on the day the game removes or renames Alpha. The
canaries should be a small configured list, with a rule for what to do when one stops
existing, so that the fix is a data edit and not a code release.

### G-0014-6. Which localization keys are checked

- **Kind:** design
- **Needed by:** phase 2

"Every localization key exists in English" needs a definition of which keys count:
those in tier 1 name and description fields only, or every key-shaped string anywhere
in a document. The trial run checked 2,147 keys; how that set was chosen should be
written into the check.

### G-0014-7. The override when nobody is awake

- **Kind:** decision
- **Needed by:** phase 3

`--accept` is a flag on a command. The pipeline starts itself when a patch appears. So
using the override means a person re-running the release by hand after reading the
report. The exact command, and whether the re-run reuses the already-built candidate
or starts again, should be in the patch-day runbook. Whether the AI agent may apply an
override without the maintainer is a policy question.

### G-0014-8. What exactly the discount-week release re-checks

- **Kind:** design
- **Needed by:** phase 2

A discount week changes only discount rows (ADR-0017). Running the whole gate,
including a full Site build, about fifty times a year for a change of a few rows is
safe but slow. Whether discount releases run the full gate or a reduced one is not
decided. The default from the decision as written is the full gate.

### G-0014-9. The patch-day runbook

- **Kind:** action
- **Needed by:** phase 5 (cutover)

The existing runbook (`PATCH_DAY.md`) describes a flow where data is always published
and the Parser is taught afterwards. With the gate, the report email gains a new
outcome ("blocked by check X"), and the `republish` step becomes "release, then let
the deployment rebuild". The runbook and the two agent skills it refers to need
rewriting (ADR-0002, G-0002-4).

## References

- `docs/research/2026-10-baseline.md`, sections 2.1 and 4.
- ADR-0011 for the tier rules the first check enforces.
