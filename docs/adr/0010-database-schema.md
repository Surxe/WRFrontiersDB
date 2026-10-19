# ADR-0010: Database schema: documents plus generic relations

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-10 |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0009 (data store), ADR-0011 (object shape), ADR-0012 (state), ADR-0013 (slugs), ADR-0014 (swap gate), ADR-0017 (discounts), ADR-0020 (assets) |

## Context

The parsed game data has an awkward shape for a relational database (baseline,
section 4):

- 47 object types and 10,862 objects, but only a handful of types have pages or are
  looked up by users.
- Objects are deeply nested. An `Ability` has eight stable fields and a dictionary of
  131 distinct raw game properties nested up to ten levels deep. The raw part changes
  whenever the game's developers add a mechanic.
- Objects refer to each other with strings of the form `OBJID_<Type>::<id>`, which can
  appear at any depth. 28,188 such references were found.
- Text is stored as keys into per-language files: 12 languages, 86 namespaces, about
  96,000 strings.
- The maintainer described the current depth of parsing as "scrappy": some structures
  are well understood and modelled, many are passed through raw.

At the same time, consumers need a few things that a pile of documents cannot give
cheaply: "what refers to this object", name search across types, and filtering and
sorting on a few well-known fields for list pages.

ADR-0009 removes migrations: the file is rebuilt on every release. A schema mistake
therefore costs one release to fix, which lowers the price of starting simple.

## Decision

1. **The schema is a hybrid.** Whole parsed objects are stored as documents and are the
   canonical form. Around them sit a few generic relational tables that are the same
   for every object type.
2. **Core tables:**
   - `objects(id, type, slug, data)`: one row per object; `data` is the full parsed
     document as JSON.
   - `refs`: one row per reference from one object to another, extracted by scanning
     every document for `OBJID_<Type>::<id>` strings at any depth. It serves reverse
     lookups ("what uses this") and the dangling-reference check before each swap
     (ADR-0014).
   - `localizations(namespace, key, lang, text)`: every string in every language.
     Documents keep their keys; a reader joins in the language it wants.
   - `search`: a full-text index (SQLite FTS5) over names, for the bot's resolver and
     the Site's search.
   - `textures`: path, width, height, content hash and which resized copies exist
     (ADR-0020).
   - state tables, loaded from `state/` on every build (ADR-0012): the build-code
     registry, robot release dates, patch manifests, slug history, and
     `discount_weeks` / `discount_items` (ADR-0017). A predictions table is written by
     a `db-build` step.
   - `meta`: key and value pairs, including the schema version, the data release id and
     the code version that built the file.
3. **Typed columns and tables are added only when a real query needs them.** An
   object's field is promoted out of the document into a column when a list page, the
   API or the bot has to filter or sort on it. Volatile structures stay in JSON only.
4. **The expected first promotions** are the filters behind today's list pages:
   - modules: rarity, faction, module type, group;
   - robots: character type, faction;
   - pilots: class, type, personality, faction.
   Many-to-many links (module to tags, pilot to talents) need nothing extra: they are
   already in `refs`.
5. **Pydantic models are the single source of truth for types** (`packages/models`).
   First drafts are generated from the current JSON and then curated by hand. The
   models:
   - validate every document in the `db-build` stage, so a patch that changes the
     structure fails loudly instead of being published;
   - produce the API's OpenAPI description;
   - produce the Site's TypeScript types, by way of JSON Schema (ADR-0003).
6. **The shape of a document is governed separately** by the three-tier rule in
   ADR-0011.

## Alternatives considered

- **A fully relational schema**: a table per object type with typed columns, and child
  tables for nested structures. It gives the strongest guarantees and the easiest ad
  hoc queries. Rejected: 47 types, nesting ten levels deep, and a shape that changes
  with game patches would mean dozens of tables that mostly mirror JSON nobody queries,
  and a schema change for every new game mechanic. The parsing depth is not uniform
  enough to model everything honestly.
- **Documents only**: one table of JSON and nothing else. Simplest. Rejected: reverse
  lookups and text search would be rebuilt by each consumer, as they are today, and
  the reference check could not be a query.
- **Entity-attribute-value** (one row per field). Rejected: it makes every query
  awkward and loses the document as a unit.
- **Hand-written TypeScript types on the Site, as today.** Rejected: two definitions
  of the same contract drift apart. This is how the Site and Parser are coupled now.
- **Types defined in JSON Schema or TypeScript first**, with Python generated from
  them. Rejected: validation happens in Python, in the pipeline, so the Python models
  must be the ones that are authoritative and expressive.

## Consequences

- A new game mechanic that only adds raw nested data changes nothing in the schema.
- Relationships are queryable for every type without per-type work, including
  references buried deep in raw data.
