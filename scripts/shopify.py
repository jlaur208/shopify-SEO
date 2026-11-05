#!/usr/bin/env python3
"""Shopify Admin API helper for stores set up with a Dev Dashboard app.

Reads <SITE>_SHOPIFY_STORE, <SITE>_SHOPIFY_CLIENT_ID and
<SITE>_SHOPIFY_CLIENT_SECRET from .env, trades them for a 24-hour token
(client credentials grant) and runs a GraphQL query.

Usage:
  python3 scripts/shopify.py --site KIDS2SHOP '{ shop { name } }'
  python3 scripts/shopify.py --site KIDS2SHOP query.graphql --vars vars.json

As a module:
  from shopify import Shop
  shop = Shop("KIDS2SHOP"); data = shop.gql(query, {"id": "..."})

Stdlib only. Read-only unless the query you pass is a mutation.
"""
import argparse, json, os, sys, urllib.request, urllib.parse, urllib.error

API_VERSION = "2026-07"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_env(site):
    env = {}
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.strip()
            if line.startswith(site + "_") and "=" in line:
                k, v = line.split("=", 1)
                env[k[len(site) + 1:]] = v.strip().strip('"').strip("'")
    return env

class Shop:
    def __init__(self, site):
        env = load_env(site)
        store = env.get("SHOPIFY_STORE", "").replace("https://", "").replace(".myshopify.com", "").strip("/")
        if not store or not env.get("SHOPIFY_CLIENT_ID") or not env.get("SHOPIFY_CLIENT_SECRET"):
            sys.exit(f"{site}_SHOPIFY_STORE / CLIENT_ID / CLIENT_SECRET missing in .env")
        self.base = f"https://{store}.myshopify.com"
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": env["SHOPIFY_CLIENT_ID"],
            "client_secret": env["SHOPIFY_CLIENT_SECRET"],
        }).encode()
        self.token = self._post("/admin/oauth/access_token", body,
                                {"Content-Type": "application/x-www-form-urlencoded"})["access_token"]

    def _post(self, path, data, headers):
        req = urllib.request.Request(self.base + path, data=data,
                                     headers={"User-Agent": "Kids2-Shopify-SEO/1.0", **headers})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            sys.exit(f"HTTP {e.code} on {path}: {e.read().decode()[:500]}")

    def gql(self, query, variables=None):
        out = self._post(f"/admin/api/{API_VERSION}/graphql.json",
                         json.dumps({"query": query, "variables": variables or {}}).encode(),
                         {"Content-Type": "application/json", "X-Shopify-Access-Token": self.token})
        if out.get("errors"):
            sys.exit("GraphQL errors: " + json.dumps(out["errors"])[:1000])
        return out["data"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True, help="env prefix, e.g. KIDS2SHOP")
    ap.add_argument("query", help="GraphQL text or a path to a .graphql file")
    ap.add_argument("--vars", help="path to a JSON file of variables")
    a = ap.parse_args()
    q = open(a.query).read() if os.path.isfile(a.query) else a.query
    v = json.load(open(a.vars)) if a.vars else None
    print(json.dumps(Shop(a.site).gql(q, v), indent=2, ensure_ascii=False))
