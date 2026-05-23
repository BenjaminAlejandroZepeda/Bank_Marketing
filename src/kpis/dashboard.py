import json
import time

from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from sklearn.compose import ColumnTransformer

from src.utils.monitoring import (
log,
_SEM_ICON,
)

from src.utils.config import (
FILE_PATH,
OUTPUT_DIR_KPI,
EXPORT_KPI_JSON,
)

from src.kpis.disponibilidad import compute_kpi_disponibilidad
from src.kpis.rendimiento import compute_kpi_rendimiento
from src.kpis.calidad import compute_kpi_calidad
from src.kpis.costo import compute_kpi_costo


def compute_kpis(
    df_raw        : pd.DataFrame,
    df_clean      : pd.DataFrame,
    X_transformed : pd.DataFrame,
    y             : pd.Series,
    preprocessor  : ColumnTransformer,
    timers        : dict,
    val_struct    : dict,
    val_sem       : dict,
    load_rep      : dict,
    pipeline_status: str,
    file_path     : str  = FILE_PATH,
    output_dir    : Path = OUTPUT_DIR_KPI,
) -> dict:
    """
    Consolida los cuatro KPIs en un único reporte estructurado.

    Health Score global (0-100)
    ---------------------------
    Ponderado: calidad (40%) · disponibilidad (30%) · rendimiento (20%) · costo (10%)

    Corrección V5 [MENOR-3]
    -----------------------
    load_rep ahora incluido en el dict kpis bajo la clave "fase_carga", dando
    trazabilidad completa a la Fase 5 en el reporte final.

    Estructura de salida
    --------------------
    {
      "metadata"     : timestamp, version, run_id
      "disponibilidad": kpi 7.1
      "rendimiento"  : kpi 7.2
      "calidad"      : kpi 7.3
      "costo"        : kpi 7.4
      "fase_carga"   : report de load_outputs   ← nuevo V5
      "resumen"      : health_score, semaforo_global, alertas
    }
    """
    log.info("=" * 65)
    log.info("SECCIÓN 7 — CONSOLIDACIÓN DE KPIs")
    log.info("=" * 65)

    t_total = sum(t.elapsed_seconds for t in timers.values() if t is not None)

    kpi_disp = compute_kpi_disponibilidad(file_path, pipeline_status, t_total)
    kpi_rend = compute_kpi_rendimiento(timers, df_raw.shape[0], X_transformed.shape[1])
    kpi_cal  = compute_kpi_calidad(df_raw, df_clean, X_transformed, y, val_struct, val_sem)
    kpi_cost = compute_kpi_costo(df_raw.shape[0], X_transformed.shape[1],
                                  t_total, file_path, output_dir)

    # ── Health Score ──────────────────────────────────────────────────────────
    SEM_SCORE = {"verde": 100, "amarillo": 60, "rojo": 0}
    scores    = {
        "disponibilidad": SEM_SCORE[kpi_disp["semaforo"]],
        "rendimiento"   : SEM_SCORE[kpi_rend["semaforo_global"]],
        "calidad"       : kpi_cal["score_calidad"],
        "costo"         : SEM_SCORE[kpi_cost["semaforo"]],
    }
    weights      = {"disponibilidad": 0.30, "rendimiento": 0.20, "calidad": 0.40, "costo": 0.10}
    health_score = round(sum(scores[k] * weights[k] for k in scores), 1)
    sem_global   = "verde" if health_score >= 85 else ("amarillo" if health_score >= 60 else "rojo")

    # ── Alertas ───────────────────────────────────────────────────────────────
    alertas = []
    if not kpi_disp["archivo_disponible"]:
        alertas.append("❌ CRÍTICO: Archivo de entrada no disponible")
    if kpi_disp["semaforo"] == "rojo":
        alertas.append(f"🔴 Disponibilidad degradada: tasa_exito={kpi_disp['tasa_exito_pct']}%")
    if kpi_rend["semaforo_global"] == "rojo":
        alertas.append(f"🔴 Rendimiento fuera de umbral: {kpi_rend['tiempo_total_segundos']}s")
    if kpi_cal["semaforo_global"] == "rojo":
        alertas.append(f"🔴 Calidad degradada: score={kpi_cal['score_calidad']}/100")
    if kpi_cal["missing_values_pct"]["X_pct"] > 0:
        alertas.append(f"🔴 NaN en X_transformed: {kpi_cal['missing_values_pct']['X_pct']:.4f}%")
    if not kpi_cal["consistencia_tipos"]:
        alertas.append("🔴 X_transformed contiene columnas no numéricas")
    if kpi_cost["semaforo"] == "rojo":
        alertas.append(f"🔴 Costo sobre umbral: ${kpi_cost['costo_estimado_procesamiento']:.6f}")
    if load_rep.get("status") == "ERROR":
        alertas.append("❌ FASE 5: error en carga/alineación de artefactos")
    for w in val_sem.get("warnings", []):
        alertas.append(f"⚠ Semántica: {w}")
    for e in val_struct.get("errors", []):
        alertas.append(f"❌ Estructural: {e}")

    resumen = {
        "health_score"      : health_score,
        "semaforo_global"   : sem_global,
        "scores_por_kpi"    : scores,
        "n_alertas"         : len(alertas),
        "alertas"           : alertas,
        "pipeline_status"   : pipeline_status,
        "filas_procesadas"  : df_raw.shape[0],
        "features_generados": X_transformed.shape[1],
    }

    kpis = {
        "metadata": {
            "timestamp"       : datetime.now(timezone.utc).isoformat(),
            "pipeline_version": "5.0.0",
            "run_id"          : f"run_{int(time.time())}",
            "file_procesado"  : str(file_path),
        },
        "disponibilidad": kpi_disp,
        "rendimiento"   : kpi_rend,
        "calidad"       : kpi_cal,
        "costo"         : kpi_cost,
        "fase_carga"    : load_rep,    # FIX V5 [MENOR-3]: antes ausente del dict
        "resumen"       : resumen,
    }

    if EXPORT_KPI_JSON:
        output_dir.mkdir(parents=True, exist_ok=True)
        p = output_dir / "kpi_report.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(kpis, f, indent=2, ensure_ascii=False, default=str)
        log.info(f"  KPI report exportado → {p}")

    _print_kpi_dashboard(kpis)

    log.info("=" * 65)
    log.info(f"SECCIÓN 7 — COMPLETADA | Health Score: {health_score}/100 [{sem_global.upper()}]")
    log.info("=" * 65)
    return kpis




