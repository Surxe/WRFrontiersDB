# ADR-0019: Cloudflare for DNS, site hosting and the tunnel

| | |
|---|---|
| Status | Proposed |
| Decided | 2026-10-09 (DNS move, hosting move, Workers static assets, staging, deploys, cache headers, old DV address), 2026-10-10 (tunnel per environment, settings document) |
| Record state | Draft for maintainer review |
| Decided by | The maintainer. Analysis and drafting by Claude (AI assistant). |
| Related | ADR-0006 (hosting), ADR-0014 (swap gate), ADR-0018 (API), ADR-0020 (assets), ADR-0021 (URLs), ADR-0022 (secrets) |

## Context

Today (baseline, sections 5 and 6):

- The project's domain is registered at Namecheap and uses Namecheap's default
  nameservers. Its apex points at GitHub Pages.
- The Site is on GitHub Pages at that domain. The Discount Visualizer is on GitHub
  Pages at an address on GitHub's own domain, because GitHub Pages allows one site per
  repository and the two are separate repositories.
- Each site publishes a full checkout of the game data with it, which was pushing
  towards GitHub Pages' size limit.
- GitHub Pages offers no control over cache headers, no redirect rules, no password
  protection and no way to deploy a second copy for testing.
- Nothing at home can be reached from the internet (ADR-0006).

What the rework needs from a host: a place for the merged site with redirects (old
addresses must keep working, ADR-0013 and ADR-0021) and cache control; a private
staging copy (ADR-0008); storage for images and models that is not the laptop
(ADR-0020); and a way for the API at home to be reached without opening the home
network.

The maintainer also wants visitor analytics, room for more than one site, and room for
the Site to depend on the API later.

## Decision

### DNS

1. **DNS hosting for the domain moves from Namecheap to Cloudflare.** The registration
   stays at Namecheap; only the nameservers change. This is the first step of the
   hosting work, because storage domains, the tunnel and site hosting all need it.

### The site

2. **The merged Site moves from GitHub Pages to Cloudflare.**
3. **It is served as Cloudflare Workers static assets, not Cloudflare Pages**, with no
   Worker script at first. Configuration lives in the repository (`wrangler.jsonc`).
4. **Deployments are made by GitHub Actions**, running `wrangler deploy` at the release
   tag, with a Cloudflare API token limited to Workers held as a GitHub secret. A data
   release triggers the same workflow from the server with an outbound call
   (ADR-0005).
5. **Staging is a second environment of the same Worker** at a staging hostname, behind
   Cloudflare Access so that only the maintainer can open it and search engines cannot
   index it.
6. **Cloudflare Web Analytics is enabled on production.** Staging is kept out of
   production's numbers by being a separate, login-protected site.
7. **Cache rules are set with a `_headers` file in the build output**, identical for
   production and staging:
   - fingerprinted build assets (`/_astro/*`): immutable, one year;
   - HTML, and the data files pages load (ADR-0021): revalidate on every request;
   - favicon, `robots.txt`, site images: one day;
   - `/data/deploy.json`: never stored;
   - optional security headers (HSTS, `nosniff`; a content security policy later).
8. **Per-pull-request preview sites are not built now** (ADR-0004). They can be added
   later with no infrastructure change (`wrangler versions upload` with a preview
   alias).

### The old Discount Visualizer address

9. **The old address gets a "this site has moved" page, then redirects.** It is on
   GitHub's domain, so it stays on GitHub Pages. The DV repository's deployment is
   replaced by a stub (an index page and a catch-all 404 page) that shows an "update
   your bookmarks" notice, sends each old path to its new address (ADR-0021 has the
   table), redirects automatically after a few seconds, and is marked `noindex` with a
   canonical link to the new address.
10. **The stub stays up permanently.**

### The API

11. **The API at home is reached through a Cloudflare Tunnel.** A `cloudflared`
    container in each Compose stack connects out to Cloudflare; visitors reach
    Cloudflare; Cloudflare passes requests down the open connection. One tunnel, with
    its own credential, per environment (ADR-0007).

