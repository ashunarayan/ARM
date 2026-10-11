# Reference audit

Method: every `\bibitem` of the submitted paper (`nish_conf_paper/main.tex`) was queried against Crossref
(`references/verify_references.py`, raw output `references/crossref_submitted.json`). Matches were compared
field by field (title, authors, venue, year, volume/issue/pages, DOI). Where the paper attributes a specific claim
or number to a source, the abstract was retrieved (Semantic Scholar / Crossref) to check that the source supports it.
Standards, reports and web documentation are not indexed by Crossref; they were checked against the issuing body.

## A. Submitted paper (26 references)

| # | Cited as | Finding | Claim check | Action in rescued paper |
|---|---|---|---|---|
| 1 | MoRTH, Basic Road Statistics of India, 2023 | Government statistics series exists; not indexed | "secondary roads surveyed once every 3-5 years" is not something this publication reports; unverifiable | removed |
| 2 | World Bank, *Road Asset Management Systems: Principles and Practice*, 2021 | No record found with this title | cited for "steep economic losses" | removed (unverifiable) |
| 3 | Sayers, Gillespie, Queiroz, World Bank TP 45, 1986 | Correct (report; not in Crossref) | IRI definition: supported | kept |
| 4 | Lane et al., IEEE Commun. Mag. 48(9):140-150, 2010 | Correct | supported | not needed |
| 5 | Mohan et al., Nericell, SenSys 2008 | Correct (doi 10.1145/1460412.1460444) | supported | kept |
| 6 | Eriksson et al., Pothole Patrol, MobiSys 2008 | Correct (doi 10.1145/1378600.1378605) | cited for RF/SVM/GBT feature pipelines: not what the paper does (it uses tuned filters/classifiers for pothole detection) | kept, cited only for crowdsourced road sensing |
| 7 | Sattar, Li, Chapman, Sensors 18(11):3845, 2018 | Correct | supported | kept |
| 8 | Alqaydi, Al-Khatib, Al-Yami, IEEE T-ITS 24(5):4812-4825, 2023 | **No such publication found** (Crossref best match is an unrelated T-ITS paper) | - | **removed** |
| R56 | AASHTO R 56-14 | Real standard (profiler certification) | used to define "accuracy tiers" for a software estimator: **not supported** by the standard | removed; not used as an accuracy framework |
| 10 | ASTM E1926 | Real standard | supported | kept (as ASTM E1926-08(2021)) |
| 11 | ISO 8608:2016 | Real standard | supported | kept |
| 12 | Mednis et al., DCOSS 2011 | Correct | supported | not needed |
| 13 | Menegazzo & von Wangenheim, SBESC 2020 | Correct | PVS-related | kept |
| 14 | Allu, Ch, R, IEEE Sensors J. 22(8):8192-8201, 2022 | **No such publication found** (closest: Opara et al., IEEE ITS Mag. 2022, different authors/title) | - | **removed** |
| 15 | BeamNG GmbH documentation | Web documentation exists | supported | kept (URL) |
| 16 | Bridgelall, J. Infrastruct. Syst. 20(4):04014017, 2014 | Real, **wrong issue/article**: 20(1):04013001, doi 10.1061/(ASCE)IS.1943-555X.0000167 | RIF: supported | kept, corrected |
| 17 | Nguyen, Widyatama, Nugraha, Sensors 19(9):2168, 2019 | **No such publication found** | - | **removed** |
| 18 | Islam, Chowdhury, Khan, Autom. Constr. 132:103935, 2021 | Real title, **wrong authors** (Arya, Maeda, Ghosh, Toshniwal, Mraz, Kashiyama, Sekimoto); image-based damage detection | cited as an IMU/single-vehicle IRI source: **not supported** | removed |
| 19 | Pawar, Vaidya, Chiddarwar, ITSC 2022, pp. 3812-3817 | **No such publication found** | - | **removed** |
| 20 | Perttunen et al., UIC 2011 | Correct | supported | not needed |
| 21 | Hanson, Cameron, Hildebrand, CJCE 41(9):819-827, 2014 | Correct | supported | kept |
| 22 | "S. M. R. Babu and S. K. S", CSITSS 2021 | Real title, **wrong authors** (Thilak, Anjaneyappa, Mehta, Pharle, Rajapur, Borah); pp. 1-7 | R^2 0.83-0.93 at 40 km/h decreasing with speed: supported by abstract | kept with correct authors |
| 23 | "Y. Chen, J. Lu, Y. Li", J. Transp. Eng. B 146(4):04020054, 2020 | Real title, **wrong authors** (Chou, Siao, Chen, Lee) and **wrong issue/article** (146(3):04020031) | "R^2 = 0.502 after aggressive band-pass filtering": **not verifiable** from the available abstract | kept only as a response-type device reference, no numbers attributed |
| 24 | "A. Al Noman, M. R. Islam, M. H. Ali", JEDT 20(6):1469-1486, 2022 | Real title, **wrong authors** (Al-Suleiman (Obaidat), Alatoom) and **wrong volume/pages** (22(4):1136-1157) | "R^2 = 0.63 relied on real-time GPS metadata": **contradicted**; 0.63 is for a pavement-deterioration regression on pavement age, traffic volume and construction quality | removed (not comparable) |
| 25 | Sang et al., IEEE IoT-J 11(14):24823-24835, 2024 | Real, **wrong issue/pages**: 11(11):19708-19720, doi 10.1109/JIOT.2024.3369109 | supported | kept, corrected |
| 26 | Gambi, Huynh, Fraser, ESEC/FSE 2019 | Correct | cited for BeamNG's soft-body vibration fidelity: **not supported** (test generation for self-driving software) | kept only for "BeamNG is used in research" |

