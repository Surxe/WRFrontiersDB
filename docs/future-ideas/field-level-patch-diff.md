# Field-level comparison between patches

| | |
|---|---|
| Recorded | 2026-10-20 |
| State | Idea; not planned for the migration |
| Related | ADR-0009 (decision 7, G-0009-3), ADR-0010 (documents table), ADR-0015 (database archive, G-0015-6; both resolved 2026-10-20 by deferring to this idea) |

## Where things stand

Decision 7 of ADR-0009 gets history between patches by keeping one database per game
patch and comparing them with SQLite's `sqldiff`. For the migration, `sqldiff` is used
only to **identify which objects changed**: added, removed or changed rows, by id
(G-0009-3, resolved 2026-10-20).

`sqldiff` cannot say *how* an object changed. Each object is one row holding the whole
document as JSON text (G-0009-2), so a changed row is reported as the entire new
document.

## The idea

A small JSON-aware comparison tool on top of the list `sqldiff` produces:

- for each changed object, load the old and new documents from the two archived
  databases and diff them by JSON path (`stats.health: 1200 -> 1350`);
- group the result by object type, and label fields with their display names rather
  than raw paths;
- emit a structured result (JSON) that several consumers can render.

Possible consumers:

- a patch-notes page on the Site ("what changed in patch X");
- a section of the pipeline's run report (ADR-0024), so a patch-day email says what
  moved, not only that something did;
- a per-object "history" panel showing how a value changed across patches;
- a bot command answering "what changed for <object> last patch".

## Why it is deferred

- Listing changed objects is all the migration needs; nothing before cutover consumes
  field-level detail.
- The useful output depends on the object shape, and the three-tier reshaping
  (ADR-0011) happens after cutover. A field-level diff written against today's shapes
  would be rewritten once the shapes change.
- It is new product surface (pages, report sections, bot commands), not part of moving
  the existing system.

## What would make it worth doing

- The archive of per-patch databases (ADR-0015) has a few patches in it, so there is
  real history to show.
- The reshaping has settled the field names that would appear in the output.
- Someone wants patch notes generated rather than read from the game's own
  announcements.

## Questions to answer first

- **Noise:** which changes are meaningful. Reordered arrays, float rounding and
  internal ids can change with no gameplay effect; the tool needs rules to ignore them.
- **Identity across patches:** objects renamed or re-keyed by the game look like one
  removal and one addition (ADR-0013 on slugs bears on this).
- **Where it runs:** a pipeline stage after the database build, or on demand against
  two archived files.
- **Whether to keep `sqldiff` at all** once a JSON-aware tool exists, since the tool
  can find changed ids itself by comparing the two `objects` tables.
