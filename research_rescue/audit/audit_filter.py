import os, numpy as np, tensorflow as tf
from scipy.stats import spearmanr
from sklearn.metrics import r2_score
ROOT = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model"
d = np.load(os.path.join(ROOT, "iri_v2", "output", "iri_v2_data.npz")); yte = d["y_test"]
nk = np.load(os.path.join(ROOT, "iri_v3", "outputs", "ablation_data_without_kn.npz"))
print("without-KN test labels identical:", np.allclose(nk["y_test"], yte))
for run in [1, 2, 3, 4, 5]:
    X, C = (d["x_test_raw"], d["x_test_ctx"]) if run <= 3 else (nk["x_test_raw"], nk["x_test_ctx"])
    out = []
    for s in [42, 43, 44, 45, 46]:
        m = tf.keras.models.load_model(os.path.join(ROOT, "iri_v3", "outputs", f"run_{run:02d}", f"seed_{s}", "best_model.keras"), compile=False)
        p = np.expm1(m.predict([X, C], verbose=0).ravel())
        keep = p < 40
        out.append((int((~keep).sum()), p.max(), spearmanr(p, yte)[0], r2_score(yte, p), r2_score(yte[keep], p[keep])))
    print(f"run {run}: discarded>=40 per seed={[o[0] for o in out]}, max raw pred={[round(float(o[1]),1) for o in out]}, "
          f"Spearman raw={[round(o[2],3) for o in out]}, R2 all={[round(o[3],2) for o in out]}, R2 after discard={[round(o[4],3) for o in out]}")
