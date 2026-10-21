# Site and API consistency across a database swap (wave 3)

| | |
|---|---|
| Recorded | 2026-10-20 |
| State | Idea; wave 3 is a later project (ADR-0018) |
| Related | ADR-0009 (G-0009-4, the swap), ADR-0014 (promotion), ADR-0018 (waves, G-0018-4, G-0018-7), ADR-0019 (Cloudflare) |

## The problem

Today, and through wave 1, the deployed Site is static files with no database behind
it; it picks up a new release only by being rebuilt and redeployed. In wave 3 the Site
starts calling the API from the browser. A data release then switches two things
separately, each atomically on its own:

- the Site, by a Cloudflare deploy;
- the API, when the pipeline repoints `current` and calls its internal reload
  endpoint (G-0009-4).

Between the two, and in browser tabs opened before the swap, pages built from one
release call an API serving another.

## The approach so far

1. **How much goes through the API is open** (ADR-0018, G-0018-7). Whatever is
   rendered into pages or shipped as build-time files under `/data/` switches with the
   deploy and cannot disagree with the pages; only what the API serves can. The split
   is a separate discussion.
2. **One ordered promotion:** deploy the Site, wait until it is live, then repoint
   `current` and call the API's reload endpoint (G-0009-4). API results link to pages,
   so pages exist before the API can link to them. In the gap the API still answers
   from the previous release; at worst a result links to a page the patch removed.
   Accepted as harmless: it lasts about a second, and nothing persists.
3. **The cache follows the swap.** If Cloudflare caches API responses, promotion purges
   that cache right after repointing `current`.

Tabs left open across a swap keep calling the new API from an old page. The effect is
the same as the gap (an occasional stale link or missing result) and ends when the
page is reloaded. No detection is planned.

## Rejected

- **Serving a specific release per request** (the page sends the release it was built
  from, and the API keeps several releases open). Rejected 2026-10-20 by the
  maintainer: too much machinery for a brief, harmless mismatch.
- **Detecting a mismatch on every response** (the API returns its release in a header,
  the page compares it with its own and prompts a reload). Judged unnecessary
  2026-10-20: the mismatch it would catch is the harmless one above.

## Questions to answer first

- The split in G-0018-7.
- Whether the API has moved off the home laptop before the Site depends on it
  (ADR-0018, G-0018-4), and whether Cloudflare's cache covers outages.
- How the purge is done (whole host or a path prefix) and with which credentials
  (ADR-0022).
