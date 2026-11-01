# G-0003-4: generating TypeScript types from the Pydantic models (measured 2026-10-31)

**Status.** Measured on 2026-10-31 on the workstation, in a scratch environment:
Pydantic 2.14.2 (Python 3.13), json-schema-to-typescript 16.0.0 and openapi-typescript
7.13.0 (Node 22). The test model and the generator script are in
[`2026-10-ts-types/`](2026-10-ts-types/). Resolves G-0003-4.

**Answer.** Pydantic to OpenAPI to TypeScript works with one config setting and one
rule about how data is written. openapi-typescript needs no workarounds;
json-schema-to-typescript needs two.

## Method

`models.py` defines a model shaped like an ADR-0011 object: required fields, a
nullable field with a `None` default, fields with other defaults, a tier 2 map
(`dict[str, float]`), an open `detail: dict[str, Any]`, a list of references, and a
union of two object types keyed on `type`. Its schema was written with
`pydantic.json_schema.models_json_schema(..., mode="serialization")`, once with Pydantic's
defaults and once with `json_schema_serialization_defaults_required=True`. Each schema
was turned into TypeScript by json-schema-to-typescript (`gen.mjs`) and, wrapped as the
`components.schemas` of an OpenAPI 3.1 document, by openapi-typescript.

## Findings

1. **Fields with defaults come out optional by default.** Even in serialization mode,
   Pydantic leaves a field with a default out of `required`, so the type says
   `rarity?: number` although the serializer always writes it. With
   `json_schema_serialization_defaults_required=True` every field is required, and a
   nullable field becomes `icon_path: string | null`.
2. **Dumping with `exclude_none=True` drops `null` fields**, so the data stops matching
   the types: `{"icon_path":null,...}` becomes `{...}` without the key. The same holds
   for `exclude_unset` and `exclude_defaults`.
3. **json-schema-to-typescript, by default, adds `[k: string]: unknown` to every
   interface**, because Pydantic models do not state `additionalProperties`. Its option
   `additionalProperties: false` stops it. It also turns every field's Pydantic
   `title` into an alias type (`Id`, `Id1`, `Name1`, `Detail1`); removing field titles
   from the schema before generating stops that.
4. **openapi-typescript needs neither fix.** Its output has no extra index signatures
   and no alias types, keeps defaults as `@default` comments, and with
   `--root-types --root-types-no-schema-prefix` also exports `type Talent = ...` for
   each schema.
5. **Both generators handle the rest correctly:**
   - `detail: dict[str, Any]` becomes `{ [key: string]: unknown }`;
   - `dict[str, float]` becomes `{ [key: string]: number }`;
   - a union keyed on `type` becomes `Talent | Pilot` with literal `type` values, so
     TypeScript narrows on `obj.type`.

## Outputs

openapi-typescript, with the config setting from finding 1 (excerpt):

```ts
Talent: {
    id: string;
    type: "talent";
    name: string;
    /** @default null */
    icon_path: string | null;
    /** @default 0 */
    rarity: number;
    stats: {
        [key: string]: number;
    };
    /** @default [] */
    unlocks: components["schemas"]["Ref"][];
    detail: {
        [key: string]: unknown;
    };
};
```

json-schema-to-typescript with Pydantic's defaults, for comparison (findings 1 and 3):

```ts
export interface Talent {
  id: Id;
  type: Type;
  name: Name;
  icon_path?: IconPath;
  rarity?: Rarity;
  stats: Stats;
  unlocks?: Unlocks;
  detail: Detail;
  [k: string]: unknown;
}
```
