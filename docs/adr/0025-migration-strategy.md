# ADR-0025: Migration strategy

| | |
|---|---|
| Status | Proposed (the cutover procedure is not yet decided) |
| Decided | 2026-10-08 (single cutover), 2026-10-10 (start now), 2026-10-11 (order of work, live data during the rework, reshaping after cutover), 2026-10-12 (ADRs and learning come first) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | every other ADR; the working plan is `docs/migration-plan.md` |

## Context

The other ADRs describe a target system that differs from the current one in almost
every part: one repository instead of nine, a database instead of a data repository,
containers in a guest instead of units on a host, Cloudflare instead of GitHub Pages,
one site instead of two. This ADR is about how to get from one to the other.

Constraints:

- **One maintainer, working with AI agents, in spare time.** The work will take weeks.
- **The live system keeps having events.** Game patches arrive every one to three
  weeks, discount announcements weekly (baseline, section 2.4). On 2026-10-10 the
  window was favourable: the last patch was four days old and the next discount week
  was already published.
- **The pieces are tightly coupled.** The new Site cannot go live without the
  database; the database needs the new pipeline; the bot needs the database and the
  new routes. There are few points at which a half-migrated system would work.
- **The server has no memory to run two full systems at once** (ADR-0006).
- **The riskiest parts are infrastructure nobody here has run before**: Docker inside a
  container guest, the Exporter inside both, DVC, the tunnel.
- The maintainer wanted to understand the new technology before building on it, and
  wanted the decisions recorded before work started.

## Decision

1. **One cutover, not a staged migration.** The old system serves users until the new
   one is complete; then everything switches.
2. **Up to about a day offline at cutover is acceptable.** Less is better.
3. **During the rework, the old code is frozen but the old pipeline keeps running.**
   (This revises an earlier decision that the old sites would simply go stale.)
   - The old repositories take no code changes except critical fixes, which are also
     made here.
   - The old host pipeline (update probe, patch day, discount watch) keeps running
     from the old repositories, so users keep getting patches and discount weeks.
   - The import of existing state into `state/` (ADR-0012) is re-runnable: once early,
     for development, and again at cutover to pick up what the old pipeline added.
   - The old pipeline on the host and the new one in the guest must never run at the
     same time. One lock file on the host is shared into the guest (ADR-0008).
   - Accepted cost: the old services keep their secrets in environment variables until
     cutover (ADR-0022).
4. **Pipe first, reshape later.** The new system is proven end to end on the Parser's
   current output shapes. The three-tier reshaping (ADR-0011) happens after cutover,
   one object type per pull request. Accepted cost: consumer code for each type is
   written once during the migration and touched again when that type is reshaped.
5. **The first wave is deliberately minimal**: the Site and the bot read the database
   file directly; the API is a placeholder (ADR-0018).
6. **Order of work**, detailed in `docs/migration-plan.md`:

   | Phase | Content | Done when |
   |---|---|---|
   | before | the maintainer learns the new technology (containers, uv, DVC) | done 2026-10-12 |
   | -1 | these ADRs and the supporting documents | reviewed and merged |
   | 0 | preparation that is independent of everything else: the agent secrets guard, the DNS move, the pipeline memory investigation | each done |
   | 1 | repository skeleton: history merge, packages, workspaces, CI. Behaviour does not change. | every existing test passes in CI |
   | 2 | the data path: models, state import, database build, image conversion, DVC, the reworked orchestrator | the pipeline produces a database that passes the gate, with assets in staging storage |
   | 3 | infrastructure and deployment: the guest, images, deploy script, tunnel, storage, backups. Mostly in parallel with phase 2. | a staging deployment comes up and `/v1/meta` answers through the tunnel; then the restore drill |
   | 4 | consumers: the merged Site and the bot | a full staging run works: pipeline, database, staging site, test bot |
   | 5 | cutover | not yet specified |
   | 6 | after cutover: the tier reshaping, API waves 2 and 3, parked ideas | ongoing |

7. **Start now.** (2026-10-10.)

## Alternatives considered

- **A staged migration**, moving one piece at a time: for example the monorepo first
  with behaviour unchanged, then the database behind the old sites, then hosting.
  Each step would be smaller and reversible. Rejected by the maintainer in favour of a
  single cutover. The coupling in the Context means many intermediate states would
  need throwaway adapters (the old Site reading the new database, the new pipeline
  writing the old Data repository). Phase 1 keeps the one staged step that is free:
  moving the code without changing what it does.
- **Freeze everything, including data, until cutover.** This was the first decision:
  up to a day of staleness seemed fine. It was revised once the work was estimated in
  weeks, during which several discount weeks and probably a patch would be missed.
- **Reshape the data first.** Do the three-tier rework before building anything on the
  data. Rejected: it is the largest and least bounded task, and doing it first would
  push every infrastructure risk to the end and lengthen the time two systems run side
  by side.
- **Move consumers to the API during the migration.** Rejected in ADR-0018.
- **Wait for the next patch day to start.** Unnecessary: the window was open.

## Consequences

- Users see no change and no staleness until cutover day.
- For the whole rework there are two code bases: the frozen old one in production and
  the new one here. A critical fix has to be made twice.
- Nothing in the new system serves real users until everything does. Problems that
  only real traffic or a real patch day would reveal are found after cutover, not
  before. Staging (ADR-0008) is the mitigation, and its fidelity matters accordingly.
- The single cutover has to be planned in detail, and it is the one part of the plan
  that is not written (G-0025-1).
- The work is ordered so that the cheapest tests of the riskiest assumptions come
  early, provided the spikes in G-0025-3 are actually done first.

## Gaps and open questions

### G-0025-1. The cutover procedure and rollback are not decided

