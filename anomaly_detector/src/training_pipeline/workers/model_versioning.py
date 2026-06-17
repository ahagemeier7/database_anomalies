import glob
import logging
import os
import re
from typing import Dict, Optional
from sklearn.feature_extraction import DictVectorizer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

import joblib


def get_next_model_version(target_table: str, models_dir: str) -> int:
    pattern = os.path.join(models_dir, f"{target_table}_v*_translator.pkl")
    versions = []
    for path in glob.glob(pattern):
        match = re.search(rf"{re.escape(target_table)}_v(\d+)_translator\.pkl$", os.path.basename(path))
        if match:
            versions.append(int(match.group(1)))

    return max(versions, default=0) + 1


def build_model_paths(target_table: str, models_dir: str, version: int) -> Dict[str, str]:
    version_tag = f"v{version:03d}"
    return {
        "translator": os.path.join(models_dir, f"{target_table}_{version_tag}_translator.pkl"),
        "if_model": os.path.join(models_dir, f"{target_table}_{version_tag}_if_model.pkl"),
        "scaler": os.path.join(models_dir, f"{target_table}_{version_tag}_scaler.pkl"),
        "rf_model": os.path.join(models_dir, f"{target_table}_{version_tag}_rf_model.pkl"),
        "latest_translator": os.path.join(models_dir, f"{target_table}_translator.pkl"),
        "latest_if_model": os.path.join(models_dir, f"{target_table}_if_model.pkl"),
        "latest_scaler": os.path.join(models_dir, f"{target_table}_scaler.pkl"),
        "latest_rf_model": os.path.join(models_dir, f"{target_table}_rf_model.pkl"),
    }


def save_versioned_models(
    target_table: str,
    models_dir: str,
    translator: DictVectorizer,
    isolation_forest: IsolationForest,
    scaler: StandardScaler,
    rf_model: Optional[RandomForestClassifier] = None,
) -> Dict[str, str]:
    os.makedirs(models_dir, exist_ok=True)
    version = get_next_model_version(target_table, models_dir)
    paths = build_model_paths(target_table, models_dir, version)

    joblib.dump(translator, paths["translator"])
    joblib.dump(translator, paths["latest_translator"])

    joblib.dump(isolation_forest, paths["if_model"])
    joblib.dump(isolation_forest, paths["latest_if_model"])

    joblib.dump(scaler, paths["scaler"])
    joblib.dump(scaler, paths["latest_scaler"])

    if rf_model is not None:
        joblib.dump(rf_model, paths["rf_model"])
        joblib.dump(rf_model, paths["latest_rf_model"])

    logging.info(
        "Saved version %s for table '%s' in %s",
        f"v{version:03d}",
        target_table,
        models_dir,
    )

    return paths
