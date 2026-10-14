# ADR-0013: Slugs and link stability

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0012 (state), ADR-0014 (swap gate), ADR-0019 (Cloudflare), ADR-0021 (URL structure) |

## Context

A page's address ends in a slug made from the object's English name: `kate-sinclair`,
`advanced-bulwark-quantum`. The current rules are in the Data repository's
`slug_map.py`: a pilot's slug is first name plus last name, a module's is its group
name plus its own name, and everything else uses its name. The slug map has 645
entries.

Slugs are rebuilt from scratch on every run. If the game renames something, the old
address stops existing and nothing remembers it.

Why that matters more here than on most sites:

- **The bot posts links into Discord, and those messages are permanent.** A broken
  link in a year-old message cannot be fixed.
- **A module's slug contains its group's name.** Renaming one group breaks the address
  of every module in it at once.
- **The migration itself changes addresses**: route folders become kebab-case
  (ADR-0021), and slug rules may be touched while the code moves.

How often names actually change was checked on 2026-10-10: across the Data
repository's history (2 to 13 commits per type), no object's English name changed
while its id stayed the same. So renames are rare. That history only covers six
months.

The maintainer's first position was that slugs should be stable, fixed for good once
assigned, and asked to be convinced otherwise.

## Decision

1. **Slugs keep following names**, with the current rules.
2. **Slug history is recorded automatically** in `state/slugs.json` (ADR-0012): for
   each object, its current slug and every slug it used to have. On each database
   build, if an object's slug differs from the recorded one, the old slug moves into
   its history.
3. **The Site build generates permanent redirects (301) from the history**, as a
   `_redirects` file for Cloudflare (ADR-0019).
4. **A current slug beats an old redirect.** If a name is freed by one object and later
   used by another, the address belongs to the object that has it now.
5. **Robots are the exception: they are routed by id** (`/robots/<id>/`), with no slug
   and no history. A robot's id is derived from its English name by the Parser, so it
   already reads like a slug. The risk of an id changing is accepted. (The maintainer
   declined a proposal to give robots slugs.)
6. **Slug problems block a data release** (ADR-0014): two objects of one type with the
   same slug; an inconsistent history; and a slug equal to the name of a fixed page
   under the same route (for example a pilot who would be called `talent-overview`,
   which is an existing page under `/pilots/`).

## Alternatives considered

- **Permanent slugs**: assign once, never change, even if the name changes. This was
  the maintainer's starting point. It gives perfectly stable links with no redirect
  machinery. Rejected after discussion: the address would then show a name the game no
  longer uses, the first-ever slug becomes permanent even if it came from a Parser
  mistake, and changing the slug rules (which the migration may do) would be
  impossible without the same history mechanism anyway.
- **Addresses by id instead of name** for everything. Stable by construction.
  Rejected: ids such as `DA_Module_Ability_ArmorShield.1` make poor addresses, and all
  existing links would change at once.
- **Do nothing; accept broken links on rename.** Rejected because of the three points
  in the Context, although the measured rename rate shows the day-to-day benefit is
  small. The decisive case is the migration and future rule changes, not game renames.
- **Hand-maintained redirects.** Rejected: nobody would notice a rename in time.

## Consequences

- An address that ever worked keeps working, by redirect, for as long as the history
  is kept, with no human action.
- Addresses still read naturally and follow the game's current names.
- `state/slugs.json` becomes permanent project state written by the pipeline, with the
  obligations in ADR-0012.
- The redirect file grows by one entry per rename, forever, against a platform limit
  (G-0013-2).
- A robot whose id changes loses its old address. The swap gate reports a robot that
  disappears in the same run that a new one appears as a suspected rename, so it is
  noticed, but nothing redirects.
- The slug map as a published file (`slug_map.json`, which the browser and the bot
  read today) becomes a view of the database.

## Gaps and open questions

### G-0013-1. On Cloudflare, a redirect wins over a real page

- **Kind:** design
- **Needed by:** phase 4

Decision 4 says a current slug beats an old redirect. The hosting platform does the
opposite: a rule in `_redirects` is always followed, even when a page exists at that
address (`docs/research/external-facts.md`). So the rule has to be enforced by the
generator: it must leave out any historical slug that is some object's current slug in
the same route. If it does not, reusing a freed name would make the new object's page
unreachable.

### G-0013-2. The redirect limit

- **Kind:** verification
- **Needed by:** phase 4

The platform allows 2,000 fixed redirects and 100 pattern redirects per site. Renames
are rare, but a single group rename adds one entry per module in the group, and a
change to the slug rules could rename hundreds of objects at once. The migration
should count how many entries it creates on day one. The route renames in ADR-0021 use
pattern redirects (about twelve) and do not count against the 2,000.

### G-0013-3. Chains and loops

- **Kind:** design
- **Needed by:** phase 4

If an object goes from A to B to C, the file should send A and B straight to C, not A
to B to C. If it goes A to B and back to A, the history contains A, which is also
current, and G-0013-1's rule drops it. The generator needs both behaviours and tests
for them.

### G-0013-4. A reused name silently points somewhere else

- **Kind:** decision
- **Needed by:** phase 4

With decision 4, if object X gives up a name and object Y takes it, every old link to
X now opens Y, with no sign that anything changed. That is probably the right
behaviour for a renamed-and-replaced game item, but it means "an old link never
breaks" is not the same as "an old link always shows what it showed". Stated here so
the trade is deliberate.

### G-0013-5. Seeding the history at migration

- **Kind:** design
- **Needed by:** phase 2 (the import)

The history must start from the slugs that are live today, before any rule or route
changes, or the migration's own changes will not get redirects. The import therefore
has to read today's slug map as the first recorded state. If the slug rules are also
changed during the migration, the first new build produces a burst of history entries;
see G-0013-2.

### G-0013-6. Redirect sources and trailing slashes

- **Kind:** verification
- **Needed by:** phase 4 (on staging)

Addresses will end in a slash (ADR-0021), and old links exist in both forms. Whether a
redirect rule written with a trailing slash also matches the address without one, and
how that interacts with the platform's own trailing-slash handling, is not documented
clearly enough to rely on. It has to be tried on staging with both forms of an old
link.

### G-0013-7. An object that changes type

- **Kind:** decision
- **Needed by:** after cutover

History is per object within a route. If the game moved an object to a different type,
its page would move to a different route folder. Nothing handles that. It may never
happen; it is listed so that it is a known limit.

### G-0013-8. The evidence window is short

- **Kind:** verification
- **Needed by:** not scheduled

"Renames are rare" rests on six months of history. It could be re-measured after a
year of slug history exists. If renames turn out to be more common than expected, the
redirect limit matters sooner.

## References

- The Data repository's `tools/wrfdb_data/slug_map.py` (moving to `packages/common`).
- `docs/research/external-facts.md`, "Cloudflare Workers static assets".
