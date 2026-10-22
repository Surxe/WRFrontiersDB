# Baseline: the system before the rework (October 2026)

This file records what existed, and what was measured, before the move into this
repository. The ADRs cite it as evidence. It is a snapshot: it is not updated as the
system changes. Where a number matters to a decision, the date and the method are given
so it can be re-measured.

Conventions used here and in the ADRs:

- **Measured** means a command was run and the result is recorded with its date.
- **Read** means the fact comes from reading code or configuration in the named repo.
- **Stated** means the maintainer said it and it was not independently checked.

Host-specific details that have no bearing on a decision (addresses, account names,
ids) are deliberately left out. They live in the `home-server` repository.

## 1. Repositories

Eleven repositories take part in the War Robots: Frontiers (WRF) data ecosystem.
Counts were measured on 2026-10-12 from local clones (`git ls-files`, `wc -l`,
`git rev-list --count HEAD`).

| Repository | Role | Language | Source lines | Test files | Commits | First commit |
|---|---|---|---|---|---|---|
| WRFrontiers-Exporter | Steam download, mapper, BatchExport driver | Python | 3,104 | 21 | 34 | 2025-10-05 |
| WRFrontiersDB-Parser | exported JSON to parsed JSON + textures | Python | 9,679 | 28 | 181 | 2025-06-12 |
| WRFrontiersDB-Orchestrator | pipeline driver, update probe, discount run, reports | Python | 3,425 | 6 | 40 | 2026-08-22 |
| WRFrontiersDB-Data | published data + `tools/wrfdb_data` index builder | Python + data | 1,563 | 8 | 57 | 2026-04-22 |
| WRFrontiersDB-Discord-Bot | `[[name]]` lookups, build-code replies | Python | 1,743 | 10 | 14 | 2026-10-01 |
| WRFrontiers-Discount-Visualizer | discount mapping backend + Astro frontend | Python + JS | 3,323 + 10,269 | 4 | 195 | 2026-05-26 |
| WRFrontiers-News-Scraper | news archive, discount detection | Python | 719 | 0 | 11 | 2026-08-08 |
| WRFrontiersDB-Site | the database website | Astro + TypeScript | 30,479 | 55 | 161 | 2025-12-28 |
| WRFrontiersDB-Design | shared CSS tokens, fonts, style guide | CSS | n/a | 0 | n/a | n/a |
| CUE4P-BatchExport | asset exporter built on CUE4Parse | C# | not counted | n/a | n/a | n/a |
| WRFrontiersDB-API | an abandoned 2025-06 sample API (see 1.3) | Python | not counted | n/a | 7 | 2025-06-13 |

All are public on GitHub under the maintainer's account. None of the WRF repositories
carries a licence file. `WRFrontiersDB-Data` has a `NOTICE` crediting the game's
publisher for the extracted assets; `WRFrontiersDB-Design` ships its font licence
(`OFL.txt`).

### 1.1 How the repositories depend on each other (read)

- The Orchestrator runs each stage by calling the sibling repository's
  `.venv/bin/python src/run.py`. Every Python repository has its own virtual
  environment and its own `requirements.txt`.
- The Site and the Discount Visualizer (DV) each vendor `WRFrontiersDB-Design` as a
  git submodule and read game data through a `WRFrontiersDB-Data` checkout placed (or
  symlinked) in their `public/` folder. The whole data checkout is therefore published
  as static files with each site.
- The bot reads a local clone of `WRFrontiersDB-Data` (`DATA_DIR`) and keeps a
  hand-copied table of the Site's route names (`object_types.py`).
- The Exporter, Parser, Orchestrator and DV backend lay their code out as loose modules
  directly under `src/` (`config`, `options`, `utils`, `stages`, ...). The bot
  (`wrfdb_bot`) and the Data tools (`wrfdb_data`) are proper packages.
- The Exporter, Parser and Orchestrator take their settings through `optionsconfig`,
  the maintainer's own library (environment variables, command-line arguments, generated
  README sections).

### 1.2 Dependency pinning today (read)

`requirements.txt` files pin direct dependencies only, and not all of them
(`optionsconfig` is unpinned in the Parser). Packages pulled in indirectly are not
pinned anywhere. The same library is pinned to different versions in different
repositories (for example `python-dotenv` 1.1.1 in the Parser and 1.2.4 in the bot).
Declared Python floors differ (`>=3.8`, `>=3.9`, `>=3.11`); the DV README says 3.12; the
Parser's CI uses 3.11; both machines run 3.13.5.

Front-end versions also differ: the Site is on Astro 5 and uses Playwright for
screenshots; the DV frontend is on Astro 6 and uses Puppeteer.

### 1.3 The old API repository

