
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline as SKPipeline
from sklearn.preprocessing import (
OrdinalEncoder,
OneHotEncoder,
RobustScaler,
StandardScaler,
)

from src.utils.monitoring import log

from src.utils.config import (
TARGET_COL,
ROBUST_COLS,
STANDARD_COLS,
OHE_COLS,
EXPECTED_FLAG_COLS,
EDUCATION_ORDER,
_MONTH_MAP,
)


def _encode_cyclic_day(df):
    df["day_sin"] = np.sin(2 * np.pi * df["day"] / 31)
    df["day_cos"] = np.cos(2 * np.pi * df["day"] / 31)
    return df.drop(columns=["day"])


def _encode_cyclic_month(df):
    month_num      = df["month"].str.strip().str.lower().map(_MONTH_MAP)
    df["month_sin"] = np.sin(2 * np.pi * month_num / 12)
    df["month_cos"] = np.cos(2 * np.pi * month_num / 12)
    return df.drop(columns=["month"])


def transform_data(df: pd.DataFrame):
    """Fase 3: encoding cíclico, ColumnTransformer, X_transformed."""
    from sklearn.pipeline import Pipeline as SKPipeline
    from sklearn.preprocessing import (OrdinalEncoder, OneHotEncoder,
                                        RobustScaler, StandardScaler)
    log.info("=" * 65 + "\nFASE 3 — TRANSFORMACIÓN\n" + "=" * 65)
    df = df.copy()
    if "duration"   in df.columns: df = df.drop(columns=["duration"])
    if TARGET_COL not in df.columns:
        raise ValueError(f"Target '{TARGET_COL}' no encontrado.")
    y = df[TARGET_COL].copy().astype(int)
    X = df.drop(columns=[TARGET_COL])
    if "day"   in X.columns: X = _encode_cyclic_day(X)
    if "month" in X.columns: X = _encode_cyclic_month(X)

    robust_feats   = [c for c in ROBUST_COLS   if c in X.columns]
    standard_feats = [c for c in STANDARD_COLS if c in X.columns]
    ohe_feats      = [c for c in OHE_COLS      if c in X.columns]
    ordinal_feats  = [c for c in ["education"] if c in X.columns]
    flag_cols      = [c for c in EXPECTED_FLAG_COLS if c in X.columns]
    cyclic_cols    = [c for c in ["day_sin","day_cos","month_sin","month_cos"] if c in X.columns]
    binary_pass    = [c for c in ["default","housing","loan"] if c in X.columns]
    passthrough    = flag_cols + cyclic_cols + binary_pass

    transformers = []
    if robust_feats:   transformers.append(("robust",   SKPipeline([("s", RobustScaler())]),   robust_feats))
    if standard_feats: transformers.append(("standard", SKPipeline([("s", StandardScaler())]), standard_feats))
    if ohe_feats:      transformers.append(("ohe", SKPipeline([("e", OneHotEncoder(
        handle_unknown="ignore", sparse_output=False))]), ohe_feats))
    if ordinal_feats:  transformers.append(("ordinal", SKPipeline([("e", OrdinalEncoder(
        categories=EDUCATION_ORDER, handle_unknown="use_encoded_value", unknown_value=-1))]), ordinal_feats))
    if passthrough:    transformers.append(("passthrough", "passthrough", passthrough))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop",
                                     verbose_feature_names_out=True)
    X_arr = preprocessor.fit_transform(X)
    names = [
        n.replace("robust__","").replace("standard__","").replace("ohe__","")
         .replace("ordinal__","").replace("passthrough__","")
        for n in preprocessor.get_feature_names_out()
    ]
    X_transformed = pd.DataFrame(X_arr, columns=names, index=X.index)
    log.info("=" * 65 + "\nFASE 3 — COMPLETADA\n" + "=" * 65)
    return X_transformed, y, preprocessor