- **Kind:** decision
- **Needed by:** before phase 5; ideally sketched before phase 3, since it shapes the deploy script

This was the last item on the decision list and was deferred when work moved to
writing these records. A cutover runbook has to settle at least:

- **The order of switches**: stop the old pipeline's timers; final state import; first
  production pipeline run in the new system; DNS and hosting switch for the Site;
  the bot's identity moving from the old process to the new container; the old DV
  address replaced by its redirect page; archiving the old repositories.
- **What users see at each step**, and which steps are the "up to a day offline".
- **The point of no return.** Before it, going back is restarting the old units.
  After it, something has changed that the old system cannot follow (for example
  state committed in the new format only, or the bot linking to new routes).
- **Rollback for each step before that point**: the frozen Data repository and the old
  GitHub Pages deployments are the fallback; DNS can be pointed back.
- **Timing**: immediately after a patch and a discount week, to have the longest quiet
  period, and what to do if a patch lands mid-cutover anyway.
- **Things already noted for the runbook** in other ADRs: updating links in the
  Discord developer portal (ADR-0021, G-0021-5); the redirect page before archiving
  (ADR-0002, G-0002-5); retiring old secrets (ADR-0022, G-0022-6); open issues in old
  repositories (ADR-0002, G-0002-6); the old API repository (ADR-0002, G-0002-3).

### G-0025-2. How to know the new system matches the old one

- **Kind:** design
- **Needed by:** phase 4

"A full staging run works" says the new system runs. It does not say it shows the
same things as the old one. With about 700 pages and a bot with intricate matching
rules, differences will exist and most will be unintended. A parity check before
cutover could compare: the set of pages (every old address resolves, directly or by
redirect); the visible text of each page between the live site and staging; and the
bot's answers to a fixed list of queries, old bot against test bot. Without something
like this, cutover is the test.

### G-0025-3. The risky assumptions should be tested before the work that depends on them

- **Kind:** action
- **Needed by:** the start of phase 3, and before phase 2 goes far

Three unverified assumptions could each change the design if they fail, and all three
are cheap to test compared with the work built on them:

1. Docker runs inside an unprivileged container guest on this server without giving
   up its confinement (ADR-0006, G-0006-1).
2. The Exporter's game-launching step works inside that (ADR-0006, G-0006-2).
3. The pipeline fits in the memory limit (ADR-0006, G-0006-3).

The plan puts infrastructure in phase 3, "mostly in parallel with phase 2". These
three spikes should come first in that parallel track, before the Dockerfiles and the
deploy script are written around an arrangement that might not work.

### G-0025-4. Design questions that block phase 2

- **Kind:** decision
- **Needed by:** the start of phase 2

Several gaps in other ADRs are not details to settle during implementation; the
pipeline cannot be laid out until they are answered. Collected here so they are not
discovered one at a time:

- which branch the pipeline commits state to, and which state it reads (ADR-0012,
  G-0012-1);
- where DVC's project directory is and what is checked out in it (ADR-0016,
  G-0016-1);
- where DVC runs relative to the containers (ADR-0016, G-0016-2);
- how a code release that changes the data is deployed (ADR-0005, G-0005-3);
- whether assets are named by content hash (ADR-0020, G-0020-1; ADR-0014, G-0014-1);
- the Site being built twice, and which build is deployed (ADR-0014, G-0014-2);
- staging storage as buckets or a prefix (ADR-0008, G-0008-2).

They interact, and are best decided together in one sitting, as a follow-up ADR.

### G-0025-5. Keeping the freeze honest

- **Kind:** decision
- **Needed by:** phase 1

"No code changes to the old repositories except critical fixes" is a rule with nothing
enforcing it, across nine repositories that agents can edit. And each critical fix
must be made twice by hand. After the history merge, a fix made only in an old
repository is silently lost at cutover. A simple guard: note the commit each old
repository was merged at, and compare before cutover.

### G-0025-6. The shared lock between the old and new pipelines

- **Kind:** design
- **Needed by:** phase 3 (as soon as anything runs in the guest)

Decision 3 relies on one lock file visible to the old pipeline on the host and the new
one in the guest. The old pipeline does not take any such lock today, so its units
have to be changed, which is a change to frozen code. The file also has to be shared
across the container boundary with ownership that both sides can use (ADR-0006,
G-0006-4). Ownership is settled: both sides run as id 1000, which is the same account
on the host and in the guest. A lock taken on the host is seen inside the guest and
inside its Docker containers through the bind mount, and the other way round, with both
`flock` and POSIX locks (tested 2026-10-23,
`docs/research/2026-10-volume-ownership.md`).

### G-0025-7. The final state import

- **Kind:** design
- **Needed by:** phase 2 (the script), phase 5 (its last run)

The import runs again at cutover to pick up what the old pipeline added. That only
works if re-running it never loses anything written by the new system in between: for
example slug history accumulated in staging, or hand corrections made in `state/`
during development. The import needs a defined merge rule per file, not just
"overwrite".

### G-0025-8. No estimate

- **Kind:** action
- **Needed by:** phase -1

The plan has an order and exit conditions but no sizes. Even rough sizes per phase
would show whether "weeks" is three or twelve, which matters for how long the freeze
and the double maintenance last, and for whether to cut scope (for example leaving
the Site on its current host for a first cutover).

### G-0025-9. Moving the bot

- **Kind:** design
- **Needed by:** phase 5

The production bot is one Discord identity. It can only sensibly run in one place at a
time. At cutover the old unit stops and the new container starts with the same token.
Whether its registered commands, its links (new routes and trailing slashes) and its
data source all switch cleanly in one step should be rehearsed with the test bot.

## References

- `docs/migration-plan.md` for the working plan.
- `docs/research/2026-10-baseline.md` for the starting point.
