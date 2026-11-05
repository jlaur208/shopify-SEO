#!/usr/bin/env python3
"""Logged-out on-page SEO audit of a site (works on Shopify, Hydrogen and WordPress).

Fetches every URL from the site's XML sitemap (or a list you pass) with no
cookies, exactly as Google sees it, and reports per URL:
status, title (+length), meta description (+length), robots, canonical,
H1 count, og:image / og:title / twitter:card, JSON-LD @types, word count,
count of href="#" links, images missing alt text (src list), and flags. Also checks duplicate titles/descriptions
across the crawl.

Usage:
  python3 scripts/audit.py https://example.com
  python3 scripts/audit.py https://example.com --urls /a/ /b/
  python3 scripts/audit.py https://example.com --json out.json

Stdlib only. Never run this from inside a logged-in browser; that is the point.
"""
import argparse, json, re, sys, html, time, urllib.request, urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, unquote

# Browser UA on purpose: SiteGround and similar hosts return 403 to unknown bot strings.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

def fetch(url, timeout=30, _tries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        # Shopify answers a fast crawl with 429; back off and retry rather than report it.
        if e.code == 429 and _tries > 1:
            time.sleep(8); return fetch(url, timeout, _tries - 1)
        return e.code, url, e.read().decode("utf-8", "replace") if e.fp else ""
    except Exception as e:
        return 0, url, str(e)

def sitemap_urls(site):
    urls = []
    for idx in ("/sitemap_index.xml", "/sitemap.xml"):
        st, _, body = fetch(site.rstrip("/") + idx)
        if st != 200 or "<loc>" not in body:
            continue
        locs = [html.unescape(l) for l in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)]
        # Shopify child sitemaps carry a query string (sitemap_pages_1.xml?from=..&to=..)
        is_map = lambda l: l.split("?")[0].endswith(".xml")
        children = [l for l in locs if is_map(l)]
        if children:
            for c in children:
                st2, _, b2 = fetch(c)
                if st2 == 200:
                    urls += [l for l in map(html.unescape, re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", b2)) if not is_map(l)]
        else:
            urls += locs
        if urls:
            break
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self._in_title = False; self._title_done = False; self._in_svg = 0
        self.desc = None; self.robots = None; self.canonical = None
        self.og = {}; self.tw = {}
        self.h1 = []; self._in_h1 = False
        self.ld = []; self._in_ld = False; self._buf = ""
        self.hash_links = 0
        self.images = 0; self.no_alt = []
        self.text = []; self._skip = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "svg": self._in_svg += 1
        # Only the first <title> outside any <svg> is the document title; SVG icons carry
        # their own <title> (Elementor's burger menu ships one) and used to be concatenated in.
        elif tag == "title" and not self._in_svg and not self._title_done: self._in_title = True
        elif tag == "meta":
            n = (a.get("name") or "").lower(); p = (a.get("property") or "").lower(); c = a.get("content")
            if n == "description": self.desc = c
            elif n == "robots": self.robots = c
            elif p.startswith("og:"): self.og[p[3:]] = c
            elif n.startswith("twitter:"): self.tw[n[8:]] = c
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical": self.canonical = a.get("href")
        elif tag == "h1": self._in_h1 = True; self.h1.append("")
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json": self._in_ld = True; self._buf = ""
            else: self._skip += 1
        elif tag == "style": self._skip += 1
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or ""
            decorative = a.get("role") == "presentation" or a.get("aria-hidden") == "true" or src.startswith("data:") or a.get("width") == "1"
            if not decorative and not self._skip:
                self.images += 1
                if not (a.get("alt") or "").strip(): self.no_alt.append(src)
        elif tag == "a" and a.get("href") in ("", "#"):
            cls = a.get("class") or ""
            # Dropdown parents and Elementor toggles legitimately use href="#"; anchors with no href at all are JS controls.
            if "elementor-item" not in cls and "toggle" not in cls and a.get("role") != "button":
                self.hash_links += 1
    def handle_endtag(self, tag):
        if tag == "svg": self._in_svg = max(0, self._in_svg - 1)
        elif tag == "title":
            if self._in_title: self._title_done = True
            self._in_title = False
        elif tag == "h1": self._in_h1 = False
        elif tag == "script":
            if self._in_ld:
                self._in_ld = False
                try:
                    j = json.loads(self._buf)
                    nodes = j if isinstance(j, list) else (j.get("@graph") or [j])
                    types = []
                    for n in nodes:
                        t = n.get("@type") if isinstance(n, dict) else None
                        types += t if isinstance(t, list) else [t]
                    self.ld.append(",".join(str(t) for t in types if t))
                except Exception: self.ld.append("parse-err")
            else: self._skip = max(0, self._skip - 1)
        elif tag == "style": self._skip = max(0, self._skip - 1)
    def handle_data(self, d):
        if self._in_title: self.title += d
        if self._in_h1: self.h1[-1] += d
        if self._in_ld: self._buf += d
        elif not self._skip: self.text.append(d)

def audit_url(url):
    st, final, body = fetch(url)
    p = Page()
    try: p.feed(body)
    except Exception: pass
    words = len(re.findall(r"\b\w+\b", " ".join(p.text)))
    rec = {
        "url": url, "status": st, "final_url": final,
        "title": html.unescape(" ".join(p.title.split())), "title_len": len(html.unescape(" ".join(p.title.split()))),
        "desc": p.desc, "desc_len": len(p.desc or ""),
        "robots": p.robots, "canonical": p.canonical,
        "h1": [h.strip() for h in p.h1], "h1_count": len(p.h1),
        "og_title": p.og.get("title"), "og_image": p.og.get("image"), "twitter_card": p.tw.get("card"),
        "schema": p.ld, "words": words, "hash_links": p.hash_links,
        "images": p.images, "images_no_alt": p.no_alt, "flags": [],
    }
    f = rec["flags"]
    if st != 200: f.append(f"status {st}")
    if not rec["title"]: f.append("no title")
    elif rec["title_len"] > 60: f.append(f"title {rec['title_len']} chars (>60)")
    elif rec["title_len"] < 30: f.append(f"title {rec['title_len']} chars (<30)")
    if not p.desc: f.append("no description")
    elif rec["desc_len"] > 160: f.append(f"description {rec['desc_len']} chars (>160)")
    elif rec["desc_len"] < 110: f.append(f"description {rec['desc_len']} chars (<110)")
    if rec["h1_count"] != 1: f.append(f"{rec['h1_count']} H1s")
    if p.robots and "noindex" in p.robots.lower(): f.append("NOINDEX")
    if p.canonical and unquote(p.canonical).rstrip("/") != unquote(final).rstrip("/"): f.append(f"canonical differs: {p.canonical}")
    if not p.canonical: f.append("no canonical")
    if not p.og.get("image"): f.append("no og:image")
    if rec["hash_links"]: f.append(f"{rec['hash_links']} href=# links")
    if p.no_alt: f.append(f"{len(p.no_alt)}/{p.images} images without alt")
    if "parse-err" in p.ld: f.append("JSON-LD parse error")
    return rec

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--urls", nargs="*", help="paths or URLs instead of the sitemap")
    ap.add_argument("--json", help="write full results to this file")
    a = ap.parse_args()
    site = a.site.rstrip("/")
    urls = [urljoin(site + "/", u) for u in a.urls] if a.urls else sitemap_urls(site)
    if not urls:
        print("No URLs found (no sitemap?). Pass --urls.", file=sys.stderr); sys.exit(1)
    results = [audit_url(u) for u in urls]
    # cross-page duplicates
    for key in ("title", "desc"):
        seen = {}
        for r in results:
            v = r.get(key)
            if v: seen.setdefault(v, []).append(r["url"])
        for v, us in seen.items():
            if len(us) > 1:
                for r in results:
                    if r.get(key) == v: r["flags"].append(f"duplicate {key} ({len(us)} pages)")
    clean = 0
    for r in results:
        mark = "OK " if not r["flags"] else "!! "
        clean += not r["flags"]
        print(f"{mark}{r['status']} {r['url']}")
        print(f"    title[{r['title_len']}]: {r['title']}")
        print(f"    desc[{r['desc_len']}]: {(r['desc'] or '')[:120]}")
        print(f"    h1={r['h1_count']} words={r['words']} images={r['images']} (no alt: {len(r['images_no_alt'])}) schema={r['schema'] or '-'} og:image={'yes' if r['og_image'] else 'NO'}")
        for fl in r["flags"]: print(f"    - {fl}")
    print(f"\n{clean}/{len(results)} clean")
    if a.json:
        with open(a.json, "w") as fh: json.dump(results, fh, indent=1)
        print(f"wrote {a.json}")

if __name__ == "__main__":
    main()
