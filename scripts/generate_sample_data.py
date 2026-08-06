#!/usr/bin/env python3
"""Generate synthetic multi-omics sample data files (for demos & tests).

Usage:  python scripts/generate_sample_data.py --out ./sample_data
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic omics sample data")
    ap.add_argument("--out", default="./sample_data", help="output directory")
    ap.add_argument("--n-genes", type=int, default=500)
    ap.add_argument("--n-ad", type=int, default=40)
    ap.add_argument("--n-cn", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    curated = ["APP", "BACE1", "PSEN1", "APOE", "TREM2", "TYROBP", "MAPT", "GSK3B",
               "IL1B", "TNF", "IL6", "CLU", "SORL1", "HMOX1", "MTOR", "BECN1", "GFAP"]
    genes = [f"GENE{i:04d}" for i in range(args.n_genes)] + curated
    ad = [f"AD_{i:03d}" for i in range(args.n_ad)]
    cn = [f"CN_{i:03d}" for i in range(args.n_cn)]
    X = rng.lognormal(0, 1.3, size=(len(genes), args.n_ad + args.n_cn))
    df = pd.DataFrame(X, index=genes, columns=ad + cn)
    for g in ["APP", "BACE1", "IL1B", "TNF", "IL6", "TYROBP", "TREM2", "APOE", "HMOX1", "GFAP"]:
        df.loc[g, ad] *= 4.0
    for g in ["MTOR", "BECN1"]:
        df.loc[g, ad] *= 0.4
    expr_path = out / "expression.csv"
    df.to_csv(expr_path)

    meta = pd.DataFrame({
        "group": ["AD"] * args.n_ad + ["CN"] * args.n_cn,
        "batch": ["B1", "B2"] * (max(args.n_ad, 1) // 2) + ["B1", "B2"] * (max(args.n_cn, 1) // 2),
        "age": np.round(rng.normal(74, 6, args.n_ad + args.n_cn), 1),
        "sex": rng.choice(["M", "F"], size=args.n_ad + args.n_cn),
    }, index=df.columns)
    meta.to_csv(out / "metadata.csv")

    print(f"Wrote {len(genes)}-gene x {df.shape[1]}-sample expression matrix and metadata to {out}")


if __name__ == "__main__":
    main()
