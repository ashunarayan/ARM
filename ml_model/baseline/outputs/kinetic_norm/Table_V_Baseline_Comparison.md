# Table V: Comprehensive Baseline Machine Learning Comparison

Evaluated on the held-out test set (`automation_test_track_trip_2` and `trip_3` across 1,903 spatial windows).
All models receive **kinetically normalised** inputs (az scaled by (22.22 / v)^2, floor 5 m/s), identical to the proposed model.

| Family                      | Model Architecture                   |   MAE (m/km) |   RMSE (m/km) |   Pearson r |   R2 Score |   Inference Latency (ms) |
|:----------------------------|:-------------------------------------|-------------:|--------------:|------------:|-----------:|-------------------------:|
| Linear Baselines            | Ridge Regression                     |       2.7938 |        5.7983 |      0.4724 |    -1.4118 |                   0.0005 |
| Tabular Ensembles           | Random Forest                        |       2.2089 |        3.1385 |      0.6704 |     0.2934 |                   0.0374 |
| Tabular Ensembles           | XGBoost                              |       2.1059 |        3.0221 |      0.6889 |     0.3448 |                   0.0068 |
| Tabular Ensembles           | LightGBM                             |       2.0702 |        2.9562 |      0.6982 |     0.3731 |                   0.0063 |
| Tabular Ensembles           | CatBoost                             |       2.0241 |        2.8839 |      0.7041 |     0.4034 |                   0.0089 |
| Recurrent & Sequential RNNs | 2-Layer Bi-LSTM                      |       2.3751 |        3.4648 |      0.3817 |     0.1388 |                   2.7263 |
| Recurrent & Sequential RNNs | 2-Layer GRU                          |       2.2546 |        3.4192 |      0.4256 |     0.1613 |                   1.1324 |
| Hybrid Late-Fusion          | Bi-LSTM + Context                    |       2.2983 |        3.4324 |      0.4178 |     0.1548 |                   0.6441 |
| Convolutional Networks      | Standard 1D-CNN (Uncalibrated)       |       1.7088 |        3.0981 |      0.6356 |     0.3114 |                   1.1199 |
| Convolutional Networks      | Proposed 1D-CNN + PICA (Section VII) |       1.6392 |        2.5664 |      0.7341 |     0.5275 |                   0.42   |

---
*Note: Lower MAE, RMSE and higher Pearson r, R² indicate superior regression performance. The Proposed 1D-CNN + PICA (Section VII) additionally incorporates asymmetric Huber loss and post-training isotonic regression calibration. Proposed model scores are from ablation Run 1 (iri\_v3/outputs/run\_01/test\_metrics.json).*