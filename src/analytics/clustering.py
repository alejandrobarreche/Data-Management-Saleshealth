"""Segmentación de clientes con PCA + KMeans."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass
class ClusteringResult:
    df: pd.DataFrame                  # df de entrada + columnas pc1, pc2, cluster
    pca: PCA
    scaler: StandardScaler
    kmeans: KMeans
    explained_variance: np.ndarray
    inertia_curve: dict[int, float]   # k -> inertia, para escoger k


def _elbow(X: np.ndarray, ks=range(2, 9), random_state=42) -> dict[int, float]:
    return {k: KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X).inertia_
            for k in ks}


def run_pca_kmeans(
    df: pd.DataFrame,
    feature_cols: list[str],
    n_clusters: int = 3,
    n_components: int = 2,
    random_state: int = 42,
) -> ClusteringResult:
    """Estandariza, aplica PCA(n_components) y KMeans(n_clusters)."""
    X = df[feature_cols].astype(float).fillna(0).to_numpy()
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    pca = PCA(n_components=n_components, random_state=random_state).fit(Xs)
    Xp = pca.transform(Xs)

    inertia = _elbow(Xp, random_state=random_state)
    km = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state).fit(Xp)

    out = df.copy()
    for i in range(n_components):
        out[f"pc{i+1}"] = Xp[:, i]
    out["cluster"] = km.labels_
    return ClusteringResult(out, pca, scaler, km, pca.explained_variance_ratio_, inertia)


def save_artifacts(result: ClusteringResult, out_dir: str | Path) -> None:
    import joblib
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(result.scaler, out / "scaler.joblib")
    joblib.dump(result.pca, out / "pca.joblib")
    joblib.dump(result.kmeans, out / "kmeans.joblib")
    result.df.to_parquet(out / "customer_segments.parquet", index=False)
