| dataset | source | vehicles | routes | km | units | label | label_mean |
|---|---|---|---|---|---|---|---|
| BeamNG (legacy corpus) | game-engine simulation | 3 (Hopper, Sunburst, Vivace) | 3 maps / 19 trips | 137 | 1370 segments | IRI of ray-cast elevation profile (raw / legacy-corrected) | 12.5 / 4.5 |
| LiRA-CD (urban) | real cars (Renault Zoe, AutoPi) | 8 telematics units | CPH1, CPH6 (43 passes) | 94 | 935 segments / 7729 segment-passes | P79 profilometer IRI | 3.36 |
| LiRA-CD (motorway) | real cars (Renault Zoe, AutoPi) | 6 telematics units | M13, M3 (48 passes) | 74 | 743 segments / 8564 segment-passes | P79 profilometer IRI | 1.16 |
| Sim: P79 profiles, train vehicles | parametric half-car + sensor model | 30 sampled | 4 profiles | 174 | 51618 segment-passes | IRI of driven profile | 2.38 |
| Sim: ISO-type profiles, train | parametric half-car + sensor model | 30 sampled | 40 profiles | 148 | 8792 segment-passes | IRI of driven profile | 4.97 |
| Sim: ISO-type, held-out routes & vehicles | parametric half-car + sensor model | 15 sampled | 15 profiles | 56 | 3302 segment-passes | IRI of driven profile | 5.15 |
| PVS | real cars (3 vehicles, 3 drivers) | 3 | 3 routes / 9 trips | 107 | 1070 windows / 148 GPS cells | surface type, subjective quality | - |
