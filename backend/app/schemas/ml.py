"""Machine learning schemas."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MLTrainingRequest(BaseModel):
    dataset_id: str
    label_column: str = "group"
    task: Literal["classification", "regression"] = "classification"
    algorithms: list[str] = Field(default_factory=lambda: ["random_forest", "xgboost", "svm", "dnn"])
    test_size: float = 0.2
    cv_folds: int = 5
    feature_selection: bool = True
    top_features: int = 100
    gnn: bool = True  # build gene-gene graph for GNN when applicable
    hyperparameters: dict[str, Any] = {}


class PredictionRequest(BaseModel):
    model_key: str
    dataset_id: str


class ModelOut(BaseModel):
    key: str
    algorithm: str
    task: str
    metrics: dict[str, float]
    feature_importance: list[dict[str, float]]
    trained_at: Optional[str] = None
    artifact_path: str = ""


class FeatureImportanceRequest(BaseModel):
    model_key: str
    top_n: int = 20
