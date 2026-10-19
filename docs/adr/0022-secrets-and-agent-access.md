# ADR-0022: Secrets and the AI agent's access

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10; one finding added 2026-10-12 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0006 (hosting), ADR-0007 (deployment), ADR-0008 (environments), ADR-0019 (Cloudflare), ADR-0023 (backups) |

## Context

Much of the work on this project is done by an AI coding agent running under its own
account on the maintainer's machines. The agent reads files, runs commands and prints
their output into a conversation. The concern the maintainer raised is specific:
**the agent accidentally exposing a secret**, by reading a file it did not need to,
dumping an environment while debugging, or including a value in a log, a commit or a
report.

What was found on the server on 2026-10-10 (baseline, section 7; only names and
permissions were examined, no secret value was read):

1. Secret files are owned by root and readable only by root. That looks protective and
   is not: the agent's account is the server's only login account and can run any
   command as root without a password. One command reads any of them.
2. Even without that, the WRF services run as the agent's account with their secrets
   in environment variables. Any process of that account can read another's
   environment, and every child process inherits it: the game launcher, the exporter,
   `npm` and `git` all run today with the Steam password and a GitHub token in their
   environment.
3. Those services run code from repositories the agent can edit.
4. The agent's home directory holds the agent's own credentials (for git, GitHub and
   itself). These are meant for it.

The maintainer had believed the agent could not act as root there.

The rework adds credentials: Cloudflare (Workers, storage, tunnels), a second Discord
bot, and a GitHub token for the pipeline's commits.

## Decision

The goal, in the maintainer's words: make secrets **difficult for the agent to read by
accident, not impossible**, while the agent stays able to develop on the server and to
publish to production when asked.

### What stays as it is

1. The host is unchanged: the agent's account keeps full administrative rights.
2. There is one WRF guest (ADR-0006). The agent has root and Docker access inside it,
   develops there, and runs production deployments when asked.

### Where secrets live

3. **One known location per machine, readable only by root**: the existing directory
   on the host, and `/etc/wrfdb/secrets/` in the guest. Never in a repository, a
   `.env` file or the agent's home directory. A broad search by the agent then meets
   "permission denied" instead of printing a value; reading one takes a deliberate
   privileged command.

### A guard in the agent's own configuration

4. **Checked into the shared machine-configuration repository, so both machines get
   it:**
   - permission rules that stop the agent's file tools from opening the secret
     locations, git credential files and SSH private keys;
   - a hook that inspects each shell command before it runs and blocks any that names
     a secret location or is known to dump secrets: printing the environment, reading
     another process's environment, listing processes with their environments,
     `docker inspect`, `docker compose config` (which prints resolved values),
     `systemctl show`. A blocked command returns a message telling the agent to ask
     the maintainer.
5. **This is a tripwire, not a wall.** It works by matching patterns and can be
   bypassed. It exists to catch accidents.

### Code that cannot print secrets

6. **Secrets reach containers as files, never as environment variables**: Compose
   `secrets:` mounts each at `/run/secrets/<name>`, and services read them through
   pydantic-settings' `secrets_dir`. They then do not appear in a container's
   environment, in `docker inspect`, in the process table, or in any child process.
7. **Every secret field is typed so that printing it shows asterisks** (`SecretStr`).
8. **A log filter in the shared package masks every loaded secret value**, which also
   covers the emailed run reports.
9. **Where a tool can only take a secret as an environment variable or argument, the
   code supplies it to that one subprocess only.**

### Keeping secrets out of git

10. **A `gitleaks` pre-commit hook in this repository, and GitHub push protection**
    (ADR-0004).

### Limiting what a leak could do

11. **Narrow credentials**: a GitHub token limited to this repository; storage tokens
    limited to their buckets; a Cloudflare token limited to Workers; one tunnel
    credential per environment; a separate bot identity for staging.
12. **Dedicated accounts** for the Steam login and for the address that sends run
    reports, so that neither is the maintainer's personal account. The maintainer
    states both are already so.

### Accepted

13. The agent can still read any secret deliberately, or through a route the hook does
    not anticipate.
14. The credentials in the agent's home directory are the agent's own and stay
    readable by it.
15. The maintainer's effort is one-time: creating the tokens and placing the secret
    files in the guest.

## Alternatives considered

### Full separation (proposed, costed and rejected)

A design in which the agent's account could not reach a production secret by any
route was worked out first:

- split the host into a human administrator account and an agent account without
  general administrative rights, the agent keeping a short allow-list of read-only
  diagnostics plus a few root-owned wrapper scripts that validate their arguments;
- two guests, production and development, with the agent having root in the second
  and no shell in the first;
- staging given its own credentials throughout, including separate storage buckets,
  with no Steam login and no email credential in the agent's reach;
- a helper for the maintainer to place a secret without it appearing on screen or in
  shell history;
- the Cloudflare deploy token held only in GitHub.

The maintainer rejected it: "that's a lot to manage, and if I have to run this much
myself, it's just not worth it for personal scale." Its cost was real: every
host-level change would become "the agent prepares, the maintainer runs", and the
project would gain a second guest and a set of privileged scripts to maintain.

Parts of it survive in the decision above (files instead of environment variables,
narrow tokens, a separate staging bot). One part was neither adopted nor explicitly
dropped and is listed as a gap: separate staging buckets (ADR-0008, G-0008-2). Where
the Site's deploy token lives had already been decided: in GitHub (ADR-0019,
decision 4).

