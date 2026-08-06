"""Shared ML utilities: data preparation, evaluation metrics, persistence."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)


def prepare_data(
    matrix: pd.DataFrame,
    labels: pd.Series,
    feature_selection: bool = True,
    top_features: int = 100,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict:
    """Split (features × samples) into X_train/y_train/X_test/y_test with scaling + optional selection."""
    common = [c for c in matrix.columns if c in labels.index]
    X = matrix[common].T.values.astype(float)
    y = labels.loc[common].astype(str).values
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    if feature_selection and X.shape[1] > top_features:
        # ANOVA F-test based selection
        from sklearn.feature_selection import SelectKBest, f_classif

        selector = SelectKBest(f_classif, k=min(top_features, X.shape[1]))
        X = selector.fit_transform(X, y_enc)
        selected = matrix.index[selector.get_support()].tolist()
    else:
        selected = list(matrix.index)
    X_train, X_test, y_train, y_test = train_test_split(X, y_enc, test_size=test_size, stratify=y_enc, random_state=random_state)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    return {
        "X_train": X_train, "X_test": X_test, "y_train": y_train, "y_test": y_test,
        "label_encoder": le, "scaler": scaler, "selected_features": selected,
        "n_classes": len(le.classes_), "classes": le.classes_.tolist(),
    }


def evaluate(y_true: np.ndarray, y_prob: np.ndarray, n_classes: int) -> dict[str, float]:
    """Compute classification metrics incl. ROC-AUC (ovr for multiclass)."""
    y_pred = y_prob.argmax(axis=1) if y_prob.ndim == 2 else (y_prob > 0.5).astype(int)
    metrics: dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
    }
    if n_classes == 2:
        prob_pos = y_prob[:, 1] if y_prob.ndim == 2 else y_prob
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, prob_pos))
        except ValueError:
            metrics["roc_auc"] = 0.5
        metrics["f1"] = float(f1_score(y_true, y_pred))
    else:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob, multi_class="ovr"))
        except ValueError:
            metrics["roc_auc"] = 0.5
    return metrics


def cross_validate(model_factory, X: np.ndarray, y: np.ndarray, cv_folds: int = 5, random_state: int = 42) -> dict[str, float]:
    """Stratified CV scoring for binary/multiclass classification."""
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    accs, aucs = [], []
    for train_idx, val_idx in skf.split(X, y):
        clf = model_factory()
        clf.fit(X[train_idx], y[train_idx])
        proba = clf.predict_proba(X[val_idx])
        y_pred = proba.argmax(axis=1)
        accs.append(accuracy_score(y[val_idx], y_pred))
        try:
            aucs.append(roc_auc_score(y[val_idx], proba[:, 1] if len(np.unique(y)) == 2 else proba, multi_class="ovr"))
        except ValueError:
            aucs.append(0.5)
    return {"cv_mean_accuracy": float(np.mean(accs)), "cv_mean_roc_auc": float(np.mean(aucs)), "cv_folds": cv_folds}


def save_model(model: Any, metadata: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "model.joblib"
    joblib.dump({"model": model, "metadata": metadata}, path)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    return path


def load_model(path: Path) -> dict:
    return joblib.load(path)
