# ADR-0011: Object shape: three tiers

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-10 (tiers, failure policy), 2026-10-11 (order of work) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0010 (schema), ADR-0014 (swap gate), ADR-0025 (migration); specification in `docs/schema.md` |

## Context

A parsed object today mixes two kinds of content with nothing to tell them apart
(baseline, section 4). Taking `Ability` as the example:

- A small stable top level: `id`, `name`, `description`, `cooldown`, `icon_path`,
  `targeting`, `ai`, `projectile_types`.
- A `misc` dictionary holding 131 distinct raw Unreal property names, nested up to ten
  levels, with separately parsed sub-structures mixed in.
- References hoisted out of the raw data by one-off code. For example
  `weapon_char_module_ref` is lifted out of
  `misc.spawn_actor_action.ActorClass.WeaponInfos`. Whether a value sits at depth one
  or depth four depends on whether someone once wrote a special case for it.

Consequences of that mix:

- A consumer cannot tell which fields are a promise and which are raw data that will
  change with the next patch.
- The Parser's handling of new game data is a human process (the patch-day runbook):
  unknown properties are logged, a person decides for each whether to parse it, skip
  it, or approve it as passed-through.
- Different types use different conventions for the same idea.

Typed models (ADR-0010) need a rule for what is typed strictly and what is not.

## Decision

1. **Every object has three tiers.**

   | Tier | What belongs in it | Typing | Storage |
   |---|---|---|---|
   | 1. Core | identity (`id`, name and description keys, icon and image paths), references to other objects, and every value the Site, API or bot reads directly | strict: fixed names and real types | in the document; promoted to a column only when a query needs it (ADR-0010) |
   | 2. Open maps | containers whose shape is stable but whose keys change, such as per-level stat maps | typed containers, for example a map from stat name to number | JSON only |
   | 3. Detail | raw game-mechanic data: raw Unreal keys at any depth | untyped; no promises | JSON only; shown at most in a "raw data" panel |

2. **Where a value sits depends on what it means, not on where the game put it.** A
   reference, or any value a consumer reads, is tier 1 and sits at the top level or in
   a declared shallow sub-object, however deep it was in the source. Lifting a value up
   is a declared mapping from source path to output name, per field, never one-off
   code.
3. **Every type has the same outline**:
   `{id, type, ...tier 1 fields..., ...tier 2 maps..., detail: {...}}`. The `misc` key
   is renamed `detail` everywhere, and every type has one.
4. **Relationships do not depend on lifting.** The `refs` table (ADR-0010) is built by
   scanning the whole document, so a reference still buried in `detail` gets the
   dangling-reference check and reverse lookups. Lifting is only for convenient
   reading.
5. **A shared sub-structure becomes its own object.** If a structure is used by several
   objects, or a page would show or link to it on its own, it gets an id and a type.
   Otherwise it stays inline in `detail`.
6. **Failure policy:**

   | Change in the game data | Severity | Effect on a data release |
   |---|---|---|
   | An unknown raw key appears | WARNING; the key passes into `detail` | does not block |
   | A tier 1 field is missing, has the wrong type or otherwise fails its model | ERROR, raised automatically | blocks |
   | A tier 2 container has the wrong shape or value type | ERROR, raised automatically | blocks |
   | A key appears or disappears inside a tier 2 map | WARNING | does not block |
   | Anything changes in tier 3 | none | does not block |

   The general rule the maintainer set: **any log line above WARNING stops the data
   release.**
7. **Validation runs twice**: at the end of parsing, and again when the database is
   built (before the swap).
8. **The reshaping is done in the Parser**, against the models in `packages/models`.
   The `db-build` stage stays simple.
9. **This is done after cutover, one type per pull request** (ADR-0025). For the
   migration itself the models mirror today's output, with `misc` renamed to `detail`.
   Order afterwards follows consumer use: Module, then robots and presets, then Pilot
   and talents, then the rest.

## Alternatives considered

- **Type everything strictly.** Maximum safety. Rejected: every new game mechanic
  would block a patch until a person had modelled it, and most raw data is never read
  by anything.
- **Type nothing; keep the current free-form objects.** Rejected: it is the current
  problem. Consumers break on changes nobody saw coming.
