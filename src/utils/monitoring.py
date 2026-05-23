#  BLOQUE 1 — LOGGER ESTRUCTURADO
#  INFO → ejecución normal | WARNING → calidad | ERROR → fallo crítico


import logging
import time

from dataclasses import dataclass, field

import pandas as pd

from src.utils.config import LOG_LEVEL

from datetime import datetime, timezone



def _build_logger(name: str = "BankPipeline.KPI") -> logging.Logger:
    """Logger con formato timestamp | nivel | mensaje. Evita duplicar handlers."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(h)
        logger.setLevel(LOG_LEVEL)
        logger.propagate = False
    return logger

log = _build_logger()


#  BLOQUE 2 — INFRAESTRUCTURA DE MEDICIÓN


@dataclass
class PhaseTimer:
    """
    Cronómetro de contexto para medir una fase del pipeline.

    Uso
    ---
    with PhaseTimer("ingesta") as t:
        df = load_data()
    print(t.elapsed_seconds)
    """
    phase_name     : str
    start_time     : float = field(default=0.0, init=False)
    end_time       : float = field(default=0.0, init=False)
    elapsed_seconds: float = field(default=0.0, init=False)
    status         : str   = field(default="pending", init=False)

    def __enter__(self):
        self.start_time = time.perf_counter()
        log.info(f"  ⏱  [{self.phase_name}] inicio")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time        = time.perf_counter()
        self.elapsed_seconds = round(self.end_time - self.start_time, 4)
        self.status          = "error" if exc_type else "ok"
        icon = "✓" if self.status == "ok" else "✗"
        log.info(
            f"  {icon} [{self.phase_name}] fin  |  "
            f"{self.elapsed_seconds:.4f}s  |  status={self.status}"
        )
        return False   # no suprimir excepciones


@dataclass
class ExecutionRegistry:
    """
    Registro acumulado de ejecuciones en memoria de sesión.

    Permite calcular la tasa de éxito real incluyendo runs fallidos.
    En producción: reemplazar por Redis, DynamoDB, o tabla en BigQuery.

    Garantía V5
    -----------
    run_with_kpis() llama a record() desde un bloque finally, lo que asegura
    que TODAS las ejecuciones — exitosas, con warning y fallidas — queden
    registradas, haciendo tasa_exito_pct estadísticamente correcto.
    """
    total    : int  = 0
    exitosas : int  = 0
    warnings : int  = 0
    errores  : int  = 0
    history  : list = field(default_factory=list)

    def record(self, status: str, ts: str, secs: float) -> None:
        self.total += 1
        if status == "success":
            self.exitosas += 1
        elif status == "warning":
            self.warnings += 1
        else:
            self.errores += 1
        self.history.append({"ts": ts, "status": status, "secs": secs})
        if len(self.history) > 100:
            self.history = self.history[-100:]

    @property
    def tasa_exito_pct(self) -> float:
        """% de ejecuciones exitosas (status='success') sobre el total."""
        return round(self.exitosas / self.total * 100, 2) if self.total > 0 else 0.0

    @property
    def tasa_disponibilidad_pct(self) -> float:
        """% de ejecuciones no-fallidas (success + warning) sobre el total."""
        return round((self.exitosas + self.warnings) / self.total * 100, 2) if self.total > 0 else 0.0


# Instancia global 
_EXEC_REGISTRY = ExecutionRegistry()


def _semaforo(value: float, verde_lim: float, amarillo_lim: float,
              invert: bool = False) -> str:
    """
    Asigna nivel de semáforo basado en umbrales.

    invert=False (mayor es mejor): value >= verde_lim    → verde
    invert=True  (menor es mejor): value <= verde_lim    → verde
    """
    if not invert:
        if value >= verde_lim:    return "verde"
        if value >= amarillo_lim: return "amarillo"
        return "rojo"
    else:
        if value <= verde_lim:    return "verde"
        if value <= amarillo_lim: return "amarillo"
        return "rojo"


_SEM_ICON: dict[str, str] = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}


def _checkpoint(label: str, df: pd.DataFrame) -> None:
    """Checkpoint de trazabilidad: shape + columnas."""
    log.info(f"  [CHECKPOINT: {label}] shape={df.shape} | cols={df.columns.tolist()}")
