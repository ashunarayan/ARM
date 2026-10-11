import os, numpy as np, tensorflow as tf
ROOT = r"D:\Coding\Hackathon\GFG\ARM\ARM\ml_model"
d = np.load(os.path.join(ROOT, "iri_v2", "output", "iri_v2_data.npz"))
m = tf.keras.models.load_model(os.path.join(ROOT, "iri_v3", "outputs", "run_01", "seed_45", "best_model.keras"), compile=False)
print("params total:", m.count_params(), "trainable:", int(sum(np.prod(w.shape) for w in m.trainable_weights)))
X, C, y = d["x_test_raw"], d["x_test_ctx"], d["y_test"]
p = np.expm1(m.predict([X, C], verbose=0).ravel())
bad = np.argsort(-p)[:8]
print("top raw predictions (seed 45): pred, true, speed_kmh, speed_std, mean(az_norm)")
for i in bad:
    print(f"  {p[i]:9.1f} {y[i]:6.2f} {3.6*C[i,0]:6.1f} {C[i,1]:6.2f} {X[i,:,2].mean():8.1f}")
print("test windows with mean speed < 25 km/h:", int((3.6*C[:,0] < 25).sum()), "| train:", int((3.6*d['x_train_ctx'][:,0] < 25).sum()))
print("train mean(az_norm) range:", float(d["x_train_raw"][:,:,2].mean(1).min()), float(d["x_train_raw"][:,:,2].mean(1).max()))
