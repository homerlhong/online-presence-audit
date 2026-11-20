"""Weekly public-record monitor for Lichuan (Leo / Homer) Hong.

Deterministic checks only (no scraping of search engines):
  1. PubMed author search            -> new PMIDs
  2. ORCID public search             -> new ORCID records named Lichuan Hong
  3. leohong.ca robots.txt + sitemap -> crawl status / lastmod changes
  4. GitHub user homerlhong          -> new or removed public repos

If anything changed: update monitor/state.json, rewrite the AUTO section of
README.md, bump the minor version, and write monitor/changes.md for the
workflow to commit, push, and open an Issue.
"""
import json, os, re, sys, urllib.request, urllib.parse, datetime, xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "monitor", "state.json")
README = os.path.join(ROOT, "README.md")
CHANGES = os.path.join(ROOT, "monitor", "changes.md")
TODAY = datetime.date.today().isoformat()
UA = {"User-Agent": "lichuan-hong-monitor/1.0 (+https://github.com/homerlhong/online-presence-audit)"}


def get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def pubmed():
    term = '"Hong Lichuan"[Author] OR "Hong Li-chuan"[Author] OR "Lichuan H"[Author]'
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        {"db": "pubmed", "term": term, "retmax": 200, "retmode": "json"})
    ids = sorted(json.loads(get(url))["esearchresult"]["idlist"])
    titles = {}
    if ids:
        s = json.loads(get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" +
                           urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "json"})))
        for i in ids:
            d = s["result"].get(i, {})
            titles[i] = f'{d.get("pubdate", "")[:4]} · {d.get("source", "")} · {d.get("title", "")[:120]}'
    return ids, titles


def orcid():
    url = "https://pub.orcid.org/v3.0/expanded-search/?" + urllib.parse.urlencode(
        {"q": 'given-names:Lichuan AND family-name:Hong', "rows": 50})
    data = json.loads(get(url, {"Accept": "application/json"}))
    rows = data.get("expanded-result") or []
    return sorted(r["orcid-id"] for r in rows)


NAMES = ["Lichuan Hong", "Li-chuan Hong", "Leo Hong", "Homer Hong", "洪礼传"]


def openalex():
    """All academic fields: OpenAlex works whose author name matches any variant."""
    found = {}
    for n in NAMES:
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
            {"filter": f"raw_author_name.search:{n}", "per-page": 100,
             "select": "id,title,publication_year", "mailto": "audit@leohong.ca"})
        for w in json.loads(get(url)).get("results", []):
            found[w["id"].rsplit("/", 1)[-1]] = f'{n} · {w.get("publication_year")} · {(w.get("title") or "")[:110]}'
    return found


def website():
    out = {}
    try:
        robots = get("https://leohong.ca/robots.txt")
        out["robots_blocks_all"] = bool(re.search(r"(?im)^\s*Disallow:\s*/\s*$", robots))
    except Exception as e:
        out["robots_blocks_all"] = f"error: {type(e).__name__}"
    try:
        sm = ET.fromstring(get("https://leohong.ca/sitemap.xml"))
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        out["sitemap"] = {u.findtext("s:loc", namespaces=ns): u.findtext("s:lastmod", namespaces=ns)
                          for u in sm.findall("s:url", ns)}
    except Exception as e:
        out["sitemap"] = f"error: {type(e).__name__}"
    return out


def github_repos():
    h = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    repos = json.loads(get("https://api.github.com/users/homerlhong/repos?per_page=100&type=owner", h))
    return sorted(r["name"] for r in repos if not r.get("private"))


