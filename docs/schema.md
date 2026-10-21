# Data schema: working specification

This is a living specification of two things: the shape of a parsed game object, and
the tables of the database built from those objects. It is edited as the design is
filled in. The reasons for its shape are in the ADRs and are not repeated here:

- object shape: [ADR-0011](adr/0011-object-shape-three-tiers.md)
- tables: [ADR-0010](adr/0010-database-schema.md)
- the file itself: [ADR-0009](adr/0009-data-store.md)

**State of this document (2026-10-12):** part 1 was agreed on 2026-10-10. Part 2 is a
skeleton: the tables and some columns were named in the decision, and everything
marked "open" has not been designed. Nothing here has been implemented.

## Part 1. The shape of an object

### 1.1 Background

The Parser's current output mixes stable fields with raw game data. Example: `Ability`
(177 objects).

- The top level is small and stable: `id`, `name`, `description`, `cooldown`,
  `icon_path`, `targeting`, `ai`, `projectile_types`.
- `misc` holds 131 distinct raw Unreal property names, nested up to 10 levels, with
  separately parsed sub-structures mixed in.
- References are lifted out of the raw data by one-off code (for example
  `weapon_char_module_ref`, lifted from
  `misc.spawn_actor_action.ActorClass.WeaponInfos`), so whether a value sits at depth 1
  or depth 4 depends on whether someone wrote a special case.

### 1.2 The three tiers

| Tier | What goes there | Typing in the models | Storage |
|---|---|---|---|
| **1. Core** | Identity (`id`, name and description localization keys, icon and image paths); references to other objects; every value the Site, API or bot reads directly (`cooldown`, rarity, faction, class, ...) | Strict: fixed field names, real types | In the document; promoted to a column only when a real query needs it |
| **2. Open maps** | Containers with a stable shape but a changing key set, such as per-level stat maps (stat name to value) and scalar tables | Typed containers: `dict[str, float]`, `list[dict[str, float]]`, ... | JSON only. Possibly, later, a generic `object_stats(object_id, level, stat, value)` table if queries across objects (sort modules by damage) are wanted |
| **3. Detail** | Raw game-mechanic data: raw Unreal keys at any depth | `dict[str, Any]`: no promises | JSON only; never queried; at most shown in a "raw data" panel |

### 1.3 Rules

1. **Position depends on meaning, not on where the game put it.** A reference, or any
   value consumers read, is tier 1 and sits at the top level (or in a declared, shallow
   sub-object), however deep it was in the source. Lifting is a declared mapping from
   source path to output name, per field, extending the Parser's key maps. It is never
   one-off code.
2. **Every type has the same outline:**
   `{id, type, ...tier 1 fields..., <tier 2 maps>, detail: {...}}`.
   `misc` is renamed `detail` everywhere, and every type has one.
3. **Relationships do not depend on lifting.** The `refs` table is built by scanning
   the whole document for `OBJID_<Type>::<id>` strings at any depth, so a reference
   buried in `detail` still gets the dangling-reference check and reverse lookups.
4. **Shared sub-structures become their own objects.** A sub-structure (an actor or
   buff class, a curve, ...) that several objects share, or that a page would show or
   link to on its own, gets an id and its own type. Otherwise it stays inline in
   `detail`.

### 1.4 Validation and failure policy

A data release is stopped by an ERROR or CRITICAL log line, or by a failed gate check
([ADR-0014](adr/0014-swap-gate.md)).

| Change | Severity | Effect on a data release |
|---|---|---|
| Unknown raw key in the source | WARNING; the key passes into `detail` | does not block |
| Tier 1 field missing, wrong type, or otherwise failing its model | ERROR, automatic | blocks |
| Tier 2 container shape or value type wrong (a map becomes a list; a non-number where a number is expected) | ERROR, automatic | blocks |
| Tier 2 key set changes (a stat key appears or disappears inside an open map) | WARNING | does not block |
| Tier 3 (`detail`) changes of any kind | none, at most INFO | does not block |

Open points:

- The split for tier 2 (shape and type errors block; key-set changes warn) is an
  interpretation of "to an extent" and is unconfirmed (ADR-0011, G-0011-2).
- The Parser's `UNKNOWN_PROPERTY` log level is numbered above WARNING, and today no log
  level blocks a release. The rule must be stated as "ERROR and above", and existing
  error-level log calls classified, before it is switched on (ADR-0011, G-0011-1).

Validation runs at the end of parsing and again when the database is built.

### 1.5 Where the reshaping happens

- In the **Parser**, which already chooses output names. The Pydantic models
  (`packages/models`) are the shape the Parser must produce.
