# Lessons

Working rules that came out of earlier sessions. Each one cost something to learn; follow them without being asked.

## Working with Jared

- One thing at a time. Report in a few lines. Bring decisions, not status lists.
- One question per turn, in plain words. Validate your own work before asking anything.
- Never give time or effort estimates in plans or reports. List the steps and do them.
- Fix clear defects without asking. Ask only about facts he alone knows.
- Never publish, merge, or make something visible without a yes. Drafts, previews, and PRs are fine.
- No em dashes anywhere, including commit messages and PR descriptions. No closers ("let me know if..."). No ranked emphasis ("most importantly").
- When asked for a named data source you cannot reach (Analytics, Semrush), ask for access. Never substitute another source and present it as the same thing.
- Report stats plainly: the figures, period over period. No "baseline", "reference month", or source labels in prose.

## Content and layout

- No AI-slop layouts: no eyebrow labels, no shouting H1, no self-describing lead paragraph, no stat tiles, no left-border accent bars on callouts. Cut words hard.
- Blog and article writing follows `templates/blog-writing-rules.md`. Source every figure before drafting. Drafts only until approved.
- Before showing a rewrite, produce a before-and-after view so the change is reviewable in one glance.

## Shopify, Hydrogen, Weaverse

- Shopify answers a fast crawl with 429. Back off and retry; do not report the 429 as a site error.
- Semrush Site Audit crawls cached HTML. Verify every flagged issue against the live page with `curl` before fixing; many are already gone or are hydration artifacts.
- Text-to-HTML ratio and "low word count" on Hydrogen pages are mostly the JSON hydration payload. Do not try to fix the ratio.
- Weaverse Studio is the only place to edit homepage and custom-page copy and button labels. Publishing there is immediate.
- Shopify `title` and `seo.title` are different fields. Setting `seo.title` is how you break title = H1 duplication without changing the visible heading.
- Save the old value in a dated JSON before every Admin API write. Store the record id, field, `old_body` and new value for each change so any write can be reversed.
- Enterprise-managed GitHub accounts cannot be invited to outside orgs. A personal account with write access is the workaround.
- Verify a code change across the whole sitemap on the Oxygen preview URL before opening the PR, not on a sample.

## Search Console

- `GSC_ACCOUNT=kidsii` switches the token file. Without it the script uses a different account's token and the property will look missing.
- "Request indexing" is not in the API. In the UI, set the inspect input with JavaScript and click with JavaScript, wait 30 to 40 seconds between steps, keep the tab in the foreground. About ten requests a day across all properties.

## Browser work

- Design and visual checks happen in real Chrome via the extension, never headless screenshots.
- Never resize the Chrome window. For a phone-width check, load the page in a 390px same-origin iframe inside the preview tab.
- The extension cannot reach incognito windows. Sign in to Shopify in the normal window.
- Clicks in a background tab die silently. Activate the tab first, screenshot, then type.
