| comparison | scope | files | n | pearson | bias | mae | mape | loa_low | loa_high |
|---|---|---|---|---|---|---|---|---|---|
| This implementation (0.1 m) vs P79-reported | consistent files | 7 | 1520 | 1.0 | 0.018 | 0.019 | 0.906 | -0.019 | 0.055 |
| This implementation (0.1 m) vs P79-reported | urban | 3 | 737 | 1.0 | 0.026 | 0.027 | 0.8 | -0.021 | 0.074 |
| This implementation (0.1 m) vs P79-reported | motorway | 4 | 783 | 1.0 | 0.011 | 0.011 | 1.007 | 0.0 | 0.022 |
| This implementation (0.125 m) vs P79-reported | consistent files | 7 | 1520 | 1.0 | 0.027 | 0.027 | 1.312 | -0.021 | 0.074 |
| This implementation (0.125 m) vs P79-reported | urban | 3 | 737 | 1.0 | 0.038 | 0.039 | 1.147 | -0.021 | 0.097 |
| This implementation (0.125 m) vs P79-reported | motorway | 4 | 783 | 1.0 | 0.016 | 0.016 | 1.468 | 0.002 | 0.03 |
| This implementation (0.25 m) vs P79-reported | consistent files | 7 | 1520 | 1.0 | 0.019 | 0.021 | 1.23 | -0.031 | 0.07 |
| This implementation (0.25 m) vs P79-reported | urban | 3 | 737 | 1.0 | 0.021 | 0.023 | 0.681 | -0.047 | 0.088 |
| This implementation (0.25 m) vs P79-reported | motorway | 4 | 783 | 0.999 | 0.018 | 0.019 | 1.746 | -0.008 | 0.043 |
| This implementation, no 250 mm filter vs P79-reported | consistent files | 7 | 1520 | 1.0 | 0.049 | 0.049 | 2.369 | -0.029 | 0.127 |
| This implementation, no 250 mm filter vs P79-reported | urban | 3 | 737 | 1.0 | 0.07 | 0.07 | 2.067 | -0.024 | 0.163 |
| This implementation, no 250 mm filter vs P79-reported | motorway | 4 | 783 | 1.0 | 0.029 | 0.029 | 2.653 | 0.006 | 0.052 |
| Legacy compute_iri (no correction) vs P79-reported | consistent files | 7 | 1513 | 1.0 | -0.002 | 0.014 | 0.759 | -0.05 | 0.046 |
| Legacy compute_iri (no correction) vs P79-reported | urban | 3 | 734 | 1.0 | -0.01 | 0.018 | 0.552 | -0.07 | 0.05 |
| Legacy compute_iri (no correction) vs P79-reported | motorway | 4 | 779 | 0.999 | 0.006 | 0.01 | 0.955 | -0.019 | 0.031 |
| Legacy pipeline incl. mesh correction vs P79-reported | consistent files | 7 | 1513 | 0.94 | -0.579 | 0.58 | 16.936 | -2.201 | 1.043 |
| Legacy pipeline incl. mesh correction vs P79-reported | urban | 3 | 734 | 0.877 | -1.096 | 1.096 | 28.143 | -2.931 | 0.739 |
| Legacy pipeline incl. mesh correction vs P79-reported | motorway | 4 | 779 | 0.975 | -0.092 | 0.093 | 6.377 | -0.338 | 0.153 |
| This implementation (0.1 m) vs P79-reported | all files | 8 | 1737 | 0.867 | 0.031 | 0.245 | 9.5 | -1.585 | 1.648 |
| Legacy mesh-corrected vs this implementation | all files | 8 | 1729 | 0.931 | -0.671 | 0.671 | 19.083 | -2.423 | 1.082 |
| Legacy mesh-corrected vs this implementation | urban | 4 | 950 | 0.866 | -1.136 | 1.136 | 28.825 | -3.058 | 0.787 |
| Legacy mesh-corrected vs this implementation | motorway | 4 | 779 | 0.974 | -0.104 | 0.104 | 7.202 | -0.355 | 0.148 |
| ARAN9000 vs P79 (profile) | all files | 8 | 1646 | 0.677 | 0.849 | 0.982 | 31.268 | -4.697 | 6.396 |
| ARAN9000 vs P79 (profile) | urban | 4 | 894 | 0.544 | 1.459 | 1.689 | 46.561 | -5.853 | 8.771 |
| ARAN9000 vs P79 (profile) | motorway | 4 | 752 | 0.954 | 0.124 | 0.143 | 13.087 | -0.12 | 0.368 |
