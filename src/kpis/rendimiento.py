from src.utils.monitoring import _semaforo



def compute_kpi_rendimiento(
    timers     : dict,
    n_rows     : int,
    n_features : int,
) -> dict:
    """
    Mide latencia total y por fase, throughput, y fase más lenta.

    Corrección V5 [MENOR-4]
    -----------------------
    semaforos_fase: simplificado de un dict-comprehension con zip anidado a una
    comprensión directa sobre fases_t.items(). Mismo resultado, mayor legibilidad.
    """
    log.info("-" * 55)
    log.info("[KPI 7.2] RENDIMIENTO")
    log.info("-" * 55)

    def _t(k: str) -> float:
        obj = timers.get(k)
        return obj.elapsed_seconds if obj else 0.0

    t_ingesta    = _t("ingesta")
    t_limpieza   = _t("limpieza")
    t_transform  = _t("transformacion")
    t_val_est    = _t("validacion_estructural")
    t_val_sem    = _t("validacion_semantica")
    t_validacion = round(t_val_est + t_val_sem, 4)
    t_carga      = _t("carga")
    t_total      = round(t_ingesta + t_limpieza + t_transform + t_validacion + t_carga, 4)

    throughput_filas    = round(n_rows    / t_total, 1) if t_total > 0 else 0.0
    throughput_features = round(n_features / t_total, 1) if t_total > 0 else 0.0

    fases_t = {
        "ingesta"       : t_ingesta,
        "limpieza"      : t_limpieza,
        "transformacion": t_transform,
        "validacion"    : t_validacion,
        "carga"         : t_carga,
    }
    umbrales_fase = {
        "ingesta"       : THRESHOLDS["max_ingesta_secs"],
        "limpieza"      : THRESHOLDS["max_limpieza_secs"],
        "transformacion": THRESHOLDS["max_transformacion_secs"],
        "validacion"    : THRESHOLDS["max_validacion_secs"],
        "carga"         : THRESHOLDS["max_carga_secs"],
    }

    # FIX V5 [MENOR-4]: simplificado respecto a V4
    semaforos_fase = {
        fase: _semaforo(t, umbrales_fase[fase] * 0.6, umbrales_fase[fase], invert=True)
        for fase, t in fases_t.items()
    }
    fase_lenta = max(fases_t, key=fases_t.get)
    sem_global = _semaforo(t_total,
                           THRESHOLDS["max_pipeline_secs"] * 0.5,
                           THRESHOLDS["max_pipeline_secs"], invert=True)

    for fase, t in fases_t.items():
        icon = _SEM_ICON[semaforos_fase[fase]]
        log.info(f"  {icon} {fase:<20} {t:>8.4f}s  [umbral: {umbrales_fase[fase]}s]")
    log.info(f"  {'─'*45}")
    log.info(f"  {_SEM_ICON[sem_global]} {'TOTAL':<20} {t_total:>8.4f}s")
    log.info(f"  throughput         : {throughput_filas:,.1f} filas/s  |  {throughput_features:,.1f} features/s")
    log.info(f"  fase_mas_lenta     : {fase_lenta} ({fases_t[fase_lenta]:.4f}s)")

    return {
        "tiempo_total_segundos"          : t_total,
        "tiempo_ingesta_segundos"        : t_ingesta,
        "tiempo_limpieza_segundos"       : t_limpieza,
        "tiempo_transformacion_segundos" : t_transform,
        "tiempo_validacion_segundos"     : t_validacion,
        "tiempo_carga_segundos"          : t_carga,
        "throughput_filas_por_seg"       : throughput_filas,
        "throughput_features_por_seg"    : throughput_features,
        "fase_mas_lenta"                 : fase_lenta,
        "semaforo_por_fase"              : semaforos_fase,
        "semaforo_global"                : sem_global,
    }
