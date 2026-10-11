"""Write results/key_metrics.md (the metrics section of FINAL_REPORT.md) from results/paper_numbers.json, so that the
report quotes exactly the numbers the paper quotes."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common.paths import RESULTS  # noqa: E402

N = json.load(open(os.path.join(RESULTS, "paper_numbers.json")))
g = lambda k: N.get(k, "??")
ci = lambda k: f"{g(k)} [{g(k + 'Lo')}, {g(k + 'Hi')}]"

ROWS = [
    ("Label validity", [
        ("IRI code vs P79-reported IRI (100 m, 7 consistent files)", f"r = {g('iriValR')}, bias {g('iriValBias')} m/km, MAE {g('iriValMae')} m/km, n = {g('iriValN')}"),
        ("CPH6-HH reported IRI vs its own profile (best over +/-3 km shifts, reversal)", f"r = {g('alignBestR')} (controls {g('alignControlR')})"),
        ("Earlier mesh correction on real profiles, urban / motorway", f"-{g('legacyCorrUrbanMape')} % / -{g('legacyCorrMotorwayMape')} % (bias {g('legacyCorrUrbanBias')} / {g('legacyCorrMotorwayBias')} m/km)"),
        ("ARAN9000 vs P79, urban / motorway (MAE, r)", f"{g('aranUrbanMae')} m/km, {g('aranUrbanR')} / {g('aranMotorwayMae')} m/km, {g('aranMotorwayR')}"),
        ("BeamNG: summed-IRI reduction by the correction; FHWA class changes", f"{g('bngCorrReduction')} %; {g('bngClassChange')} %"),
    ]),
    ("Earlier protocol on BeamNG (earlier labels)", [
        ("Earlier recipe, earlier split (S3) / leave-one-map-out (S1), MAE", f"{ci('bngSthreeLegacyMae')} / {ci('bngSoneLegacyMae')} m/km"),
        ("Same, uncalibrated, leave-one-map-out (mean over seeds)", f"{g('bngSoneLegacyUncalMae')} m/km"),
        ("Discard rule (> 40 m/km) on uncalibrated S3 predictions", f"{g('discardMinN')}-{g('discardMaxN')} segments/seed removed; worst MAE {g('discardMaxUnfiltered')} -> {g('discardMaxFiltered')} m/km"),
        ("Vehicle and map unseen (S2): constant / vibration index / LightGBM / CNN", f"{g('bngStwoConstMae')} / {g('bngStwoPhysMae')} / {g('bngStwoGbmMae')} / {g('bngStwoCnnMae')} m/km"),
    ]),
    ("Real cars, LiRA-CD, leave-one-route-out, 100 m segments", [
        ("LightGBM", f"MAE {ci('liraGbmMae')} m/km, Spearman {g('liraGbmRho')}, kappa {g('liraGbmKappa')}"),
        ("MLP (= inner-validation choice M6)", f"MAE {ci('liraMlpMae')} m/km (diff {g('liraMlpDmae')}, p = {g('liraMlpP')})"),
        ("1D-CNN (earlier architecture)", f"MAE {ci('liraCnnMae')} m/km (diff {g('liraCnnDmae')}, p {g('liraCnnP')})"),
        ("Vibration index, alpha fitted / alpha = 2", f"{g('liraPhysCMae')} / {g('liraPhysDMae')} m/km"),
        ("Speed only / constant", f"{g('liraSpeedMae')} / {g('liraConstMae')} m/km"),
        ("LightGBM urban routes (CPH1, CPH6) / motorways (M3, M13)", f"{g('liraGbmMaeCphOne')}, {g('liraGbmMaeCphSix')} / {g('liraGbmMaeMwThree')}, {g('liraGbmMaeMwThirteen')} m/km"),
        ("Partial Spearman given speed, LightGBM vs speed-only (urban / motorway)", f"{g('liraGbmPartialUrban')} / {g('liraGbmPartialMotorway')} vs {g('liraSpeedPartialUrban')} / {g('liraSpeedPartialMotorway')}"),
    ]),
    ("Simulation to real (LiRA-CD, LightGBM)", [
        ("Trained only on simulated drives over measured profiles of other routes", f"MAE {ci('zsPsevenGbmMae')} m/km (paired diff to real training {g('zsPsevenGbmDmae')} m/km, p = {g('zsPsevenGbmP')})"),
        ("Same, urban / motorway", f"{g('zsPsevenGbmMaeUrban')} / {g('zsPsevenGbmMaeMotorway')} m/km (real training: {g('liraGbmMaeUrban')} / {g('liraGbmMaeMotorway')})"),
        ("Synthetic profiles only / one fixed vehicle / ideal sensor", f"{g('zsIsoGbmMae')} / {g('zsFixVehGbmMae')} / {g('zsIdealGbmMae')} m/km"),
        ("Trained on the BeamNG corpus (earlier labels / raw-profile labels)", f"{g('zsBngCorrGbmMae')} / {g('zsBngRawGbmMae')} m/km"),
        ("Real-only with 1 / 5 / 20 km / all routes", f"{g('fsRealGbmOne')} / {g('fsRealGbmFive')} / {g('fsRealGbmTwenty')} / {g('fsRealGbmAll')} m/km"),
        ("Simulation + 1 / 5 / 20 km / all routes", f"{g('fsSimRealGbmOne')} / {g('fsSimRealGbmFive')} / {g('fsSimRealGbmTwenty')} / {g('fsSimRealGbmAll')} m/km"),
    ]),
    ("Speed", [
        ("PVS AUC asphalt vs rest: speed / earlier model / RMS/sqrt(v)", f"{g('pvsSurfSpeed')} / {g('pvsSurfModel')} / {g('pvsSurfRmsV')}"),
        ("PVS AUC bad vs regular: speed / earlier model / RMS", f"{g('pvsBadSpeed')} / {g('pvsBadModel')} / {g('pvsBadRms')}"),
        ("Sweep 40->100 km/h, trained on synthetic: on synthetic / on measured (LightGBM)", f"{g('spIsoGbm')} % ({g('spIsoGbmPass')}) / {g('spPsevenGbm')} % ({g('spPsevenGbmPass')})"),
        ("Sweep 40->100 km/h, trained on measured profiles (LightGBM)", f"{g('spPtrainPsevenGbm')} % ({g('spPtrainPsevenGbmPass')})"),
        ("Kinetic normalisation (v_ref/v)^2 on synthetic / measured", f"{g('spIsoPhysD')} % / {g('spPsevenPhysD')} %"),
        ("Speed exponent gamma of vibration: LiRA urban / motorway / simulator", f"{g('gammaLiraUrban')} / {g('gammaLiraMw')} / {g('gammaSim')}"),
    ]),
    ("Controlled generalisation and robustness (simulation)", [
        ("Unseen vehicles, parametric: LightGBM / CNN / vibration index (relative MAE increase)", f"{g('uvGbmRel')} % / {g('uvCnnRel')} % / {g('uvPhysRel')} % (criterion <= 10 %: {g('uvGbmPass')}/{g('uvCnnPass')}/{g('uvPhysPass')})"),
        ("Unseen vehicle, BeamNG: LightGBM / CNN", f"{g('bngVehGbmRel')} % / {g('bngVehCnnRel')} %"),
        ("Sampling rate 200 / 50 / 25 Hz (LightGBM MAE)", f"{g('rbGbmRateTwoHundred')} / {g('rbGbmRateFifty')} / {g('rbGbmRateTwentyFive')} m/km"),
    ]),
]


def posthoc_block():
    """Post-hoc sensor sensitivity analysis (results/lira/zeroshot_sensor_*), if it has been run."""
    import pandas as pd
    p = os.path.join(RESULTS, "lira", "zeroshot_sensor_segment_metrics.csv")
    if not os.path.exists(p):
        return ""
    d = pd.read_csv(p)
    rows = ["Post-hoc sensitivity analysis (added after all primary results; reported, not used for the primary claims):",
            "zero-shot LightGBM and vibration index trained on simulated drives over measured profiles with",
            "`p79` = the primary sensor mixture (telematics 55-62 Hz / smartphone-like, 50/50),",
            "`p79-measuredsensor` = only a telematics sensor matched to the measured LiRA-CD statistics,",
            "`p79-measuredmix` = the matched telematics sensor mixed 50/50 with the primary smartphone-like sensor.",
            "Paired differences to `p79` LightGBM on the same 1,678 segments.", "",
            "| Simulation set / estimator | MAE [95 % CI] | Spearman | paired diff to p79 LightGBM [95 % CI] |",
            "|---|---|---|---|"]
    for _, r in d.iterrows():
        p = "< 0.001" if r.p_holm < 0.0005 else f"= {r.p_holm:.3f}"      # bootstrap p = 0 means below 1/B
        diff = "ref." if r.model == r.reference else f"{r.dmae_vs_ref:+.3f} [{r.dmae_lo:+.3f}, {r.dmae_hi:+.3f}], p_Holm {p}"
        rows.append(f"| {r.model} | {r.mae:.3f} [{r.mae_lo:.3f}, {r.mae_hi:.3f}] | {r.spearman:.3f} | {diff} |")
    return "\n".join(rows) + "\n"


def splice(path, tag, content):
    if not os.path.exists(path):
        return
    s = open(path, encoding="utf-8").read()
    a, b = f"<!-- BEGIN {tag} -->", f"<!-- END {tag} -->"
    if a in s and b in s:
        s = s[:s.index(a) + len(a)] + "\n" + content + s[s.index(b):]
        open(path, "w", encoding="utf-8").write(s)


def main():
    out = ["| Quantity | Value |", "|---|---|"]
    for sec, rows in ROWS:
        out.append(f"| **{sec}** | |")
        out += [f"| {a} | {b} |" for a, b in rows]
    txt = "\n".join(out) + "\n"
    missing = [l for l in out if "??" in l]
    open(os.path.join(RESULTS, "key_metrics.md"), "w", encoding="utf-8").write(txt)
    report = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FINAL_REPORT.md")
    splice(report, "KEY METRICS", txt)
    splice(report, "POSTHOC", posthoc_block())
    print(txt)
    print("missing:", len(missing))


if __name__ == "__main__":
    main()
