# ADR-0017: Discount data

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 (state, release path, matching), 2026-10-11 (prediction builder's home) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0010 (schema), ADR-0012 (state), ADR-0014 (swap gate), ADR-0021 (URLs), ADR-0022 (secrets) |

## Context

The game announces a set of discounted items each week in a news post. The Discount
Visualizer (DV) turns that into a page: a grid of the discounted items, a page per
past week, per-item history, a timeline, and predictions for the next week (baseline,
sections 2.2 and 5.2).

How it works today:

- The News-Scraper keeps an archive of news posts (298 posts from 2022-11 to 2026-09)
  and detects a new discount announcement. A timer runs it four times a day.
- On a new week it dispatches a GitHub Actions workflow in the DV repository with the
  item names and dates as text.
- That workflow maps each name to a game object id in three steps: a pinned mapping
  (`manual_mapping.json`, six entries), then an exact name match, then **Jev**, a
  third-party typed classifier service. Each new Jev match is written back to the pin
  file so later runs reuse it.
- A robot ("virtual bot") in the list is expanded to its core modules, with titan
  weapons filtered out.
- The mapped week is committed to the DV repository's `archive/discounts/` (59 weeks
  since 2025-05-23), a screenshot is taken for link previews, and the site is built
  and published.
- The prediction builder ranks robots by how often a robot that had waited this long
  was discounted, re-runs a walk-forward backtest over the whole history every time,
  and appends a row to an accuracy-history file.

The DV is a separate site with its own repository, its own deployment and its own copy
of the game data. ADR-0002 merges it into the main Site. The bot has its own,
different name matcher for `[[name]]` lookups.

There is also an older hand-kept note, `old_discounts.md`, covering weeks from
February to March 2025, before the archive began.

## Decision

1. **Mapped discount weeks are accumulated state**: `state/discounts/<week>.json`, one
   file per week, storing object ids (ADR-0012). The 59 existing weeks are imported.
   The ids are authoritative: mapping announcement text to objects again later is not
   reliable, because names change and the matcher changes.
2. **The scraped news posts are kept as provenance** in `state/news/`. The scraper's
   working folder on the server is only a working copy.
3. **A new discount week is a data release through the ordinary pipeline.** The watch
   detects it, maps it, and writes the week's file. Only the database build re-runs
   (ADR-0016). Then the swap gate, the state commit, the database swap, and a Site
   rebuild at the deployed tag, including the link-preview screenshot (ADR-0014).
4. **In the database:** `discount_weeks(week, starts, ends)` and
   `discount_items(week, object_id)`. Analysis such as "last discounted" and "how often
   discounted" is computed for the Site's discount pages.
5. **The prediction builder becomes a step of the database build**, writing a
   predictions table, so that the API and the bot can use predictions later instead of
   their being locked inside the Site's build. (Decided 2026-10-11.)
6. **One name-matching engine is shared** by discount mapping and the bot's lookups,
   built on the database's search index and alias data (ADR-0010).
7. **The pin file goes away.** Typo pins become alias entries in the shared matcher;
   the cache of Jev matches is unnecessary once the result of mapping is stored as ids.
   Its full extent is to be confirmed at implementation.
8. **Jev stays available to the mapping step**, and its API key joins the pipeline's
   secrets (ADR-0022). Where Jev sits relative to the shared matcher is to be decided
   at implementation.
9. **`old_discounts.md` stays an archived raw note.** It is not imported. A check on
   2026-10-10 confirmed the scraper's archive does not cover those weeks (the first
   discount announcement it holds is 2025-05-23), and that no other archive exists on
   either machine.
10. **The watch's own "already seen" file is operational** and stays on the server, out
    of git.
11. **The DV's pages move under `/discounts/` on the merged Site** (ADR-0021).

## Alternatives considered

- **Keep discounts as a separate site and pipeline.** No migration work. Rejected with
  ADR-0002: it is a second deployment, a second copy of game data and a second set of
  name-matching rules to keep in step.
- **Store the announced names and map them at every build.** Always uses the latest
  matcher. Rejected: an old week's result would change whenever names or the matcher
  changed, and an external classifier in the build path makes builds unrepeatable.
- **Compute predictions in the Site build**, as the DV does. Rejected in favour of the
  database build so other consumers can read them.
- **Re-map the 59 archived weeks** with the new matcher to check them. Not chosen: the
  stored ids are treated as the truth.
- **Recover the early 2025 weeks** from the hand-kept note. Not chosen: the note is raw
  and nothing corroborates it.

