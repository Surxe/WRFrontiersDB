# ADR-0009: Data store: a SQLite file, rebuilt and swapped

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-08 (database instead of the Data repository, SQLite, build and swap, no public dataset) |
| Record state | Reviewed |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0010 (schema), ADR-0012 (state), ADR-0014 (swap gate), ADR-0015 (archive), ADR-0018 (API), ADR-0020 (assets) |

## Context

Today the pipeline's product is a git repository, `WRFrontiersDB-Data`: one JSON file
per object type, a JSON file per language, 613 textures, 258 model files, and an
`index/` folder of derived lookups (baseline, section 4). The Parser publishes by
recloning that repository, replacing a folder and pushing. Every consumer reads the
files directly:

- the Site and DV place a checkout in their `public/` folder, so the whole repository
  is also published as static files with each site;
- the bot reads a local clone;
- the browser fetches some of the JSON files at run time.

Problems with a git repository as the data store:

1. **Size.** Its history is 346 MB after six months and grows with every patch, because
   each patch rewrites large files. Each pipeline run reclones it. GitHub Pages, which
   publishes the checkout with each site, has a size limit the project was approaching.
2. **No queries.** "Which objects refer to this one" or "find a name in any language"
   means every consumer loading whole files and building its own lookups. The Site, the
   bot and the DV each do this separately, in two languages.
3. **The file layout is the contract.** Nothing describes the shape of an object except
   the files themselves, so every consumer is coupled to the Parser's output format.
4. **Publishing is not atomic.** `PUSH` and `INDEX` are two commits; the Site deploys
   later. Consumers can see data and index out of step, which is why the bot has to
   watch a deploy-state file before linking to a page.
5. **Derived state and accumulated state are mixed** in `index/`: some files are
   rebuilt from scratch each run, others (the build-code registry, robot release dates)
   must never lose history.

The maintainer also wants an API server for the Site and bot to use, partly to learn
server and API work properly and partly for the room it gives the project to grow.

## Decision

1. **The Data repository is retired as the published artifact.** The pipeline's output
   goes into a database.
2. **The database is a single SQLite file.**
3. **The Parser keeps writing JSON.** A separate stage (`db-build`) converts the parsed
   JSON into the SQLite file. The JSON remains on disk as an intermediate.
4. **The database is deployed by build-and-swap.** Each data release builds a complete
   new file, `wrfdb-<release>.sqlite`, from scratch, with the schema defined by the
   code at that release. It is validated (ADR-0014) and then swapped in atomically.
   **There are no migrations, ever.**
5. **The file is read-only in service.** Services mount it read-only. A FastAPI server
   over it is the long-term way for consumers to read the data (ADR-0018). In the first
   wave, the Site build and the bot read the file directly.
6. **The file records the schema version it was built with**, and a service checks it
   on opening.
7. **History between patches comes from keeping one database per game patch** and
   comparing them (ADR-0015), using SQLite's `sqldiff`.
8. **No public dataset.** The database is not offered for download.
9. **Anything that must survive a rebuild lives outside the database**, in `state/` in
   this repository (ADR-0012). The database is never the only home of anything.

## Alternatives considered

- **Keep the Data repository and fix its problems** (shallow clones, large-file
  storage, pruning history). Rejected: it addresses size only. Querying, the contract
  and atomic publishing stay as they are.
- **SQLite as a downloadable artifact, with no API**: consumers fetch the file and
  query it themselves. This is in fact what the first wave does (ADR-0018). Rejected as
  the end state because the maintainer wants the API, and because a browser cannot
  reasonably download and query the file for dynamic features.
- **An API over PostgreSQL.** The conventional choice for an API server. Rejected for
  this workload:
  - The data is derived, small (about 30 MB) and replaced wholesale on every release.
    Nothing writes to it between releases. A database server's strengths (concurrent
    writers, transactions, online schema change) go unused.
  - A file can be built off to one side, checked, archived, compared with the previous
    one, copied to another machine and swapped in with one rename. With a server each
    of those needs a procedure.
  - It is one more always-on process on a machine with about 2.5 GiB for everything
    (ADR-0006).
  - Wholesale replacement in PostgreSQL means either migrations or dump-and-restore on
    every release.
- **A document or search service** (MongoDB, Elasticsearch, Meilisearch). Rejected for
  the same resource reason, and because SQLite covers documents, relations and text
  search in one file at this scale (ADR-0010).
