# ADR-0020: Assets: object storage, image formats and models

| | |
|---|---|
| Status | Accepted |
| Decided | 2026-10-08 (assets off GitHub, no laptop on page views), 2026-10-10 (models to storage, image formats, sizes, `textures` table) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0009 (data store), ADR-0010 (schema), ADR-0014 (swap gate), ADR-0016 (DVC), ADR-0019 (Cloudflare) |

## Context

The game data includes binary assets (baseline, section 4):

- 613 textures, 140 MB, all PNG with transparency;
- 258 model files, 405 MB, as JSON mesh data, up to 9.7 MB each.

Today both live in the Data repository and are published with the Site as static
files. The bot links to textures at a raw GitHub address pinned to a commit.

Two problems:

1. **Where they live.** With the Data repository retired (ADR-0009) they need a home
   that is not git and not the laptop at home.
2. **How they are served.** Every image is delivered as its original PNG, whatever
   size it is drawn at. The browser downloads the whole file and scales it down.
   Measured on 2026-10-10:
   - the robots list page draws 43 robot icons at 24 px; each is a 2048 px render of
     1.1 to 2.5 MB; the page transfers about **74 MB**, all at once (no lazy loading);
   - the module list draws 237 icons at 24 px from mostly 512 px files: about
     **32 MB**.

Measurements behind the decision, made on 2026-10-10 with ImageMagick 7 and libwebp
1.5.0 on all 613 files (about 5 seconds on 8 threads):

| Group | Files | PNG | WebP |
|---|---|---|---|
| 256 px or smaller, lossless | 195 | 1.5 MB | 0.5 MB |
| 257 to 512 px, quality 85 | 357 | 59.5 MB | 12.2 MB |
| larger than 512 px, quality 85 | 61 | 79.2 MB | 11.0 MB (1.6 MB at 512 px) |
| **Total** | 613 | **140 MB** | **24 MB** |

A 128 px copy of every image larger than 128 px came to 583 files and 2.2 MB in total
(about 3.7 KB each). On a 20-file sample AVIF was about 28% smaller than WebP and took
three times as long to encode. No loss was visible on the robot renders at quality 85.

## Decision

### Where assets live

1. **Images and models are stored in Cloudflare R2 object storage**, in a public
   bucket served through its own hostname (ADR-0019).
2. **The home machine never serves an image on a page view** (ADR-0006).
3. **Objects keep stable names, and addresses carry the content hash as a query
   marker: `<path>?v=<hash>`.** Responses are cached as immutable. A changed image gets
   a new marker, so no cache purge is needed. (Explicit purges were accepted earlier as
   tolerable; versioned addresses were then chosen as simpler.)
4. **The bot does not need commit-pinned image addresses.** Image names rarely change.
5. **The database has a `textures` table**: path, width, height, content hash, and
   which resized copies exist (ADR-0010). The hash supplies the `?v=` marker; width
   and height are written onto `<img>` tags so pages do not shift while loading.

### Image formats

6. **WebP is the only format the Site displays.**
7. **Encoding depends on size:** images of 256 px or smaller are lossless, which keeps
   the edges of icons sharp (some are used as masks and recoloured); larger images are
   lossy at quality 85.
8. **Resized copies:** every image larger than 128 px also gets a 128 px copy
   (`<path>.128.webp`); every image larger than 512 px also gets a 512 px copy
   (`<path>.512.webp`).
9. **The Site's image component uses `srcset` and `sizes`** so the browser picks the
   128 px, 512 px or full-size file, and images load lazily.
10. **The original PNGs stay in storage** at their current paths. Link previews
    (`og:image`) point at the PNG, which every preview service accepts.
11. **Discord embeds use the 512 px copy.**
12. **Conversion is its own pipeline stage** (`apps/textures`), after the Parser writes
    textures and before the upload. It re-runs only when textures change (ADR-0016),
    and staging gets identical files.
13. **The swap gate's "every image exists" check covers the WebP copies** (ADR-0014).

### Models

14. **Model files move to the same storage, as JSON, unchanged for now**, relying on
    Cloudflare compressing JSON in transit.
15. **A binary mesh format is deferred.** It is estimated to be about half the size again and
    faster to parse, but changes both the Parser's output and the Site's 3D viewer. It
    is tracked outside the migration.

Expected effect of 8 and 9: the robots list goes from about 74 MB to about 0.2 MB; the
module list from about 32 MB to about 0.9 MB.

## Alternatives considered

- **Keep assets in a git repository.** Rejected with ADR-0009: size, and coupling
  every consumer to a checkout.
- **Backblaze B2 instead of R2.** The maintainer already uses it for backups. R2 was
  chosen because it charges nothing for downloads and sits behind the same provider
  as the Site.
- **Serve assets from the home server.** Rejected outright (decision 2).
- **Purge the cache on each change** instead of versioned addresses. Accepted as
  workable, then replaced by the marker, which needs no purge step.
- **Astro's built-in image pipeline.** Rejected: the images are not part of the Site's
  build, and the bot needs the same files.
- **AVIF**, alone or alongside WebP. Rejected: a second copy of every image and a
  `<picture>` fallback, to save a few megabytes across the whole site after WebP has
  already removed most of the weight. Discord's handling of AVIF in embeds was also
  uncertain.
