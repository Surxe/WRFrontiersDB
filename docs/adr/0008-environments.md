# ADR-0008: Environments: local, staging and production

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-08 (test bot, configurable sinks), 2026-10-09 (staging), 2026-10-10 (staging through the deploy script, same gate) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0006 (hosting), ADR-0007 (deployment), ADR-0014 (swap gate), ADR-0016 (DVC), ADR-0019 (Cloudflare), ADR-0022 (secrets) |

## Context

Today there is one environment: production. The pipeline's outputs are hard-wired to
public places. `PUSH` and `INDEX` commit to the live Data repository (the remote is
fixed in the code), `SITE-DEPLOY` publishes the live site, the discount run dispatches
the live DV workflow, and the one bot token belongs to the live bot. Trying a change
end to end means either doing it in production or switching stages off by hand with
`SHOULD_*` flags and hoping the right ones were chosen.

The maintainer first asked whether a complete local end-to-end run would remove the
need for a test environment. It cannot, for a reason specific to this project: the
workstation's game data is stale. Patches are only downloaded and processed on the
server, so pipeline work and end-to-end testing have to happen there.

The maintainer then asked for a test environment "with minimal differences from
production".

## Decision

1. **A staging environment exists, and differs from production only in three things:**
   where outputs go, which credentials it uses, and its ports and hostnames. Same
   images, same Compose file, same pipeline, same deploy script.
2. **It runs on the same guest as production**, as a separate Compose project, and it
   is complete end to end: staging pipeline, staging database, staging object storage,
   staging API, a test Discord bot, and the Site built against the staging database and
   served at a staging hostname behind a login (ADR-0019).
3. **It is always deployed with the deploy script** (`deploy --env staging <ref>`),
   never started by hand, so every staging run also exercises the deployment path
   (ADR-0007).
4. **It reuses production's downloaded game files read-only.** Staging never downloads
   the game and so needs no Steam login (ADR-0016).