- **Migrations instead of rebuilding.** Rejected: there is no state in the database
  worth migrating. Rebuilding makes a schema mistake cost one release instead of a
  migration that must be kept forever.

## Consequences

- A release of data is one file with one id. "What data is live" has an exact answer,
  and going back is swapping the previous file in.
- Schema changes ship with the code that needs them, with no migration to write. The
  price is that a code release which changes the schema must rebuild the database as
  part of its deployment (ADR-0005, G-0005-3).
- Consumers get queries, and one description of the data's shape (ADR-0010), instead
  of files and conventions.
- The pipeline no longer commits data to git on each run. What it still commits is
  small accumulated state (ADR-0012).
- Nobody outside can browse the data on GitHub any more. The archived Data repository
  remains public, frozen at the last pre-migration patch.
- A new stage exists that can fail: converting JSON to SQLite. It is also where
  validation happens, which is the point.
- Per-patch history starts at the first patch after migration. Older history stays in
  the archived repository's git log, in the old shape (ADR-0015).

## Gaps and open questions

### G-0009-1. Which SQLite versions must be supported

- **Kind:** decision
- **Needed by:** phase 2

The schema uses SQLite's binary JSON format (ADR-0010), which needs version 3.45 or
newer. Both machines have 3.46.1, but the version that matters is the one inside each
container image and each tool that touches the file:

- Python uses the SQLite the image's operating system provides. The default official
  Python images are Debian 13 and carry 3.46.1, with JSONB working (measured
  2026-10-20); only the explicit `-bookworm` (Debian 12) tags carry 3.40.1, which is
  too old (`docs/research/external-facts.md`);
- the Site build reads the file from Node, through either Node's built-in module or a
  package that bundles its own SQLite;
- `sqldiff` and the `sqlite3` shell come from operating-system packages.

A minimum version should be stated, checked at start-up by every reader, and tested in
CI.

**Proposed default:** minimum SQLite 3.45. Python images name the Debian release
explicitly (`python:3.13-slim-trixie`, not the floating `slim` tag). Every program that
opens the file checks that `jsonb()` works at start-up and refuses to run otherwise,
and CI runs that check inside each built image.

**Resolved 2026-10-20:** The proposed default is accepted, adjusted for G-0009-2
(documents stored as JSON text, so binary JSON is not used). The minimum is SQLite
**3.38**, the first version with the JSON functions built in by default and the `->` /
`->>` operators. The start-up check runs a `->>` query instead of `jsonb()`. Python
images still name the Debian release (`-trixie`), and CI still runs the check inside
each built image. Even Debian 12's 3.40.1 would meet this minimum.

### G-0009-2. Binary JSON or text JSON for stored documents

- **Kind:** decision
- **Needed by:** phase 2

ADR-0010 stores each object as binary JSON. That format is internal to SQLite:
applications must read it through SQLite's functions, and tools that print raw values
show it as an opaque blob. The gain is faster field extraction and a slightly smaller
file. For a 30 MB read-only database queried mostly by id, the gain is probably
unmeasurable, while the costs are concrete: the version floor in G-0009-1, and
comparison output (decision 7) that shows changed documents as unreadable binary.
Storing documents as JSON text avoids both and still allows the same queries. This
should be decided with a quick measurement rather than assumed.

**Resolved 2026-10-20:** Documents are stored as JSON text, without a measurement.
SQLite's JSON functions and the `->` / `->>` operators read text JSON directly, so
the same queries work, the file stays readable in any tool, and `sqldiff` output
shows changed documents as text. Nothing in the schema now needs the binary format,
which changes the reason for the version floor in G-0009-1.

### G-0009-3. What `sqldiff` can and cannot show

- **Kind:** verification
- **Needed by:** phase 2

Decision 7 relies on `sqldiff` for "what changed between patches". It reports rows
added, removed and changed. For a table whose rows are whole documents, a changed row
is reported as the entire new document, not the fields that changed. That is enough to
list which objects changed, but not to say how. A readable per-field comparison (the
kind a patch-notes page would need) requires a small JSON-aware tool on top. `sqldiff`
is also not installed on either machine today.

