# Future ideas

Ideas that are deliberately **not** part of the current plan. Each one records what it
would change, why it is deferred, and what would make it worth picking up. None of them
is a decision; an idea that is adopted becomes an ADR (see [`../adr/`](../adr/README.md)).

| Idea | Summary | Recorded |
|---|---|---|
| [`cue4parse-release-in-dvc.md`](cue4parse-release-in-dvc.md) | Wire the WRFrontiersDB-CUE4Parse build into the DVC pipeline instead of consuming a manually cut GitHub release | 2026-10-19 |
| [`field-level-patch-diff.md`](field-level-patch-diff.md) | Compare archived per-patch databases field by field, beyond `sqldiff`'s list of changed objects | 2026-10-20 |
| [`site-api-swap-consistency.md`](site-api-swap-consistency.md) | Keep the static Site and the API consistent across a database swap once the Site uses the API (wave 3) | 2026-10-20 |