`WRFrontiersDB-API` (created 2025-06-13, last pushed the same day, 7 commits) is a
sample Flask service with a committed `game_data.db` and a `render.yaml`. It is not part
of the pipeline and nothing in the other repositories refers to it. Whether its hosted
deployment still exists was not checked.

## 2. The pipeline today

### 2.1 Patch day (read: Orchestrator `README.md`, `PATCH_DAY.md`)

```
update probe (every 20 min, anonymous Steam check)
  -> wrf-orchestrator@<version>
       preflight -> EXPORT -> PARSE -> PUSH -> INDEX -> SITE -> SITE-DEPLOY
  -> run-report email
```

| Stage | Where the code lives | What it does |
|---|---|---|
| EXPORT | Exporter | DepotDownloader pulls the game; the mapper launches the game under Proton to dump a `.usmap`; BatchExport writes JSON |
| PARSE | Parser | exported JSON to parsed objects, localization, textures, models |
| PUSH | Parser | reclones the Data repo, replaces `current/`, commits and pushes |
| INDEX | Data `tools/wrfdb_data`, run by the Orchestrator | rebuilds `index/` (slug map, build-code registry, nicknames, aliases, abbreviations, robot release dates, patch manifests), commits and pushes |
| SITE | Site | `npm run sync:slugs` and `npm run build` locally |
| SITE-DEPLOY | Site CI | dispatches the Site's GitHub Actions workflow, which builds again and publishes GitHub Pages; the Orchestrator waits for it |

Failure policy today (read: `PATCH_DAY.md`, confirmed in the code): **only a crashing
stage stops the run.** A parse that completes is published even with thousands of
warnings, and even with `logger.error` lines. The Parser defines a custom log level,
`UNKNOWN_PROPERTY`, numbered 31, which sits between WARNING (30) and ERROR (40).

Counts from recent parse logs (measured 2026-10-12 on the server):

| Run | WARNING | ERROR | UNKNOWN_PROPERTY |
|---|---|---|---|
| 2026-09-29 patch | 1,500 | 0 | 0 |
| 2026-10-06 patch | 0 | 0 | 4 |
| 2026-10-10 re-run | 0 | 0 | 0 |

Patch day also has a human part: reading the report email, then the `patch-warnings`
skill (Parser repo) and the `republish` skill (Orchestrator repo) to teach the Parser
new game data and publish again.

### 2.2 Discount weeks (read)

A timer runs the Orchestrator's discount run four times a day. It drives the
News-Scraper (scrape the latest posts, detect a new weekly discount) and, on a new
week, dispatches the DV's `All` GitHub Actions workflow with the announced item names
and dates. That workflow maps names to ids (pinned name, then exact name, then the Jev
classifier), commits the mapped week to the DV repo's `archive/discounts/`, takes a
screenshot for the link preview, builds, and publishes GitHub Pages.

### 2.3 What the pipeline needs to run (read: `home-server/wrf-gpu`, Exporter)

The mapper step is the demanding one. It launches the game's Windows executable with
`umu-run` and a custom Proton build, inside `gamescope --backend headless`. On the
server that needs: the Mesa Vulkan driver for the laptop's integrated AMD GPU,
`gamescope` from Debian backports, 32-bit libraries, `umu-launcher` from its GitHub
release, a Wine prefix and the Proton build on the data volume (about 2 GB), the
running account in the `render` and `video` groups, and a persistent
`XDG_RUNTIME_DIR`.

DepotDownloader receives the Steam password as a command-line argument (`-password`),
together with `-remember-password`. Its remembered login is kept under the running
account's home directory, not in the data volume.

### 2.4 Schedule and cadence

- 22 game builds are recorded between 2025-03-20 and 2026-10-06 (Data
  `index/patch_manifests.json`): roughly 15 a year, with recent gaps of one to three
  weeks.
- Discount weeks are weekly. The DV archive holds 59 mapped weeks from 2025-05-23.

### 2.5 How long a patch-day run takes (measured 2026-10-12)

From the last-written times of the per-stage log files of the 2026-10-06 patch-day run
on the server. That run downloaded 742 MB of game update.

