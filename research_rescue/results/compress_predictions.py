"""Write gzip copies of the per-unit prediction files (results/predictions/*.csv -> *.csv.gz) for release.
The uncompressed CSVs (up to ~370 MB) exceed typical repository file limits and are git-ignored; pandas reads the
.csv.gz files directly (pd.read_csv('...csv.gz'))."""
import glob
import gzip
import os
import shutil

here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predictions")
for f in sorted(glob.glob(os.path.join(here, "*.csv"))):
    g = f + ".gz"
    if os.path.exists(g) and os.path.getmtime(g) >= os.path.getmtime(f):
        continue
    with open(f, "rb") as src, gzip.open(g, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1 << 20)
    print(f"{os.path.basename(g)}: {os.path.getsize(f) / 1e6:.0f} MB -> {os.path.getsize(g) / 1e6:.0f} MB")
