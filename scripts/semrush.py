#!/usr/bin/env python3
"""Semrush Site Audit from the terminal. No pip packages.

Reads SEMRUSH_API_KEY from .env in the repo root (Kids2 Semrush account, Projects API).
Every call uses API units; `units` shows the balance.

Commands:
  python3 scripts/semrush.py units
  python3 scripts/semrush.py projects                      # Site Audit status for every Kids2 project
  python3 scripts/semrush.py issues babyeinstein.com       # errors and warnings with page counts, new since last crawl marked
  python3 scripts/semrush.py issues babyeinstein.com --notices
  python3 scripts/semrush.py pages babyeinstein.com 213    # URLs flagged for one issue id
  python3 scripts/semrush.py recrawl babyeinstein.com      # start a new crawl now

A site can be given as its domain (or part of it) or its Semrush project id.
Semrush crawls cached HTML: confirm each flagged URL with curl before fixing (see LESSONS.md).
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.semrush.com"


def key():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip().startswith("SEMRUSH_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    if os.environ.get("SEMRUSH_API_KEY"):
        return os.environ["SEMRUSH_API_KEY"]
    sys.exit("SEMRUSH_API_KEY missing in .env")


def get(path, method="GET", **params):
    params["key"] = key()
    url = (path if path.startswith("http") else API + path) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"Semrush {e.code}: {e.read().decode()[:300]}")
    try:
        return json.loads(body)
    except ValueError:
        return body.strip()


def projects():
    return [p for p in get("/management/v1/projects")]


def find(site):
    ps = projects()
    for p in ps:
        if str(p["project_id"]) == site:
            return p
    hits = [p for p in ps if site.lower() in p["url"].lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"No Semrush project matches {site}. Run `projects`.")
    exact = [p for p in hits if p["url"].lower().removeprefix("www.") == site.lower().removeprefix("www.")]
    if len(exact) == 1:
        return exact[0]
    sys.exit(f"{site} matches several projects: " + ", ".join(p["url"] for p in hits))


def audit(pid):
    return get(f"/reports/v1/projects/{pid}/siteaudit/info")


def when(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M") if ms else "-"


def cmd_projects():
    print(f"{'project':>9}  {'site':32} {'status':9} {'last crawl':16} {'pages':>6} {'errors':>6} {'warn':>6}")
    for p in projects():
        a = audit(p["project_id"])
        if not isinstance(a, dict) or "status" not in a:
            print(f"{p['project_id']:>9}  {p['url']:32} no Site Audit")
            continue
        print(f"{p['project_id']:>9}  {p['url']:32} {a['status']:9} {when(a.get('last_audit')):16} "
              f"{a.get('pages_crawled', 0):>6} {a.get('errors', 0):>6} {a.get('warnings', 0):>6}")


def cmd_issues(site, notices=False):
    p = find(site)
    a = audit(p["project_id"])
    snap = a["current_snapshot"]
    names = {i["id"]: i["title"] for i in get(f"/reports/v1/projects/{p['project_id']}/siteaudit/meta/issues")["issues"]}
    print(f"{p['url']}  crawl {when(a.get('last_audit'))}  pages {a.get('pages_crawled')}  snapshot {snap['snapshot_id']}")
    groups = [("error", snap["errors"]), ("warning", snap["warnings"])]
    if notices:
        groups.append(("notice", snap["notices"]))
    for label, items in groups:
        for i in sorted((i for i in items if i["count"]), key=lambda i: -i["count"]):
            new = f"  +{i['new_count']} new" if i.get("new_count") else ""
            print(f"{label:8} {i['id']:>4}  {i['count']:>5}  {names.get(i['id'], '?')}{new}")


def cmd_pages(site, issue, limit=500):
    p = find(site)
    snap = audit(p["project_id"])["current_snapshot"]["snapshot_id"]
    page = 1
    while True:
        d = get(f"/reports/v1/projects/{p['project_id']}/siteaudit/snapshot/{snap}/issue/{issue}", page=page, limit=100)
        for row in d.get("data", []):
            print(row.get("source_url") or row.get("url"), row.get("target_url", ""))
        if page * 100 >= min(d.get("total", 0), limit):
            break
        page += 1


def cmd_recrawl(site):
    p = find(site)
    print(get(f"/reports/v1/projects/{p['project_id']}/siteaudit/launch", method="POST"))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        sys.exit(__doc__)
    c = a[0]
    if c == "units":
        print(get("https://www.semrush.com/users/countapiunits.html"))
    elif c == "projects":
        cmd_projects()
    elif c == "issues" and len(a) >= 2:
        cmd_issues(a[1], "--notices" in a)
    elif c == "pages" and len(a) >= 3:
        cmd_pages(a[1], a[2])
    elif c == "recrawl" and len(a) >= 2:
        cmd_recrawl(a[1])
    else:
        sys.exit(__doc__)
