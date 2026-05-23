
import pandas as pd
from pathlib import Path

from src.utils.monitoring import log
from src.utils.config import (
FILE_PATH,
DTYPE_MAP,
ALL_EXPECTED_COLS,
)

def load_data(file_path: str = FILE_PATH) -> pd.DataFrame:
    """Fase 1: ingesta con detección automática de separador."""
    log.info("=" * 65)
    log.info("FASE 1 — INGESTA DE DATOS")
    log.info("=" * 65)
    if not Path(file_path).exists():
        raise FileNotFoundError(
            f"[INGESTA] Archivo no encontrado: '{file_path}'."
        )
    log.info(f"[1.1] Cargando: {file_path}")
    df = pd.read_csv(
        file_path, sep=None, engine="python",
        na_values=["", " ", "NA", "N/A"],
        keep_default_na=False, dtype=str,
    )
    log.info(f"  Leído: {df.shape[0]:,} filas × {df.shape[1]} columnas")
    original_cols = df.columns.tolist()
    df.columns    = df.columns.str.strip().str.lower()
    renamed = {o: n for o, n in zip(original_cols, df.columns) if o != n}
    if renamed: log.info(f"[1.2] Columnas renombradas: {renamed}")
    for col in [c for c in DTYPE_MAP if c in df.columns]:
        if DTYPE_MAP[col] == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    cols_faltantes = [c for c in ALL_EXPECTED_COLS if c not in df.columns]
    if cols_faltantes:
        log.warning(f"  ⚠ Columnas ausentes ({len(cols_faltantes)}): {cols_faltantes}")
    else:
        log.info("  ✓ Todas las columnas del esquema presentes.")
    log.info(f"  Nulos reales: {df.isnull().sum().sum()}")
    log.info("=" * 65 + "\nFASE 1 — COMPLETADA\n" + "=" * 65)
    return df