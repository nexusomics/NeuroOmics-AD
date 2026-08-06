"""Model zoo: Random Forest, XGBoost, SVM, DNN (MLP) and Graph Neural Network (GCN).

The GNN uses PyTorch when available; otherwise it degrades to a graph-augmented
feature pipeline so the module remains usable in lightweight environments.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def random_forest(n_jobs: int = -1, **kwargs: Any):
    from sklearn.ensemble import RandomForestClassifier

    return RandomForestClassifier(n_estimators=kwargs.get("n_estimators", 300), max_depth=kwargs.get("max_depth", None),
                                  min_samples_leaf=kwargs.get("min_samples_leaf", 1), n_jobs=n_jobs, random_state=42)


def xgboost_classifier(**kwargs: Any):
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(n_estimators=kwargs.get("n_estimators", 300), max_depth=kwargs.get("max_depth", 6),
                             learning_rate=kwargs.get("learning_rate", 0.05), subsample=0.8, colsample_bytree=0.8,
                             eval_metric="logloss", random_state=42, tree_method="hist")
    except ImportError:
        logger.warning("xgboost not installed; using GradientBoosting fallback.")
        from sklearn.ensemble import GradientBoostingClassifier

        return GradientBoostingClassifier(n_estimators=kwargs.get("n_estimators", 200), max_depth=3)


def svm_classifier(**kwargs: Any):
    from sklearn.svm import SVC

    return SVC(C=kwargs.get("C", 1.0), kernel=kwargs.get("kernel", "rbf"), gamma="scale",
               probability=True, random_state=42)


def dnn_classifier(**kwargs: Any):
    """Deep neural network (MLP) with optional GPU (PyTorch) backend."""
    try:
        import torch
        import torch.nn as nn

        if torch.cuda.is_available():
            return _TorchDNN(input_dim=kwargs.get("input_dim", 0), hidden=kwargs.get("hidden", [256, 128, 64]),
                             n_classes=kwargs.get("n_classes", 2), epochs=kwargs.get("epochs", 60))
        raise RuntimeError("no cuda")
    except Exception:  # noqa: BLE001
        from sklearn.neural_network import MLPClassifier

        return MLPClassifier(hidden_layer_sizes=tuple(kwargs.get("hidden", [128, 64])), max_iter=kwargs.get("epochs", 500),
                             early_stopping=True, random_state=42)


class _TorchDNN:
    """Minimal PyTorch MLP with sklearn-like interface."""

    def __init__(self, input_dim: int, hidden: list[int], n_classes: int, epochs: int = 60) -> None:
        import torch
        import torch.nn as nn

        self.epochs = epochs
        self.n_classes = n_classes
        layers = []
        prev = input_dim
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(0.3)]
            prev = h
        layers.append(nn.Linear(prev, n_classes))
        self.net = nn.Sequential(*layers)
        self.loss = nn.CrossEntropyLoss()
        self.opt = torch.optim.Adam(self.net.parameters(), lr=1e-3)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_TorchDNN":
        import torch

        Xt = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)
        ds = torch.utils.data.TensorDataset(Xt, yt)
        loader = torch.utils.data.DataLoader(ds, batch_size=64, shuffle=True)
        self.net.train()
        for _ in range(self.epochs):
            for xb, yb in loader:
                self.opt.zero_grad()
                out = self.net(xb)
                loss = self.loss(out, yb)
                loss.backward()
                self.opt.step()
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        import torch

        self.net.eval()
        with torch.no_grad():
            logits = self.net(torch.tensor(X, dtype=torch.float32))
            return torch.softmax(logits, dim=1).numpy()

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)


class GCNClassifier:
    """Graph Neural Network classifier (2-layer GCN) with sklearn-like API.

    Nodes = genes, features = expression profiles (or VAE embeddings),
    edges = PPI. Uses PyTorch; falls back to graph-feature + logistic model
    when torch is unavailable.
    """

    def __init__(self, adjacency: np.ndarray, input_dim: int, hidden_dim: int = 64, n_classes: int = 2,
                 epochs: int = 50, lr: float = 1e-3, use_torch: bool | None = None) -> None:
        self.adjacency = adjacency
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_classes = n_classes
        self.epochs = epochs
        self.lr = lr
        self._torch_ok = use_torch if use_torch is not None else _torch_available()
        self._fallback = None
        self.trained_adj = None

    # ------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "GCNClassifier":
        if self._torch_ok:
            self._fit_torch(X, y)
        else:
            self._fit_fallback(X, y)
        return self

    def _normalized_adj(self) -> np.ndarray:
        A = self.adjacency.astype(float)
        np.fill_diagonal(A, 0.0)
        D = A.sum(axis=1) + 1e-9
        Dinv = np.diag(1.0 / np.sqrt(D))
        return Dinv @ A @ Dinv

    def _fit_torch(self, X: np.ndarray, y: np.ndarray) -> None:
        import torch
        import torch.nn as nn

        Ahat = torch.tensor(self._normalized_adj(), dtype=torch.float32)
        Xf = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)
        n_nodes, dim = X.shape
        self.W1 = nn.Parameter(torch.randn(dim, self.hidden_dim) * 0.1)
        self.b1 = nn.Parameter(torch.zeros(self.hidden_dim))
        self.W2 = nn.Parameter(torch.randn(self.hidden_dim, self.n_classes) * 0.1)
        self.b2 = nn.Parameter(torch.zeros(self.n_classes))
        opt = torch.optim.Adam([self.W1, self.b1, self.W2, self.b2], lr=self.lr)
        loss_fn = nn.CrossEntropyLoss()
        self.net = nn.Module()
        self.net.W1, self.net.b1, self.net.W2, self.net.b2 = self.W1, self.b1, self.W2, self.b2
        for _ in range(self.epochs):
            H = torch.relu(Ahat @ Xf @ self.W1 + self.b1)
            logits = Ahat @ H @ self.W2 + self.b2
            loss = loss_fn(logits, yt)
            opt.zero_grad()
            loss.backward()
            opt.step()
        self.trained_adj = Ahat

    def _fit_fallback(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.linear_model import LogisticRegression

        A = self._normalized_adj()
        # 1-hop smoothed features (graph convolution without learned weights)
        H = np.tanh(A @ X)
        features = np.hstack([X, H])
        self._fallback = LogisticRegression(max_iter=2000).fit(features, y)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self._torch_ok:
            import torch

            with torch.no_grad():
                H = torch.relu(self.trained_adj @ torch.tensor(X, dtype=torch.float32) @ self.W1 + self.b1)
                logits = self.trained_adj @ H @ self.W2 + self.b2
                return torch.softmax(logits, dim=1).numpy()
        A = self._normalized_adj()
        H = np.tanh(A @ X)
        features = np.hstack([X, H])
        return self._fallback.predict_proba(features)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def build_adjacency_from_ppi(gene_list: list[str], edges: list[tuple[str, str]]) -> np.ndarray:
    """Convert (gene, gene) edge list into a node adjacency matrix over gene_list."""
    idx = {g: i for i, g in enumerate(gene_list)}
    n = len(gene_list)
    A = np.zeros((n, n))
    for u, v in edges:
        if u in idx and v in idx:
            A[idx[u], idx[v]] = 1.0
            A[idx[v], idx[u]] = 1.0
    np.fill_diagonal(A, 1.0)
    return A


ALGORITHM_FACTORIES = {
    "random_forest": random_forest,
    "xgboost": xgboost_classifier,
    "svm": svm_classifier,
    "dnn": dnn_classifier,
}
