# G-0006-7: starting again after a power cut (desk research 2026-10-28)

**Status.** Research only, not yet tested. The facts about the host were read on the
server as `dev`, without root, so the guest configs and the system journal were out of
reach. The remaining checks are listed at the end. A real reboot test is one of them.

**Answer, provisionally.** Most power cuts are not a restart problem, because the
server is a laptop with a battery. Three cases need different handling:

1. **A short cut (the battery lasts).** The host and guests keep running. The router
   loses power, so the uplink drops and later returns. What has to work is
   reconnection: wifi, the tunnel, the bot's gateway connection, and any timer that
   fires while the link is down.
2. **A long cut (the battery runs out).** Everything stops at once, uncleanly. When
   mains returns, the laptop probably **does not power itself on**, so a person has to
   press the button. No software setting can change that.
3. **A reboot** (an upgrade, a kernel, a crash, or the button after case 2). This is
   what the gap describes: each layer has to come back in order without help.

The design for case 3 is a short list of settings. Most of them already exist on the
host or in the Valheim stack. Cases 1 and 2 add two items the gap did not name: a
clean shutdown on low battery, and a way to learn that the server went down
(ADR-0024).

## The machine and its battery

| | |
|---|---|
| Model | Acer Swift 3 SF314-42, Insyde BIOS V1.08 (2020-10-14) |
| Battery | LG AP18C8K, Li-ion, 103 cycles |
| Charge, full / design | 3.235 / 4.267 Ah, so 76% of design |
| Energy at 11.25 V nominal | about 36 Wh (design about 48 Wh) |
| State on 2026-10-28 | on AC, full |
| Uptime | 38 days; last boot 2026-09-20 |

**How long the battery lasts is not measured.** The host's draw with Valheim and the
probes running is unknown. A guess of 6 to 12 W idle gives 3 to 6 hours. A patch-day
run uses the GPU and all cores, so it would shorten that. A measurement needs no
root: unplug the charger and log `/sys/class/power_supply/BAT1/charge_now` every
minute (see "Checks still needed").

**Powering on when mains returns.** Server boards have an "AC power recovery" or
"power on AC" setting. Consumer laptops usually do not. No source shows the option on
the SF314-42. Search results only turned up owner threads about the machine not
starting. So after a cut long enough to empty the battery, the server stays off until
someone presses the button. The option needs checking in the BIOS setup screen (Main
and Advanced pages), which needs physical access.

**Nothing shuts the host down cleanly on low battery.** Nothing like upower's
critical action or NUT is configured, and `logind.conf.d/home-server.conf` sets only
the lid switch. When the battery empties, the power just goes off. Valheim's world
save, the guest's filesystems, Docker, a pipeline run in progress and the DVC cache
all stop mid-write. The host should shut itself down cleanly at a threshold, for
example 10% while discharging. That is host configuration (ADR-0006 decision 8), so it
belongs in `home-server`, as a small timer or udev rule that reads the same sysfs
files.

## Layer by layer, after a reboot

| Layer | What brings it back | State today | Needed for the WRF guest |
|---|---|---|---|
| Host wifi | `home-server-wifi.service` (enabled): waits for `wlp1s0`, then wpa_supplicant and dhclient | Tested by three reboots on 2026-09-20 | Nothing |
| Guest bridge and NAT | `vmbr0` in `/etc/network/interfaces`; the masquerade rule is added in `post-up` | Independent of wifi being up | Nothing |
| Clock | RTC, then `chrony.service` (enabled) | Calendar timers rely on it | Nothing |
| Guests | `pve-guests.service` (enabled) starts every guest with `onboot: 1` | Valheim VM created with `--onboot 1` (`guests/create-vm.sh`) | `onboot: 1` in the creation script; an optional `startup: order=2` after Valheim |
| Docker | `docker.service` (enabled by the package) | Valheim's Compose file uses `restart: unless-stopped` | Same policy for `api`, `bot`, `cloudflared` |
| One-off pipeline containers | `docker compose run --rm` from timers | n/a | No restart policy: a run is started again by its timer, not by Docker |
| Scheduled jobs | systemd timers in the guest (ADR-0007 decision 13) | The host's probe and discount timers already use `Persistent=true` | `Persistent=true`; `After=`/`Wants=network-online.target` and `After=docker.service` |
| Tunnel | `cloudflared` service in the stack | n/a | Restart policy as above; see "The tunnel" |
| Bot | Compose service | Today a host unit: `Restart=on-failure`, `After=network-online.target` | Restart policy as above |

Notes on the table:

- **`unless-stopped`, not `always`.** After a reboot both start the container again.
  The difference is that a service someone stopped on purpose (for example staging,
  ADR-0008) stays stopped. That is what we want.
- **Starting the guest does not wait for wifi.** `pve-guests` does not wait for
  `network-online.target` on the host, and a guest on `vmbr0` sees its own link as up
  as soon as the bridge exists. So everything in the guest must tolerate starting
  with no internet. The tunnel and the bot retry. A timer's catch-up run (below) can
  fail on its first attempt.
- **`Persistent=true` catch-up.** A timer that should have fired while the machine
  was off fires once at boot. The update probe and the discount watch may then start
  together. ADR-0008's lock already makes them take turns. A catch-up run that fails
  because the uplink is not up yet is caught by the next regular run (every 20 minutes
  for the probe). That is acceptable, but it should be deliberate. Otherwise every
  unit needs a startup retry.
- **Guest 101.** `/etc/pve/lxc/101.conf` exists, probably the `lxc-lab` spike guest.
  Its `onboot` setting could not be read without root. If it is still there at cutover
  and set to start on boot, it competes with the WRF guest for memory.