### Recording the configuration

12. **Cloudflare's dashboard settings are described in a checked-in document,
    `docs/cloudflare.md`**: DNS records, buckets and their lifecycle rules, the Access
    policy, tunnel hostnames, token names and scopes (never values). It is updated on
    every change. Managing them as code with Terraform was considered and deferred as
    a future learning project.

## Alternatives considered

- **Stay on GitHub Pages.** Free and already working. Rejected: one site per
  repository was already a conflict before the merge, and it offers none of redirects,
  cache control, a private staging copy or a place for a later API proxy.
- **Cloudflare Pages.** The closer equivalent to GitHub Pages, with built-in preview
  deployments. The maintainer leaned away from it: analytics, more than one site, and
  later dependence on the API all pointed at Workers, where a script can be added in
  front of the same assets.
- **Netlify or Vercel.** Comparable static hosting. Not chosen: Cloudflare was already
  being adopted for DNS, object storage and the tunnel, and one provider is less to
  manage.
- **Port forwarding on the home router** for the API. Rejected: it publishes the home
  address, breaks when the provider changes it, needs forwarding at two layers on this
  network, and is impossible if the provider itself uses shared addresses.
- **A remote-access mesh** for the API. It only reaches the maintainer's own devices,
  not the public.
- **Terraform for the Cloudflare configuration.** Proper infrastructure as code, with
  drift detection. Deferred by the maintainer: it is a new tool to learn for about
  fifteen to twenty settings. The checked-in document is the stopgap.
- **Leave the old DV address to break**, or redirect it instantly without a notice.
  The maintainer chose a notice first so that users learn the new address.

## Consequences

- One provider now holds DNS, the site, the images, the database archive and the API's
  front door. That is simple to operate and a single point of failure and of account
  compromise.
- Old addresses can be kept working by redirect rules generated at build time.
- A staging site exists that the public cannot see.
- The home server is reachable for the API without any inbound connection, and its
  address is not published.
- Deploying the Site depends on GitHub Actions and on a Cloudflare token stored there.
- The configuration that is not in `wrangler.jsonc` is only as accurate as
  `docs/cloudflare.md` is kept.

## Gaps and open questions

### G-0019-1. The domain has email forwarding records

- **Kind:** verification
- **Needed by:** phase 0, before the nameserver change

The domain has mail records for Namecheap's forwarding service and a matching SPF
record (baseline, section 6). Namecheap's forwarding only works while the domain uses
Namecheap's nameservers (`docs/research/external-facts.md`). If any address at the
domain forwards to the maintainer today (for example a contact address on the privacy
page, or the address a service account was registered with), it stops working the
moment the nameservers change, silently. The records may simply be Namecheap's
defaults with no address behind them. This must be checked in Namecheap's panel before
the move. If forwarding is in use, Cloudflare's own email routing is the replacement
and has to be set up as part of the move.

**Resolved 2026-10-19:** Namecheap's panel (Advanced DNS, Redirect Email) lists no
forwarder and no catch-all, so no address at the domain receives mail. No repository
under the maintainer's account, nor its history, contains an address at the domain,
and the live site publishes none. The `MX` and SPF records are Namecheap's defaults
with nothing behind them: nothing breaks when the nameservers change, and they need
not be carried over to Cloudflare. No email routing is set up.

### G-0019-2. The DNS move, step by step

- **Kind:** design
- **Needed by:** phase 0

"Nothing visible changes" holds only if every existing record is recreated at
Cloudflare before the switch. To write down first: the complete list of current
records; that the records pointing at GitHub Pages are set to "DNS only" at
Cloudflare, not proxied, for as long as GitHub serves the site (proxying can interfere
with GitHub's certificate renewal); whether DNSSEC is on at Namecheap (it must be
switched off before the move and back on after); and how to go back (restore the old
nameservers). The registration's renewal date and price are a separate reminder
already noted by the maintainer.

### G-0019-3. How the data bucket is read from GitHub Actions

