from pathlib import Path

import pandas as pd

from sklearn.compose import ColumnTransformer

from src.utils.monitoring import log

from src.utils.config import (
OUTPUT_DIR_KPI,
EXPORT_LOAD_PARQUET,
EXPORT_LOAD_CSV,
)

from src.db.supabase_client import get_supabase


def load_outputs(
    X_transformed: pd.DataFrame,
    y            : pd.Series,
    preprocessor : ColumnTransformer,
    df_clean     : pd.DataFrame,
    output_dir   : Path = OUTPUT_DIR_KPI,
) -> dict:
    """
    Fase 5: persiste artefactos y valida alineación de índices.
    Retorna dict de trazabilidad incorporado en el reporte KPI final.
    """
    log.info("=" * 65 + "\nFASE 5 — CARGA (LOADING)\n" + "=" * 65)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts, status = {}, "OK"

    if EXPORT_LOAD_PARQUET:
        for name, obj in [("X_transformed", X_transformed), ("df_clean", df_clean)]:
            p = output_dir / f"{name}.parquet"
            obj.to_parquet(p, index=True, engine="pyarrow")
            artifacts[f"{name}_parquet"] = str(p)
            log.info(f"  ✓ Parquet → {p}")

    if EXPORT_LOAD_CSV:
        p_X = output_dir / "X_transformed.csv"
        p_y = output_dir / "y_target.csv"
        X_transformed.to_csv(p_X, index=True)
        y.to_csv(p_y, index=True, header=True)
        artifacts.update({"X_csv": str(p_X), "y_csv": str(p_y)})
        log.info(f"  ✓ CSV X → {p_X}  |  y → {p_y}")

    if not EXPORT_LOAD_PARQUET and not EXPORT_LOAD_CSV:
        log.info("  (exportación desactivada — ajustar EXPORT_LOAD_PARQUET / CSV)")

    aligned = X_transformed.index.equals(y.index)
    if not aligned:
        log.error("  ❌ Índices X ↔ y NO alineados"); status = "ERROR"
    else:
        log.info(f"  ✓ Índices X ↔ y alineados: {len(X_transformed):,} registros")

    vc_y   = y.value_counts().to_dict()
    report = {
        "status"       : status,
        "artifacts"    : artifacts,
        "shapes"       : {"X": list(X_transformed.shape), "y": list(y.shape)},
        "target_dist"  : {str(k): int(v) for k, v in vc_y.items()},
        "n_features"   : X_transformed.shape[1],
        "indices_ok"   : aligned,
        "preprocessor" : "listo para joblib.dump(preprocessor, 'preprocessor.pkl')",
    }
    log.info(f"FASE 5 — COMPLETADA | STATUS: {status}")
    log.info("=" * 65)
    return report




from src.db.supabase_client import get_supabase


import pandas as pd

from src.db.supabase_client import get_supabase


def upload_to_supabase(df_clean):

    try:
        supabase = get_supabase()

        # Copia segura
        df_upload = df_clean.copy()

        # Evitar palabra reservada SQL
        df_upload = df_upload.rename(
            columns={"default": "default_flag"}
        )


        int_cols = [
            "default_flag",
            "housing",
            "loan",
            "deposit",
            "flag_balance_negativo",
            "flag_outlier_balance",
            "flag_outlier_campaign",
            "pdays_flag_nuevo_cliente",
            "flag_outlier_pdays",
            "flag_outlier_previous",
        ]

        for col in int_cols:
            if col in df_upload.columns:
                df_upload[col] = (
                    pd.to_numeric(df_upload[col], errors="coerce")
                    .fillna(0)
                    .astype(int)
                )

        # PostgreSQL NULL compatibility
        df_upload = df_upload.where(pd.notnull(df_upload), None)

        # Renombrar target para coincidir con tabla
        if "deposit" in df_upload.columns:
            df_upload = df_upload.rename(
                columns={"deposit": "y"}
            )

        datos = df_upload.to_dict(orient="records")

        if not datos:
            print("No hay datos para subir")
            return None

        response = (
            supabase
            .table("bank_marketing")
            .upsert(datos)
            .execute()
        )

        print(f"✓ Registros enviados a Supabase: {len(datos):,}")

        return response

    except Exception as e:
        print(f"❌ Error subiendo datos a Supabase: {e}")
        raise