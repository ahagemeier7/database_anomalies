import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from scripts.model_testing import model_testing


def test_default_dataset_is_resolved_inside_repository():
    dataset_path = model_testing.default_dataset_path()

    assert dataset_path.name == "creditcard_small.csv"
    assert dataset_path.parent.name == "startup_datasets_seed"
    assert dataset_path.is_file()


def test_cli_help_is_emitted_as_utf8():
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "0"

    completed = subprocess.run(
        [sys.executable, str(Path(model_testing.__file__)), "--help"],
        check=True,
        capture_output=True,
        env=environment,
    )

    assert "modelo híbrido" in completed.stdout.decode("utf-8")


def test_load_dataset_removes_target_and_ignored_columns(tmp_path):
    dataset_path = tmp_path / "transactions.csv"
    pd.DataFrame(
        {
            "Time": [1, 2, 3, 4],
            "V1": [0.1, 0.2, 0.3, 0.4],
            "Class": [0, 1, 0, 1],
        }
    ).to_csv(dataset_path, index=False)

    features, target = model_testing.load_dataset(
        dataset_path,
        target_column="Class",
        ignored_columns=["Time"],
    )

    assert features.columns.tolist() == ["V1"]
    assert target.tolist() == [0, 1, 0, 1]


def test_load_dataset_rejects_missing_target_column(tmp_path):
    dataset_path = tmp_path / "transactions.csv"
    pd.DataFrame({"V1": [0.1, 0.2]}).to_csv(dataset_path, index=False)

    with pytest.raises(ValueError, match="Class"):
        model_testing.load_dataset(dataset_path, target_column="Class")


def test_metrics_show_total_anomalies_detected_and_frauds_caught():
    target = pd.Series([0, 0, 1, 1, 1])
    predictions = {
        "Isolation Forest": np.array([0, 1, 1, 0, 1]),
        "Random Forest": np.array([0, 0, 1, 1, 0]),
        "Hybrid (IF + RF)": np.array([1, 1, 1, 1, 1]),
    }

    metrics = model_testing._metrics_table(target, predictions)

    assert metrics["Anomalies Detected"].tolist() == [3, 2, 5]
    assert metrics["Frauds Caught"].tolist() == [2, 2, 3]


def test_evaluation_compares_three_models_and_generates_artifacts(tmp_path):
    rng = np.random.default_rng(42)
    normal = rng.normal(loc=0.0, scale=1.0, size=(80, 3))
    fraud = rng.normal(loc=4.0, scale=1.0, size=(20, 3))
    features = pd.DataFrame(
        np.vstack([normal, fraud]),
        columns=["V1", "V2", "Amount"],
    )
    target = pd.Series([0] * len(normal) + [1] * len(fraud), name="Class")

    report = model_testing.evaluate_models(features, target, random_state=42)
    generated_files = model_testing.save_artifacts(report, tmp_path)

    assert report.metrics["Model"].tolist() == [
        "Isolation Forest",
        "Random Forest",
        "Hybrid (IF + RF)",
    ]
    assert set(report.predictions) == {
        "Isolation Forest",
        "Random Forest",
        "Hybrid (IF + RF)",
    }
    assert report.split_sizes == {"train": 60, "validation": 20, "test": 20}
    assert {path.name for path in generated_files} == {
        "metrics.csv",
        "metrics_comparison.png",
        "confusion_matrices.png",
        "evaluation_config.json",
    }
    assert all(path.is_file() and path.stat().st_size > 0 for path in generated_files)