- **Kind:** decision
- **Needed by:** phase 4

The Site is built in GitHub Actions from a database that lives in a private bucket
(ADR-0015). So the workflow needs a read credential for that bucket, stored as a
GitHub secret. That is one more secret outside the server (ADR-0022) and it conflicts
mildly with the spirit of "no public dataset" on a public repository's CI. The
alternative is to build on the server and hand the built files to the workflow, which
ADR-0014, G-0014-2, also raises for a different reason. One answer should settle both.

### G-0019-4. Two things can deploy the Site

- **Kind:** design
- **Needed by:** phase 4

A code release deploys the Site. A data release deploys the Site. A discount week on
the same afternoon as a release means two workflow runs that can overlap or finish out
of order, leaving the older build live. The workflow needs a concurrency rule, and the
build must always use the current deployed tag and current database, not whatever its
trigger named.

### G-0019-5. Image and model domains, and cross-origin requests

- **Kind:** design
- **Needed by:** phase 3

Images and models are served from a storage bucket through its own hostname
(ADR-0020). The hostname is not chosen. Because it differs from the Site's, the
browser's requests for model files (JSON fetched by script) are cross-origin and will
be refused unless the bucket is configured to allow the Site's origins, production and
staging. Images in `<img>` tags are not affected.

### G-0019-6. Things to confirm on staging

- **Kind:** verification
- **Needed by:** phase 4

Already listed in the decision, plus what was learned while checking the
documentation (`docs/research/external-facts.md`):

- `_headers` is honoured, and the default caching of HTML without it (`curl -I`);
- no catch-all rule exists, because overlapping rules add up, and a repeated header's
  values are joined with a comma;
- `_headers` does not apply to anything a Worker script returns, which matters the day
  a script is added for `/api/*`;
- model files are served compressed through the storage hostname;
- model files (JSON) are cached at the edge, which may need an explicit cache rule;
- the trailing-slash setting behaves as ADR-0021 expects, including for redirect
  sources (ADR-0013, G-0013-6);
- Web Analytics collects on a site served this way;
- the Access login on staging also covers the staging API hostname, if wanted.

### G-0019-7. The old DV stub and archiving

- **Kind:** verification
- **Needed by:** phase 5

The decision asks to verify that GitHub Pages keeps serving once the DV repository is
archived. There is a third-party report that it does and no official statement
(`docs/research/external-facts.md`). Since the stub is meant to stay up permanently,
the safe course is to deploy the stub, then archive, then check, and un-archive if it
stops. See ADR-0002, G-0002-5. The stub's redirect is done by script and meta refresh
on a static host, so it cannot return a real permanent-redirect status; search engines
will treat it as a soft redirect.

### G-0019-8. Account security

- **Kind:** action
- **Needed by:** phase 0

The Cloudflare account becomes able to redirect the domain, replace the site and read
the databases. Two-factor authentication on it, and on the Namecheap and GitHub
accounts, was raised early in planning and never recorded as done.

### G-0019-9. Limits to keep in view

- **Kind:** verification
- **Needed by:** phase 4

Verified limits: 20,000 files and 25 MiB per file per site version; 100 header rules;
2,000 fixed plus 100 pattern redirects; 100,000 script invocations a day on the free
plan, with static asset requests free and unlimited. The site is about 700 pages
today, far inside all of these. The one to watch is the redirect count (ADR-0013,
G-0013-2). Assumed and not verified: that the free Access plan covers a single-user
login for staging.

### G-0019-10. `www` and other names

- **Kind:** decision
- **Needed by:** phase 5

`www` currently resolves to the same site. Whether it redirects to the apex or serves
the site, and which form is canonical, is not stated. The Site's `robots.txt` is
written by hand against the old routes and there is no sitemap (baseline,
section 5.1); both need redoing for the new routes (ADR-0021).

## References

- `docs/research/2026-10-baseline.md`, sections 5 and 6.
- `docs/research/external-facts.md`, the Cloudflare and Namecheap sections.
- ADR-0021 for the redirect table used by the old DV stub.