## Consequences

- Discount history has the same durability as the rest of project state: in git,
  reviewable, correctable by hand.
- A discount week takes the same path as a patch, so it is validated the same way and
  shows up at the same time on the Site, the bot and (later) the API.
- About fifty more data releases a year, each with a database build, a full gate and a
  Site deployment.
- The mapping step is the only place an external service (Jev) and free text from a
  news post enter the pipeline. A mapping mistake is committed to permanent state.
- The DV's backend (about 3,300 lines) is taken apart: mapping to the orchestrator,
  matching to a shared package, grid generation and predictions to the database build
  and the Site.

## Gaps and open questions

### G-0017-1. What happens when an announced item cannot be mapped

- **Kind:** decision
- **Needed by:** phase 2

Today an item that Jev cannot map fails the DV workflow, and the maintainer gets an
email. In the new flow the mapping happens before the week's file is written. Options
when one item out of ten will not map: write nothing and report (the week is delayed
until a person adds an alias); write the nine and report (the week goes live
incomplete); or write the week with the unmapped name recorded as text. This is a
product choice as much as a technical one, and it decides whether discount weeks can
block.

### G-0017-2. The matcher, and Jev's place in it

- **Kind:** design
- **Needed by:** phase 2

Decision 6 calls for one engine; decision 8 leaves Jev's position open. The two
matchers being unified have different jobs. The bot's is interactive, forgiving and
ranked by type (ADR-0010, G-0010-4). Discount mapping wants one confident answer per
announced name, or a refusal. Whether one engine can serve both, with Jev as a
fallback for mapping only, needs a design and a test set. The 59 archived weeks are
not a test set as they stand: checked on 2026-10-12, an archived week holds its dates
and a list of object ids, not the names that were announced. A test set would have to
be rebuilt by pairing archived weeks with the announcement text in the scraped posts,
where that text exists.

### G-0017-3. What exactly `manual_mapping.json` does

- **Kind:** verification
- **Needed by:** phase 2

The decision to remove it is conditional on confirming its full extent. It has six
entries and "also caches each new Jev match". Before it is deleted, each entry needs
classifying as a typo pin (becomes an alias), a Jev cache entry (dropped), or
something else.

### G-0017-4. Robot expansion and what a discount item is

- **Kind:** design
- **Needed by:** phase 2

`discount_items(week, object_id)` stores one id per row. The DV expands an announced
robot into its core modules and filters titan weapons, and the 59 archived weeks store
the result of that expansion (module ids), not the robot that was announced (checked
2026-10-12). To decide for new weeks: does the stored week hold what was announced
(the robot), what was expanded (the modules), or both? If only the expansion is
stored, a later change to a robot's parts cannot be reapplied; if only the
announcement is stored, the expansion rule becomes part of every build and old weeks
change when a robot's parts change. Whatever is chosen, the imported weeks can only
ever hold the expansion, so both kinds of week must be readable side by side.

### G-0017-5. Prediction history as state

- **Kind:** decision
- **Needed by:** phase 2

The prediction builder appends a row to an accuracy-history file on every run and
keeps a per-week record of what it would have predicted. If the formula changes, old
rows reflect the old formula and cannot be regenerated as they were. Under ADR-0012
anything that cannot be rebuilt is state. These files are not on the state list. See
G-0012-5.

### G-0017-6. The link-preview screenshot

- **Kind:** design
- **Needed by:** phase 4

The current discount table is captured as an image so that a link pasted into Discord
shows the table. That needs a headless browser wherever the Site is built. The DV uses
Puppeteer for pipeline screenshots, and that is the tool to use here (ADR-0003,
G-0003-3). It also means the image for `/discounts/` changes weekly while Discord
caches previews, which is existing behaviour.

### G-0017-7. Detection depends on a third party's page

- **Kind:** verification
- **Needed by:** phase 2

The watch reads the game's news feed. If its format changes, detection silently finds
nothing, and with email-only reporting (ADR-0024) a quiet poll looks the same as a
broken one. Today a quiet poll deletes its own log. A cheap guard: report when no new
discount week has been seen for longer than, say, ten days.

### G-0017-8. How often the watch runs and when it reports

- **Kind:** decision
- **Needed by:** phase 3

Today: four polls a day, and an email only on a new week or a problem. Whether both
carry over unchanged is assumed, not decided.

## References

- `docs/research/2026-10-baseline.md`, sections 2.2 and 5.2.
- The DV repository's `README.md` and `src/backend/build_predictions.py`.
