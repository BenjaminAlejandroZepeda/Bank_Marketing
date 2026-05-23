from pathlib import Path

from src.utils.monitoring import (
_EXEC_REGISTRY,
_semaforo,
)

def compute_kpi_disponibilidad(
    file_path      : str,
    pipeline_status: str,
    elapsed_secs   : float,
) -> dict:
    """
    Mide disponibilidad e integridad de acceso al pipeline.

    Métricas
    --------
    archivo_disponible    → bool: el CSV existe en la ruta configurada
    archivo_legible       → bool: pandas puede leer 5 filas sin error
    archivo_size_bytes    → int
    pipeline_status       → "success" | "warning" | "error"
    ejecuciones_totales   → int (acumulado en sesión)
    ejecuciones_exitosas  → int
    ejecuciones_warnings  → int
    ejecuciones_errores   → int
    tasa_exito_pct        → float  (solo success / total)
    tasa_disponibilidad_pct → float (success + warning / total)
    semaforo              → "verde" | "amarillo" | "rojo"

    Garantía V5
    -----------
    Este método es llamado desde compute_kpis() que a su vez se invoca desde
    el bloque finally de run_with_kpis(). El registro en _EXEC_REGISTRY ya
    ocurrió antes, por lo tanto tasa_exito_pct incluye el run actual (exitoso o fallido).
    """
    log.info("-" * 55)
    log.info("[KPI 7.1] DISPONIBILIDAD")
    log.info("-" * 55)

    path_obj       = Path(file_path)
    archivo_existe = path_obj.exists()
    archivo_size   = path_obj.stat().st_size if archivo_existe else 0

    log.info(f"  archivo_disponible      : {archivo_existe}")
    if archivo_existe:
        log.info(f"  archivo_size            : {archivo_size:,} bytes ({archivo_size/1024:.1f} KB)")
    else:
        log.error(f"  ❌ Archivo NO encontrado: {file_path}")

    archivo_legible = False
    if archivo_existe:
        try:
            pd.read_csv(file_path, sep=None, engine="python", nrows=5,
                        keep_default_na=False)
            archivo_legible = True
            log.info("  archivo_legible         : True  (lectura de muestra OK)")
        except Exception as e:
            log.error(f"  ❌ Error al leer archivo: {e}")

    # ── Usar estado ya registrado en _EXEC_REGISTRY ───────────────────────────
    # En V4 el record() solo se llamaba en runs exitosos.
    # En V5 se garantiza que _EXEC_REGISTRY ya tiene el run actual registrado
    # antes de llamar a compute_kpis() (ver bloque finally en run_with_kpis).
    tasa_ex   = _EXEC_REGISTRY.tasa_exito_pct
    tasa_disp = _EXEC_REGISTRY.tasa_disponibilidad_pct

    log.info(f"  pipeline_status         : {pipeline_status}")
    log.info(
        f"  ejecuciones             : total={_EXEC_REGISTRY.total}  "
        f"exitosas={_EXEC_REGISTRY.exitosas}  "
        f"warnings={_EXEC_REGISTRY.warnings}  "
        f"errores={_EXEC_REGISTRY.errores}"
    )
    log.info(f"  tasa_exito_pct          : {tasa_ex:.2f}%")
    log.info(f"  tasa_disponibilidad_pct : {tasa_disp:.2f}%")

    if not archivo_existe or not archivo_legible or pipeline_status == "error":
        sem = "rojo"
    elif tasa_ex < THRESHOLDS["min_tasa_exito_pct"]:
        sem = "amarillo"
    else:
        sem = "verde"

    log.info(f"  semaforo                : {_SEM_ICON[sem]} {sem.upper()}")

    return {
        "archivo_disponible"       : archivo_existe,
        "archivo_legible"          : archivo_legible,
        "archivo_size_bytes"       : archivo_size,
        "archivo_path"             : str(file_path),
        "pipeline_status"          : pipeline_status,
        "ejecuciones_totales"      : _EXEC_REGISTRY.total,
        "ejecuciones_exitosas"     : _EXEC_REGISTRY.exitosas,
        "ejecuciones_warnings"     : _EXEC_REGISTRY.warnings,
        "ejecuciones_errores"      : _EXEC_REGISTRY.errores,
        "tasa_exito_pct"           : tasa_ex,
        "tasa_disponibilidad_pct"  : tasa_disp,
        "timestamp_ejecucion"      : datetime.now(timezone.utc).isoformat(),
        "semaforo"                 : sem,
    }