| Stage | Duration |
|---|---|
| EXPORT (download, mapper, BatchExport) | 8 min 10 s |
| PARSE and PUSH | 1 min 51 s |
| INDEX | 2 s |
| SITE (install, slug sync, build) | about 41 s |
| SITE-DEPLOY (dispatch and wait for the Site's CI) | about 3 min |
| **Whole run** | **about 14 min** |

The pipeline's systemd unit allows the export stage 60 minutes and its comments
mention "30+ minutes"; that is an allowance, not a measurement. One run is thin
evidence; a patch with a larger download would take longer.

## 3. The server

Facts confirmed on 2026-10-09 to 2026-10-12.

- An old laptop running Proxmox VE 9.2: 8-core Ryzen 7 4700U, 7.1 GiB RAM, one 476 GB
  NVMe, uplink over wifi. Guests sit on an internal bridge and reach the network
  through the host (NAT). No Linux containers exist yet.
- One guest today: the Valheim game-server VM, with a fixed 4 GiB of memory (a
  reduction to 3 GiB was decided and is being applied separately). Measured peak use
  with two players: about 2.0 GB; a six-player peak was not measured.
  *Update: the reduction was applied on 2026-10-11 as 3.5 GiB, not 3 GiB (ADR-0006).*
- All WRF workloads run directly on the host as systemd units, as the same account the
  AI agent uses: the pipeline, the update probe, the discount watch and the bot.
- Storage: host root 40 GB (about 19 GB free); a dedicated 68 GB ext4 volume for WRF
  data (25 GB used, 39 GB free); about 300 GB free in the thin pool for guests.
- A USB stick (227 GB, 91 GB free) receives host backups: an encrypted restic
  repository twice a day (host configuration, secret files, the todo store) and a
  daily Valheim VM dump (22.6 GB each, six kept). Nothing backs up WRF.
- SQLite 3.46.1 and Python 3.13.5 on both machines. `sqldiff` is installed on neither.
  Docker is installed on the workstation (29.8.2) and not on the server host.

### 3.1 Pipeline memory (measured 2026-10-09 from the systemd journal)

| Run | CPU time | Memory peak | Swap peak |
|---|---|---|---|
| 2026-09-29 (three runs) | 2 to 3 min | 2.6 to 2.8 GB | 0.04 to 0.58 GB |
| 2026-10-06 (full run) | 11 min 46 s | 4.2 GB | 1.7 GB |
| 2026-10-07 | about 2 min | 3.3 GB | 0.26 GB |

The memory figure is the control-group peak, which includes file cache. How much is
real process memory was not measured. Other units are small: bot about 65 MB, probe and
discount watch under 55 MB each.

*Update 2026-10-21:* the real requirement has now been measured
(`docs/research/2026-10-pipeline-memory.md`): about 2.8 GiB of anonymous memory at the
peak, from the Parser's model step, on every run; the rest of the pipeline stays under
1.4 GiB. Under a 2.5 GiB cap a forced full run finished with 0.9 GiB of swap. Two
corrections to the table: these runs predate the 2026-10-14 change that starts the
export in its own user scope, so from then on the journal's figure for the pipeline
unit leaves the export out (the 2026-10-20 run logged 3.1 GB plus 1.1 GB of swap
without it); and the swap figures include pages the kernel moved out under host-wide
pressure, not only the pipeline's own need.

### 3.2 Working data on the server (measured 2026-10-12)

| Path under the data volume | Size | Notes |
|---|---|---|
| `steam-download/` | 15 GB, 317 files | one static folder, patched in place; one 12 GB `.ucas` file |
| `exports/<date>/` | 5.9 GB | two dated copies kept |
| `parsed/<date>/` | 837 MB | two dated copies kept |
| `textures/<date>/` | 269 MB | two dated copies kept |
| `mapper/<date>/` | 7 MB | two dated copies kept |

Sizes are disk usage (`du`). The export folder holds 30,496 files whose contents add
up to 3.05 GB; the rest is file-system overhead on many small files.

On the 2026-10-06 patch day DepotDownloader downloaded 742 MB (959 MB uncompressed)
into the existing 15 GB folder.

### 3.3 How much an export changes between patches (measured 2026-10-12)

The two dated export folders on the server (2026-09-29 and 2026-10-06) were compared
file by file, by size and then by content hash:

| | Files | Size |
|---|---|---|
| Unchanged | 30,161 | |
| Changed | 57 | 23 MB |
| Added | 278 | 184 MB |
| Removed | 202 | |

So about 99% of exported files were byte-for-byte identical across the two patches,
and the new or changed content was about 208 MB. This is one pair of patches; the
parsed output and textures were not compared.

## 4. The published data

Measured 2026-10-10 to 2026-10-12 from the Data repository.

- 47 object types, 10,862 objects, 7.8 MB of JSON. The largest types by count are
  `ScrapReward` (6,142) and `UpgradeCost` (3,072); the ones with pages are far smaller
  (`Module` 259, `Pilot` 82, `VirtualBot` 43).
- **No id is shared between two types today.** Nothing guarantees that.
- References between objects are strings of the form `OBJID_<Type>::<id>`. A scan found
  28,188 of them. Before a Parser fix on 2026-10-10, 9,214 pointed at ids that did not
  exist (two currency ids hard-coded without their `.0` suffix).
- Localization: 12 languages (de, en, es, fr, ja, ko, pl, pt-BR, ru, tr, zh-Hans,
  zh-Hant), one JSON file each of 0.7 to 0.8 MB, organised as 86 namespaces of keys;
  about 96,000 strings in total. One key used by an object was missing from the game's
  English file (also fixed since).
- Textures: 613 PNG files, 140 MB, all with transparency. 195 are 256 px or smaller
  (1.5 MB), 357 are 257 to 512 px (59.5 MB), 61 are larger (79 MB). 43 of the large
  ones are 2048 px robot renders of 1.1 to 2.5 MB each.
- Models: 258 JSON files of mesh data, 405 MB, up to 9.7 MB each. One compressed
  3.5 times with gzip.
- `Analysis/`: nine derived files. Only `shoulder_profiles.json` is read by anything
  (the Site).
- `index/`: the slug map (645 entries), build-code registry, nicknames (102), aliases
  (138), abbreviations (13, curated in code), robot release dates (38 robots, 5 titans,
  plus hand-entered pending entries), patch manifests (22).
- The repository's git history is 346 MB.
- An object's shape mixes stable fields with raw game data. Example: `Ability` (177
  objects) has eight stable top-level fields and a `misc` dictionary with 131 distinct
  raw property names nested up to ten levels deep.

