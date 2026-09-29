"""Compare the anomaly-detection models without starting the Docker stack."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


MODEL_NAMES = (
    "Isolation Forest",
    "Random Forest",
    "Hybrid (IF + RF)",
)


@dataclass(frozen=True)
class EvaluationReport:
    """Results needed by both the terminal summary and generated artifacts."""

    metrics: pd.DataFrame
    predictions: dict[str, np.ndarray]
    y_test: pd.Series
    thresholds: dict[str, float]
    split_sizes: dict[str, int]
    random_state: int


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_dataset_path() -> Path:
    return repository_root() / "scripts" / "startup_datasets_seed" / "creditcard_small.csv"


def default_output_path() -> Path:
    return repository_root() / "artifacts" / "model_testing"


def load_dataset(
    dataset_path: str | Path,
    target_column: str = "Class",
    ignored_columns: Sequence[str] = ("Time",),
) -> tuple[pd.DataFrame, pd.Series]:
    """Load and validate a numeric, binary classification dataset."""

    path = Path(dataset_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")

    dataset = pd.read_csv(path)
    if target_column not in dataset.columns:
        raise ValueError(f"Coluna alvo '{target_column}' não encontrada em {path.name}.")

    target = pd.to_numeric(dataset[target_column], errors="raise").astype(int)
    target_values = set(target.unique().tolist())
    if target_values != {0, 1}:
        raise ValueError(
            f"A coluna alvo '{target_column}' deve conter exatamente as classes 0 e 1. "
            f"Valores encontrados: {sorted(target_values)}"
        )

    columns_to_drop = [target_column, *ignored_columns]
    features = dataset.drop(columns=columns_to_drop, errors="ignore")
    if features.empty:
        raise ValueError("O dataset não possui colunas de entrada após as exclusões.")

    try:
        features = features.apply(pd.to_numeric, errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError("Todas as colunas de entrada precisam ser numéricas.") from exc

    if not np.isfinite(features.to_numpy(dtype=float)).all():
        raise ValueError("As colunas de entrada não podem conter valores ausentes ou infinitos.")

    return features, target


def _best_rf_threshold(probabilities: np.ndarray, target: pd.Series) -> float:
    candidates = np.linspace(0.1, 0.9, 81)
    return float(
        max(
            candidates,
            key=lambda threshold: f1_score(
                target,
                (probabilities >= threshold).astype(int),
                zero_division=0,
            ),
        )
    )


def _hybrid_predictions(
    rf_probabilities: np.ndarray,
    if_scores: np.ndarray,
    rf_high: float,
    rf_moderate: float,
    if_combined: float,
    if_standalone: float,
) -> np.ndarray:
    predictions = np.zeros(len(rf_probabilities), dtype=int)
    high_confidence = rf_probabilities >= rf_high
    moderate_confidence = (rf_probabilities >= rf_moderate) & (rf_probabilities < rf_high)
    combined_anomaly = if_scores < if_combined
    standalone_anomaly = if_scores < if_standalone

    predictions[high_confidence] = 1
    predictions[(moderate_confidence & combined_anomaly) | standalone_anomaly] = 1
    return predictions


def _best_hybrid_thresholds(
    rf_probabilities: np.ndarray,
    if_scores: np.ndarray,
    target: pd.Series,
) -> tuple[float, float, float, float]:
    best_f1 = -1.0
    best_config = (0.85, 0.4, -0.15, -0.1)
    rf_high_candidates = np.linspace(0.4, max(0.7, float(rf_probabilities.max())), 12)
    rf_moderate_candidates = np.linspace(0.1, 0.4, 7)
    if_combined_candidates = np.linspace(
        float(if_scores.min()),
        min(-0.001, float(if_scores.max())),
        7,
    )
    if_standalone_candidates = np.linspace(
        float(if_scores.min()),
        min(-0.001, float(if_scores.max())),
        7,
    )

    for rf_high in rf_high_candidates:
        for rf_moderate in rf_moderate_candidates:
            if rf_moderate >= rf_high:
                continue
            for if_combined in if_combined_candidates:
                for if_standalone in if_standalone_candidates:
                    predictions = _hybrid_predictions(
                        rf_probabilities,
                        if_scores,
                        float(rf_high),
                        float(rf_moderate),
                        float(if_combined),
                        float(if_standalone),
                    )
                    score = f1_score(target, predictions, zero_division=0)
                    if score > best_f1:
                        best_f1 = score
                        best_config = (
                            float(rf_high),
                            float(rf_moderate),
                            float(if_combined),
                            float(if_standalone),
                        )

    return best_config


def _metrics_table(
    target: pd.Series,
    predictions: dict[str, np.ndarray],
) -> pd.DataFrame:
    rows = []
    for model_name in MODEL_NAMES:
        model_predictions = predictions[model_name]
        tn, fp, fn, tp = confusion_matrix(
            target,
            model_predictions,
            labels=[0, 1],
        ).ravel()
        rows.append(
            {
                "Model": model_name,
                "Precision": precision_score(target, model_predictions, zero_division=0),
                "Recall": recall_score(target, model_predictions, zero_division=0),
                "F1-Score": f1_score(target, model_predictions, zero_division=0),
                "Anomalies Detected": int(tp + fp),
                "Frauds Caught": int(tp),
                "TP": int(tp),
                "FP": int(fp),
                "FN": int(fn),
                "TN": int(tn),
            }
        )
    return pd.DataFrame(rows)


def evaluate_models(
    features: pd.DataFrame,
    target: pd.Series,
    random_state: int = 42,
) -> EvaluationReport:
    """Train, tune on validation data, and compare all models on held-out data."""

    train_full_x, test_x, train_full_y, test_y = train_test_split(
        features,
        target,
        test_size=0.2,
        stratify=target,
        random_state=random_state,
    )
    train_x, validation_x, train_y, validation_y = train_test_split(
        train_full_x,
        train_full_y,
        test_size=0.25,
        stratify=train_full_y,
        random_state=random_state,
    )

    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train_x)
    validation_scaled = scaler.transform(validation_x)
    test_scaled = scaler.transform(test_x)

    contamination = min(0.5, max(0.01, float(train_y.mean())))
    isolation_forest = IsolationForest(
        contamination=contamination,
        n_estimators=200,
        n_jobs=1,
        random_state=random_state,
    )
    isolation_forest.fit(train_scaled)

    random_forest = RandomForestClassifier(
        n_estimators=150,
        class_weight="balanced",
        max_depth=12,
        min_samples_leaf=2,
        n_jobs=1,
        random_state=random_state,
    )
    random_forest.fit(train_scaled, train_y)

    fraud_class_index = list(random_forest.classes_).index(1)
    rf_validation_probabilities = random_forest.predict_proba(validation_scaled)[
        :, fraud_class_index
    ]
    rf_test_probabilities = random_forest.predict_proba(test_scaled)[:, fraud_class_index]
    if_validation_scores = isolation_forest.decision_function(validation_scaled)
    if_test_scores = isolation_forest.decision_function(test_scaled)

    rf_threshold = _best_rf_threshold(rf_validation_probabilities, validation_y)
    rf_high, rf_moderate, if_combined, if_standalone = _best_hybrid_thresholds(
        rf_validation_probabilities,
        if_validation_scores,
        validation_y,
    )

    predictions = {
        "Isolation Forest": np.where(isolation_forest.predict(test_scaled) == -1, 1, 0),
        "Random Forest": (rf_test_probabilities >= rf_threshold).astype(int),
        "Hybrid (IF + RF)": _hybrid_predictions(
            rf_test_probabilities,
            if_test_scores,
            rf_high,
            rf_moderate,
            if_combined,
            if_standalone,
        ),
    }

    return EvaluationReport(
        metrics=_metrics_table(test_y, predictions),
        predictions=predictions,
        y_test=test_y.reset_index(drop=True),
        thresholds={
            "rf": rf_threshold,
            "rf_high": rf_high,
            "rf_moderate": rf_moderate,
            "if_combined": if_combined,
            "if_standalone": if_standalone,
        },
        split_sizes={
            "train": len(train_x),
            "validation": len(validation_x),
            "test": len(test_x),
        },
        random_state=random_state,
    )


def save_artifacts(report: EvaluationReport, output_path: str | Path) -> list[Path]:
    """Save machine-readable metrics and publication-ready comparison charts."""

    destination = Path(output_path).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    metrics_path = destination / "metrics.csv"
    metrics_chart_path = destination / "metrics_comparison.png"
    confusion_chart_path = destination / "confusion_matrices.png"
    config_path = destination / "evaluation_config.json"

    report.metrics.to_csv(metrics_path, index=False)

    chart_data = report.metrics.melt(
        id_vars="Model",
        value_vars=["Precision", "Recall", "F1-Score"],
        var_name="Metric",
        value_name="Score",
    )
    figure, axis = plt.subplots(figsize=(10, 6))
    sns.barplot(data=chart_data, x="Model", y="Score", hue="Metric", ax=axis)
    axis.set(title="Comparação dos modelos", xlabel="Modelo", ylabel="Score", ylim=(0, 1))
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(metrics_chart_path, dpi=160)
    plt.close(figure)

    figure, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for axis, model_name in zip(axes, MODEL_NAMES):
        matrix = confusion_matrix(
            report.y_test,
            report.predictions[model_name],
            labels=[0, 1],
        )
        sns.heatmap(
            matrix,
            annot=True,
            fmt="d",
            cmap="Blues",
            cbar=False,
            xticklabels=["Normal", "Fraude"],
            yticklabels=["Normal", "Fraude"],
            ax=axis,
        )
        axis.set(title=model_name, xlabel="Predição", ylabel="Valor real")
    figure.tight_layout()
    figure.savefig(confusion_chart_path, dpi=160)
    plt.close(figure)

    config_path.write_text(
        json.dumps(
            {
                "random_state": report.random_state,
                "split_sizes": report.split_sizes,
                "thresholds": report.thresholds,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return [metrics_path, metrics_chart_path, confusion_chart_path, config_path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compara Isolation Forest, Random Forest e o modelo híbrido "
            "sem iniciar Docker, bancos ou aplicação web."
        )
    )
    parser.add_argument("--dataset", type=Path, default=default_dataset_path())
    parser.add_argument("--target-column", default="Class")
    parser.add_argument("--ignore-columns", nargs="*", default=["Time"])
    parser.add_argument("--output-dir", type=Path, default=default_output_path())
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(arguments: Sequence[str] | None = None) -> int:
    _configure_utf8_console()
    args = build_parser().parse_args(arguments)
    features, target = load_dataset(
        args.dataset,
        target_column=args.target_column,
        ignored_columns=args.ignore_columns,
    )
    report = evaluate_models(features, target, random_state=args.seed)
    generated_files = save_artifacts(report, args.output_dir)

    print(f"Dataset: {Path(args.dataset).resolve()}")
    print(f"Registros: {len(features)} | Fraudes: {int(target.sum())}")
    print(
        "Divisão: "
        f"treino={report.split_sizes['train']}, "
        f"validação={report.split_sizes['validation']}, "
        f"teste={report.split_sizes['test']}"
    )
    print("\nComparação no conjunto de teste:")
    print(report.metrics.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print("\nArquivos gerados:")
    for path in generated_files:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
