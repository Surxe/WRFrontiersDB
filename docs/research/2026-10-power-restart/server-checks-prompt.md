# Prompt: finish G-0006-7 on the server

Hand this to an agent running on the home server (the Proxmox host), as a user with
sudo. It completes the checks that the workstation session could not run as `dev`.

---

You are on the home server (Proxmox host, hostname `home-server`). The repository is
`/srv/dev/repos/WRFrontiersDB`. Check out the branch `research/g-0006-7-power-restart`
and read these first:

- `docs/research/2026-10-power-restart.md`: the desk research for gap G-0006-7
  ("Starting again after a power cut"), with a "Checks still needed" table;
- `docs/adr/0006-hosting-topology.md`, section G-0006-7, and how G-0006-1 to G-0006-6
  were marked resolved (the "**Resolved YYYY-MM-DD:**" paragraphs and the "Decided"
  row at the top);
- `docs/adr/0024-observability.md`, the table of failures that produce no email.

Rules: read-only on production. Do not reboot the host, stop Valheim (VM 100), or
change any guest's configuration without asking Ethan first. Do not read or print
secrets. No emojis in files.

## Checks you can do alone

1. **Guest 101.** Run `pct config 101` and `pct status 101`. Record its name, `onboot`,
   `startup`, memory and swap. Is it the `lxc-lab` spike guest, and does anything
   still need it? Do not delete it; recommend what to do.
2. **VM 100.** Run `qm config 100`. Record `onboot` and `startup`.
3. **Past reboots.** For boots -1, -2 and -3 (`journalctl --list-boots`), check
   whether `pve-guests.service` started VM 100 without help, and how long it took
   from kernel start to:
   - `home-server-wifi.service` finishing;
   - `network-online.target`;
   - VM 100 starting.

   Check whether each previous boot ended cleanly. Use `journalctl -b <n> -u pve-guests`,
   `-u home-server-wifi`, and `journalctl -b <n> -o short-monotonic`.
4. **Low-battery handling.** Confirm that nothing handles low battery: upower and its
   `CriticalPowerAction`, NUT, acpid rules, udev rules on `power_supply`. List what is
   installed. Name the smallest host-side mechanism that would run `systemctl poweroff`
   at 10% while discharging.
5. **The probe's "seen" state** (code reading). In `/srv/dev/repos/WRFrontiersDB-Orchestrator`
   and the update probe's unit in `/srv/dev/repos/home-server/systemd/`: when is a
   new game build recorded as handled? If it is recorded before the pipeline
   succeeds, a run cut off by a power loss skips that patch for good. Give the file
   and line.
6. **Docker in the guest.** If the WRF guest exists by now, check:
   - `docker.service` is enabled in it;
   - the restart policy of every running container;
   - every WRF timer has `Persistent=`, `After=network-online.target` and
     `After=docker.service`.

   If the guest does not exist yet, say so.

## Checks that need Ethan

Ask him before each one, and record the result with the date.

7. **Battery runtime.** He unplugs the charger. Log
   `date, status, charge_now, capacity` from `/sys/class/power_supply/BAT1/` every 60
   seconds to a file, with Valheim and the normal timers running. Stop at 20% or when
   he says, and plug back in. Report minutes per 10% and the extrapolated time to
   empty. Save the log under `docs/research/2026-10-power-restart/`.
8. **BIOS AC power-on.** He checks the BIOS setup screen (Acer Swift 3 SF314-42,
   Insyde V1.08) for an option to power on when AC returns. Record yes or no.
9. **Router-only outage.** He unplugs the router for about 2 minutes while the host
   runs on mains. Then check:
   - `wlp1s0` re-associated without help, and how long it took;
   - the DHCP address is unchanged;
   - the bot reconnected (`journalctl -u hs-wrf-discord-bot`);
   - Valheim's container is still up.
10. **Full reboot** (only if Ethan agrees, at a time with no Valheim players). Run
    `sudo reboot`, then time the return of each layer: wifi, VM 100, the WRF guest
    if it exists, the timers (`systemctl list-timers`, catch-up runs), the bot. Also
    record whether hs-boot-report's email arrived, if `home-server` has deployed it.

## What to write

- Add a "Results (YYYY-MM-DD, on the server)" section to
  `docs/research/2026-10-power-restart.md`. Fill in or remove each row of
  "Checks still needed". Correct anything in the desk research that turned out wrong.
- In `docs/adr/0006-hosting-topology.md`, under G-0006-7:
  - if the proposed resolution holds, add a "**Resolved YYYY-MM-DD:**" paragraph in
    the style of G-0006-1 to G-0006-6, and a matching entry in the "Decided" row;
  - if it does not, update the gap text with what was learned and leave it open.
- If the probe check (5) finds a skipped-patch risk, add it as a new gap in the ADR
  that owns the probe, not in ADR-0006.
- Regenerate `docs/open-questions.md` with `python tools/docs/gen_open_questions.py`.
  Never edit that file by hand.
- Commit on the same branch and push. Do not open or merge a PR unless Ethan asks.
  End the commit message with the attribution line your harness gives you.
