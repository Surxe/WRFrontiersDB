# ADR-0021: URL structure of the merged site

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0002 (merge of Site and DV), ADR-0013 (slugs), ADR-0014 (swap gate), ADR-0019 (Cloudflare), ADR-0020 (assets) |

## Context

Two sites are becoming one (ADR-0002), and both have addresses that people and the
bot have already linked to (baseline, sections 5.1 and 5.2).

**The Site**, at the project's domain:

- one folder per object type, plural and snake_case (`/module_groups/`,
  `/pilot_talents/`), with a list page and a page per object ending in a kebab-case
  slug;
- robots routed by id, not slug;
- three view pages (`/pilots/talent-overview` and two siblings) sharing the
  `/pilots/` folder with pilot slugs;
- three `test_*` pages deployed to production;
- machine-readable files loose at the root: `slug_map.json`, `langs.json`,
  `build_codes.json`, `meta_descriptions.json`, `deploy.json`, `build-code.js`,
  `locales/`;
- links written without a trailing slash, while the bot's links have one;
- language chosen in the browser, not in the address.

**The Discount Visualizer**, at an address on GitHub's domain:

- `/` (the latest week), `/week/<date>`, `/items?group=...`, `/timeline`;
- `/predictions`, `/history` (prediction history), `/methodology` (how predictions are
  calculated), `/predictions-og` (a page that exists only to be screenshotted);
- three pages that are not about discounts: `/costs` (upgrade costs, which is general
  game data), `/privacy-policy` and `/terms-of-service`.

The two sites do not link to each other. The merged site would otherwise mix two
naming styles, snake_case folders with kebab-case slugs and pages.

## Decision

1. **All discount pages live under `/discounts/`.**
   - `/discounts/` renders the latest week as a full page, not a redirect, so "current
     discounts" is one fixed link.
   - Each week has a permanent address `/discounts/<YYYY-MM-DD>/`. There is no `week/`
     segment: a date cannot collide with a named page.
   - `/discounts/items/`, `/discounts/timeline/`, `/discounts/predictions/`,
     `/discounts/predictions/history/`, `/discounts/predictions/methodology/`.
2. **Pages that are not about discounts go to the top level:**
   - `/costs` becomes `/upgrade-costs/`;
   - `/privacy-policy/` and `/terms-of-service/` sit at the root and cover the Site,
     the discount pages and the bot;
   - there is one 404 page for the whole site.
3. **Route folders switch to kebab-case** (`/module-groups/`, `/pilot-talents/`). Each
   old snake_case folder gets a permanent pattern redirect
   (`/module_groups/* /module-groups/:splat 301`), about twelve rules, so old links
   keep working.
4. **The table from object type to route lives once**, in the shared models package.
   The Site, the bot and the redirect generator all read it. The bot's hand-copied
   table goes.
5. **Robots stay routed by id** (`/robots/<id>/`). Every other type with pages uses
   slugs with history (ADR-0013).
6. **A slug may not equal a fixed page name under the same folder.** This is a blocking
   check in the swap gate (ADR-0014).
7. **Every address ends in a slash.** Astro is set to `trailingSlash: 'always'` and the
   host to its matching setting; canonical links and `og:url` use the slash form.
8. **Data files that pages load go under `/data/`**: the DV's files in
   `/data/discounts/`; the Site's loose root files, `build-code.js` and `locales/` under
   `/data/`. One cache rule then covers them (ADR-0019). Only well-known files stay at
   the root: `robots.txt`, the favicon, a sitemap. The bot's fetch of `deploy.json` is
   updated in the same migration. Most of these files go away once pages read from the
   API (ADR-0018).
9. **Test and internal pages stay off production.** `test_*` pages are built for
   staging only. The screenshot source page moves under `/discounts/` with the rest and
   stays deployed, marked `noindex` and left out of the sitemap.
10. **Language stays a browser-side setting, not part of the address.** No `/de/...`.
11. **The old DV address redirects by this table** (paths relative to the old site):

    | Old path | New address |
    |---|---|
    | `/` | `/discounts/` |
    | `/week/<date>` | `/discounts/<date>/` |
    | `/items?group=x` | `/discounts/items/?group=x` (query kept) |
    | `/timeline` | `/discounts/timeline/` |
    | `/predictions`, `/history`, `/methodology` | `/discounts/predictions/`, `.../history/`, `.../methodology/` |
    | `/costs` | `/upgrade-costs/` |
    | `/privacy-policy`, `/terms-of-service` | the same paths at the root |
    | anything else | `/discounts/` |

## Alternatives considered

- **Keep snake_case folders.** No redirects needed. Rejected: the merged site would mix
  two styles permanently, hyphens are the web convention, and the migration is the
  cheapest moment to change, with everything else changing too. The cost is about
  twelve redirect rules kept forever.
