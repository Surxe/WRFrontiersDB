# ADR-0023: Backups and recovery

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-10 (backups), 2026-10-12 (settings document instead of Terraform) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0006 (hosting), ADR-0012 (state), ADR-0015 (database archive), ADR-0016 (DVC), ADR-0019 (Cloudflare), ADR-0022 (secrets) |

## Context

What is backed up on the server today (baseline, section 3):

- an encrypted file-level backup of the host's configuration, its secret files, the
  Proxmox configuration and a few small stores, to a USB stick, twice a day;
- a daily whole-machine dump of the Valheim VM to the same stick, 22.6 GB each, six
  kept.

Nothing backs up WRF. That has been tolerable because everything irreplaceable was in
git: the published data and its accumulated index in the Data repository, the mapped
discount weeks in the DV repository.

After the migration the things that exist are these:

| Thing | Where it lives | Can it be rebuilt? |
|---|---|---|
| Code | GitHub, plus a clone on each machine | not needed |
| Accumulated state (`state/`) | this repository | no; it is the record (ADR-0012) |
| Published databases | a private storage bucket | yes, slowly, from game files plus state (ADR-0015) |
| Images and models | a public storage bucket, plus the stage cache | yes, by the pipeline |
| Working data: game download, exports, the stage cache | the data volume on the server | yes: one download and one export |
| The guest: installed units, Compose set-up, secret files, operational state, logs | the WRF container guest | mostly, from this repository; secrets and operational state are the exceptions |
| Cloudflare settings | Cloudflare's dashboard | only from memory, unless written down |

## Decision

1. **Nothing irreplaceable lives only on the server.** Code and accumulated state are
   in git, on GitHub and in a clone on each machine. Databases are in object storage.
2. **The WRF guest is dumped daily to the USB stick, keeping three**, by a host
   systemd timer that runs after the Valheim dump.
   - Left out of the dump: the data volume (it is a mount, not part of the guest's
     disk); Docker's own storage (images are pulled again from the registry; exclude
     it with `--exclude-path '/var/lib/docker/?*' --exclude-path '/var/lib/containerd/?*'`,
     tested 2026-10-23 in ADR-0006, G-0006-5); the local copies of databases
     (downloaded again from storage).
   - Operational state (the update probe's and discount watch's state files, logs)
     therefore lives in a plain directory in the guest, not in a Docker-managed
     volume, so that the dump includes it.
   - Expected size: well under 1 GB per dump.
   - To restore: restore the dump, then run the deploy script, which pulls the images.
3. **No off-site copy for WRF.** The stick is attached to the same machine, so a fire
   or theft takes both; but everything irreplaceable is already elsewhere (decision
   1). The off-site copy of the WRF secrets is the maintainer's password manager; the
   tokens and accounts can also be re-created.
4. **The data volume and the stage cache are not backed up.** Losing them costs one
   download and one export.
5. **Published databases have no second copy** (ADR-0015).
6. **One restore drill at migration**: restore the first dump to a spare guest id,
   confirm that the deploy script brings the stack up, then delete it.
7. **Backup failures are reported by email**, the same way as other failures
   (ADR-0024).
8. **The backup timer is host-level configuration and lives in the `home-server`
   repository**, as the Valheim one lives in that server's own repository (ADR-0006).
9. **Cloudflare settings are recorded in a checked-in document** (`docs/cloudflare.md`,
   ADR-0019), not managed as code. Terraform was deferred.

## Alternatives considered

- **No backup of the guest; rebuild from the repository.** Everything in the guest
  except secrets and operational state can be recreated from `deploy/` and
  `home-server`. Rejected as the only path: it is slower, and it relies on the
  creation scripts being complete, which is only known after trying. The dump is cheap
  and makes recovery one command. The drill tests both.
- **File-level backup of the few paths that matter**, with the existing encrypted tool,
  instead of a whole-guest dump. Smaller and encrypted. Not chosen: the dump is
  Proxmox's standard mechanism and matches how Valheim is handled. See G-0023-2,
  which reopens this for the secrets directory.
- **Off-site copies** (the existing backup provider). Declined: nothing irreplaceable
  would be in them.
- **Backing up the data volume.** 25 GB and growing, all of it reproducible. Rejected.
- **Terraform for Cloudflare.** Deferred (ADR-0019).

## Consequences

- After a disk failure, recovery is: restore the guest, deploy, and let the pipeline
  rebuild its working data on the next run. Hours, mostly unattended.
- After losing the whole machine and the stick: rebuild the host from its repository,
  recreate the guest, re-enter secrets from the password manager, deploy. Longer, and
  never rehearsed.
- GitHub is the only remote home of accumulated state, and one storage account is the
  only home of the database archive. Both were accepted.
- The backup's value depends on the dump actually containing what is needed, which
  only the restore drill shows.

## Gaps and open questions

### G-0023-1. What the dump includes and excludes, exactly

- **Kind:** verification
- **Needed by:** phase 3

Decision 2 assumes three things about Proxmox's dump tool that were not confirmed in
its documentation (the relevant page was only partly read;
`docs/research/external-facts.md`): that a bind-mounted host directory is never
included; that a path inside the guest (Docker's storage) can be excluded; and that a
snapshot-style dump works for a container on this storage while Docker is running in
it. The first dump should be listed and its size checked against "well under 1 GB".

### G-0023-2. Secrets in an unencrypted dump

- **Kind:** decision
- **Needed by:** phase 3

Same as ADR-0022, G-0022-4. The dump includes the guest's secret files and is not
encrypted, while the host's secret files go through an encrypted backup on the same
stick. Excluding the secrets directory from the dump makes a restore need one more
manual step (re-entering secrets), which the drill would then cover.

### G-0023-3. A backup that silently stops

- **Kind:** decision
- **Needed by:** after cutover

Decision 7 reports failures. It cannot report a timer that never fires, a stick that
is unmounted, or a job that hangs. The existing backup script refuses to run when the
stick is not mounted, which produces a failure email only if that mechanism is wired
for the new timer too. Nothing checks that a recent dump exists. See ADR-0024.

### G-0023-4. The drill covers one failure, not the worst one

- **Kind:** decision
- **Needed by:** not scheduled

The drill restores a dump onto the same working host. The harder case, losing the
machine, depends on the host's own rebuild instructions, on the guest-creation script,
and on every secret being in the password manager. That path is documented in the
`home-server` repository for the host; the WRF part of it has never been walked. Once
after cutover would be enough to know.

### G-0023-5. Where operational state lives

- **Kind:** design
- **Needed by:** phase 3

Decision 2 says "a plain directory in the guest". The path, its ownership, and which
containers mount it are not fixed. What counts as operational state also needs
listing: the update probe's state and registry, the discount watch's state, run logs,
and DepotDownloader's remembered login (ADR-0022, G-0022-2), which is both
operational state and a secret.

### G-0023-6. `docs/cloudflare.md` does not exist yet

- **Kind:** action
- **Needed by:** phase 0 (it should be started with the DNS move)

The document is the only record of settings made in a dashboard. It is most useful if
it is written as each setting is made, beginning with the list of DNS records that the
move in ADR-0019 needs anyway.

## References

- `docs/research/2026-10-baseline.md`, section 3.
- The `home-server` repository's backup scripts and restore runbook.
