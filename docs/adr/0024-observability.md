# ADR-0024: Observability: email reports only, for now

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0007 (deployment), ADR-0014 (swap gate), ADR-0017 (discounts), ADR-0023 (backups) |

## Context

How the maintainer learns that something happened today (baseline, section 2):

- **The run-report email.** After every pipeline run, on success, on a failed stage or
  on a failed preflight, the Orchestrator emails a report: counts of warnings, errors
  and unknown properties per step, the parse log's warnings grouped, and the logs
  attached. The discount run sends the same kind of report, but only when there is a
  new week or a problem; a quiet poll sends nothing and deletes its own log folder.
- **The journal.** Services and timers are systemd units on the host, so their output
  and their memory and CPU summaries are in the system journal.
- **Nothing else.** No uptime check, no alert when the bot stops, no dashboard.

The new system has more moving parts that can fail quietly: containers in a guest, a
tunnel, a storage upload, a deployment workflow on GitHub, a gate that can decide not
to publish.

## Decision

1. **Email is the only reporting channel for now.** Run reports are emailed to the
   maintainer from a dedicated sender account, as the Orchestrator does today.
2. **Considered and not adopted now:**
   - heartbeat monitoring (a service such as healthchecks.io that each scheduled job
     and the bot would ping, and which emails when a ping is late);
   - an outside check that the API answers through the tunnel.
3. **A proper observability or tracing service is a later project**, recorded outside
   the migration.

## Alternatives considered

- **Heartbeat monitoring.** Proposed because it covers the two things email cannot:
  a job that never ran, and a long-running service that died. Each ping is an outbound
  request, so it works from behind the home router. Declined for now by the
  maintainer.
- **An outside reachability check** for the API, for example a scheduled GitHub
  Actions run. Deferred to the API phase: in the first wave nothing depends on the API
  (ADR-0018).
- **A metrics and logs stack** (Prometheus, Grafana, Loki). Rejected for now: it would
  take a real share of the guest's 3 GiB (ADR-0006), and a one-person project does not
  need dashboards to know a patch day failed. Named as a possible learning project.

## Consequences

- No new accounts, services or memory are needed.
- **Email reports only tell you about things that ran.** The following produce no
  email and would go unnoticed until someone looks or a user complains:

  | Failure | Why no email arrives |
  |---|---|
  | The guest, the host or the home connection is down | nothing is running to send one |
  | A timer stops firing | no run, so no report |
  | The bot or the API crashes and does not restart | they have no "run" to report on |
  | The tunnel drops | same |
  | The update probe is broken and sees no patches | a quiet probe and a broken probe look the same |
  | The news feed changes format and no discount week is detected | a quiet poll sends nothing by design (ADR-0017, G-0017-7) |
  | Email sending itself fails | the report is the thing that failed |
  | A backup stops happening | ADR-0023, G-0023-3 |

- **The swap gate raises the stakes of an unread email.** Before, a problem on patch
  day meant the patch went out with gaps. Now a blocking check means the patch does
  not go out at all until a person acts (ADR-0014). The report is the only thing that
  tells them.

## Gaps and open questions

### G-0024-1. Which silent failures are worth closing first

- **Kind:** decision
- **Needed by:** after cutover

The table above is the argument for revisiting decision 2. The cheapest partial fix
that needs no new service: a daily "still alive" line in an email, or a rule that the
pipeline reports when it has seen no patch for longer than the longest gap on record
and no discount week for more than ten days. Whether to do either is the maintainer's
call.

### G-0024-2. What the new run report contains

- **Kind:** design
- **Needed by:** phase 2

The existing report is built around the old stages. The new one has to carry: which
stages ran and which were reused from the cache (ADR-0016); the gate's result, check
by check, with any override used (ADR-0014); the data release id; what was added,
removed and changed against production; and the outcome of promotion and of the Site
deployment. For staging runs it doubles as the branch-against-production summary
(ADR-0008). Its `file://` links to logs will mean something different when logs are
inside a guest.

### G-0024-3. Logs: where they go and how long they are kept

- **Kind:** design
- **Needed by:** phase 3

Same as ADR-0007, G-0007-8. Container logs grow without limit unless a size cap or a
journal driver is configured. Pipeline run logs accumulate one folder per run. No
retention is set for either, on a guest whose disk is not yet sized.

### G-0024-4. Reports from staging

- **Kind:** decision
- **Needed by:** phase 3

Whether staging runs send email at all, and how a staging report is told apart from a
production one at a glance (a subject prefix), is open. See ADR-0008, G-0008-7.

### G-0024-5. Knowing how available the bot and API are

- **Kind:** decision
- **Needed by:** before any decision to rent a server

ADR-0006 leaves "move the API and bot to a rented server" without a trigger, and a
sensible trigger is measured downtime. With email only, downtime is not measured.
Even a crude record (the deploy script and a daily job appending the result of a
`/v1/meta` request to a file) would give a number to decide with.

## References

- `docs/research/2026-10-baseline.md`, section 2.
- The Orchestrator's `README.md`, "Run-report email".