- One definition of each type feeds validation, the API description and the Site's
  types.
- Queries on fields that have not been promoted go through JSON functions. That is
  acceptable for 10,862 rows; it would not be for millions.
- The schema will change often as fields are promoted. That is cheap because of
  build-and-swap, but each change is a schema version change that every reader has to
  be in step with (ADR-0005, G-0005-6).
- The `refs` table depends on references being written exactly as `OBJID_<Type>::<id>`.
  A reference the Parser emits in any other form is invisible to it.

## Gaps and open questions

### G-0010-1. The actual table definitions

- **Kind:** design
- **Needed by:** phase 2

No `CREATE TABLE` statement has been written. The decision names tables and some
columns. Still to define: every column and its type, primary keys, indexes, whether
tables are declared `STRICT`, and which foreign keys are declared (the swap gate checks
"declared foreign keys", which means some must exist). `docs/schema.md` is the place
for this.

### G-0010-2. What identifies an object

- **Kind:** decision
- **Needed by:** phase 2

References name an object by type and id together. Today no id is shared between two
types (measured 2026-10-12), but nothing guarantees it, since each type's ids come from
separate game assets. So is the primary key `id` alone or `(type, id)`? The second is
safe but makes every join two columns wide. The first is simpler and needs a gate check
that ids stay unique across types.

### G-0010-3. What a `refs` row contains

- **Kind:** design
- **Needed by:** phase 2

At least source and destination. Useful extras: where in the document the reference
was found (so "which field uses this" can be answered, and so two references between
the same pair are distinguishable), and whether the destination type is one that has
objects at all. Also undecided: references whose destination type has no object file
(if any exist), and self-references.

### G-0010-4. Text search does not cover what the bot does today

- **Kind:** design
- **Needed by:** phase 4

The bot's name matching has specific rules (baseline, section 5.3, and the bot's
README): a priority order between types that share a name, pilots answering to first
names, robot part names, abbreviations tried only after a query fails as typed, and
typo correction. FTS5 finds words and prefixes; it does not rank by type, does not
correct typos, and its default tokenizer does not split Chinese, Japanese or Korean
text into words. ADR-0017 additionally wants the same matching engine for mapping
discount announcements to objects.

So `search` is a candidate index, and the matching rules still have to live in code
(`packages/common`). To settle: which names go in the index (English only, or all 12
languages), which tokenizer, whether the Site's search uses the same rules as the bot
(the Site's is TypeScript in the browser, the bot's is Python), and where nicknames,
aliases and abbreviations are stored.

### G-0010-5. Which fields the models must get right first

- **Kind:** design
- **Needed by:** phase 2

In the first pass the models mirror the Parser's current output, strict only for
fields that consumers read (ADR-0025). That requires knowing which fields those are.
The Site's hand-written TypeScript types, the bot's lookups and the DV's backend are
the evidence; no inventory has been made. Without it, "strict where consumers read"
cannot be implemented or tested.

### G-0010-6. Generating models from current JSON

- **Kind:** design
- **Needed by:** phase 2

"First drafts generated from current JSON" needs a method. A generator will infer
optional fields from whichever objects happen to lack them, and number types from
whichever values happen to be whole. Decisions needed: how missing fields and nulls
are distinguished, whether whole-number floats are integers, and how fields seen in
only a few objects are treated. These choices become the contract.

### G-0010-7. How localization is exposed

- **Kind:** design
- **Needed by:** phase 4

The `localizations` table holds about 96,000 rows. The Site today ships the selected
language's entire file to the browser on every page (baseline, section 5.1). Whether
the new Site keeps doing that (generated from this table into `/data/`), ships only the
strings a page uses, or renders text at build time, is not decided, and it determines
how the table is queried. The Site also has a few strings of its own (`locales/`) that
are not game data.

### G-0010-8. The contents of `meta`

- **Kind:** design
- **Needed by:** phase 2

Named so far: schema version, data release id, code version. Also needed by other
decisions: the game version and Steam manifest id, the build time, the minimum SQLite
version (ADR-0009, G-0009-1), and something that lets a reader detect a file that was
only partly written.

### G-0010-9. Whether promoted columns duplicate or replace document fields

- **Kind:** decision
- **Needed by:** phase 2

When `rarity` becomes a column, does it also stay inside `data`? Keeping both is
simple for readers but allows the two to disagree if the build has a bug. Generated
columns (computed by SQLite from the document) remove that risk and cost a little at
build time.

## References

- `docs/schema.md` for the working specification.
- `docs/research/2026-10-baseline.md`, section 4.
- SQLite FTS5: https://sqlite.org/fts5.html
