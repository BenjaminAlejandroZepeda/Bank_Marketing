import pandas as pd
import numpy as np
from src.utils.monitoring import log
from src.utils.config import EXPECTED_FLAG_COLS
from src.utils.monitoring import (
log,
_semaforo,
)
from src.utils.config import (
ALL_EXPECTED_COLS,
)



#  BLOQUE 4 — VALIDACIÓN ESTRUCTURAL  (Fase 4A)


def validate_structural(
    df_raw: pd.DataFrame,
    df_clean: pd.DataFrame,
    X_transformed: pd.DataFrame,
) -> dict:

    log.info("=" * 65 + "\nFASE 4A — VALIDACIÓN ESTRUCTURAL\n" + "=" * 65)

    report = {"errors": [], "warnings": [], "checks": {}}

    # Consistencia de filas
    filas_ok = (df_raw.shape[0] == df_clean.shape[0] == X_transformed.shape[0])
    report["checks"]["filas_consistentes"] = filas_ok

    if not filas_ok:
        msg = (
            f"Filas inconsistentes: raw={df_raw.shape[0]} "
            f"clean={df_clean.shape[0]} X={X_transformed.shape[0]}"
        )
        report["errors"].append(msg)
        log.error(f"  ❌ {msg}")

    else:
        log.info(f"  ✓ Filas consistentes: {df_raw.shape[0]:,}")

    
    num_X = X_transformed.select_dtypes(include="number")

    zv = num_X.columns[num_X.var() == 0].tolist()

    report["checks"]["zero_variance_cols"] = zv

    if zv:
        log.warning(f"  ⚠ Varianza cero en: {zv}")

    else:
        log.info("  ✓ Sin columnas de varianza cero.")

    # NaN en X
    nan_X_total = int(X_transformed.isnull().sum().sum())

    nan_X_pct = nan_X_total / X_transformed.size * 100

    report["checks"]["nan_X_total"] = nan_X_total
    report["checks"]["nan_X_pct"] = round(nan_X_pct, 4)

    if nan_X_total > 0:
        msg = f"X_transformed contiene {nan_X_total:,} NaN ({nan_X_pct:.4f}%)"

        report["errors"].append(msg)

        log.error(f"  ❌ {msg}")

    else:
        log.info("  ✓ X_transformed libre de NaN.")

    # Tipos numéricos
    non_num = X_transformed.select_dtypes(exclude="number").columns.tolist()

    report["checks"]["non_numeric_cols"] = non_num

    if non_num:
        msg = f"Columnas no numéricas en X: {non_num}"

        report["errors"].append(msg)

        log.error(f"  ❌ {msg}")

    else:
        log.info(f"  ✓ Todos los {X_transformed.shape[1]} features son numéricos.")

    # Flags de negocio
    flags_ausentes = [
        f for f in EXPECTED_FLAG_COLS
        if f not in df_clean.columns
    ]

    report["checks"]["flags_ausentes"] = flags_ausentes

    if flags_ausentes:
        log.warning(f"  ⚠ Flags ausentes: {flags_ausentes}")

    else:
        log.info(
            f"  ✓ Los {len(EXPECTED_FLAG_COLS)} flags de negocio presentes."
        )

    # Columnas all-NaN
    empty_X = [
        c for c in X_transformed.columns
        if X_transformed[c].isnull().all()
    ]

    report["checks"]["empty_cols_X"] = empty_X

    if empty_X:
        msg = f"Columnas all-NaN en X: {empty_X}"

        report["errors"].append(msg)

        log.error(f"  ❌ {msg}")

    report["status"] = (
        "ERROR"
        if report["errors"]
        else ("WARNING" if report["warnings"] else "OK")
    )

    log.info(f"FASE 4A — COMPLETADA | STATUS: {report['status']}")

    log.info("=" * 65)

    return report



#  VALIDACIÓN SEMÁNTICA 


def validate_semantic(
    df_clean: pd.DataFrame,
    X_transformed: pd.DataFrame,
) -> dict:

    log.info("=" * 65 + "\nFASE 4B — VALIDACIÓN SEMÁNTICA\n" + "=" * 65)

    report = {"errors": [], "warnings": [], "checks": {}}


    if (
        "pdays" in df_clean.columns
        and "pdays_flag_nuevo_cliente" in df_clean.columns
    ):

        n_m1 = int((df_clean["pdays"] == -1).sum())

        n_flag = int(df_clean["pdays_flag_nuevo_cliente"].sum())

        ok = (n_m1 == n_flag)

        report["checks"]["pdays_flag_consistente"] = ok

        if not ok:
            msg = f"pdays=-1 ({n_m1}) ≠ flag ({n_flag})"

            report["errors"].append(msg)

            log.error(f"  ❌ {msg}")

        else:
            log.info(
                f"  ✓ pdays_flag_nuevo_cliente consistente: {n_m1:,}"
            )

    
    cyclic_ok = {}

    for sin_c, cos_c, lbl in [
        ("day_sin", "day_cos", "day"),
        ("month_sin", "month_cos", "month"),
    ]:

        if sin_c in X_transformed.columns and cos_c in X_transformed.columns:

            identity = (
                X_transformed[sin_c]**2
                + X_transformed[cos_c]**2
            )

            n_bad = int((identity < 0.9999).sum())

            cyclic_ok[lbl] = (n_bad == 0)

            if n_bad > 0:
                msg = (
                    f"Cíclico '{lbl}': "
                    f"{n_bad} violaciones sin²+cos²≈1"
                )

                report["warnings"].append(msg)

                log.warning(f"  ⚠ {msg}")

            else:
                log.info(
                    f"  ✓ Encoding cíclico '{lbl}': identidad OK"
                )

    report["checks"]["cyclic_encoding"] = cyclic_ok

    
    if "housing" in df_clean.columns and "loan" in df_clean.columns:

        n_dd = int(
            (
                (df_clean["housing"] == 1)
                & (df_clean["loan"] == 1)
            ).sum()
        )

        pct_dd = round(n_dd / len(df_clean) * 100, 2)

        report["checks"]["doble_deuda_pct"] = pct_dd

        log.info(
            f"  Doble deuda (housing=1 AND loan=1): "
            f"{n_dd:,} ({pct_dd:.1f}%)"
        )


    if "deposit" in df_clean.columns:

        vc = df_clean["deposit"].value_counts()

        min_pct = float((vc / vc.sum() * 100).min())

        report["checks"]["min_class_pct"] = round(min_pct, 2)

        if min_pct < 20.0:
            msg = f"Clase minoritaria al {min_pct:.1f}% (< 20%)"

            report["warnings"].append(msg)

            log.warning(f"  ⚠ {msg}")

        else:
            log.info(
                f"  ✓ Balance de clases OK: "
                f"clase minoritaria {min_pct:.1f}%"
            )

    report["status"] = (
        "ERROR"
        if report["errors"]
        else ("WARNING" if report["warnings"] else "OK")
    )

    log.info(f"FASE 4B — COMPLETADA | STATUS: {report['status']}")

    log.info("=" * 65)

    return report
