import pandas as pd
import numpy as np

from src.utils.monitoring import _semaforo

def compute_kpi_calidad(
    df_raw       : pd.DataFrame,
    df_clean     : pd.DataFrame,
    X_transformed: pd.DataFrame,
    y            : pd.Series,
    val_struct   : dict,
    val_sem      : dict,
) -> dict:
    """
    Mide la calidad de los datos en todas las etapas del pipeline.

    Corrección V5 [MENOR-2]
    -----------------------
    Semáforo de NaN en X usaba literal 0.0 como verde_lim. Ahora referencia
    THRESHOLDS["max_nan_pct_X"] (0.0 por defecto, pero configurable).
    Esto hace el umbral coherente con el esquema de configuración global.
    """
    log.info("-" * 55)
    log.info("[KPI 7.3] CALIDAD")
    log.info("-" * 55)

    n_clean   = len(df_clean)
    penalties = []

    # ── missing_values_pct ────────────────────────────────────────────────────
    null_pct_raw   = df_raw.isnull().sum().sum()    / df_raw.size    * 100
    null_pct_clean = df_clean.isnull().sum().sum()  / df_clean.size  * 100
    null_pct_X     = X_transformed.isnull().sum().sum() / X_transformed.size * 100

    # FIX V5 [MENOR-2]: usar THRESHOLDS["max_nan_pct_X"] en lugar de 0.0 literal
    sem_nan = _semaforo(null_pct_X,
                        THRESHOLDS["max_nan_pct_X"],       # ← corregido
                        THRESHOLDS["max_nan_pct_clean"],
                        invert=True)
    missing = {
        "df_raw_pct"  : round(null_pct_raw, 4),
        "df_clean_pct": round(null_pct_clean, 4),
        "X_pct"       : round(null_pct_X, 4),
        "semaforo"    : sem_nan,
    }
    log.info(
        f"  missing_values_pct : raw={null_pct_raw:.4f}%  "
        f"clean={null_pct_clean:.4f}%  X={null_pct_X:.4f}%  [{_SEM_ICON[sem_nan]}]"
    )
    if   sem_nan == "rojo":     penalties.append(30)
    elif sem_nan == "amarillo": penalties.append(10)

    # ── outliers_pct (desde flags de df_clean) ────────────────────────────────
    flag_to_col = {
        "flag_outlier_balance" : "balance",
        "flag_outlier_campaign": "campaign",
        "flag_outlier_pdays"   : "pdays",
        "flag_outlier_previous": "previous",
    }
    outliers_por_col = {}
    for flag, col in flag_to_col.items():
        if flag in df_clean.columns:
            n_out = int(df_clean[flag].sum())
            pct   = round(n_out / n_clean * 100, 2)
            sem   = _semaforo(pct, 5.0, THRESHOLDS["max_outlier_pct"], invert=True)
            outliers_por_col[col] = {"n": n_out, "pct": pct, "semaforo": sem}
            log.info(f"  outliers {col:<12}: {pct:>6.2f}%  {_SEM_ICON[sem]}")
            if   sem == "rojo":     penalties.append(10)
            elif sem == "amarillo": penalties.append(5)

    # ── class_balance ─────────────────────────────────────────────────────────
    vc_y   = y.value_counts()
    vc_pct = y.value_counts(normalize=True) * 100
    min_pct = float(vc_pct.min())
    ratio   = round(float(vc_y.max() / vc_y.min()), 2) if vc_y.min() > 0 else None
    sem_cb  = _semaforo(min_pct, THRESHOLDS["min_class_minority_pct"], 10.0)
    class_balance = {
        "clase_0_n"      : int(vc_y.get(0, 0)),
        "clase_1_n"      : int(vc_y.get(1, 0)),
        "clase_0_pct"    : round(float(vc_pct.get(0, 0.0)), 2),
        "clase_1_pct"    : round(float(vc_pct.get(1, 0.0)), 2),
        "ratio_desbalance": ratio,
        "semaforo"       : sem_cb,
    }
    log.info(
        f"  class_balance      : 0={class_balance['clase_0_pct']:.1f}%  "
        f"1={class_balance['clase_1_pct']:.1f}%  ratio={ratio}  {_SEM_ICON[sem_cb]}"
    )
    if   sem_cb == "rojo":     penalties.append(10)
    elif sem_cb == "amarillo": penalties.append(5)

    # ── columnas_validas_pct ──────────────────────────────────────────────────
    cols_con_nan  = [c for c in X_transformed.columns if X_transformed[c].isnull().any()]
    num_X         = X_transformed.select_dtypes(include="number")
    cols_zv       = num_X.columns[num_X.var() == 0].tolist()
    cols_invalidas = set(cols_con_nan + cols_zv)
    cols_validas_pct = round(
        (X_transformed.shape[1] - len(cols_invalidas)) / X_transformed.shape[1] * 100, 2
    ) if X_transformed.shape[1] > 0 else 0.0
    sem_cols = _semaforo(cols_validas_pct, THRESHOLDS["min_columnas_validas_pct"], 80.0)
    log.info(
        f"  columnas_validas   : {cols_validas_pct:.2f}%  "
        f"({X_transformed.shape[1]-len(cols_invalidas)}/{X_transformed.shape[1]})  {_SEM_ICON[sem_cols]}"
    )
    if   sem_cols == "rojo":     penalties.append(15)
    elif sem_cols == "amarillo": penalties.append(7)

    # ── consistencia ──────────────────────────────────────────────────────────
    consistencia_tipos   = len(X_transformed.select_dtypes(exclude="number").columns) == 0
    consistencia_indices = X_transformed.index.equals(y.index)
    log.info(f"  consistencia_tipos  : {'✓ OK' if consistencia_tipos   else '❌ FAIL'}")
    log.info(f"  consistencia_indices: {'✓ OK' if consistencia_indices else '❌ FAIL'}")
    if not consistencia_tipos:   penalties.append(25)
    if not consistencia_indices: penalties.append(25)

    # flags activados
    flags_activados = {
        f: {"n": int(df_clean[f].sum()),
            "pct": round(int(df_clean[f].sum()) / n_clean * 100, 2)}
        for f in EXPECTED_FLAG_COLS if f in df_clean.columns
    }
    log.info(f"  flags_activados    : {len(flags_activados)}/{len(EXPECTED_FLAG_COLS)} presentes")

    # semáforo global de calidad
    score_cal = max(0, 100 - sum(penalties))
    sem_gbl   = "verde" if score_cal >= 85 else ("amarillo" if score_cal >= 60 else "rojo")
    log.info(f"  {_SEM_ICON[sem_gbl]} semaforo_global calidad: {sem_gbl.upper()} (score={score_cal}/100)")

    return {
        "missing_values_pct"           : missing,
        "outliers_pct"                 : outliers_por_col,
        "class_balance"                : class_balance,
        "columnas_validas_pct"         : cols_validas_pct,
        "columnas_invalidas"           : list(cols_invalidas),
        "consistencia_tipos"           : consistencia_tipos,
        "consistencia_indices"         : consistencia_indices,
        "flags_activados"              : flags_activados,
        "validacion_estructural_status": val_struct.get("status", "N/A"),
        "validacion_semantica_status"  : val_sem.get("status", "N/A"),
        "score_calidad"                : score_cal,
        "semaforo_global"              : sem_gbl,
    }
