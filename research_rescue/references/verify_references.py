"""Query Crossref for every \\bibitem of a LaTeX file and record the best match (title similarity, authors,
venue, year, volume/issue/pages, DOI). Output: references/crossref_<name>.json and a CSV summary.
Usage: python verify_references.py <path/to/main.tex> <out_name>"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def bibitems(tex: str):
    body = tex[tex.index(r"\begin{thebibliography}"):tex.index(r"\end{thebibliography}")]
    parts = re.split(r"\\bibitem\{([^}]*)\}", body)[1:]
    return [(parts[i], " ".join(parts[i + 1].split())) for i in range(0, len(parts), 2)]


def clean(s: str) -> str:
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = s.replace("~", " ").replace("``", '"').replace("''", '"').replace("\\", "")
    return re.sub(r"[{}]", "", s)


def title_of(ref: str) -> str:
    m = re.search(r'"([^"]+)"', ref)
    if m:
        return m.group(1).strip(" ,.")
    m = re.search(r"emph\{([^}]+)\}", ref)
    return m.group(1) if m else ref[:120]


def crossref(query: str, rows: int = 5):
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": query, "rows": rows})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ref-audit/1.0"}), timeout=60) as r:
                return json.load(r)["message"]["items"]
        except Exception:
            time.sleep(3 * (attempt + 1))
    return []


def summarise(it):
    a = it.get("author", [])
    return dict(doi=it.get("DOI"), title=(it.get("title") or [""])[0], container=(it.get("container-title") or [""])[0],
                year=(it.get("issued", {}).get("date-parts") or [[None]])[0][0], volume=it.get("volume"), issue=it.get("issue"),
                page=it.get("page") or it.get("article-number"),
                authors=[f"{x.get('given', '')} {x.get('family', '')}".strip() for x in a][:8], type=it.get("type"))


def main():
    tex_path, name = sys.argv[1], sys.argv[2]
    tex = open(tex_path, encoding="utf-8").read()
    out = []
    for key, raw in bibitems(tex):
        ref = clean(raw); t = title_of(ref)
        items = crossref(ref)
        best, best_sim = None, 0.0
        for it in items:
            s = summarise(it)
            sim = difflib.SequenceMatcher(None, t.lower(), s["title"].lower()).ratio()
            if sim > best_sim:
                best, best_sim = s, sim
        out.append(dict(key=key, cited=ref, cited_title=t, best_match=best, title_similarity=round(best_sim, 3)))
        print(f"[{key}] sim={best_sim:.2f} | {t[:70]} -> {(best or {}).get('title', '')[:70]} ({(best or {}).get('doi')})", flush=True)
        time.sleep(1.0)
    json.dump(out, open(os.path.join(HERE, f"crossref_{name}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
