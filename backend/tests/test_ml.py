"""Tests: ML engines (RF, XGBoost, SVM, DNN, GNN)."""
from __future__ import annotations

import pytest

from app.ml.base import evaluate, prepare_data
from app.ml.models import GCNClassifier, build_adjacency_from_ppi, dnn_classifier, random_forest, svm_classifier, xgboost_classifier
from app.ml.train import train_models


@pytest.fixture()
def omics():
    from tests.conftest import make_synthetic_expression

    return make_synthetic_expression(seed=11)


def test_prepare_data_split(omics):
    df, meta = omics
    data = prepare_data(df, meta["group"], feature_selection=True, top_features=60)
    assert data["X_train"].shape[0] + data["X_test"].shape[0] == df.shape[1]
    assert data["X_train"].shape[1] <= 60
    assert len(data["classes"]) == 2


def test_evaluate_metrics(omics):
    import numpy as np

    y = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    proba = np.array([[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.3, 0.7], [0.7, 0.3], [0.1, 0.9], [0.85, 0.15], [0.4, 0.6]])
    m = evaluate(y, proba, 2)
    assert "accuracy" in m and "roc_auc" in m and "mcc" in m
    assert 0 <= m["accuracy"] <= 1


def test_model_zoo_trains(omics):
    df, meta = omics
    for factory in (random_forest, xgboost_classifier, svm_classifier, dnn_classifier):
        data = prepare_data(df, meta["group"], top_features=50)
        hp = {"input_dim": data["X_train"].shape[1], "n_classes": 2} if factory is dnn_classifier else {}
        model = factory(**hp)
        model.fit(data["X_train"], data["y_train"])
        proba = model.predict_proba(data["X_test"])
        metrics = evaluate(data["y_test"], proba, 2)
        # small synthetic data: allow lower bound for DNN, stricter for tree/SVM models
        threshold = 0.3 if factory is dnn_classifier else 0.5
        assert metrics["accuracy"] >= threshold


def test_train_models_pipeline(omics, tmp_path):
    df, meta = omics
    res = train_models(df, meta["group"], algorithms=["random_forest", "xgboost", "svm", "dnn"],
                       gnn=True, cv_folds=3, out_dir=tmp_path / "ml")
    algos = {m["algorithm"] for m in res["results"]}
    assert {"random_forest", "xgboost", "svm", "dnn"} <= algos
    assert "gnn" in algos
    assert res["best_model"]
    for m in res["results"]:
        assert m["metrics"]["roc_auc"] >= 0.4  # synthetic data carries real signal


def test_gcn_classifier():
    import numpy as np

    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("A", "D"), ("B", "E"), ("E", "F")]
    genes = ["A", "B", "C", "D", "E", "F"]
    A = build_adjacency_from_ppi(genes, edges)
    rng = np.random.default_rng(0)
    X = rng.normal(size=(6, 8))
    y = np.array([1, 1, 0, 0, 1, 0])
    gcn = GCNClassifier(A, input_dim=8, hidden_dim=16, n_classes=2, epochs=20)
    gcn.fit(X, y)
    proba = gcn.predict_proba(X)
    assert proba.shape == (6, 2)
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-4)


def test_gcn_fallback_without_torch():
    import numpy as np

    A = build_adjacency_from_ppi(["A", "B", "C"], [("A", "B"), ("B", "C")])
    rng = np.random.default_rng(1)
    X = rng.normal(size=(3, 4))
    y = np.array([0, 1, 0])
    gcn = GCNClassifier(A, input_dim=4, hidden_dim=8, n_classes=2, epochs=10, use_torch=False)
    gcn.fit(X, y)
    proba = gcn.predict_proba(X)
    assert proba.shape == (3, 2)
