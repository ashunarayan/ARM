| Quantity | Value |
|---|---|
| **Label validity** | |
| IRI code vs P79-reported IRI (100 m, 7 consistent files) | r = 1.000, bias +0.018 m/km, MAE 0.019 m/km, n = 1,520 |
| CPH6-HH reported IRI vs its own profile (best over +/-3 km shifts, reversal) | r = 0.13 (controls 1.000) |
| Earlier mesh correction on real profiles, urban / motorway | -28 % / -6 % (bias -1.10 / -0.09 m/km) |
| ARAN9000 vs P79, urban / motorway (MAE, r) | 1.69 m/km, 0.54 / 0.14 m/km, 0.95 |
| BeamNG: summed-IRI reduction by the correction; FHWA class changes | 64 %; 34 % |
| **Earlier protocol on BeamNG (earlier labels)** | |
| Earlier recipe, earlier split (S3) / leave-one-map-out (S1), MAE | 1.67 [1.29, 2.11] / 1.99 [1.76, 2.25] m/km |
| Same, uncalibrated, leave-one-map-out (mean over seeds) | 251 m/km |
| Discard rule (> 40 m/km) on uncalibrated S3 predictions | 1-2 segments/seed removed; worst MAE 1,555 -> 1.94 m/km |
| Vehicle and map unseen (S2): constant / vibration index / LightGBM / CNN | 7.60 / 6.88 / 7.25 / 11.06 m/km |
| **Real cars, LiRA-CD, leave-one-route-out, 100 m segments** | |
| LightGBM | MAE 0.42 [0.39, 0.45] m/km, Spearman 0.95, kappa 0.91 |
| MLP (= inner-validation choice M6) | MAE 0.42 [0.40, 0.45] m/km (diff +0.00, p = 0.458) |
| 1D-CNN (earlier architecture) | MAE 0.48 [0.45, 0.51] m/km (diff +0.06, p <0.001) |
| Vibration index, alpha fitted / alpha = 2 | 0.67 / 0.73 m/km |
| Speed only / constant | 0.74 / 1.67 m/km |
| LightGBM urban routes (CPH1, CPH6) / motorways (M3, M13) | 0.60, 0.70 / 0.13, 0.15 m/km |
| Partial Spearman given speed, LightGBM vs speed-only (urban / motorway) | 0.82 / 0.80 vs 0.07 / 0.30 |
| **Simulation to real (LiRA-CD, LightGBM)** | |
| Trained only on simulated drives over measured profiles of other routes | MAE 0.44 [0.41, 0.47] m/km (paired diff to real training +0.02 m/km, p = 0.001) |
| Same, urban / motorway | 0.63 / 0.20 m/km (real training: 0.64 / 0.14) |
| Synthetic profiles only / one fixed vehicle / ideal sensor | 0.71 / 0.63 / 0.67 m/km |
| Trained on the BeamNG corpus (earlier labels / raw-profile labels) | 1.36 / 1.97 m/km |
| Real-only with 1 / 5 / 20 km / all routes | 1.41 / 0.82 / 0.46 / 0.42 m/km |
| Simulation + 1 / 5 / 20 km / all routes | 0.46 / 0.45 / 0.43 / 0.41 m/km |
| **Speed** | |
| PVS AUC asphalt vs rest: speed / earlier model / RMS/sqrt(v) | 0.97 / 0.94 / 0.99 |
| PVS AUC bad vs regular: speed / earlier model / RMS | 0.75 / 0.41 / 0.23 |
| Sweep 40->100 km/h, trained on synthetic: on synthetic / on measured (LightGBM) | +1 % (yes) / +60 % (no) |
| Sweep 40->100 km/h, trained on measured profiles (LightGBM) | -1 % (yes) |
| Kinetic normalisation (v_ref/v)^2 on synthetic / measured | -52 % / -32 % |
| Speed exponent gamma of vibration: LiRA urban / motorway / simulator | 0.60 / 0.79 / 1.20 |
| **Controlled generalisation and robustness (simulation)** | |
| Unseen vehicles, parametric: LightGBM / CNN / vibration index (relative MAE increase) | +19 % / +24 % / +15 % (criterion <= 10 %: no/no/no) |
| Unseen vehicle, BeamNG: LightGBM / CNN | +21 % / +27 % |
| Sampling rate 200 / 50 / 25 Hz (LightGBM MAE) | 0.77 / 0.87 / 1.39 m/km |
