#!/usr/bin/env python3
"""Google Search Console from the terminal. No pip packages.

Two ways to authenticate. OAuth as the Google account that owns the properties is preferred: one login
covers every property that account can see. A service account needs to be added as a
user on each property.

OAuth setup (once, Jared does this):
  1. console.cloud.google.com -> project -> APIs & Services -> Enable "Google Search Console API".
  2. OAuth consent screen: Internal if the account is on Google Workspace; otherwise External
     and then "Publish app" so refresh tokens do not expire after 7 days.
  3. Credentials -> Create credentials -> OAuth client ID -> Desktop app. Download the JSON and
     save it as gsc-oauth-client.json in the project root (git-ignored).
  4. python3 scripts/gsc.py login   -> opens a browser; approve as that account.
     The refresh token is stored in .gsc-token.json (git-ignored).

Service account setup (alternative, once per Google Cloud project):
  1. console.cloud.google.com -> create or pick a project -> APIs & Services -> Enable
     "Google Search Console API".
  2. IAM & Admin -> Service Accounts -> Create. No roles needed. Keys -> Add key -> JSON.
     Save the file as gsc-service-account.json in the project root (git-ignored).
  3. In Search Console, open the property -> Settings -> Users and permissions -> Add user:
     the service account's email (client_email in the JSON), permission "Full".
     Only an Owner of the property can add users.

Commands:
  python3 scripts/gsc.py login                                        # OAuth, once
  python3 scripts/gsc.py sites
  python3 scripts/gsc.py inspect https://example.com/ https://example.com/page/
  python3 scripts/gsc.py sitemaps https://example.com/                 # list
  python3 scripts/gsc.py sitemaps https://example.com/ --submit sitemap_index.xml
  python3 scripts/gsc.py perf https://example.com/ --days 28 [--by page|query|date] [--filter-page /collections/] [--start YYYY-MM-DD --end YYYY-MM-DD]

Property URLs must match Search Console exactly: "https://example.com/" for a URL-prefix
property, "sc-domain:example.com" for a domain property.

"Request indexing" is not available through the API for ordinary pages; do that in the
Search Console UI (URL inspection -> Request indexing).
"""
import argparse, base64, json, os, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse, datetime, webbrowser, secrets
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPE = "https://www.googleapis.com/auth/webmasters https://www.googleapis.com/auth/analytics.readonly"

