"""Build the rescued paper's bibliography from authoritative metadata.

* Items with a DOI: metadata (authors, title, venue, year, volume, issue, pages) fetched from Crossref by DOI;
  the abstract is fetched from Semantic Scholar (when available) so that every citation can be checked against
  what the paper is cited for (see REFERENCE_AUDIT.md).
* Items without a DOI (standards, technical reports, books, web documentation): entered manually with a URL or
  publisher and marked 'manual'.
Outputs: references/references.json (metadata + abstracts), references/references.tex (IEEE-style bibitems).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

DOI_ITEMS = {
    "skar2023lira": "10.1016/j.dib.2023.109426",
    "levenberg2021lira": "10.1177/03611981211016852",
    "menegazzo2020pvs": "10.1109/sbesc51047.2020.9277846",
    "sang2024iri": "10.1109/jiot.2024.3369109",
    "bridgelall2014rif": "10.1061/(asce)is.1943-555x.0000167",
    "hanson2014iri": "10.1139/cjce-2014-0183",
    "sattar2018review": "10.3390/s18113845",
    "eriksson2008pothole": "10.1145/1378600.1378605",
    "mohan2008nericell": "10.1145/1460412.1460444",
    "jeong2020cnn": "10.1111/mice.12546",
    "opara2022roughness": "10.1109/mits.2021.3049382",
    "chou2020response": "10.1061/jpeodx.0000183",
    "gambi2019beamng": "10.1145/3338906.3338942",
    "zhang2026semisup": "10.1061/JCCEE5.CPENG-7395",
    "mounting2026": "10.1061/JCCEE5.CPENG-7202",
    "evalframework2023": "10.1080/10298436.2023.2183402",
    "speedadaptive2025": "10.3390/machines13050391",
    "rcnn2023sim": "10.3390/s23042271",
    "profilerecon2025": "10.1080/14680629.2025.2574300",
    "perttunen2011": "10.1007/978-3-642-23641-9_8",
    "thilak2021": "10.1109/csitss54238.2021.9682804",
    # revision v2 (review/first.md, s11): closest physics-based work on the same fleet and a recent KF inversion
    "skar2024inversion": "10.1061/jpeodx.pveng-1385",
    "agebjar2025fusion": "10.23919/fusion65864.2025.11123970",
    # revision v3 (INDEPENDENT_REVIEW_V3.md, D3): closest simulation-trained / real-validated work, verified 2026-10-10
    "nitsche2014wlp": "10.1061/(ASCE)CP.1943-5487.0000285",
    "ngwangwa2014exp": "10.1016/j.jterra.2014.03.002",
    "wu2023calib": "10.1080/10298436.2023.2287688",
    "jeongjo2024irinet": "10.1109/JIOT.2023.3312353",
    "peng2018dr": "10.1109/ICRA.2018.8460528",
    "chebotar2019simopt": "10.1109/ICRA.2019.8793789",
}
QUERY_ITEMS = {
    "gonzalez2008accel": "The use of vehicle acceleration measurements to estimate road roughness Gonzalez OBrien Li Cashell Vehicle System Dynamics 2008",
    "ngwangwa2010ann": "Reconstruction of road defects and road roughness classification using vehicle responses with artificial neural networks simulation Ngwangwa Heyns",
    "fieldwelsh2007": "Bootstrapping clustered data Field Welsh Journal of the Royal Statistical Society Series B 2007",
    "tobin2017dr": "Domain randomization for transferring deep neural networks from simulation to the real world Tobin 2017",
    "zhao2017freq": "IRI estimation by the frequency domain analysis of vehicle dynamic responses Zhao Nagayama",
    "trc2021crowd": "Large-scale pavement roughness measurements with vehicle crowdsourced data using semi-supervised learning",
    "menegazzo2021pvs": "Road surface type classification based on inertial sensors and machine learning comparison classical and deep Menegazzo von Wangenheim Computing",
}
MANUAL = {
    "sayers1986tp45": "M. W. Sayers, T. D. Gillespie, and C. A. V. Queiroz, \\emph{The International Road Roughness Experiment: Establishing Correlation and a Calibration Standard for Measurements}, World Bank Technical Paper No. 45, Washington, DC, 1986.",
    "sayers1986tp46": "M. W. Sayers, T. D. Gillespie, and W. D. O. Paterson, \\emph{Guidelines for Conducting and Calibrating Road Roughness Measurements}, World Bank Technical Paper No. 46, Washington, DC, 1986.",
    "astm_e1926": "ASTM International, \\emph{ASTM E1926-08(2021): Standard Practice for Computing International Roughness Index of Roads from Longitudinal Profile Measurements}, West Conshohocken, PA, 2021.",
    "iso8608": "International Organization for Standardization, \\emph{ISO 8608:2016 Mechanical Vibration -- Road Surface Profiles -- Reporting of Measured Data}, Geneva, 2016.",
    "gillespie1992": "T. D. Gillespie, \\emph{Fundamentals of Vehicle Dynamics}. Warrendale, PA: Society of Automotive Engineers, 1992.",
    "fhwa490": "U.S. Federal Highway Administration, ``National Performance Management Measures; Assessing Pavement Condition,'' 23 CFR Part 490, Subpart C, \\S\\,490.313 (IRI condition thresholds).",
    "beamng": "BeamNG GmbH, ``BeamNG.tech documentation,'' 2024. [Online]. Available: \\url{https://documentation.beamng.com/beamng_tech/}",
    "ke2017lightgbm": "G. Ke, Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, and T.-Y. Liu, ``LightGBM: A highly efficient gradient boosting decision tree,'' in \\emph{Advances in Neural Information Processing Systems 30}, 2017, pp. 3146--3154.",
    "sayers1995iri": "M. W. Sayers, ``On the calculation of International Roughness Index from longitudinal road profile,'' \\emph{Transportation Research Record}, no.~1501, pp.~1--12, 1995.",
    "holm1979": "S. Holm, ``A simple sequentially rejective multiple test procedure,'' \\emph{Scandinavian Journal of Statistics}, vol.~6, no.~2, pp.~65--70, 1979.",
    "bajic2021ml": "M. Bajic, S. M. Pour, A. Skar, M. Pettinari, E. Levenberg, and T. S. Alstr{\\o}m, ``Road roughness estimation using machine learning,'' arXiv:2107.01199, 2021.",
    "lira_data":"A. Skar \\emph{et al.}, ``Live Road Assessment Custom Dataset (LiRA-CD),'' Technical University of Denmark, data collection, 2023, CC BY 4.0, doi: 10.11583/DTU.c.6659909.",
}


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ref-audit/1.0"}), timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(3 * (k + 1))
    return None


def crossref_doi(doi):
    j = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    return j["message"] if j else None


def crossref_query(q):
    j = get("https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": q, "rows": 3}))
    return j["message"]["items"] if j else []


def s2_abstract(doi):
    j = get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi)}?fields=title,abstract,year,venue")
    time.sleep(3.5)
    return (j or {}).get("abstract")


def meta(it):
    a = it.get("author", [])
    return dict(doi=it.get("DOI"), title=(it.get("title") or [""])[0], container=(it.get("container-title") or [""])[0],
                year=(it.get("issued", {}).get("date-parts") or [[None]])[0][0], volume=it.get("volume"), issue=it.get("issue"),
                page=it.get("page") or it.get("article-number"), type=it.get("type"),
                authors=[(x.get("given", ""), x.get("family", x.get("name", ""))) for x in a])


def ieee(m):
    au = []
    for g, f in m["authors"]:
        ini = " ".join(p[0] + "." for p in g.replace("-", " ").split() if p) if g else ""
        au.append(f"{ini} {f}".strip())
    if not au:
        au_s = "[no author metadata]"
    else:
        au_s = (au[0] if len(au) == 1 else f"{au[0]} and {au[1]}" if len(au) == 2       # IEEE: no comma for two authors
                else ", ".join(au[:-1]) + ", and " + au[-1] if len(au) <= 6 else au[0] + " \\emph{et al.}")
    t = m["title"].rstrip(".")
    venue = m["container"]
    s = f"{au_s}, ``{t},'' "
    if m["type"] in ("proceedings-article", "book-chapter"):
        s += f"in \\emph{{{venue}}}, {m['year']}"
    else:
        s += f"\\emph{{{venue}}}"
        if m["volume"]:
            s += f", vol.~{m['volume']}"
        if m["issue"]:
            s += f", no.~{m['issue']}"
        s += f", {m['year']}" if not m["page"] else ""
    if m["page"]:
        pg = str(m["page"]).replace("-", "--")
        s += (f", pp.~{pg}" if "--" in pg else f", Art.~no.~{pg}")
        if m["type"] not in ("proceedings-article", "book-chapter"):
            s += f", {m['year']}"
    s += f", doi: {m['doi']}."
    return s


def main():
    out = {}
    for k, doi in DOI_ITEMS.items():
        it = crossref_doi(doi)
        if not it:
            print("FAILED", k, doi); continue
        m = meta(it); m["abstract"] = s2_abstract(m["doi"]); m["source"] = "crossref-doi"
        out[k] = m; print("ok ", k, "|", m["title"][:70], "|", m["year"], flush=True)
    for k, q in QUERY_ITEMS.items():
        items = crossref_query(q)
        if not items:
            print("NOTFOUND", k); continue
        m = meta(items[0]); m["query"] = q; m["source"] = "crossref-query (check title!)"
        m["abstract"] = s2_abstract(m["doi"]) if m["doi"] else None
        out[k] = m; print("q  ", k, "|", m["title"][:70], "|", m["year"], "|", m["doi"], flush=True)
    for k, v in MANUAL.items():
        out[k] = dict(manual=v, source="manual")
    json.dump(out, open(os.path.join(HERE, "references.json"), "w"), indent=1)
    with open(os.path.join(HERE, "references.tex"), "w", encoding="utf-8") as f:
        for k, m in out.items():
            f.write(f"\\bibitem{{{k}}}\n{m['manual'] if 'manual' in m else ieee(m)}\n\n")


if __name__ == "__main__":
    main()