Summary: 4 references could not be found at all ([8], [14], [17], [19]); 4 carry wrong author lists ([18], [22], [23],
[24]); 3 have wrong volume/issue/pages ([16], [23], [25]); 4 are cited for claims they do not support ([18], [24],
[26], R 56), and 2 for numbers that cannot be verified ([1], [23]).

## B. Rescued paper

All references with a DOI are generated from Crossref metadata fetched by DOI (`references/build_bib.py` ->
`references/references.json`, `references/references.tex`), so authors, venue, volume and pages are correct by
construction. Abstracts were retrieved where available and each citation in the rewritten paper was checked against
the abstract (Section C, completed after the paper rewrite). Items without DOIs (standards, World Bank reports, the
Gillespie textbook, FHWA regulation, LightGBM proceedings, arXiv preprint) are entered manually and listed as such.

The rewritten paper cites 37 references (`paper/references_cited.tex`, generated by `paper/make_bib_cited.py` in order
of first citation; it fails if a cited key has no verified entry). Three verified entries are not cited and therefore
not printed (`chou2020response`, `perttunen2011`, `profilerecon2025`).

## C. Claim check of every citation in the rewritten paper (2026-10-02)

Evidence: "abstract" = the abstract stored in `references/references.json` (Crossref/Semantic Scholar), read for this
check; "arXiv" = abstract fetched from the arXiv API; "standard/known content" = standards, reports and textbooks
whose relevant content is their defining subject (no abstract available); "title" = the claim is a paraphrase of
the title only. Verdicts: supported / supported after rewording (the sentence was changed) / title-level.

