# Kids2 Shopify SEO: operating rules

This repo is the toolkit for SEO work on the Kids2 brand sites that run on the Kids2Shop Shopify store. Read this file and `LESSONS.md` before touching a site. Jared Lauritsen owns these sites internally at Kids2 and gives approvals.

## Sites

All four are served by one Shopify store, Kids2Shop (`kids2-babyeinstein.myshopify.com`), so one Admin API app reaches all of them. Products, blogs and collections are shared across the store; check which site a record belongs to before writing.

| Site | Storefront | Search Console | Semrush project |
|---|---|---|---|
| babyeinstein.com | Hydrogen on Oxygen, Weaverse | sc-domain:babyeinstein.com | 30336930 |
| brightstarts.com | Hydrogen on Oxygen, Weaverse | sc-domain:brightstarts.com | 31868613 |
| ingenuitybaby.com | Hydrogen on Oxygen, Weaverse | sc-domain:ingenuitybaby.com | 30894648 |
| shop.kids2.com | Shopify Online Store (store primary domain) | sc-domain:shop.kids2.com | 24603101 |

Not in scope: kids2.com (WordPress on Azure), parent.com (separate store), helloeinsteinstudios.com (Squarespace).

## Local work files

`clients/` is git-ignored and stays on the machine doing the work. Keep one `clients/<site>.md` per site (access notes, scope, work log, open items) and create it at the start of the first session on that site. Backups and exports go in `clients/<site>-<topic>-<yyyy-mm>/`. Never commit store data, order exports, or backups.

## How to work

- **One item at a time.** Finish one thing, report it in a few lines, take the next. No multi-item "still open" lists. When several problems surface, name them in one line each and queue them.
- **Fix obvious defects without asking.** Broken meta, over-length titles, dead links, empty anchors, typos, http resources: fix and report. Ask only for facts only Jared or the brand team knows (whether a product exists, which collection is canonical, legal wording).
- **Never surface a finding you are not acting on.** If it is fixable, fix it in the same turn. If it has no fix, say "no action needed" in the same breath.
- **Never invent a business fact.** Every claim on a page comes from the live site, the Shopify product data, or a primary source (AAP, CPSC, a published study). If it is in none of those, ask once or leave it out.
- **Verify from outside.** Use `scripts/audit.py` or `curl` from the terminal against the live URL or the Oxygen preview URL, never a fetch from a logged-in browser tab.
- **Backup gate.** Before any Shopify data write (SEO title, description, article body, collection description), save the current values to a dated JSON file under `clients/<site>-<topic>-<yyyy-mm>/`. The log in the intake file points at each backup.
- **Code goes through PRs.** Hydrogen changes are made on a branch in the Weaverse repo, verified on the Oxygen preview deploy across the full sitemap, then opened as a PR into `main`. Never push to `main`.
- **Read before writing.** Read a script's header before running it. Admin API queries are read-only unless the GraphQL you pass is a mutation; treat every mutation as a write that needs the backup gate.

## What needs Jared's explicit yes

- Any new page, article, or collection, and anything added to navigation. Draft it, show it, get a yes.
- Setting a page or section noindex, or excluding it from the sitemap.
- Merging, deleting, or redirecting collections or products.
- Changing visible design, templates, or navigation in Weaverse Studio beyond label text.
- Rewriting an article body (show the before and after first; link and anchor repairs inside an article do not need a yes).
- Anything that goes to the Weaverse developers, the brand teams, or anyone outside the two of us.

Approval for one of these does not carry over to the next one.

## Shopify and Hydrogen specifics

- Admin API: `python3 scripts/shopify.py --site KIDS2SHOP '<graphql>'`. Credentials in `.env` from the `k2 SEO` Dev Dashboard app; one set covers all four sites. Fast crawls get 429; `audit.py` already backs off.
- The brands share the store, so one brand's blogs and collections also resolve on the other brand domains. On babyeinstein.com the Bright Starts and Ingenuity ones are noindex,follow and out of the sitemap. Never write one brand's content onto another brand's records.
- Text-to-HTML ratio warnings are inherent to Hydrogen hydration data. No action.
- Titles: on babyeinstein.com the `brandTitle` helper in the Hydrogen code appends the brand once, so the SEO title field in Shopify goes without the brand suffix. Check each other site's title output with `curl` before setting titles there.
- Weaverse Studio changes publish immediately. Verify with `curl` after publishing.
- Search Console: `GSC_ACCOUNT=kidsii python3 scripts/gsc.py perf sc-domain:<site> --days 28`. The Kids2 Google account owns all four properties.
- Hydrogen code: the Baby Einstein repo is `Weaverse/kids2-baby-einstein-hydrogen`. The Bright Starts and Ingenuity Hydrogen repos are not recorded yet; ask Jared before any code change on those sites.

## Semrush Site Audit

The Kids2 Semrush account runs a weekly Site Audit on each site in the table above. `scripts/semrush.py` reads it through the API with `SEMRUSH_API_KEY` from `.env`.

- `python3 scripts/semrush.py projects`: every project with last crawl, pages, errors, warnings.
- `python3 scripts/semrush.py issues babyeinstein.com`: errors and warnings with page counts; "+N new" marks issues that appeared since the previous crawl. Add `--notices` for notices.
- `python3 scripts/semrush.py pages babyeinstein.com <issue id>`: the URLs flagged for one issue.
- `python3 scripts/semrush.py recrawl babyeinstein.com`: start a crawl now. It uses API units; `units` shows the balance.

Checking for issues: run `issues`, take the new ones first, confirm each flagged URL with `curl` against the live page (Semrush crawls cached HTML), then fix under the rules above. The Semrush account also has kids2.com, parent.com and helloeinsteinstudios.com projects; those sites are outside this repo.

## Writing

- Articles follow `templates/blog-writing-rules.md`. No em dashes, no closers, no triplets, no label-then-list. Source every figure before writing.
- Nothing that reaches the site, the repo, or a PR mentions Claude, Anthropic, or that AI was used. No `Co-Authored-By` trailers. Search the diff for "claude" and "anthropic" before pushing.
- Commits in this repo are authored as Jared Lauritsen with his Kids2 address.

## Reporting to Jared

Lead with status (live, preview, draft; 200 or 404), one bulleted list of what changed, any single inference needing confirmation, the preview or live link, and one line naming the next item. No time estimates, ever.

## Files

- `clients/`: local work files, never committed (see Local work files).
- `scripts/audit.py`: logged-out crawl of a site's sitemap. `scripts/shopify.py`: Admin API. `scripts/gsc.py`: Search Console. `scripts/semrush.py`: Semrush Site Audit.
- `templates/blog-writing-rules.md`: article rules.
- `LESSONS.md`: things learned the hard way; read it.
- `.env`: credentials, never committed. Copy from `.env.example`.
