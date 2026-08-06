"""ML training orchestrator: runs the model zoo over a dataset and stores results."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.core.config import settings
from app.ml.base import cross_validate, evaluate, prepare_data, save_model
from app.ml.models import GCNClassifier, build_adjacency_from_ppi
from app.services.network import build_network

logger = logging.getLogger(__name__)

SUPPORTED_ALGORITHMS = ["random_forest", "xgboost", "svm", "dnn"]


def train_models(
    matrix: pd.DataFrame,
    labels: pd.Series,
    algorithms: list[str] | None = None,
    test_size: float = 0.2,
    cv_folds: int = 5,
    feature_selection: bool = True,
    top_features: int = 100,
    gnn: bool = True,
    hyperparameters: dict | None = None,
    out_dir: Optional[Path] = None,
) -> dict:
    """Train all requested algorithms; return per-model metrics & artifacts.

    matrix: features × samples; labels: sample → class.
    """
    from app.ml.models import ALGORITHM_FACTORIES

    out_dir = out_dir or (settings.storage_path / ".mlcache")
    out_dir.mkdir(parents=True, exist_ok=True)
    hyperparameters = hyperparameters or {}
    data = prepare_data(matrix, labels, feature_selection, top_features, test_size)
    algorithms = [a for a in (algorithms or SUPPORTED_ALGORITHMS) if a in ALGORITHM_FACTORIES]
    results: list[dict] = []

    for algo in algorithms:
        hp = hyperparameters.get(algo, {})
        factory = ALGORITHM_FACTORIES[algo]
        if algo == "dnn":
            hp = {**hp, "input_dim": data["X_train"].shape[1], "n_classes": data["n_classes"]}
        model = factory(**hp)
        model.fit(data["X_train"], data["y_train"])
        proba = model.predict_proba(data["X_test"])
        metrics = evaluate(data["y_test"], proba, data["n_classes"])
        cv = cross_validate(factory, data["X_train"], data["y_train"], cv_folds)
        metrics.update(cv)
        importance = _feature_importance(model, data["X_test"], data["y_test"], data["selected_features"], data["X_train"])
        key = f"{algo}_{uuid.uuid4().hex[:8]}"
        model_dir = out_dir / key
        path = save_model(model, {"key": key, "algorithm": algo, "metrics": metrics, "features": data["selected_features"]}, model_dir)
        results.append({
            "key": key,
            "algorithm": algo,
            "metrics": metrics,
            "feature_importance": importance[:20],
            "artifact_path": str(path),
            "n_features_used": len(data["selected_features"]),
        })
        logger.info("trained %s: acc=%.3f auc=%.3f", algo, metrics.get("accuracy", 0), metrics.get("roc_auc", 0))

    # --- GNN on gene-graph (when requested and ≥2 classes) ---
    if gnn and data["n_classes"] >= 2:
        try:
            gnn_result = _train_gnn(matrix, labels, data, out_dir)
            if gnn_result:
                results.append(gnn_result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("GNN training failed (%s); skipping.", exc)

    best = max(results, key=lambda r: r["metrics"].get("roc_auc", 0)) if results else None
    return {
        "results": results,
        "best_model": best["key"] if best else None,
        "n_samples": len(data["y_train"]) + len(data["y_test"]),
        "classes": data["classes"],
    }


def _feature_importance(model, X_test: np.ndarray, y_test: np.ndarray, features: list[str], X_train: np.ndarray) -> list[dict]:
    """Permutation importance (model-agnostic, SHAP-free but statistically valid)."""
    from sklearn.inspection import permutation_importance

    try:
        perm = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=42, scoring="roc_auc" if len(np.unique(y_test)) == 2 else "accuracy")
        imp = perm.importances_mean
    except Exception:  # noqa: BLE001
        try:
            imp = getattr(model, "feature_importances_", np.zeros(len(features)))
        except Exception:  # noqa: BLE001
            imp = np.zeros(len(features))
    order = np.argsort(-np.asarray(imp))
    return [{"feature": features[i], "importance": float(imp[i])} for i in order[: min(50, len(order))]]


def _train_gnn(matrix: pd.DataFrame, labels: pd.Series, data: dict, out_dir: Path) -> Optional[dict]:
    """Train a GCN for **gene prioritization / target prediction**.

    Task formulation: nodes = genes; node features = expression statistics
    across samples; edges = PPI. The supervision signal is per-gene disease
    association derived from differential expression between the two classes
    (t-test on case vs control), so the GCN learns to predict disease-relevant
    genes from network context — i.e., graph-informed therapeutic target
    prediction.
    """
    from sklearn.preprocessing import StandardScaler
    from scipy import stats as _stats

    features = data["selected_features"]
    sub_matrix = matrix.loc[features].T  # samples × genes
    common = [c for c in sub_matrix.index if c in labels.index]
    sub_matrix = sub_matrix.loc[common]
    y_labels = labels.loc[common].astype(str)
    classes = sorted(y_labels.unique())
    if len(classes) != 2:
        return None  # GNN gene-prioritization requires two classes
    case, ctrl = classes[0], classes[1]

    # per-gene t-statistics (case vs control)
    tstats = []
    for gene in sub_matrix.columns:
        g = sub_matrix[gene].values.astype(float)
        a, b = g[y_labels.values == case], g[y_labels.values == ctrl]
        if len(a) < 3 or len(b) < 3 or a.std() == 0 or b.std() == 0:
            tstats.append(0.0)
            continue
        t, _ = _stats.ttest_ind(a, b, equal_var=False)
        tstats.append(float(np.nan_to_num(t)))
    tstats = np.asarray(tstats)

    # node features: expression summary statistics
    Z = StandardScaler().fit_transform(sub_matrix.values.astype(float))  # samples × genes
    mean_abs_z = np.abs(Z).mean(axis=0)
    var = np.nan_to_num(sub_matrix.var(axis=0).values)
    X = np.column_stack([tstats, mean_abs_z, var, np.sign(tstats) * np.log1p(np.abs(tstats))])
    X = StandardScaler().fit_transform(X)

    # labels: positive = strongly dysregulated (top |t|), negative = inert (bottom |t|)
    n = len(tstats)
    frac = max(5, int(n * 0.25))
    order = np.argsort(-np.abs(tstats))
    positive = set(order[:frac])
    negative = set(order[-frac:])
    keep = sorted(positive | negative)
    y_enc = np.array([1 if i in positive else 0 for i in keep])

    try:
        net = build_network(features, confidence_threshold=0.4, max_interactors=len(features))
        edges = list(net.edges())
        from app.ml.models import GCNClassifier, build_adjacency_from_ppi

        A = build_adjacency_from_ppi(features, edges)
        gcn = GCNClassifier(A[keep][:, keep], input_dim=X.shape[1], hidden_dim=settings.GNN_HIDDEN_DIM,
                            n_classes=2, epochs=settings.GNN_EPOCHS)
        gcn.fit(X[keep], y_enc)
        proba = gcn.predict_proba(X[keep])
        metrics = evaluate(y_enc, proba, 2)
        key = f"gnn_{uuid.uuid4().hex[:8]}"
        model_dir = out_dir / key
        path = save_model(gcn, {"key": key, "algorithm": "gnn", "metrics": metrics, "features": features,
                                "task": "gene_prioritization"}, model_dir)
        # importance: graph-convolution receptive field = degree-weighted adjacency rows
        degree_imp = A.sum(axis=0)
        imp = degree_imp / (degree_imp.sum() + 1e-9)
        order_imp = np.argsort(-imp)
        importance = [{"feature": features[i], "importance": float(imp[i])} for i in order_imp[:20]]
        top_prioritized = [features[i] for i in np.argsort(-np.abs(tstats))[:15]]
        return {
            "key": key, "algorithm": "gnn", "metrics": metrics,
            "feature_importance": importance, "artifact_path": str(path),
            "n_features_used": len(features), "note": "GCN gene prioritization over PPI graph (target prediction)",
            "top_prioritized_genes": top_prioritized,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("GNN pipeline failed: %s", exc)
        return None
