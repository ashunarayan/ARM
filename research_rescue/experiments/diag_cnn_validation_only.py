"""Diagnostic (training-domain data only; no test-map data is loaded into any model):
checks whether the CNN fits training and inner-validation data comparably to LightGBM for BeamNG S1 folds."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import models as M
from experiments.exp_beamng import load, sub
meta, D = load()
for ylab in ["iri_raw", "iri_corr"]:
    for test_map in ["automation_test_track", "east_coast_usa", "west_coast_usa"]:
        tr = np.where((meta["map"] != test_map) & ~meta.is_val_trip)[0]
        va = np.where((meta["map"] != test_map) & meta.is_val_trip)[0]
        y = meta[ylab].to_numpy(); g = meta.cluster.to_numpy()
        fit = np.concatenate([tr, va]); Dfit = sub(D, fit, y, g); Dva = sub(D, va, y, g); Dtr = sub(D, tr, y, g)
        cnn = M.TorchModel("cnn", seeds=(0, 1)).fit(Dfit, val_idx=np.arange(len(tr), len(fit)))
        gbm = M.GBM().fit(Dtr)
        r = lambda m, DD: np.mean(np.abs(m.predict(DD) - DD["y"]))
        print(f"{ylab:8s} excl.{test_map:22s} CNN train MAE {r(cnn, Dtr):6.2f} val MAE {r(cnn, Dva):6.2f} | GBM(train only) val MAE {r(gbm, Dva):6.2f} | val label mean {Dva['y'].mean():.2f}", flush=True)