- **Only a 512 px copy**, as first proposed. Rejected after measuring: most of the
  waste is on list pages drawing icons at 24 to 48 px, which a 512 px copy does not
  fix. The 128 px copy does, for 2.2 MB in total.
- **Drop the PNG originals.** Rejected: they cost 140 MB of a 10 GB allowance, are the
  safest format for link previews, and are the full-quality source.

## Consequences

- List pages become light enough for mobile connections; total stored size of
  displayed images falls from 140 MB to about 26 MB.
- An image address can be cached indefinitely and still change when the image does.
- Every image address now needs a lookup of its hash and its available copies. The
  Site's build and the bot have the database to hand. Code running in the browser
  (the robot builder and 3D viewer) does not, and needs that information shipped to
  it.
- A new stage and a new upload step exist in the pipeline.
- Game assets are now served from the project's own domain. They were already public
  in the Data repository; the attribution notice that lived there moves to this
  repository's `NOTICE` and the Site footer (ADR-0002, G-0002-2).

## Gaps and open questions

### G-0020-1. Stable names mean uploads overwrite live files

- **Kind:** decision
- **Needed by:** phase 2

With decision 3, a changed image replaces the object at the same name. The upload
happens before the swap gate has passed (ADR-0014, G-0014-1), so a candidate release
alters what production serves before it is approved, and a rollback of the database
does not roll images back: the previous database's hash would then point at bytes that
no longer exist under that name.

Naming objects by content hash (`<path>.<hash>.webp`) would fix all three: uploads
never overwrite, old and new releases each find their own files, rollback works, and
the `?v=` marker becomes unnecessary. The cost is that addresses are no longer
guessable from the path, which matters only to someone linking to an image without
the database.

### G-0020-2. Nothing deletes assets

- **Kind:** decision
- **Needed by:** after cutover

When the game removes or renames an image, its object stays in storage forever. With
the whole image set at 140 MB, that is harmless for years. With content-hashed names
(G-0020-1)
every changed image leaves its old version behind as well. A clean-up rule (delete
what no kept database refers to) can wait but should be written down as owed.

### G-0020-3. How code in the browser gets hashes and copies

- **Kind:** design
- **Needed by:** phase 4

The 3D viewer fetches model files by id at run time, and the builder shows module
images. Both need the versioned address. Either the object tables shipped to the
browser carry the hash and sizes, or a small manifest is generated at build time.
See ADR-0009, G-0009-6.

### G-0020-4. Model files: caching, compression and cross-origin access

- **Kind:** verification
- **Needed by:** phase 4 (on staging)

Three assumptions sit under decision 14, none verified
(`docs/research/external-facts.md`): that JSON served from a storage bucket through
its hostname is compressed in transit; that it is cached at Cloudflare's edge at all
(JSON is not on the default list of cached file types, so a cache rule is probably
needed); and that the browser is allowed to fetch it from a different hostname than
the Site's (ADR-0019, G-0019-5). If compression does not apply, a 9.7 MB model
downloads at full size, and pre-compressing the stored files becomes the fallback.

### G-0020-5. Details the encoding rule leaves open

- **Kind:** design
- **Needed by:** phase 2

- "256 px" and "128 px" refer to which side of a non-square image (some are 1088 by
  400, some 512 by 864)? The measurements used the longest side.
- Is the 128 px copy of a lossless image itself lossless?
- Are images scaled up if the game ships one smaller than expected? (No, presumably.)
- Which tool does the conversion in the pipeline image: ImageMagick as measured, or a
  Python library? The choice sets the encoder version.

### G-0020-6. The encoder is an input to the hash

- **Kind:** verification
- **Needed by:** phase 2

A WebP file's bytes depend on the encoder's version and settings. Upgrading the
library in the pipeline image can change every converted file's hash without any
image changing, which re-uploads everything and invalidates every cached address.
That is harmless but should be expected, and the encoder version should be visible to
the stage cache (ADR-0016, G-0016-2 and G-0016-5).

### G-0020-7. Quality was judged on one kind of image

- **Kind:** verification
- **Needed by:** phase 4

"No visible loss at quality 85" was checked on robot renders. Pilot portraits, offer
backgrounds with gradients, and faction banners with text were converted and measured
but not inspected. A visual pass over one of each on staging would confirm the setting
or show where it needs raising.

### G-0020-8. WebP in Discord embeds

- **Kind:** verification
- **Needed by:** phase 4

Decision 11 assumes Discord shows a WebP thumbnail in an embed. Believed true and not
tested. The test bot (ADR-0008) can confirm it in a minute; if it fails, embeds use the
PNG.

### G-0020-9. Upload mechanics

- **Kind:** design
- **Needed by:** phase 2

Not chosen: the upload tool; how it decides what to upload (compare hashes, or upload
everything); the content type and cache headers set on each object; and whether the
upload is a pipeline stage or part of promotion. A full upload is about 2,100 objects,
far inside the free allowance of write operations.

## References

- `docs/research/2026-10-baseline.md`, sections 4 and 5.1.
- `docs/research/external-facts.md`, "Cloudflare R2" and "Cloudflare compression".