- **Two tiers** (strict and raw). Considered. The middle tier exists because of things
  like stat tables, where the container is dependable but the set of keys legitimately
  changes with patches; putting them in the strict tier would block patches for no
  reason, and putting them in the raw tier would give up validation that is easy to
  have.
- **Unknown keys block the release.** The maintainer was explicit that they must not:
  the pipeline should keep publishing when the game adds data it does not understand
  yet.
- **Do the reshaping before cutover.** Rejected in ADR-0025: it is the largest and
  least bounded piece of work, and doing it first would delay proving the new
  infrastructure.

## Consequences

- A consumer has a written promise: tier 1 and the shape of tier 2 are stable and
  validated; `detail` is not.
- A new raw property no longer needs a decision before the next release. It lands in
  `detail` with a warning, and is promoted later if something needs it.
- The patch-day approval process changes meaning: decisions are now about promoting a
  value to tier 1 or 2 (a model change plus a Parser mapping), not about whether to
  allow a key through.
- A change in the game that breaks a tier 1 field now stops the release until someone
  fixes the Parser. Before, the release would have gone out with a gap. Users see
  slightly older complete data instead of current incomplete data. This is the
  intended trade.
- Each type's reshaping touches the model, the Parser, and every consumer of that type,
  and consumer code written during the migration against today's shape gets touched a
  second time.

## Gaps and open questions

### G-0011-1. "Above WARNING blocks" is new behaviour, and one level sits in between

- **Kind:** decision
- **Needed by:** phase 2

The working notes described "any Parser log above WARNING stops deployment" as an
existing rule being kept. The code and the patch-day runbook say otherwise: today only
a crashed stage stops a run, and a parse with `logger.error` lines is still published
(baseline, section 2.1). So this is a new rule, and two details need pinning down:

- The Parser's custom `UNKNOWN_PROPERTY` level is numbered 31, which is above WARNING
  (30). Read literally, the rule would block on every unknown property, which
  contradicts the first row of the failure table. The rule should be stated as
  "ERROR and above", or the custom level renumbered.
- Which stages the rule covers. Other stages log errors that are deliberately
  advisory today (for example two premium pilots sharing a first name). ADR-0014 lists
  that case as a warning. Every existing `logger.error` call needs to be classified as
  blocking or not before the rule is switched on.

Recent parse runs logged no ERROR lines (baseline, section 2.1), so the rule would not
have blocked them.

### G-0011-2. The tier 2 split was the assistant's reading

- **Kind:** decision
- **Needed by:** phase 6 (when the first type is reshaped)

The maintainer said tier 2 should raise errors "to an extent". The split in the table
(wrong shape or value type is an error; a changed set of keys is a warning) is the
assistant's interpretation and has not been confirmed.

### G-0011-3. The format of the lifting map

- **Kind:** design
- **Needed by:** phase 6

Decision 2 requires lifting to be declared as a mapping from source path to output
name. The Parser already has key maps per parser. How those are extended to express a
deep source path, a default when the path is absent, and a lift out of a list, is not
designed.

### G-0011-4. When a sub-structure deserves to be an object

- **Kind:** design
- **Needed by:** phase 6

Decision 5 gives the rule; nobody has applied it yet. A survey of which structures
are shared (actor classes, buff classes, curves) would say how many new object types
this creates, and whether their ids are stable across patches.

### G-0011-5. How much `detail` weighs, and who can see it

- **Kind:** verification
- **Needed by:** the API phase

`detail` holds the bulk of the bytes. Whether the API returns it by default, and
whether the Site ships it to the browser in the object tables it loads at run time
(ADR-0009, G-0009-6), affects response sizes and how much raw data is exposed. Not
measured.

### G-0011-6. Validating twice

- **Kind:** design
- **Needed by:** phase 2

Decision 7 validates at the end of parsing and at database build. If both use the same
models on the same documents, the second run can only catch corruption between the two
stages. If the first is meant to be a quicker, partial check, that should be said.

## References

- `docs/schema.md`: the working specification this ADR explains.
- `docs/research/2026-10-baseline.md`, sections 2.1 and 4.