**Resolved 2026-10-20:** For the migration, `sqldiff` is used only to identify which
objects changed. Field-level comparison is out of scope and recorded as a future idea
([`../future-ideas/field-level-patch-diff.md`](../future-ideas/field-level-patch-diff.md)).

### G-0009-4. How the swap works, and how readers notice

- **Kind:** design
- **Needed by:** phase 3

"Atomically swaps it in" needs a mechanism. The usual one is a symbolic link named
`current` that is repointed to the new file with a rename. Details that decide whether
it actually works:

- a process that already has the old file open keeps reading the old file until it
  reopens, so each service needs a way to notice: a restart, a periodic check of the
  link, or a signal;
- a container must mount the directory that contains the link, not the file, or it
  will never see the change;
- the file should be opened read-only and in a mode that creates no side files next to
  it.

The API's side of this was explicitly deferred (ADR-0018). The bot needs the same
answer in the first wave.

**Proposed default:**

- Promoted files live in a releases directory that DVC does not manage (a DVC re-run
  deletes its outputs, ADR-0016, G-0016-8). `current` is a **relative** symbolic link
  in that directory, repointed by creating a new link and renaming it over the old one.
- Services mount the directory read-only, never the file.
- The database is built in the default rollback-journal mode, not WAL, and readers open
  it as `file:.../current?mode=ro&immutable=1`: read-only, no locking, no side files.
- **The pipeline tells the services.** The API and the bot each expose an internal
  reload endpoint (for example `POST /internal/reload`) on the Compose network only,
  never routed through the Cloudflare tunnel. On a call, the service opens the file
  `current` now points at, switches to it, and closes the old one once requests in
  flight have finished. The bot gains a minimal HTTP listener for this.
- Each service reports the release it has open (the API through `/v1/meta`, the bot
  through an equivalent internal endpoint).
- **Promotion is one ordered step**, run by the pipeline: deploy the Site and wait until
  it is live; repoint `current`; call each service's reload endpoint in the same
  environment (staging and production are separate Compose projects); confirm each
  reports the new release; then, once the API's responses are cached, purge that
  cache. A failed reload or confirmation is reported in the run report (ADR-0024).
- A service always opens `current` when it starts, so a restart is the fallback for a
  missed reload. No polling.
- The Site's own pickup is its redeploy; it holds no database open in service.

Between the Site going live and the reload calls, API answers come from the previous
release: at worst a result links to a page the patch removed, for about a second.
Nothing breaks and nothing persists; this was accepted. How the Site and the API stay
consistent once the Site uses the API (wave 3) is a future idea
([`../future-ideas/site-api-swap-consistency.md`](../future-ideas/site-api-swap-consistency.md)).

Alternatives considered for how services notice the swap:

- **Periodic check of `current`** (the bot polls every 10 minutes today). Rejected: the
  services lag the Site by up to the interval.
- **Resolving `current` on every request**, the way a static host serves files.
  Instant and simple, but adds a lookup to every request. Not chosen.
- **Watching the directory** (inotify). Instant, no coupling, but the pipeline cannot
  confirm the pickup as part of promotion. Not chosen.
- **Signalling through Docker** (`docker kill -s HUP`, `docker compose exec`). Rejected:
  it needs the Docker socket, which is root on the guest, inside a pipeline that runs
  third-party code (Proton, the game, DepotDownloader, CUE4Parse).

**Resolved 2026-10-20:** The proposed default is accepted, with the internal reload
endpoint called by the pipeline.

### G-0009-5. The swap is not atomic across consumers

- **Kind:** design
- **Needed by:** phase 3

There are three consumers: the API and the bot (which read the file on the server) and
the Site (which is built from the file and then deployed to Cloudflare, minutes later).
A rename is atomic for the first two; nothing makes the Site change at the same
instant. During that window the bot could link to a page that is not deployed yet,
which is the exact problem the old deploy-state file solved. ADR-0014 puts the Site
build before the swap to shorten the window, but the order of "flip the pointer" and
"Site deployment finished", and what happens when the deployment fails after the flip,
is not defined. See G-0014-2.

**Resolved 2026-10-20:** The order is set by G-0009-4: the Site version is deployed and
live before `current` is repointed, so the bot never links to an undeployed page. If
the Site deployment fails, `current` and the services are untouched. Failure and retry
of the whole promotion are settled in ADR-0014, G-0014-2.

### G-0009-6. Data the browser fetches at run time