- **A subdomain for discounts** (`discounts.<domain>`). Rejected: it would stay a
  second site in everything but repository.
- **`/discounts/week/<date>/`**, keeping the DV's segment. Rejected as redundant.
- **`/discounts/` redirecting to the latest week's address.** Rejected: the "current
  discounts" link would then change address every week, and link previews would cache
  the wrong page.
- **Slugs for robots.** Proposed for consistency, since an id is not guaranteed to stay
  name-like. Declined by the maintainer: robot ids are derived from the English name by
  the Parser, and the risk is accepted.
- **Moving the three view pages out of `/pilots/`** to avoid sharing a folder with
  slugs. Rejected in favour of the general collision check (decision 6).
- **A language segment in the address.** It would let search engines index translated
  text. Rejected: twelve times the pages and redirects, for an audience that does not
  arrive by searching in other languages.
- **No trailing slash.** Either form works; one had to be picked. The slash form
  matches how the host serves folder index pages and what the bot already emits.

## Consequences

- One consistent address style across the merged site.
- Every existing Site link changes folder name and is caught by a pattern redirect;
  every existing DV link is caught by the stub on the old address (ADR-0019).
- The route table has one owner. Adding or renaming a route is one edit that the Site,
  the bot and the redirects all follow.
- `/data/` becomes a public interface in practice, since anything can fetch from it.
- Non-English text is not indexed by search engines. Accepted.
- Robots have a weaker link guarantee than everything else (ADR-0013).

## Gaps and open questions

### G-0021-1. Redirects, real pages and trailing slashes on the host

- **Kind:** verification
- **Needed by:** phase 4 (on staging)

Two properties of the host bear on decisions 3 and 7
(`docs/research/external-facts.md`): a redirect rule is followed even when a real page
exists at that address; and the documentation does not say whether a redirect keeps
the visitor's query string. To confirm on staging, with real old links in both slash
forms: that `/module_groups/x` and `/module_groups/x/` both arrive at
`/module-groups/x/` in one hop; that the trailing-slash setting does not add a second
hop; and that no pattern rule can ever match a new address.

### G-0021-2. Which address is canonical for the latest week

- **Kind:** decision
- **Needed by:** phase 4

`/discounts/` and `/discounts/<latest date>/` show the same content. Search engines
should be told which is the original. Pointing the canonical link at the dated address
keeps each week's page distinct in search results; pointing it at `/discounts/` favours
the "current" link.

### G-0021-3. Outside users of files that are moving

- **Kind:** verification
- **Needed by:** phase 4

Decision 8 moves files that have had public addresses. The bot is updated in step. Any
other consumer (the codec file is advertised for other sites to use, ADR-0003,
G-0003-6) would break. Plain redirects from the old root addresses cost nothing and
should probably be added regardless.

### G-0021-4. What generates the files under `/data/`

- **Kind:** design
- **Needed by:** phase 4

These files came from the Data checkout or from the Site's build. In the new design
each must be generated from the database at build time. The list, and the shape of
each file, is not written down. Same question as ADR-0009, G-0009-6.

**Resolved 2026-10-20:** Settled with ADR-0009, G-0009-6: the Site build generates
them from the database in today's shapes, under `/data/`. The list itself is ADR-0009,
G-0009-9.

### G-0021-5. Legal pages and the Discord application

- **Kind:** action
- **Needed by:** phase 5 (cutover)

The privacy policy and terms pages exist only on the DV today. Moving them to the root
changes their address and their scope (they will now speak for the Site and the bot as
well). Their text needs reviewing for that, and if the Discord developer portal links
to the old copies, those links must be updated at cutover.

### G-0021-6. How staging-only pages are kept out of production

- **Kind:** design
- **Needed by:** phase 4

Decision 9 needs a mechanism: a build-time flag that excludes `test_*` routes, set by
the environment. Since staging and production are meant to be the same build
(ADR-0008), this is a deliberate, small difference between them and should be the only
one.

### G-0021-7. Sitemap and robots file

- **Kind:** action
- **Needed by:** phase 4

There is no sitemap today, and `robots.txt` is hand-written against the old folder
names. Both should be generated from the route table so they cannot go stale again.

### G-0021-8. `/shoulder_profiles` and other existing redirects

- **Kind:** verification
- **Needed by:** phase 4

The Site already has one redirect in its Astro configuration
(`/shoulder_profiles` to `/module_groups/shoulder`), whose target is itself renamed by
decision 3. Existing redirects need collecting into the generated file with their
targets updated, so that none becomes a two-hop chain.

## References

- `docs/research/2026-10-baseline.md`, sections 5.1 and 5.2.
- `docs/research/external-facts.md`, "Cloudflare Workers static assets".
