"""Audit step 1: resolve every macro used in the main paper (text + tables) to its printed value."""
import os, re, sys

P = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue\paper"
T = r"d:\Coding\Hackathon\GFG\ARM\ARM\research_rescue\tables"

defs = {}
for f in ("numbers.tex", "numbers_v2.tex", "numbers_v3.tex"):
    txt = open(os.path.join(P, f), encoding="utf-8").read()
    for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{((?:[^{}]|\{[^{}]*\})*)\}", txt):
        name, val = m.group(1), m.group(2)
        if name in defs:
            print("DUPLICATE", name, f)
        defs[name] = (val, f)
print("macros defined:", len(defs))

srcs = [os.path.join(P, "main.tex"), os.path.join(P, "fig_pipeline.tex")]
srcs += [os.path.join(P, "sections", s) for s in os.listdir(os.path.join(P, "sections"))]
srcs += [os.path.join(T, t) for t in ("v2_real.tex", "v3_variants.tex", "v3_value.tex")]
used = []
for s in srcs:
    txt = open(s, encoding="utf-8").read()
    for m in re.finditer(r"\\([A-Za-z]+)", txt):
        n = m.group(1)
        if n in defs and n not in used:
            used.append(n)
print("macros used in main paper:", len(used))
for n in used:
    v, f = defs[n]
    print(f"{n:28s} = {v:22s} [{f}]")
# control characters check (backslash pitfall)
for s in srcs + [os.path.join(P, f) for f in ("numbers.tex", "numbers_v2.tex", "numbers_v3.tex", "references_cited.tex", "supplementary.tex")]:
    b = open(s, "rb").read()
    bad = [c for c in b if c < 32 and c not in (9, 10, 13)]
    if bad:
        print("CONTROL CHARS in", s, set(bad))