- **Kind:** design
- **Needed by:** phase 4

"The Site build reads the SQLite file" covers pages generated at build time. But the
browser also fetches data while a page is open (baseline, section 5.1): the selected
language's full localization file on every page, five object tables for the robot
builder, the build-code registry, model files and the slug map. These come from the
Data checkout today. In the new design they must be produced by the Site build from the
database and written under `/data/` (ADR-0021), or served from object storage. Which
files, in what shape, generated by which step, is not listed anywhere. It is also where
most of the data becomes public again (see G-0009-7).

**Resolved 2026-10-20:**

1. **Shape:** the run-time files keep today's shapes, regenerated from the database. No
   trimming or redesign before cutover (ADR-0025, decision 4).
2. **Step:** the Site build generates them, so they ship in the same Worker version as
   the pages and switch with them atomically on promotion (ADR-0014, G-0014-2).
3. **Location:** under `/data/`, at the paths ADR-0021 sets.
4. **Images and models are not among them.** They are served from object storage
   (ADR-0020); only their addresses reach the browser (ADR-0020, G-0020-3, still open).
5. **Localization:** the browser keeps receiving the whole file for the chosen
   language, as today. Better options are post-cutover work (ADR-0010, G-0010-7).

The list of files itself is G-0009-9.

### G-0009-7. What "no public dataset" means

- **Kind:** decision
- **Needed by:** phase 4

The database file will not be downloadable. But the Site will still serve complete
localization files and several complete object tables to every browser (G-0009-6), and
all textures and models are in a public bucket (ADR-0020). So the data remains
obtainable; what goes away is a supported, documented, versioned download. If the
intent is stronger than that (for example, to make bulk copying harder), the run-time
files need rethinking. If the intent is only "we do not publish and support a dataset",
the decision should say so.

**Resolved 2026-10-20:** The intent is only that the project does not publish or
support a dataset: no documented, versioned download of the database. No effort is
spent on obscuring the run-time files or making bulk copying harder.

### G-0009-8. How long the intermediate JSON is kept

- **Kind:** decision
- **Needed by:** phase 2

Decision 3 keeps the parsed JSON on disk. Under ADR-0016 it lives in the stage cache,
subject to that cache's clean-up rule. Whether the JSON for old patches is worth
keeping (for example to rebuild an old database with a newer schema) is undecided.

**Resolved 2026-10-20:** Nothing extra is kept. The parsed JSON is retained only as
long as the stage cache's clean-up rule keeps it (ADR-0016, decision 8); the archived
databases (ADR-0015) are the record of each patch.

### G-0009-9. The list of run-time data files

- **Kind:** action
- **Needed by:** phase 4

G-0009-6 settles how the browser's run-time files are produced, but the list itself
is not written down anywhere. It should become a contract, in `docs/schema.md` or the
Site's documentation: each file, its path under `/data/`, its shape, and the feature
that loads it. A first inventory, read from the Site's code on 2026-10-20 (sizes from
an older local build):

| Feature | Fetches | Size |
|---|---|---|
| every page | the chosen language's localization file | about 0.7 MB per language |
| robot builder | object tables `Module`, `ModuleType`, `ModuleSocketType`, `VirtualBot`, `CharacterModule` | 2.9 MB, 0.8 MB and small |
| robot builder | the build-code registry (`/build_codes.json`) | small |
| 3D model viewer | `Models/<id>.json` (object storage, ADR-0020) | 405 MB in 258 files |
| map viewer | object tables `Map` and `Powerup` | 27 KB and 6 KB |
| map viewer | per-map pin files (`Maps/*.json`) | 0.1 MB in 12 files |
| map viewer | per-map base and foliage 3D models (`Maps/*.glb`; object storage, ADR-0020) | 81 MB in 84 files |
| object links | `/slug_map.json` | small |
| images | textures (object storage, ADR-0020) | 140 MB of PNG |

The map viewer was added on 2026-10-15, after the baseline was taken (see the update
note in its section 5.1); map sizes are from the published Data repository on
2026-10-20. The inventory should be checked against the Site's code once more when
the Site moves in.

## References

- `docs/research/2026-10-baseline.md`, section 4.
- SQLite as an application file format: https://sqlite.org/appfileformat.html
- `sqldiff`: https://sqlite.org/sqldiff.html