def diff_list(label, old, new):
    added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    lines = [f"- **{label}** new: `{x}`" for x in added] + [f"- **{label}** removed: `{x}`" for x in removed]
    return lines


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    new, changes, errors = {}, [], []

    for key, fn in [("pubmed", pubmed), ("openalex", openalex), ("orcid", orcid), ("website", website), ("github", github_repos)]:
        try:
            new[key] = fn()
        except Exception as e:
            errors.append(f"{key}: {type(e).__name__}: {e}")
            new[key] = state.get(key)

    if new["pubmed"] is not None and state.get("pubmed") is not None:
        old_ids = state["pubmed"][0]
        ids, titles = new["pubmed"]
        for p in sorted(set(ids) - set(old_ids)):
            changes.append(f"- **PubMed** new PMID [{p}](https://pubmed.ncbi.nlm.nih.gov/{p}/): {titles.get(p, '')} — *needs review: same Lichuan Hong?*")
        for p in sorted(set(old_ids) - set(ids)):
            changes.append(f"- **PubMed** PMID {p} no longer returned")
    if state.get("openalex") is not None and new["openalex"] is not None:
        for k in sorted(set(new["openalex"]) - set(state["openalex"])):
            changes.append(f"- **OpenAlex** new work [{k}](https://openalex.org/{k}): {new['openalex'][k]} — *needs review: same person?*")
    if state.get("orcid") is not None and new["orcid"] is not None:
        changes += diff_list("ORCID", state["orcid"], new["orcid"])
    if state.get("github") is not None and new["github"] is not None:
        changes += diff_list("GitHub repo", state["github"], new["github"])
    if state.get("website") and new["website"] and state["website"] != new["website"]:
        changes.append(f"- **leohong.ca** changed: `{json.dumps(state['website'])}` → `{json.dumps(new['website'])}`")

    first_run = not state
    json.dump({**new, "checked": TODAY}, open(STATE, "w"), indent=2, ensure_ascii=False)

    if first_run:
        print("Initialised state; no comparison on first run.")
        update_readme(new, None, [], errors)
        return
    if not changes:
        print("No changes.", "Errors: " + "; ".join(errors) if errors else "")
        return

    version = update_readme(new, state, changes, errors)
    with open(CHANGES, "w") as f:
        f.write(f"## {version} — {TODAY}\n\n" + "\n".join(changes) + "\n")
        if errors:
            f.write("\nCheck errors:\n" + "\n".join(f"- {e}" for e in errors) + "\n")
    print(open(CHANGES).read())


def update_readme(new, old, changes, errors):
    s = open(README).read()
    m = re.search(r"\*\*Version:\*\* v(\d+)\.(\d+)", s)
    major, minor = (int(m.group(1)), int(m.group(2))) if m else (2, 0)
    version = f"v{major}.{minor + 1}" if changes else f"v{major}.{minor}"
    if changes:
        s = re.sub(r"\*\*Version:\*\* v\d+\.\d+ · [^·\n]+ · [^\n]+",
                   f"**Version:** {version} · {TODAY} · auto-update", s, count=1)
        summary = "; ".join(re.sub(r"[\[\]`*]|\(http[^)]*\)", "", c[2:])[:80] for c in changes[:3])
        s = s.replace("|---|---|---|\n| v", f"|---|---|---|\n| {version} | {TODAY} | Auto: {summary} |\n| v", 1)

    ids, titles = new["pubmed"] or ([], {})
    w = new["website"] or {}
    block = [
        "<!-- AUTO:START (written by monitor/check.py — do not edit by hand) -->",
        "## Auto-monitor (weekly)",
        f"Last checked: **{TODAY}**",
        "",
        "| Source | Current |",
        "|---|---|",
        f"| PubMed (`Hong Lichuan` / `Hong Li-chuan` / `Lichuan H`) | {len(ids)} records |",
        f"| OpenAlex works, any field (Lichuan / Li-chuan / Leo / Homer Hong, 洪礼传) | {len(new.get('openalex') or {})} |",
        f"| ORCID records named Lichuan Hong | {len(new['orcid'] or [])} |",
        f"| leohong.ca robots.txt blocks all | {w.get('robots_blocks_all')} |",
        f"| leohong.ca sitemap URLs | {len(w['sitemap']) if isinstance(w.get('sitemap'), dict) else w.get('sitemap')} |",
        f"| GitHub @homerlhong public repos | {len(new['github'] or [])} |",
    ]
    if changes:
        block += ["", f"### Changes in {version}", *changes]
    if errors:
        block += ["", "Check errors: " + "; ".join(errors)]
    block.append("<!-- AUTO:END -->")
    block = "\n".join(block)
    if "<!-- AUTO:START" in s:
        s = re.sub(r"<!-- AUTO:START.*?<!-- AUTO:END -->", lambda _: block, s, flags=re.S)
    else:
        s = s.rstrip() + "\n\n" + block + "\n"
    open(README, "w").write(s)
    return version


if __name__ == "__main__":
    sys.exit(main())