A trial load of the objects and all localization strings into SQLite with a full-text
index produced a 27 MB file (9 MB gzipped).

## 5. The sites and the bot

### 5.1 Site (read)

- Astro, fully static, served from GitHub Pages at the project's domain. About 700
  pages; the built output is 55 MB in 702 files without the data folder.
- Routes are plural snake_case folders (`/module_groups/`, `/pilot_talents/`); page
  slugs are kebab-case. Robots are routed by id. Three test pages are deployed. There is
  no sitemap, and `robots.txt` lists routes by hand.
- **The browser loads data at run time**, not only at build time: the chosen
  language's whole localization file on every page; five object tables (`Module`,
  `ModuleType`, `ModuleSocketType`, `VirtualBot`, `CharacterModule`), the build-code
  registry and model files for the robot builder and 3D viewer; and the slug map.
  These come from the data checkout published with the site.
  *Update 2026-10-20: a map viewer was added on 2026-10-15, after this snapshot. It
  loads the `Map` and `Powerup` object tables (27 KB and 6 KB) and per-map files from
  the Data repository's `current/Maps/`: 84 `.glb` 3D models (81 MB in all, a base
  model per map and game mode plus foliage) and 12 JSON pin files (0.1 MB). Measured
  from the published Data repository.*
- Every image is served as the original PNG. The robots list page draws 43 robot icons
  at 24 px and transfers about 74 MB; the module list transfers about 32 MB.

### 5.2 Discount Visualizer (read)

- Astro frontend plus a Python backend, served from GitHub Pages under the
  maintainer's `github.io` address. Pages: the latest week, a page per week, items,
  timeline, predictions, prediction history, methodology, upgrade costs, privacy policy
  and terms of service.
- The prediction builder re-runs a walk-forward backtest over the whole history each
  time and appends a row to an accuracy-history file.

### 5.3 Bot (read)

- A Discord bot run as a host systemd unit. It resolves `[[name]]` with its own rules
  (type priority, first names, part names, abbreviations, typo correction with
  RapidFuzz) over the data checkout, links to Site pages through the slug map, and
  decodes build codes with the codec from the data checkout.
- It refreshes by re-reading the data checkout and watches a deploy-state file so that
  it never links to a page the Site has not deployed yet.

## 6. Domain and DNS (measured 2026-10-12 with `dig`)

- The project's domain is registered at Namecheap and uses Namecheap's default
  nameservers.
- The apex has four `A` records pointing at GitHub Pages; `www` is an alias of the
  apex. There is no `AAAA` record.
- The domain has `MX` records for Namecheap's email-forwarding service and a matching
  SPF `TXT` record. Whether any forwarding address is actually in use is not known.
  *Update: checked 2026-10-19, none is defined (ADR-0019, G-0019-1).*

## 7. Secrets and access today (names and permissions only; no value was read)

- Secret files on the server are owned by root and readable only by root.
- The account the AI agent runs as is the server's only login account and can run any
  command as root without a password, so those permissions do not keep the agent out.
- The WRF services run as that same account with their secrets in environment
  variables, where any other process of the account can read them, and where every
  child process inherits them.
- The maintainer states that the Steam account and the report sender address are
  dedicated accounts, and that the credentials in the agent account's home directory
  are the agent's own.