| Key | Claim in the rewritten paper | Evidence | Verdict |
|---|---|---|---|
| sayers1986tp45 | IRI is the standard roughness summary; Golden Car at 80 km/h | standard/known content (World Bank TP 45 established the IRI) | supported |
| sayers1986tp45 | simulator ranges "contain the Golden-Car reference vehicle" | known content (Golden-Car body ~1.2-1.3 Hz, damping ratio ~0.38; inside our ranges) | supported after rewording (was cited as a source of passenger-car ranges, which it is not) |
| astm_e1926 | IRI definition and computation (250 mm average, 80 km/h, 11 m initialisation) | standard | supported |
| sayers1995iri | IRI algorithm details | known content (TRR 1501) | supported |
| sattar2018review | smartphone road sensing; a review of smartphone studies | abstract (review of smartphone road-surface monitoring) | supported |
| sang2024iri | IRI from smartphone data of real vehicles with a model accounting for speed, vehicle type and mounting | abstract | supported |
| levenberg2021lira | LiRA collected CAN-bus and accelerometer data from a fleet of production cars | abstract (fleet of 400 electric cars in Copenhagen) | supported |
| sayers1986tp46 | response-type systems must be correlated with a reference profiler; response depends on vehicle and speed | known content (TP 46: calibration of response-type systems by correlation) | supported |
| thilak2021 | agreement of smartphone estimates with reference roughness depends on speed, vehicle and phone | abstract (several phones, vehicle types and speeds; reference: ROMDAS) | supported after rewording ("profiler IRI" -> "reference roughness measurements", since ROMDAS is not a profiler) |
| mounting2026 | effect of mounting | title | title-level |
| opara2022roughness | agreement improves with repeated runs | abstract (r ~0.7 single run, 0.85 with multiple sensors and rides, vs laser profilometer) | supported |
| hanson2014iri | "see also" for smartphone IRI evaluation | title | title-level (no specific claim attributed; removed from the intro sentence on mounting and speed) |
| gonzalez2008accel | model-based estimation from a specific vehicle's responses | abstract | supported |
| zhao2017freq | half-car identified from drive tests, frequency-domain IRI estimation | abstract | supported |
| bridgelall2014rif | road impact factor for connected vehicles | title + earlier audit of the paper | supported |
| eriksson2008pothole, mohan2008nericell | early crowdsourced sensing focused on event (pothole/bump) detection | abstracts | supported |
| zhang2026semisup, trc2021crowd | semi-supervised learning on unlabelled responses of public/crowdsourced vehicles | abstracts | supported |
| skar2023lira, lira_data | LiRA-CD: car data with reference survey measurements of the same roads | abstract; data set documentation | supported |
| bajic2021ml | ML pipeline predicting roughness from car vertical acceleration and speed | arXiv abstract | supported |
| evalframework2023 | evaluation framework for smartphone roughness systems | abstract | supported |
| ngwangwa2010ann | neural networks on simulated responses to reconstruct profiles and classify roughness | title | title-level |
| rcnn2023sim | roughness-grade classification from quarter-car simulations of white-noise roads | abstract | supported |
| speedadaptive2025 | speed-adaptive classifier from quarter-car simulation and real-vehicle tests | abstract | supported |
| jeong2020cnn | CNN for calibration-free roughness assessment | abstract | supported |
| gambi2019beamng | BeamNG is used in software-testing research | abstract (physically accurate crash simulations for testing self-driving software) | supported (no claim about vibration fidelity is made any more) |
| beamng | BeamNG.tech provides soft-body vehicles | vendor documentation | supported |
| tobin2017dr | domain randomisation for simulation-to-real transfer | abstract | supported |
| gillespie1992 | passenger-car ride parameter ranges | textbook content (ride frequency ~1-1.5 Hz, damping ratio 0.2-0.4, wheel hop ~10-12 Hz) | supported |
| iso8608 | synthetic profiles with displacement PSD proportional to n^-2 | standard | supported |
| menegazzo2020pvs, menegazzo2021pvs | PVS: nine trips, three vehicles/drivers, surface type and quality labels, no IRI | abstract (nine datasets) and data set documentation | supported |
| ke2017lightgbm | LightGBM | known content | supported |
| fhwa490 | FHWA IRI bands 1.50 / 2.68 m/km (95 / 170 in/mi) | regulation text (23 CFR 490.313) | supported |
| fieldwelsh2007 | cluster bootstrap | title (JRSS-B paper on bootstrapping clustered data) | supported |
| holm1979 | Holm's step-down correction | known content | supported |

Result: the only numbers attributed to sources are standard content (Golden Car at 80 km/h, the 250 mm base, the
FHWA thresholds 95/170 in/mi = 1.50/2.68 m/km); no source is cited for a claim its abstract contradicts. Three citations are title-level only (mounting2026, hanson2014iri, ngwangwa2010ann); a human
should read these papers before submission (listed in `FINAL_REPORT.md`, section J).

## D. Revision v2 (2026-10-03)

The revised paper cites 32 references (`paper/references_cited.tex`). Entries that are no longer cited because their
content moved to the supplement or was removed: `menegazzo2020pvs`, `menegazzo2021pvs` (PVS, now Supplement S2 only),
`fhwa490` (no condition bands are used), `fieldwelsh2007`, `holm1979` (inference is now by block bootstrap without
p-values), `eriksson2008pothole`, `mohan2008nericell`, `perttunen2011`, `chou2020response`, `profilerecon2025`.

