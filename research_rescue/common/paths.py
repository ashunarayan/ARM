"""Central path registry for the research-rescue pipeline."""
import os

RESCUE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RESCUE)

# Legacy (rejected-paper) assets — read only
BEAMNG_RAW = os.path.join(REPO, "ml_model_work", "data", "simulation", "data", "IRI_new_experiments")
LEGACY_LABEL_CODE = os.path.join(REPO, "ml_model", "iri_compliant")
LEGACY_V2_NPZ = os.path.join(REPO, "ml_model", "iri_v2", "output", "iri_v2_data.npz")
LEGACY_V3_OUT = os.path.join(REPO, "ml_model", "iri_v3", "outputs")
PVS_RAW = os.path.join(REPO, "ml_model_work", "data", "raw", "multi_class_kaggle")
PVS_LEGACY_PRED = os.path.join(REPO, "ml_model", "pvs_comparision", "output", "pvs_all_predictions.csv")

# Public data (downloaded by research_rescue/data/raw/*.py)
LIRA_RAW = os.path.join(RESCUE, "data", "raw", "lira_cd")
LIRA_CAR = os.path.join(LIRA_RAW, "car")
LIRA_REF = os.path.join(LIRA_RAW, "reference")

# Generated artefacts
PROCESSED = os.path.join(RESCUE, "data", "processed")
FIGURES = os.path.join(RESCUE, "figures")
TABLES = os.path.join(RESCUE, "tables")
RESULTS = os.path.join(RESCUE, "results")
LOGS = os.path.join(RESCUE, "logs")

for _d in (PROCESSED, FIGURES, TABLES, RESULTS, LOGS):
    os.makedirs(_d, exist_ok=True)

LIRA_ROUTES = ["CPH1", "CPH6", "M3", "M13"]
LIRA_DIRS = ["HH", "VH"]