### Others

- **Encrypt secrets in the repository** (sops, git-crypt). Rejected for this problem:
  the key would be on the same machine, readable by the same account, and the
  decrypted values would still reach processes somehow.
- **A secrets manager service** (Vault and similar). Far more machinery than a
  handful of tokens on one machine warrant.
- **Rely on the agent's instructions alone** ("never read secrets"). This is the
  situation today. It depends on the agent never making a mistake, which is the thing
  being guarded against.
- **Do nothing.** Rejected by the maintainer: "that needs to go away, obviously."

## Consequences

- An accidental exposure now needs several things to go wrong at once: a command that
  slips past the hook, aimed at a root-only path, or a code path that defeats both the
  type and the log filter.
- A determined or confused agent is not stopped. This is a deliberate limit of the
  design.
- Secrets are no longer inherited by child processes. Today the game launcher and
  third-party tools run with them.
- Production and staging share a guest in which the agent has root, so staging's
  separate credentials limit the damage of a staging *mistake*, not of a leak.
- The security model is described in a public repository. It was written without
  addresses, account names or ids, and the machine repositories that hold those
  details are themselves already public.

## Gaps and open questions

### G-0022-1. The guard does not exist yet

- **Kind:** action
- **Needed by:** phase 0

Decision 4 is unbuilt. It is independent of the migration and would protect the
current server, where the exposure in the Context exists today. Until it is built,
nothing has changed. A second agent harness in use on these machines needs an
equivalent, if it supports such hooks; that was not checked.

### G-0022-2. The Steam password is passed on a command line

- **Kind:** decision
- **Needed by:** phase 2

Found on 2026-10-12: the Exporter gives DepotDownloader the Steam password as a
command-line argument. A process's command line is visible to every user of a machine
for as long as it runs. This contradicts decision 9's intent and was recorded as a
finding, not yet agreed as a change. The Exporter also passes `-remember-password`,
which should make the password unnecessary after a first login.

Two related points: DepotDownloader keeps its remembered login in the running
account's home directory (baseline, section 2.3), so in a container that location
must be a persistent volume and must be treated as a secret in its own right; and
without it, every pipeline run would need the password again.

### G-0022-3. File permissions for secrets inside containers

- **Kind:** design
- **Needed by:** phase 3

A file-based Compose secret appears in the container with the ownership and mode of
the file on the guest. A file readable only by root cannot be read by a service
running as an ordinary user inside its container, which is how services should run.
The ownership scheme (a dedicated group, or one owner per service) has to be chosen
together with the user-id mapping in ADR-0006, G-0006-4.

### G-0022-4. Secrets in backups

- **Kind:** decision
- **Needed by:** phase 3

The guest is backed up as a whole-container dump to a USB stick (ADR-0023). The dump
includes `/etc/wrfdb/secrets/`, and such dumps are not encrypted. The host's own
secret files are backed up through an encrypted repository on the same stick, so the
two are treated differently for no stated reason. Options: exclude the secrets
directory from the dump (the maintainer's password manager is the stated off-site
copy); encrypt the dump; or accept it, given that the stick sits in the same room as
the machine.

### G-0022-5. The list of secrets

- **Kind:** action
- **Needed by:** phase 3

`deploy/secrets.example` is to list every secret by name with its purpose and scope,
never its value. The list as understood today:

| Secret | Used by | Production | Staging |
|---|---|---|---|
| Steam login | pipeline (download) | yes | not needed (ADR-0016) |
| Discord bot token | bot | production bot | test bot |
| Storage, read-write | pipeline | production buckets | staging buckets |
| Storage, read-only | API | database bucket | staging database bucket |
| Tunnel credential | `cloudflared` | production tunnel | staging tunnel |
| GitHub token | pipeline (state commits, workflow trigger) | yes | to decide (ADR-0008, G-0008-7) |
| Jev API key | discount mapping | yes | to decide |
| Email sender credential | run reports | yes | to decide |
| Cloudflare Workers token | Site deployment | in GitHub only | in GitHub only |
| Storage read token for the Site build | GitHub Actions | to decide (ADR-0019, G-0019-3) | to decide |

### G-0022-6. Retiring the old secrets

- **Kind:** action
- **Needed by:** phase 5 (cutover)

The old services keep their secrets in environment variables until cutover; that was
accepted (ADR-0025). After cutover the old secret files on the host should be removed
and the credentials that only the old system used should be revoked, in particular
the GitHub token that pushes to the Data repository.

### G-0022-7. Rotation

- **Kind:** decision
- **Needed by:** after cutover

Nothing says when a token is replaced, or what to do when one is suspected leaked.
With narrow tokens the procedure is short, which is a reason to write it down once.

### G-0022-8. What the log filter cannot catch

- **Kind:** verification
- **Needed by:** phase 2

Masking works on exact values. It will not catch a secret that has been encoded,
split across lines, or embedded in a URL that a library logs in its own format. A
test that pushes each loaded secret through the logging path, in plain and
URL-encoded form, would show what gets through.

### G-0022-9. Account security outside the machines

- **Kind:** action
- **Needed by:** phase 0

See ADR-0019, G-0019-8: two-factor authentication on the Cloudflare, GitHub and
registrar accounts.

## References

- `docs/research/2026-10-baseline.md`, sections 2.3 and 7.
- pydantic-settings, secrets directories:
  https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Compose secrets: https://docs.docker.com/compose/how-tos/use-secrets/
