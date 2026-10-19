# ADR-0018: API rollout in waves

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-08 (an API over SQLite), 2026-10-10 (waves, `/v1/meta`) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0006 (hosting), ADR-0009 (data store), ADR-0010 (schema), ADR-0019 (Cloudflare tunnel) |

## Context

The maintainer wants an API server that the Site and the bot read from. Two reasons
were given, in this order: to learn server and API work properly, as career
development; and for the room it gives the project to grow beyond pages generated at
build time.

Neither consumer needs an API today. The Site is fully static and reads files at build
time. The bot reads files from a local folder. Putting an API in front of both during
the migration would add a network dependency, an availability dependency on a laptop
at home (ADR-0006), and a great deal of new surface, all at the moment when everything
else is also changing.

There is also a sample API repository from June 2025 that was never developed. It is
obsolete, has no remaining deployments, and is ignored here (ADR-0002, G-0002-3).

## Decision

1. **The long-term design is a FastAPI server over the read-only SQLite file**
   (ADR-0009).
2. **It arrives in waves, each its own later project:**
   - **Wave 1, this migration.** The Site's build reads the SQLite file directly. The
     bot also reads the SQLite file directly: its lookups move from JSON files to the
     `objects`, `search` and `localizations` tables, and the build-code codec becomes a
     shared package instead of being loaded from a data checkout. **The API ships as a
     placeholder with no consumers.**
   - **Wave 2, later.** The bot moves to the API, and the API gains what the bot needs.
   - **Wave 3, later and larger.** The Site moves to the API.
3. **The placeholder has one real endpoint, `/v1/meta`**, returning the code version,
   the data release id and the schema version. It has three jobs:
   - the deploy script's health check (ADR-0007);
   - proof that the tunnel from Cloudflare to the home server works (ADR-0019);
   - proof that a database swap was picked up.
4. **Deferred until wave 2 starts:**
   - the scope of version 1;
   - whether the API is public, and API keys and rate limiting;
   - how the API picks up a new database (restart or reload);
   - observability for it;
   - which Site features become dynamic;
   - whether the Site reaches it as `/api/*` on the same domain or at an `api.`
     subdomain.
5. **Once the API exists, the rule that the Site is fully static may no longer hold.**
   That was accepted. What still holds: the home machine is never needed to load a page
   or an icon (ADR-0006).
6. **If a Worker script is ever added to the Site for proxying, it runs only on
   `/api/*`**, so that static pages stay outside the free plan's daily limit on script
   invocations (ADR-0019).

## Alternatives considered

- **No API; consumers read the SQLite file for good.** This is what wave 1 is, and it
  works. Rejected as the end state by the maintainer for the two reasons in the
  Context.
- **Move both consumers to the API during the migration.** Rejected: it makes the
  migration larger and riskier, and makes the websites depend on home uptime from day
  one.
- **Skip the placeholder; add the API when wave 2 starts.** Rejected: the placeholder
  is cheap, and it proves the three hardest infrastructure pieces (container, tunnel,
  database pickup) while nothing depends on them.
- **GraphQL instead of REST.** Not discussed in depth. The data's shape (documents plus
  references) would suit it; the maintainer's learning goal named FastAPI.
- **An API over PostgreSQL.** Rejected in ADR-0009.

## Consequences

- After the migration, the API runs in production, reachable through the tunnel, and
  nothing breaks if it is down.
- The Site stays fully static and independent of the home server through wave 1.
- The bot's data access is rewritten twice: once to SQLite in wave 1, and again to
  HTTP in wave 2. This was accepted as the price of not doing everything at once.
- Design work on the API's real surface is put off, which means the database schema
  (ADR-0010) is being designed before its main future consumer exists. Build-and-swap
  makes later schema changes cheap, which is what makes this order tolerable.

## Gaps and open questions

### G-0018-1. A hostname is needed now

- **Kind:** decision
- **Needed by:** phase 3

The address question (`/api/*` or `api.`) is deferred to wave 2, but the placeholder
needs a public hostname in wave 1 for the tunnel to point at. Whatever is chosen
becomes hard to change once anything links to it.

**Proposed default:** `api.<domain>` for production and a matching staging name, with
the path-proxy question left open as planned.

### G-0018-2. Who can reach the placeholder

- **Kind:** decision
- **Needed by:** phase 3

"Public or private" is deferred, yet the placeholder will be on the internet in wave 1.
`/v1/meta` reveals only version strings, so leaving it open is low risk. But FastAPI
also serves interactive documentation and its schema by default, and anything added
for testing would be public too. A stated rule for wave 1 (for example: only
`/v1/meta` is routed; documentation pages are switched off or kept behind a login)
avoids deciding by accident.

### G-0018-3. Picking up a new database

- **Kind:** design
- **Needed by:** phase 3

Deferred for the API, but `/v1/meta`'s third job is to prove a swap was picked up, and
the bot needs the same mechanism in wave 1. So this cannot wait for wave 2. See
ADR-0009, G-0009-4.

### G-0018-4. What triggers waves 2 and 3

- **Kind:** decision
- **Needed by:** not scheduled

The waves have no start condition. Wave 3 in particular makes the Site depend on a
laptop at home unless the API has moved to a rented server first (ADR-0006, G-0006-9)
or Cloudflare caches its responses well enough to cover outages. The order of "move
the API off the laptop" and "make the Site depend on the API" should be decided before
wave 3 is designed.

### G-0018-5. The bot's query rules as an API

- **Kind:** design
- **Needed by:** wave 2

The bot's matching rules are intricate (ADR-0010, G-0010-4). In wave 2 either the API
implements them (one search endpoint that does everything the bot does today) or the
bot fetches candidates and applies the rules itself. The first makes the API's most
complex endpoint its first real one.

### G-0018-6. Versioning the API

- **Kind:** design
- **Needed by:** wave 2

The path says `/v1`. What counts as a breaking change, how long an old version is
kept, and how the API version relates to the schema version (ADR-0005, G-0005-6) are
undefined.

## References

- FastAPI: https://fastapi.tiangolo.com/
- ADR-0009, G-0009-4, for the database pickup mechanism.
