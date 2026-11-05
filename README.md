# Kids2 Shopify SEO

Instructions and scripts for making SEO changes on the Kids2 brand sites on the Kids2Shop Shopify store: babyeinstein.com, brightstarts.com, ingenuitybaby.com and shop.kids2.com. Built to be driven by Claude Code (or any agent that reads `AGENTS.md`). The rules the agent follows are in `CLAUDE.md`. Work files and logs stay local in `clients/`, which git ignores.

## Set up on a new machine

1. Clone this repo. Python 3 is the only requirement; the scripts use the standard library.
2. Copy `.env.example` to `.env`. Get the `k2 SEO` Shopify app client ID and secret and the Kids2 Semrush API key (Semrush, Subscription info, API units) from Jared and paste them in. Never commit `.env`.
3. Search Console: get `gsc-oauth-client.json` from Jared, put it in the repo root, then run
   ```
   GSC_ACCOUNT=kidsii python3 scripts/gsc.py login
   ```
   and sign in as the Kids2 account that owns the properties.
4. Verify access:
   ```
   python3 scripts/shopify.py --site KIDS2SHOP '{ shop { name } }'
   GSC_ACCOUNT=kidsii python3 scripts/gsc.py sites
   python3 scripts/audit.py https://www.babyeinstein.com --urls / /collections/all
   python3 scripts/semrush.py projects
   ```
5. For code changes, clone the Hydrogen repo into `site-code/babyeinstein` (git-ignored) with write access from Weaverse:
   ```
   git clone https://github.com/Weaverse/kids2-baby-einstein-hydrogen.git site-code/babyeinstein
   ```
6. Install the Claude in Chrome extension if you will do Weaverse Studio or Search Console UI work.

## Starting a session

Open Claude Code in this folder. It reads `CLAUDE.md` automatically. Say which site and what you want worked on, for example "check Semrush for new issues on brightstarts.com", and it will continue from there. Every session ends with a line appended to that site's local log in `clients/<site>.md`.