| Key | Claim in the revised paper | Evidence | Verdict |
|---|---|---|---|
| skar2024inversion (new, doi 10.1061/JPEODX.PVENG-1385) | profiles inverted from the accelerations of ten nominally identical electric cars with a quarter-car model, a PID controller and nonlinear error minimisation, compared with a laser profilometer | publisher/DTU Orbit abstract (fetched 2026-10-03; Crossref has no abstract) | supported |
| skar2024inversion | "the vehicle parameters calibrated in [it] are not available to us (its open code contains only the Golden-Car parameters)" | public code repository asmusskar/RIVA: the only parameter set (`example/RIVA_insilico.m`) is K1 = 653, K2 = 63.3, C = 6, U = 0.15, i.e. the Golden Car | supported (statement limited to what is available to us) |
| agebjar2025fusion (new, doi 10.23919/FUSION65864.2025.11123970) | system identification of a production car, Kalman-filter reconstruction of the profile, IRI | abstract (230 km of real data, errors 1-10 % of reference) | supported |
| jeong2020cnn | CNNs trained on simulated responses of four vehicle types with real driving-speed profiles, validated numerically with real road IRI information | abstract | supported (wording follows the abstract; no claim of a real-vehicle test) |
| speedadaptive2025 | roughness-grade classification from simulation and a real-vehicle test, using the unsprung-mass response | abstract ("based on simulation tests of the quarter-vehicle model and real-vehicle test") | supported after rewording (v1 and the first v2 draft grouped it with simulation-only validation; corrected in the introduction and related work) |
| bajic2021ml | regressors on vertical acceleration and speed along M3, tested on the last 20 % of the same road | full text read in the first round (Greenwood profiler IRI, overlapping 100 m windows, within-road holdout) | supported |

Title-level citations that a human should still read before submission: `mounting2026`, `hanson2014iri`,
`ngwangwa2010ann` (unchanged from Section C).

## E. Revision v3 (2026-10-11)

New entries were added by DOI through `references/build_bib.py` (Crossref metadata; log `logs/build_bib_v3.log`), so
authors, venue, volume and pages are correct by construction. `paper/make_bib_cited.py` regenerates
`paper/references_cited.tex` from the keys cited in the paper (38 references in v3).

| Key | Claim in the v3 paper | Evidence | Verdict |
|---|---|---|---|
| nitsche2014wlp (doi 10.1061/(ASCE)CP.1943-5487.0000285) | regressors trained on features of simulated vehicle responses over measured road profiles, validated on a probe vehicle against an inertial profilometer, for the weighted longitudinal profile rather than IRI; "as Bajic et al. note, without the effect of varying speed" | no abstract in Crossref; secondary description in Bajic et al. (arXiv 2107.01199, full text read 2026-10-11): "A comparison of different ML models for the weighted longitudinal profile prediction, using simulated dynamic response of a vehicle traversing over a measured road profile ... tested on data recorded with a probe vehicle and a target measured using an inertial profilometer ... validated on measured data, however without including the effect of varying speed" | supported via the secondary source, and the speed statement is attributed to Bajic et al. in the text; **a human should read the primary article before submission** |
| ngwangwa2014exp (doi 10.1016/j.jterra.2014.03.002) | networks trained on simulated responses ... "then applied to experimental vehicle data"; intro: tested on real vehicles "for profile reconstruction" | title ("Reconstruction of road defects and road roughness classification using ANN simulation and vehicle dynamic responses: Application to experimental data"); Bajic et al. ref. [20] describe it as an MLP trained on the simulated response of a full vehicle model at measured road profiles and tested on data driven over discrete obstacles and Belgian paving (RMSE 15 %). Publisher full text not accessible (ScienceDirect 403) | supported at title level plus secondary description; **a human should read the primary article** |
| wu2023calib (doi 10.1080/10298436.2023.2287688) | full-car model of the test vehicle updated from a few impact tests; linear IRI-RMS relation derived by simulation over random profiles; validated on real roads | abstract (impact tests, model updating, full-car model, randomly generated profiles, linear IRI-RMS relation, validation on roads in Shanghai) | supported |
| jeongjo2024irinet (doi 10.1109/JIOT.2023.3312353) | deep IRI estimator validated on data of 29 vehicles against an inertial profiler | abstract (IRI-Net, 29 vehicles, reference IRI from an inertial profiler) | supported; cited only for real-vehicle validation (training split not characterised, as the review advised) |
| peng2018dr (doi 10.1109/ICRA.2018.8460528) | randomising the simulator dynamics is a standard device for simulation-to-real transfer | abstract | supported |
| chebotar2019simopt (doi 10.1109/ICRA.2019.8793789) | adapting the randomisation with a few real roll-outs | abstract ("adapt the simulation parameter distribution using a few real world roll-outs") | supported |
| skar2023lira (existing) | telematics unit "fixed to the frame in the middle console, close to the front axle" | full text (Europe PMC PMC10375556, read 2026-10-11): "The AutoPi units were physically fixed to the frame in the middle of the GM car close to the front axle"; Fig. 5 caption: "the location of the AutoPi telematics unit inside the middle console" | supported |
| lira_data (existing, dataset) | P79 surveys in September 2020 (CPH1, M3, M13) and June 2020 (CPH6); car passes on these routes November 2020 to August 2021, two to fifteen months later; ARAN dates in Table S13 | dataset readme files `data/raw/lira_cd/reference/readme.txt` (P79 10-09-2020 for CPH1, M3, M13; 04-06-2020 for CPH6; ARAN 12-08-2020 CPH1, 13-08-2020 M3 and M13, 30-08-2021 CPH6) and `data/raw/lira_cd/car/readme.txt` (task dates 03-11-2020 to 27-08-2021; 1.8 to 14.8 months after the survey of the same route) | supported (v2 said "two to fourteen months"; corrected) |
| bajic2021ml (existing) | Table S10 caption: "a different reference survey and processing (a profiler operated by the Danish Road Directorate, IRI per 10 m averaged over overlapping 100 m windows)" | full text (first round); replaces v2's unverified "different profiler" | supported |

