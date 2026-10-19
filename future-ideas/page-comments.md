# Future idea: comments on object pages

| | |
|---|---|
| State | Idea. Not part of the migration plan. |
| Recorded | 2026-10-18 |
| Origin | todo t-0207 |
| Related | ADR-0006 (hosting), ADR-0009 (data store), ADR-0012 (state), ADR-0013 (slugs), ADR-0014 (swap gate), ADR-0015 (data releases), ADR-0018 (API), ADR-0019 (Cloudflare), ADR-0021 (URL structure), ADR-0022 (secrets), ADR-0023 (backups) |

ADR numbers refer to the decision records on the `docs/adr-seed` branch.

## The idea

Give each page on the merged Site a discussion section, modelled on Wikipedia's talk
pages rather than on a blog's comment box.

A Wikipedia talk page is about the article, not a reaction to it. For a datamined
database that means comments such as "this stat is wrong", "this changed in patch X" or
"this build code does not decode". The feature is as much a correction channel for the
data as a social one.

## What the migration's decisions already imply

None of the ADRs mention comments, but several of them constrain how comments could
work.

1. **Comments are a new kind of data.** Everything in the planned system is either
   rebuildable (the SQLite file, rebuilt and swapped, read-only, never migrated:
   ADR-0009) or accumulated state committed to `state/` (ADR-0012). Comments are
   neither: the public writes them at any time, and they cannot be rebuilt. This would
   be the system's first public write path.
2. **The Site is static on Cloudflare Workers static assets, with no Worker script**
   (ADR-0019). ADR-0018 item 6 already allows a script on `/api/*` only, which keeps
   static pages outside the free plan's 100,000 daily invocations. A comments endpoint
   fits there.
3. **The home server is never needed to load a page** (ADR-0006, ADR-0018). Comments
   served from home would have to load after the page and fail quietly when home is
   down.
4. **Comments attach to the object id, never the address.** Slugs follow names and
   change (ADR-0013). Wikipedia moves the talk page with the article; attaching to the id
   gets the same result. The exception is robots: their id comes from the English name,
   and the risk of it changing was accepted, so a renamed robot would orphan its
   comments unless an id-alias map is kept.

## Borrowed from Wikipedia

| Wikipedia | Here |
|---|---|
| One talk page per article | One thread list per object id, plus one per fixed page (`/discounts/<date>/`, the prediction pages) |
| Comments sit against an article revision | Each comment records the data release id it was posted on (ADR-0015), so the page can say "posted before patch X" |
| Sections and threads | Top-level topics with replies, no deeper nesting |
| Signed, account-based | Login required; anonymous posting is too much moderation for one maintainer |
| Archiving | Threads older than some number of patches are collapsed |
| Page moves carry the talk page | Free with id anchoring; robots need the alias map |

## Options

### A. Worker on `/api/comments/*`, Cloudflare D1, Discord login, Turnstile (preferred)

- Fits ADR-0018 item 6. The home server is not involved.
- Discord login suits the audience, which already uses the bot.
- Turnstile (Cloudflare's challenge) and rate limits cut spam.
- Learning value of the same kind as the API (ADR-0018's first reason), without
  public writes reaching the home machine.
- Costs: a new store to back up (ADR-0023 does not cover it), new secrets (Discord
  OAuth client, D1 binding: ADR-0022), and the first Worker code in the Site.

### B. Giscus (GitHub Discussions)

- Almost no infrastructure; moderation happens in GitHub.
- Must be set to map by a specific term (the object id), not by page path.
- Needs a GitHub account to post, which most players will not have.

### C. Discord forum threads

- The bot opens a forum thread per object; the page links to "Discuss on Discord" and
  may show the latest messages.
- Lowest effort, and where the community already is.
- The discussion lives off the Site and is not indexed.

### D. FastAPI at home, through the tunnel, with a second writable SQLite (rejected for now)

- Would give the API its first real consumer.
- Puts public writes, spam and abuse handling on the home machine, and blurs ADR-0009's
  rule that the database is read-only in service.

## Open questions

1. Which option. A is the current preference.
2. Moderation: who can hide a comment, a report button, rate limits, bans.
3. Backups and restore for the comment store (ADR-0023).
4. Privacy policy and terms of service updates (ADR-0021 moves them to the root), and
   how a user deletes their own comments.
5. Whether the swap gate (ADR-0014) warns when a robot id disappears and its comments
   would be orphaned.
6. Whether comments appear in the bot (for example a count, or a link to the thread).
7. Whether fixed pages without an object id get threads, and what they are keyed on.

## When

After cutover at the earliest. It depends on the Cloudflare set-up from phase 3 and
blocks nothing. If it goes ahead, it gets its own ADR.
