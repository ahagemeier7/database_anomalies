import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "anomaly_detector"))

from src.interference_pipeline.worker import Worker


@pytest.mark.parametrize(
    "mode, score_if, prob_rf, expected",
    [
        ("if", -0.2, None, True),
        ("if", -0.05, None, False),
        ("rf", None, 0.9, True),
        ("rf", None, 0.2, False),
        ("hybrid", -0.2, 0.3, True),
        ("hybrid", -0.2, 0.5, True),
    ],
)
def test_judge_prediction_modes(mode, score_if, prob_rf, expected):
    worker = Worker(
        target_table="test_table",
        group_id="group_test",
        columns_to_ignore=["id"],
        inference_mode=mode,
    )

    assert worker._judge_prediction(score_if=score_if, prob_rf=prob_rf) is expected