def b64url(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def load_key():
    path = os.environ.get("GSC_SERVICE_ACCOUNT_JSON")
    if not path:
        envp = os.path.join(ROOT, ".env")
        if os.path.exists(envp):
            for line in open(envp):
                if line.startswith("GSC_SERVICE_ACCOUNT_JSON="): path = line.split("=", 1)[1].strip()
    path = path or "./gsc-service-account.json"
    if not os.path.isabs(path): path = os.path.join(ROOT, path)
    if not os.path.exists(path):
        sys.exit(f"Service account key not found at {path}. See the setup notes at the top of scripts/gsc.py.")
    return json.load(open(path))

OAUTH_CLIENT = os.path.join(ROOT, "gsc-oauth-client.json")
# GSC_ACCOUNT=<name> switches to .gsc-token-<name>.json so a second Google account
# can be logged in alongside the first one.
_acct = os.environ.get("GSC_ACCOUNT", "").strip()
TOKEN_FILE = os.path.join(ROOT, f".gsc-token-{_acct}.json" if _acct else ".gsc-token.json")

def oauth_client():
    j = json.load(open(OAUTH_CLIENT))
    return j.get("installed") or j.get("web") or j

def oauth_login():
    if not os.path.exists(OAUTH_CLIENT):
        sys.exit(f"OAuth client JSON not found at {OAUTH_CLIENT}. See the setup notes at the top of scripts/gsc.py.")
    c = oauth_client()
    state = secrets.token_urlsafe(16)
    got = {}
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
            self.wfile.write(b"<p style='font-family:sans-serif'>Search Console and Analytics access granted. You can close this tab.</p>")
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    redirect = f"http://127.0.0.1:{srv.server_port}/"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Opening browser for Google sign-in. Approve as the Google account that owns the Search Console properties.")
    print("If no browser opens, visit:\n" + url)
    webbrowser.open(url)
    while "code" not in got and "error" not in got: srv.handle_request()
    if got.get("error"): sys.exit("Sign-in failed: " + got["error"])
    if got.get("state") != state: sys.exit("State mismatch; try again.")
    data = urllib.parse.urlencode({"code": got["code"], "client_id": c["client_id"], "client_secret": c["client_secret"],
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen(urllib.request.Request(c["token_uri"], data=data, method="POST"), timeout=30) as r:
        tok = json.loads(r.read())
    if "refresh_token" not in tok: sys.exit("No refresh token returned. Remove the app's access at myaccount.google.com/permissions and run login again.")
    json.dump({"refresh_token": tok["refresh_token"]}, open(TOKEN_FILE, "w")); os.chmod(TOKEN_FILE, 0o600)
    print(f"Saved refresh token to {TOKEN_FILE}. Run: python3 scripts/gsc.py sites")

def oauth_access_token():
    c = oauth_client(); rt = json.load(open(TOKEN_FILE))["refresh_token"]
    data = urllib.parse.urlencode({"refresh_token": rt, "client_id": c["client_id"], "client_secret": c["client_secret"], "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(c["token_uri"], data=data, method="POST"), timeout=30) as r:
            return json.loads(r.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Refresh failed ({e.code}): {e.read().decode()[:200]}\nRun: python3 scripts/gsc.py login")

def access_token():
    if os.path.exists(OAUTH_CLIENT) and os.path.exists(TOKEN_FILE):
        return oauth_access_token()
    if os.path.exists(OAUTH_CLIENT):
        sys.exit("OAuth client found but not logged in. Run: python3 scripts/gsc.py login")
    key = load_key()
    now = int(time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64url(json.dumps({"iss": key["client_email"], "scope": SCOPE, "aud": key["token_uri"], "iat": now, "exp": now + 3600}).encode())
    signing_input = f"{header}.{claims}".encode()
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(key["private_key"]); pem = f.name
    try:
        sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", pem], input=signing_input, capture_output=True, check=True).stdout
    finally:
        os.unlink(pem)
    jwt = f"{header}.{claims}.{b64url(sig)}"
    data = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}).encode()
    req = urllib.request.Request(key["token_uri"], data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Token exchange failed: {e.code} {e.read().decode()[:300]}")

def call(token, method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode(); return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:400]
        if e.code == 403 and "permission" in msg.lower():
            msg += "\n-> The service account is not a user on this property, or the property URL does not match exactly."
        sys.exit(f"{method} {url}\n{e.code} {msg}")

def enc(site): return urllib.parse.quote(site, safe="")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("sites")
    s = sub.add_parser("inspect"); s.add_argument("site"); s.add_argument("urls", nargs="+")
    s = sub.add_parser("sitemaps"); s.add_argument("site"); s.add_argument("--submit", help="sitemap path or URL to submit")
    s = sub.add_parser("perf"); s.add_argument("site"); s.add_argument("--days", type=int, default=28); s.add_argument("--by", choices=["page", "query", "date"], default="page"); s.add_argument("--filter-page"); s.add_argument("--limit", type=int, default=25); s.add_argument("--start"); s.add_argument("--end")
    a = ap.parse_args()
    if a.cmd == "login":
        oauth_login(); return
    tok = access_token()

    if a.cmd == "sites":
        r = call(tok, "GET", "https://www.googleapis.com/webmasters/v3/sites")
        for s in r.get("siteEntry", []): print(f"{s['permissionLevel']:<22} {s['siteUrl']}")
        if not r.get("siteEntry"): print("No properties. Add the service account email as a user on the property in Search Console.")
    elif a.cmd == "inspect":
        for u in a.urls:
            r = call(tok, "POST", "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", {"inspectionUrl": u, "siteUrl": a.site})
            idx = r.get("inspectionResult", {}).get("indexStatusResult", {})
            print(f"{u}\n  verdict={idx.get('verdict')} coverage={idx.get('coverageState')} lastCrawl={idx.get('lastCrawlTime')} robots={idx.get('robotsTxtState')} indexing={idx.get('indexingState')}\n  googleCanonical={idx.get('googleCanonical')} userCanonical={idx.get('userCanonical')}")
    elif a.cmd == "sitemaps":
        base = f"https://www.googleapis.com/webmasters/v3/sites/{enc(a.site)}/sitemaps"
        if a.submit:
            feed = a.submit if a.submit.startswith("http") else a.site.rstrip("/") + "/" + a.submit.lstrip("/")
            call(tok, "PUT", f"{base}/{enc(feed)}"); print("submitted", feed)
        r = call(tok, "GET", base)
        for s in r.get("sitemap", []):
            print(f"{s['path']}\n  submitted={s.get('lastSubmitted')} downloaded={s.get('lastDownloaded')} pending={s.get('isPending')} errors={s.get('errors')} warnings={s.get('warnings')} urls={sum(int(c.get('submitted',0)) for c in s.get('contents',[]))}")
    elif a.cmd == "perf":
        end = datetime.date.fromisoformat(a.end) if a.end else datetime.date.today() - datetime.timedelta(days=2)
        start = datetime.date.fromisoformat(a.start) if a.start else end - datetime.timedelta(days=a.days)
        body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": [a.by], "rowLimit": a.limit}
        if a.filter_page:
            body["dimensionFilterGroups"] = [{"filters": [{"dimension": "page", "operator": "contains", "expression": a.filter_page}]}]
        r = call(tok, "POST", f"https://www.googleapis.com/webmasters/v3/sites/{enc(a.site)}/searchAnalytics/query", body)
        rows = r.get("rows", [])
        print(f"{start} to {end}  ({a.by})")
        print(f"{'clicks':>7} {'impr':>7} {'ctr':>6} {'pos':>5}  {a.by}")
        for row in rows:
            print(f"{row['clicks']:>7.0f} {row['impressions']:>7.0f} {row['ctr']*100:>5.1f}% {row['position']:>5.1f}  {row['keys'][0]}")
        if not rows: print("no rows")

if __name__ == "__main__":
    main()
