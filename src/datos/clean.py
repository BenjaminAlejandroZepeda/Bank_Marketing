
import numpy as np
import pandas as pd

from src.utils.monitoring import (
log,
_checkpoint,
)

from src.utils.config import (
CATEGORICAL_COLS,
BINARY_COLS,
OUTLIER_SPECIAL_EXCLUDE,
_BINARY_YES_VARIANTS,
_BINARY_NO_VARIANTS,
)



def _flag_outliers_iqr(df, col, label, exclude_values=None):
    series = df[col].copy()
    if exclude_values:
        mask_special   = series.isin(exclude_values)
        series_for_iqr = series[~mask_special]
    else:
        mask_special   = pd.Series(False, index=series.index)
        series_for_iqr = series
    if series_for_iqr.dropna().empty:
        df[label] = 0
        return df
    q1, q3 = series_for_iqr.quantile(0.25), series_for_iqr.quantile(0.75)
    iqr     = q3 - q1
    lo, hi  = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    df[label] = (((series < lo) | (series > hi)) & ~mask_special).astype(int)
    log.info(f"  {label:<35} → {int(df[label].sum()):,} outliers [rango: {lo:.2f}–{hi:.2f}]")
    return df


def _map_binary_tolerant(series, col_name):
    normalized = series.astype(str).str.strip().str.lower()
    def _map(v):
        if v in _BINARY_YES_VARIANTS: return 1
        if v in _BINARY_NO_VARIANTS:  return 0
        return np.nan
    mapped    = normalized.map(_map).astype("float64")
    n_nan_new = mapped.isnull().sum() - series.isnull().sum()
    if n_nan_new > 0:
        bad = normalized[mapped.isnull() & series.notna()].unique()
        log.warning(f"  {col_name:<15} → ⚠ {n_nan_new} no mapeables | {bad[:5]}")
    else:
        log.info(f"  {col_name:<15} → OK [1={int(mapped.sum()):,} | 0={int((mapped==0).sum()):,}]")
    return mapped


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Fase 2: limpieza, mapping binario, flags de negocio."""
    log.info("=" * 65 + "\nFASE 2 — LIMPIEZA DE DATOS\n" + "=" * 65)
    df = df.copy()
    _checkpoint("inicio limpieza", df)
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()
    for col in BINARY_COLS:
        if col in df.columns:
            df[col] = _map_binary_tolerant(df[col], col)
    _checkpoint("post-mapping binario", df)
    if "balance"  in df.columns:
        df["flag_balance_negativo"] = (df["balance"] < 0).astype(int)
        df = _flag_outliers_iqr(df, "balance",  "flag_outlier_balance")
    if "campaign" in df.columns:
        df = _flag_outliers_iqr(df, "campaign", "flag_outlier_campaign")
    if "pdays"    in df.columns:
        df["pdays_flag_nuevo_cliente"] = (df["pdays"] == -1).astype(int)
        df = _flag_outliers_iqr(df, "pdays", "flag_outlier_pdays",
                                exclude_values=OUTLIER_SPECIAL_EXCLUDE.get("pdays"))
    if "previous" in df.columns:
        df = _flag_outliers_iqr(df, "previous", "flag_outlier_previous")
    _checkpoint("fin limpieza", df)
    log.info("=" * 65 + "\nFASE 2 — COMPLETADA\n" + "=" * 65)
    return df