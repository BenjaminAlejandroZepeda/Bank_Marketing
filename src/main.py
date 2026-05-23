from src.utils.monitoring import (
    log,
    PhaseTimer,
    _EXEC_REGISTRY,
    _SEM_ICON,
    _semaforo,
    _checkpoint,
)
from src.datos.ingest import load_data
from src.datos.clean import clean_data
from src.datos.transform import transform_data

from src.kpis.dashboard import compute_kpis

from src.utils.config import (
    FILE_PATH,
    OUTPUT_DIR_KPI,
    EXPORT_KPI_JSON,
)

from src.datos.validate import (
    validate_structural,
    validate_semantic,
)


from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from sklearn.compose import ColumnTransformer
from src.datos.load import load_outputs, upload_to_supabase

from fastapi import FastAPI, HTTPException
from src.db.supabase_client import get_supabase

import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {
        "api": "bank-marketing-dataops",
        "status": "running"
    }


@app.get("/test-db")
def test_db():
    try:
        supabase = get_supabase()

        response = (
            supabase
            .table("bank_marketing")
            .select("*")
            .limit(1)
            .execute()
        )

        return {
            "status": "ok",
            "data": response.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run-pipeline")
def run_pipeline():
    try:
        outputs = run_with_kpis()

        return {
            "status": "success",
            "health_score": outputs["kpis"]["resumen"]["health_score"],
            "rows": len(outputs["df_clean"]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def run_with_kpis(file_path: str = FILE_PATH) -> dict[str, Any]:
    """
    Ejecuta el pipeline completo (Fases 1-7) con medición de KPIs.

    """
    ts_inicio       = datetime.now(timezone.utc).isoformat()
    pipeline_status = "success"
    timers: dict    = {}
    _exc            = None   

    # Valores por defecto (usados si el pipeline aborta antes de crearlos)
    df_raw = df_clean = X = y = preprocessor = None
    val_struct = val_sem = {"errors": [], "warnings": [], "status": "N/A"}
    load_rep   = {"status": "N/A", "shapes": {"X": [0]}, "n_features": 0}

    log.info("╔" + "═" * 65 + "╗")
    log.info("║   BANCO PIPELINE V5 — KPIs DataOps / MLOps                   ║")
    log.info(f"║   {ts_inicio:<63}║")
    log.info("╚" + "═" * 65 + "╝")

    try:
        # ── Fase 1: Ingesta ───────────────────────────────────────────────────
        timers["ingesta"] = PhaseTimer("ingesta")
        with timers["ingesta"]:
            df_raw = load_data(file_path)

        # ── Fase 2: Limpieza ──────────────────────────────────────────────────
        timers["limpieza"] = PhaseTimer("limpieza")
        with timers["limpieza"]:
            df_clean = clean_data(df_raw)

        # ── Fase 3: Transformación ────────────────────────────────────────────
        timers["transformacion"] = PhaseTimer("transformacion")
        with timers["transformacion"]:
            X, y, preprocessor = transform_data(df_clean)

        # ── Fase 4A: Validación Estructural ───────────────────────────────────
        timers["validacion_estructural"] = PhaseTimer("validacion_estructural")
        with timers["validacion_estructural"]:
            val_struct = validate_structural(df_raw, df_clean, X)

        # ── Fase 4B: Validación Semántica ─────────────────────────────────────
        timers["validacion_semantica"] = PhaseTimer("validacion_semantica")
        with timers["validacion_semantica"]:
            val_sem = validate_semantic(df_clean, X)

        # ── Fase 5: Carga ─────────────────────────────────────────────────────
        timers["carga"] = PhaseTimer("carga")

        with timers["carga"]:
            load_rep = load_outputs(X, y, preprocessor, df_clean)

            # subida a supabase

            
            upload_to_supabase(df_clean)

        # Ajustar status según validaciones (no es error, pero requiere revisión)
        if val_struct.get("status") == "ERROR" or val_sem.get("status") == "ERROR":
            pipeline_status = "warning"

    except Exception as exc:
        # ── Captura de fallo: NO re-raise aquí → finally debe ejecutarse ──────
        pipeline_status = "error"
        _exc = exc
        log.error(f"  ❌ EXCEPCIÓN EN PIPELINE: {exc}")

        # Inicializar timers faltantes con elapsed=0 para no romper KPI 7.2
        for fase in ["ingesta", "limpieza", "transformacion",
                     "validacion_estructural", "validacion_semantica", "carga"]:
            if fase not in timers:
                t = PhaseTimer(fase); t.elapsed_seconds = 0.0; t.status = "error"
                timers[fase] = t

        # Inicializar DataFrames vacíos si el pipeline abortó antes de crearlos
        if df_raw   is None: df_raw   = pd.DataFrame()
        if df_clean is None: df_clean = pd.DataFrame()
        if X        is None: X        = pd.DataFrame()
        if y        is None: y        = pd.Series(dtype=int)

    finally:
        # ── GARANTÍA V5: siempre se ejecuta, exitoso O fallido ────────────────
        ts_now = datetime.now(timezone.utc).isoformat()
        elapsed_total = sum(t.elapsed_seconds for t in timers.values())

        # 1. Registrar run (CRÍTICO: en V4 esto nunca ocurría en runs fallidos)
        _EXEC_REGISTRY.record(pipeline_status, ts_now, elapsed_total)
        log.info(
            f"  [REGISTRY] Ejecución registrada: status={pipeline_status}  "
            f"total={_EXEC_REGISTRY.total}  "
            f"tasa_exito={_EXEC_REGISTRY.tasa_exito_pct:.1f}%"
        )

        # 2. Computar KPIs con los datos disponibles (parciales si hubo error)
        kpis = compute_kpis(
            df_raw=df_raw, df_clean=df_clean,
            X_transformed=X, y=y, preprocessor=preprocessor or ColumnTransformer([]),
            timers=timers,
            val_struct=val_struct, val_sem=val_sem,
            load_rep=load_rep,
            pipeline_status=pipeline_status,
            file_path=file_path,
            output_dir=OUTPUT_DIR_KPI,
        )

        # 3. Re-raise si hubo excepción (el caller debe saberlo)
        if _exc is not None:
            raise _exc

    log.info("╔" + "═" * 65 + "╗")
    log.info("║   PIPELINE V5 — EJECUCIÓN COMPLETADA                         ║")
    log.info(f"║   Health Score: {kpis['resumen']['health_score']}/100  [{kpis['resumen']['semaforo_global'].upper():<8}]{'':<33}║")
    log.info(f"║   Status      : {pipeline_status:<49}║")
    log.info(f"║   Filas       : {df_raw.shape[0]:,}{'':<49}║")
    log.info(f"║   Features    : {X.shape[1]:<49}║")
    log.info("╚" + "═" * 65 + "╝")

    return {
        "df_raw"     : df_raw,
        "df_clean"   : df_clean,
        "X"          : X,
        "y"          : y,
        "preprocessor": preprocessor,
        "val_struct" : val_struct,
        "val_sem"    : val_sem,
        "load_report": load_rep,
        "kpis"       : kpis,
    }


#  PUNTO DE ENTRADA


if __name__ == "__main__":

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


   