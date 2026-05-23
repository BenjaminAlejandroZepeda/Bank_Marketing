from pathlib import Path

from src.utils.monitoring import _semaforo
from src.utils.config import FILE_PATH, OUTPUT_DIR_KPI
import os
import pandas as pd

def compute_kpi_costo(
    n_rows      : int,
    n_features  : int,
    elapsed_secs: float,
    file_path   : str  = FILE_PATH,
    output_dir  : Path = OUTPUT_DIR_KPI,
) -> dict:
    """
    Estimación de costos de cómputo, I/O y almacenamiento.

    Modelo de costos orientativo (GCP n1-standard-2 ~$0.095/hora).
    Para costos reales usar: Cloud Billing API / AWS Cost Explorer.
    """
    log.info("-" * 55)
    log.info("[KPI 7.4] COSTO (simulación)")
    log.info("-" * 55)

    horas_usadas        = elapsed_secs / 3600
    costo_computo_final = round(
        horas_usadas * COST_MODEL["compute_usd_per_hour"] * COST_MODEL["overhead_factor"], 8
    )
    input_bytes  = Path(file_path).stat().st_size if Path(file_path).exists() else 0
    input_gb     = input_bytes / (1024 ** 3)
    costo_io     = round(input_gb * COST_MODEL["io_usd_per_gb"], 8)

    output_bytes  = sum(f.stat().st_size for f in output_dir.rglob("*")
                        if f.is_file()) if output_dir.exists() else 0
    output_gb_mo  = output_bytes / (1024 ** 3)
    costo_storage = round(output_gb_mo * COST_MODEL["storage_usd_per_gb_mo"], 8)

    costo_total           = round(costo_computo_final + costo_io + costo_storage, 8)
    costo_por_1k_filas    = round(costo_total / (n_rows / 1000), 8) if n_rows > 0 else 0.0
    filas_por_centavo_usd = round(n_rows / (costo_total * 100), 1) if costo_total > 0 else 0.0
    eficiencia_score      = min(100, round((filas_por_centavo_usd / 10_000) * 100, 1))

    sem = _semaforo(costo_total,
                    THRESHOLDS["max_costo_usd"] * 0.5,
                    THRESHOLDS["max_costo_usd"], invert=True)

    log.info(f"  filas_procesadas           : {n_rows:,}")
    log.info(f"  features_generados         : {n_features}")
    log.info(f"  tiempo_ejecucion           : {elapsed_secs:.4f}s ({horas_usadas:.6f}h)")
    log.info(f"  input_size                 : {input_bytes:,} bytes ({input_gb*1024:.2f} KB)")
    log.info(f"  output_size                : {output_bytes:,} bytes")
    log.info(f"  costo_computo_usd          : ${costo_computo_final:.8f}")
    log.info(f"  costo_io_usd               : ${costo_io:.8f}")
    log.info(f"  costo_storage_usd          : ${costo_storage:.8f}")
    log.info(f"  costo_total_estimado_usd   : ${costo_total:.8f}")
    log.info(f"  costo_por_1000_filas_usd   : ${costo_por_1k_filas:.8f}")
    log.info(f"  filas_por_centavo_usd      : {filas_por_centavo_usd:,.1f}")
    log.info(f"  eficiencia_score           : {eficiencia_score}/100")
    log.info(f"  {_SEM_ICON[sem]} semaforo : {sem.upper()}")
    log.info(f"  [NOTA] Simulación orientativa — usar APIs de billing para costos reales.")

    return {
        "filas_procesadas"             : n_rows,
        "features_generados"           : n_features,
        "tiempo_ejecucion_segundos"    : elapsed_secs,
        "input_size_bytes"             : input_bytes,
        "output_size_bytes"            : output_bytes,
        "costo_computo_usd"            : costo_computo_final,
        "costo_io_usd"                 : costo_io,
        "costo_storage_usd"            : costo_storage,
        "costo_estimado_procesamiento" : costo_total,
        "costo_por_1000_filas_usd"     : costo_por_1k_filas,
        "filas_por_centavo_usd"        : filas_por_centavo_usd,
        "eficiencia"                   : eficiencia_score,
        "modelo_costo"                 : COST_MODEL,
        "nota"                         : "Simulación orientativa. Usar APIs de billing para costos reales.",
        "semaforo"                     : sem,
    }