5. **Every output destination in the pipeline is configuration** ("configurable
   sinks"), with named profiles. Nothing a non-production profile does can touch
   anything public.
6. **A second Discord bot identity** (its own token, a private test server) is used
   outside production.
7. **One lock is shared by every pipeline run on the machine.** Production and staging
   pipelines never run at the same time, so the guest's memory limit holds (ADR-0006).
   During the migration the old host pipeline takes the same lock (ADR-0025).
8. **Staging runs the same swap gate as production**, with the same thresholds,
   comparing its candidate database against production's current one. Its gate report
   therefore doubles as a description of what a branch would change (ADR-0014).
9. **Staging data is short-lived**: its published databases expire after 14 days
   (ADR-0015).
10. **Per-pull-request preview sites are not staging and are not built now**
    (ADR-0004). A preview would show Site code against production data; staging shows
    the whole chain.

## Alternatives considered

- **No staging; rely on unit tests and careful releases.** Rejected: most of the risk
  in this system is in the joins between stages and in real game data, which unit tests
  with fixtures do not reach.
- **A full local end-to-end environment on the workstation instead.** Rejected: stale
  data, as above. Local remains useful for unit tests and for working on one app.
- **Staging on a separate guest or machine.** Better isolation, and it was part of a
  proposed security design (ADR-0022). Rejected with that design: more to manage, and
  the machine has no memory to spare for a second copy of anything.
- **Staging only for the Site** (preview deployments). Rejected as insufficient: the
  Site is the part least likely to break silently.
- **A staging pipeline with its own download of the game.** Rejected: 15 GB more disk,
  a second Steam login, and nothing learned from it.

## Consequences

- A change to any stage can be run through the whole chain, on real current data,
  without anything public changing.
- The deploy script and the swap gate are exercised often, not only on release day.
- Staging shares a machine, a memory limit, a Docker daemon and a data volume with
  production. It is production-like, not isolated: a staging run delays a production
  run that arrives while it holds the lock, and a mistake in staging's configuration
  could in principle write to a production path.
- Staging needs its own set of external resources: buckets, a tunnel, a hostname, a
  bot, tokens. Each has to be created once (ADR-0022).
- The pipeline code has to be reworked so that no destination is hard-wired. This is a
  precondition for everything else here.

## Gaps and open questions

### G-0008-1. Is "dev" on the server a third environment

- **Kind:** decision
- **Needed by:** phase 3

The decisions describe two things on the server besides production: a Compose project
run from a working copy (`-p wrfdb-dev --profile dev`), and staging, deployed by
script from CI-built images. The original staging decision placed staging "on the same
guest as the dev Compose project", which can be read as either "they are the same" or
"they sit side by side".

**Proposed default:** treat them as two environments with different purposes.

| | Code comes from | Started by | For |
|---|---|---|---|
| Local | working copy on the workstation | hand | unit tests, one app at a time |
| Dev | working copy on the server | hand | iterating on pipeline code against real data |
| Staging | CI-built image, any commit | deploy script | end-to-end proof before a release |
| Production | CI-built image, release tag | deploy script | users |

If that is right, dev and staging need separate project names, output locations and
lock handling, and "dev" needs its own rule about what it may write to.

### G-0008-2. Staging storage: a prefix or separate buckets

- **Kind:** decision
- **Needed by:** phase 3

The decisions say staging writes to "a dev prefix" in object storage and that its
databases live under "its own prefix". The storage provider's access tokens can be
limited to whole buckets but not to a prefix inside a bucket
(`docs/research/external-facts.md`). With a shared bucket, staging's token could
therefore overwrite production's objects, and public access (granted per bucket) could
not differ between the two. Separate staging buckets were proposed during the secrets
discussion as part of a design that was rejected as a whole; this point was not decided
on its own.

**Proposed default:** separate staging buckets, one for assets and one for databases,
each with its own token.

### G-0008-3. What staging does with accumulated state

- **Kind:** design
- **Needed by:** phase 2

The production pipeline reads `state/`, updates it and commits it (ADR-0012). Staging
must read the same state to produce a comparable database, but must never push its
changes to the shared history. The log says staging's lockfile "stays in the dev
workspace"; state was not addressed. Staging also has to start from production's
current state, which only exists in git after production's last commit.

### G-0008-4. The scheduled jobs in staging

- **Kind:** decision
- **Needed by:** phase 3

Should staging run the update probe and the discount watch on a timer, or only when
asked? If on a timer, a new patch would be processed twice, once per environment, with
the two runs queueing on the lock. If only on request, staging does not test the
scheduled path.

**Proposed default:** no timers in staging; the same commands are run by hand or by the
deploy script when a staging run is wanted.

### G-0008-5. Staging's shared write access to the stage cache

- **Kind:** verification
- **Needed by:** phase 2

Staging and production share one DVC cache so that staging can reuse production's
stage outputs (ADR-0016). Staging can therefore add entries that production may later
reuse (a staging run with production-identical inputs is, by design, interchangeable),
and a cache clean-up run from one environment can delete entries the other still needs
unless told about it (`docs/research/external-facts.md`). The clean-up procedure must
name every workspace. See G-0016-3.

### G-0008-6. Data release ids in staging

- **Kind:** design
- **Needed by:** phase 2

A data release id is the game version plus a counter (ADR-0015). If staging counts
independently, a staging database and a production database can carry the same id with
different contents. Staging ids need to be visibly different (for example a suffix),
and the gate's "not older than production" check has to cope with that.

### G-0008-7. Credentials that staging shares with production

- **Kind:** decision
- **Needed by:** phase 3

Staging has its own bot token and tunnel. Not yet decided for staging: the email
sender for run reports (same account with a marked subject line, or no email), the Jev
classifier key used for discount mapping (ADR-0017), the GitHub token, and read access
to production's database bucket (needed for the gate comparison in decision 8).

### G-0008-8. How the staging Site gets built and deployed

- **Kind:** design
- **Needed by:** phase 4

The production Site is deployed by a GitHub Actions workflow at a release tag
(ADR-0019). The staging Site must be built from an arbitrary commit against the staging
database and deployed to the staging hostname. That needs a variant of the workflow
that takes a commit and an environment, and a way for the guest to trigger it. An
earlier wording described this as a "preview deploy"; the later decision (a named
staging environment behind a login) replaces it.

### G-0008-9. What can be done on the workstation

- **Kind:** design
- **Needed by:** phase 2

"Local" is where most editing happens, and its data is stale. It needs a defined way
to get a database to work against: download the current production database (which
needs a credential on the workstation, since the bucket is private), or build a small
one from fixtures. This is the same question as ADR-0004, G-0004-2, and should have the
same answer.

### G-0008-10. Protection against a staging run writing to production

- **Kind:** design
- **Needed by:** phase 2

Decision 5 depends on configuration being right. A second line of defence would be for
each profile's credentials to be unable to write to the other's destinations (which
G-0008-2 and ADR-0022 partly provide) and for the pipeline to refuse to start if its
profile name and its destinations disagree.

## References

- `docs/research/2026-10-baseline.md`, section 2.
- ADR-0014 for the gate that staging shares.