Considered and not cited: Shangguan et al. 2025 (J. Comput. Civ. Eng. 39(6), doi 10.1061/JCCEE5.CPENG-6782; CNN with
signal decomposition predicting pavement roughness from connected-car data). The review asked to cite it only if it
uses LiRA-CD. Crossref (queried 2026-10-11) has no abstract; its 46 references include Bajic et al. 2021 but not the
LiRA-CD data article, so its data source could not be established and it is not cited. A human with access to the
full text should check whether it uses LiRA data; if so, it belongs in Related Work next to Bajic et al.

Title-level or secondary-source citations that a human should read before submission: `mounting2026`,
`hanson2014iri`, `ngwangwa2010ann`, `ngwangwa2014exp`, `nitsche2014wlp`.

## F. Final audit (2026-10-11)

All 29 DOIs of the cited bibliography were checked against Crossref (title, venue, volume, issue, pages / article
number): all match. Wu et al. 2023 is vol. 25 (print 2024, issued online 2023); cited as 2023, which matches Crossref's
`issued` date.

Primary-source checks of the two citations the final audit marked unverified:

| Key | Source read | What it supports | Change to the text |
|---|---|---|---|
| `ngwangwa2014exp` | Accepted manuscript, University of Pretoria repository (handle 2263/46320, `Ngwangwa_Reconstruction_2014.pdf`), abstract and introduction | Land Rover Defender 110 driven over discrete obstacles and Belgian paving; training data "numerically generated by making minor adjustments to the real measured profiles and applying them to a full vehicle model of the Land Rover"; a static feed-forward network is "trained and consequently tested on the real measured data"; road profiles reconstructed, roughness assessed via displacement spectral densities | Related Work: "then, trained on a full-vehicle model driven over slightly modified measured profiles, applied to the measured responses of that vehicle". Introduction ("tested on real vehicles ... for profile reconstruction") supported as is. |
| `nitsche2014wlp` | Abstract on the AIT publication page (full text paywalled, not read) | MLP, SVM and random forest; inputs from accelerometer and wheel-speed signals; trained on features of vehicle response simulations "on accurate replications of roads"; validated with probe-vehicle measurements; target weighted longitudinal profile; SVM best | The abstract does not state that the simulated roads were measured profiles, that the reference was an inertial profilometer, or that speed was not varied. These three details come from Bajic et al. (full text, arXiv:2107.01199: "simulated dynamic response of a vehicle traversing over a measured road profile", "a target measured using an inertial profilometer", "without including the effect of varying speed") and are now attributed to them in Related Work. |

Still secondary or title-level: the full text of Nitsche et al. 2014, and `mounting2026`, `hanson2014iri`,
`ngwangwa2010ann` (not re-checked in this round).
