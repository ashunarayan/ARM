"""Parse numbers.tex / numbers_v2.tex and print selected macros; also list every macro used in main.tex sections that
is undefined (would print ??)."""
import re
import sys
import glob
import os

P = sys.argv[1]  # research_rescue/paper
defs = {}
for f in ("numbers.tex", "numbers_v2.tex"):
    txt = open(os.path.join(P, f), encoding="utf-8").read()
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", txt, flags=re.M):
        val = m.group(2).replace("\\ensuremath{", "").replace("}", "").replace("{", "")
        defs[m.group(1)] = val
want = sys.argv[2].split(",") if len(sys.argv) > 2 else []
for w in want:
    print(f"{w:28s} = {defs.get(w, '<<UNDEFINED>>')}")
# undefined macro check over main sources
used = set()
for f in [os.path.join(P, "main.tex")] + glob.glob(os.path.join(P, "sections", "*.tex")) + \
         glob.glob(os.path.join(P, "..", "tables", "v2*.tex")) + [os.path.join(P, "supplementary.tex")]:
    used |= set(re.findall(r"\\([a-z][A-Za-z]+)", open(f, encoding="utf-8").read()))
cand = [u for u in used if u not in defs and re.match(r"^(vr|vv|pc|vb|el|ep|ss|sp|bg|bgc|rk|ud|bj|ar|inv|acf|inf|vs|rbv|lira|iri|sim|bng|legacy)[A-Z]", u)]
print("possibly undefined number macros:", sorted(cand))
