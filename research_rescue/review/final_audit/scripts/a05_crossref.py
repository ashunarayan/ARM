"""Audit step 5: check every DOI in the cited bibliography against Crossref (title, first author, year, volume, issue,
pages/article number)."""
import json, re, time, urllib.request, urllib.parse

BIB = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue\paper\references_cited.tex"
txt = open(BIB, encoding="utf-8").read()
items = re.split(r"\\bibitem\{", txt)[1:]
for it in items:
    key = it.split("}", 1)[0]
    body = " ".join(it.split("}", 1)[1].split())
    m = re.search(r"doi: (10\.[^\s,]+?)\.?$", body) or re.search(r"doi: (10\.\S+?)[,.]?\s", body + " ")
    if not m:
        print(f"[{key}] NO DOI :: {body[:140]}")
        continue
    doi = m.group(1).rstrip(".")
    if doi.startswith("10.11583"):
        print(f"[{key}] DataCite DOI {doi} (not in Crossref) :: {body[:120]}")
        continue
    try:
        req = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi),
                                     headers={"User-Agent": "reference-audit/1.0 (mailto:noreply@example.org)"})
        w = json.load(urllib.request.urlopen(req, timeout=30))["message"]
    except Exception as e:
        print(f"[{key}] CROSSREF ERROR {doi}: {e}")
        continue
    title = (w.get("title") or [""])[0]
    au = w.get("author", [])
    first = (au[0].get("family", "") + ", " + au[0].get("given", "")) if au else "-"
    yr_print = (w.get("published-print") or w.get("published-online") or w.get("issued"))["date-parts"][0][0]
    yr_issued = w.get("issued", {}).get("date-parts", [[None]])[0][0]
    print(f"[{key}] {doi}\n   CR: {first} (+{len(au) - 1}) | {title[:110]} | {(w.get('container-title') or [''])[0][:60]} | "
          f"vol {w.get('volume')} no {w.get('issue')} pp {w.get('page')} art {w.get('article-number')} | year print/online {yr_print} issued {yr_issued}")
    print(f"   PAPER: {body[:230]}")
    time.sleep(0.3)