## A run cut off part-way

- **Locks.** `flock` and POSIX locks belong to a process and are released when it
  dies. A lock file left on the volume does not block the next run (G-0025-6 tested
  the lock across host, guest and container, but not across a crash; the kernel's
  semantics cover it).
- **What production serves.** Only promotion changes what is served, and repointing
  `current` is a rename (ADR-0009, ADR-0014). A run that dies before promotion leaves
  the previous release live. A rename that the journal had not yet written is undone,
  and the old file is served.
- **Whether the patch is picked up again.** This depends on when the probe records a
  build as seen. If it records the build before the pipeline succeeds, the patch is
  silently skipped after the restart. The probe's state handling needs checking for
  this (see "Checks still needed").
- **DVC and stage outputs.** A stage killed mid-write leaves partial files. Whether
  ADR-0016's cache can mistake them for a finished stage is the same question as
  for a crash. It is noted here, not answered.

## The tunnel

`cloudflared` reconnects by itself when its connections drop, and Docker's restart
policy covers the process exiting. Reports from other users (Unraid and OpenWrt
forums, linked below) describe two other failures: a tunnel that stays alive but
never reconnects, and one started before the network was ready. Plain Docker does not
restart a container that is merely unhealthy (only Swarm does). A healthcheck on
cloudflared's `/ready` metrics endpoint would show the state in `docker ps`, but would
not fix it. This failure belongs to ADR-0024's table ("The tunnel drops"). G-0006-7 does
not have to solve it.

## Finding out it happened

ADR-0024 lists "the guest, the host or the home connection is down" as producing no
email. A restart is the moment it can be noticed cheaply. A oneshot host unit at boot
sends one email: when the host started, and whether the previous boot ended cleanly.
The journal of the last boot ends at `shutdown.target` or it does not. The battery's
charge can go in the same email. That uses the email path ADR-0024 already chose, with
no new account. It does not cover a cut long enough that the host never comes back,
which only an outside heartbeat would catch (declined in ADR-0024).

## Two things found along the way

- **The host's address is a plain DHCP lease** (192.168.0.239, no reservation;
  `home-server/docs/06-ethan-tasks.md` says that was fine because nothing connected
  to the box). ADR-0007 decision 9 has `wrf release` connect from the workstation to
  the server over the home network. If the router gives out a different address after
  a cut, releases fail until someone finds the new address. This needs a DHCP
  reservation on the router, or a name that resolves without one.
- **Repeating an outage over a plain DHCP lease.** The router reboots when mains
  returns, while the laptop on battery stays up. wpa_supplicant re-associates by
  itself, and dhclient keeps renewing. That is the expected behaviour, but it has not
  been tested on this host. `home-server-wifi.service` is a oneshot, so nothing runs
  the bring-up script again if re-association fails.

## Proposed resolution

1. **Guest:** `onboot: 1` and `startup: order=2` (after Valheim) in `home-server`'s
   guest creation script.
2. **Compose:** `restart: unless-stopped` on every long-running service. Pipeline
   commands get none.
3. **Timers in `deploy/`:** `Persistent=true`, plus `Wants=`/`After=network-online.target`
   and `After=docker.service`. A failed catch-up run is left to the next regular run.
4. **Host, in `home-server`:** a clean shutdown at 10% battery while discharging, and
   a boot email (case 2 and ADR-0024).
5. **Accepted limitation:** after a cut long enough to empty the battery, the server
   stays off until someone presses the button (unless the BIOS check below finds an
   AC power-on option).
6. **Router:** a DHCP reservation for the host.

## Checks still needed

| Check | Needs | How |
|---|---|---|
| Battery runtime under normal load | Ethan to unplug the charger; no root | log `charge_now` and `status` from sysfs once a minute until 20%, then plug back in |
| AC power-on option in the BIOS | physical access | BIOS setup, Main and Advanced pages |
| Guest 101's `onboot` and whether it should still exist | root | `pct config 101` |
| Whether the last three reboots brought Valheim back without help | root (system journal) | `journalctl -b -1 -u pve-guests` |
| A full reboot with the WRF guest built to this design | root, after the guest exists | reboot; check guest, containers, timers, tunnel, bot, all without help |
| A router-only power cut | Ethan unplugs the router | check that the host re-associates, the tunnel and bot reconnect, and the address is unchanged |
| When the probe records a build as seen | code reading, Orchestrator | if before success, an interrupted patch day is skipped |

## Sources

- On the server, as `dev`, 2026-10-28: `/sys/class/power_supply/BAT1/*`,
  `/sys/class/dmi/id/*`, `journalctl --list-boots`, `systemctl list-unit-files`,
  `systemctl list-timers`, `/etc/systemd/logind.conf.d/home-server.conf`.
- `home-server` repository: `systemd/home-server-wifi.service`, `host/hs-wifi-up.sh`,
  `host/interfaces`, `guests/create-vm.sh`, `systemd/hs-wrf-*.timer`,
  `systemd/hs-wrf-discord-bot.service`, `docs/06-ethan-tasks.md`, `docs/07-status.md`.
- `valheim-server` repository: `valheim/docker-compose.yml` (`restart: unless-stopped`).
- Proxmox `pct` documentation, `onboot` and `startup`:
  https://pve.proxmox.com/pve-docs/pct.1.html
- Acer community threads on the SF314-42 (no AC power-on option found):
  https://community.acer.com/en/discussion/661064/acer-swift-3-sf314-42-wont-turn-on-no-signs-of-life
- cloudflared failing to reconnect, user reports:
  https://forums.unraid.net/topic/139806-cloudflared-container-tunnel-connections-quic/ ,
  https://forum.gl-inet.com/t/cloudflare/71014