- The database build stays simple: it loads validated documents, extracts references
  and localizations, and fills promoted columns.
- Approving a new key changes meaning. Tier 1 and 2 changes are deliberate (a model
  change plus a Parser mapping). Tier 3 changes are parsing matters only, never
  contract changes.

### 1.6 Order of work

- **During the migration:** the models mirror today's output. Fields that consumers
  read are strict; `misc` is renamed `detail` and typed `dict[str, Any]`. Nothing else
  is reshaped. Which fields consumers read has not been inventoried (ADR-0010,
  G-0010-5).
- **After cutover:** one type per pull request (model, Parser mapping, consumers,
  promoted columns), ordered by consumer use: Module; then robots and presets; then
  Pilot and talents; then the rest. `Ability` is reshaped as module pages need it.

## Part 2. Database tables

A single SQLite file, rebuilt from scratch for every data release and opened
read-only. Column lists below are what the decision named. Types, keys and indexes are
open unless stated (ADR-0010, G-0010-1).

### 2.1 `objects`

One row per parsed object.

| Column | Notes |
|---|---|
| `id` | the object's id as the Parser emits it (for example `DA_Module_ChassisAlpha.1`, `alpha`) |
| `type` | the object type name (for example `Module`, `VirtualBot`) |
| `slug` | the page slug, for types that have pages; empty otherwise |
| `data` | the whole document as JSON |
| promoted columns | added per type as queries need them (2.8) |

Open: whether the primary key is `id` or `(type, id)`. No id is shared between types
today, but nothing guarantees it (ADR-0010, G-0010-2). `data` is stored as JSON
text, not SQLite's binary JSON (ADR-0009, G-0009-2).

### 2.2 `refs`

One row per reference from one object to another, extracted from every
`OBJID_<Type>::<id>` string at any depth in `data`.

Columns named so far: source and destination. Open: the path within the source
document where the reference was found; how references to types without objects are
recorded (ADR-0010, G-0010-3).

### 2.3 `localizations`

`(namespace, key, lang, text)`. Twelve languages, 86 namespaces, about 96,000 rows.
Documents keep their keys; readers join in the language they want.

Open: how the Site consumes it (ADR-0010, G-0010-7).

### 2.4 `search`

A full-text index (FTS5) over names.

Open: which names and languages are indexed, the tokenizer, and how the bot's matching
rules, nicknames, aliases and abbreviations sit on top of it (ADR-0010, G-0010-4).

### 2.5 `textures`

Path, width, height, content hash, and which resized copies exist
([ADR-0020](adr/0020-assets-images-and-models.md)).

Open: whether models get the same treatment (a hash is needed for their addresses
too); whether objects are named by content hash (ADR-0020, G-0020-1).

### 2.6 State tables

Loaded on every build from `state/` in the repository
([ADR-0012](adr/0012-accumulated-state.md)). The database is never their only home.

| Table (working names) | Source |
|---|---|
| build-code registry | `state/` |
| robot release dates | `state/` |
| patch manifests | `state/` |
| slug history | `state/slugs.json` ([ADR-0013](adr/0013-slugs-and-link-stability.md)) |
| `discount_weeks(week, starts, ends)` | `state/discounts/` ([ADR-0017](adr/0017-discount-data.md)) |
| `discount_items(week, object_id)` | `state/discounts/` |
| predictions | computed by a build step from discount history |

Open: every column list; whether a discount item records what was announced or what it
was expanded to (ADR-0017, G-0017-4).

### 2.7 `meta`

Key and value pairs. Named so far: schema version, data release id, code version.
Proposed additions: game version, Steam manifest id, build time, minimum SQLite
version (ADR-0010, G-0010-8).

### 2.8 Promoted columns

Added only when a list page, the API or the bot must filter or sort on a field.
Expected first:

- modules: rarity, faction, module type, group;
- robots: character type, faction;
- pilots: class, type, personality, faction.

Many-to-many links (module to tags, pilot to talents) come from `refs` and need no
column.

Open: whether a promoted column duplicates the field in `data` or is generated from
it (ADR-0010, G-0010-9).

## Part 3. Files derived from the database

Some consumers do not query the database but read files generated from it. These are
not designed yet and are listed so that the list exists somewhere
(ADR-0009, G-0009-6; ADR-0021, G-0021-4):

- files the browser loads at run time, under `/data/` on the Site: the selected
  language's strings, the object tables the robot builder needs, the build-code
  registry, the slug map, the deploy record;
- the redirect file generated from slug history and the route table;
- TypeScript types and the OpenAPI description generated from the models
  (`packages/types`).