def _print_kpi_dashboard(kpis: dict) -> None:
    """
    Dashboard visual en consola.

    Corrección V5 [ESTÉTICO-5]
    --------------------------
    La línea HEALTH SCORE usaba un emoji de ancho visual 2 que desalineaba
    los bordes ║ del box. Ajustado el espaciado interno para que coincida.
    """
    r    = kpis["resumen"]
    d    = kpis["disponibilidad"]
    rend = kpis["rendimiento"]
    cal  = kpis["calidad"]
    cost = kpis["costo"]
    load = kpis.get("fase_carga", {})
    ts   = kpis["metadata"]["timestamp"][:19].replace("T", " ")
    hs   = r["health_score"]
    sg   = r["semaforo_global"]
    W    = 65   # ancho interior del box (sin los ║)

    def _line(content: str = "") -> str:
        """Línea interior del box, sin padding (padding es responsabilidad del caller)."""
        return f"║{content:{W}}║"

    print()
    print("╔" + "═" * W + "╗")
    print(_line(f"  {'DASHBOARD KPIs DataOps — BankPipeline V5':^{W-2}}"))
    print(_line(f"  {'Run: ' + ts:^{W-2}}"))
    print("╠" + "═" * W + "╣")

    # FIX [ESTÉTICO-5]: emoji tiene ancho visual 2 pero len() 1 en Python.
    # Compensamos con un espacio extra para alinear correctamente.
    icon = _SEM_ICON[sg]
    hs_line = f"  {icon}  HEALTH SCORE: {hs}/100  [{sg.upper():<8}]"
    print(f"║{hs_line:<{W}}║")
    print("╠" + "═" * W + "╣")

    # Categorías
    print(_line(f"  {'CATEGORÍA':<22}{'SCORE':>8}  {'SEMÁFORO':<12}{'DETALLE':<21}"))
    print(_line(f"  {'─'*(W-2)}"))
    cat_rows = [
        ("7.1 Disponibilidad", r["scores_por_kpi"]["disponibilidad"],
         d["semaforo"],          f"tasa_éxito={d['tasa_exito_pct']:.1f}%"),
        ("7.2 Rendimiento",    r["scores_por_kpi"]["rendimiento"],
         rend["semaforo_global"],f"total={rend['tiempo_total_segundos']:.3f}s"),
        ("7.3 Calidad",        cal["score_calidad"],
         cal["semaforo_global"], f"válidas={cal['columnas_validas_pct']:.1f}%"),
        ("7.4 Costo",          r["scores_por_kpi"]["costo"],
         cost["semaforo"],       f"${cost['costo_estimado_procesamiento']:.7f}"),
    ]
    for nombre, sc, sem_cat, detalle in cat_rows:
        icon_c = _SEM_ICON[sem_cat]
        row    = f"  {icon_c} {nombre:<20}  {sc:>6}/100  {sem_cat.upper():<12}{detalle:<20}"
        print(f"║{row:<{W}}║")

    print("╠" + "═" * W + "╣")

    # Rendimiento por fase
    print(_line("  RENDIMIENTO POR FASE:"))
    for fase in ["ingesta", "limpieza", "transformacion", "validacion", "carga"]:
        secs   = rend.get(f"tiempo_{fase}_segundos", 0.0)
        icon_f = _SEM_ICON[rend["semaforo_por_fase"][fase]]
        bar    = "█" * min(20, int(secs * 10)) + "░" * max(0, 20 - int(secs * 10))
        row    = f"    {icon_f} {fase:<18} {secs:>7.4f}s  {bar}"
        print(f"║{row:<{W}}║")

    print("╠" + "═" * W + "╣")

    # Calidad + Carga
    m_val = cal["missing_values_pct"]
    cb    = cal["class_balance"]
    print(_line("  CALIDAD:"))
    nan_row  = f"    NaN%(X): {m_val['X_pct']:>7.4f}% {_SEM_ICON[m_val['semaforo']]}"
    cls_row  = f"   Clases: 0={cb['clase_0_pct']:.1f}%  1={cb['clase_1_pct']:.1f}% {_SEM_ICON[cb['semaforo']]}"
    print(f"║    {nan_row:<30}{cls_row:<{W-35}}║")

    load_status = load.get("status", "N/A")
    load_icon   = "✓" if load_status == "OK" else "❌"
    load_n      = load.get("shapes", {}).get("X", ["?"])[0]
    print(_line(f"  CARGA: {load_icon} status={load_status}  │  {load_n:,} registros exportables"))

    print("╠" + "═" * W + "╣")

    # Alertas
    n_al = r["n_alertas"]
    if n_al:
        print(_line(f"  ALERTAS ({n_al}):"))
        for a in r["alertas"][:5]:
            print(_line(f"    {a[:W-6]}"))
        if n_al > 5:
            print(_line(f"    ... y {n_al-5} alerta(s) más → kpis['resumen']['alertas']"))
    else:
        print(_line("  ✓ Sin alertas activas."))

    print("╚" + "═" * W + "╝")
    print()
