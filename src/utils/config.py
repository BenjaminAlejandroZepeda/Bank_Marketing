from pathlib import Path
from dotenv import load_dotenv
import logging
import numpy as np

# Cargar variables de entorno si existiera un archivo .env
load_dotenv()

#  BLOQUE 0 — CONFIGURACIÓN Y ESQUEMA

BASE_DIR = Path(__file__).resolve().parents[2]

FILE_PATH = BASE_DIR / "02_bank.csv"

OUTPUT_DIR_KPI = BASE_DIR / "pipeline_outputs"

LOG_LEVEL       = logging.INFO

EXPORT_KPI_JSON     = False
EXPORT_LOAD_CSV     = False
EXPORT_LOAD_PARQUET = False

NUMERIC_COLS: list[str] = [
    "age", "balance", "day", "duration", "campaign", "pdays", "previous"
]
CATEGORICAL_COLS: list[str] = [
    "job", "marital", "education", "contact", "poutcome", "month"
]
BINARY_COLS: list[str] = ["default", "housing", "loan", "deposit"]
ALL_EXPECTED_COLS: list[str] = NUMERIC_COLS + CATEGORICAL_COLS + BINARY_COLS

DTYPE_MAP: dict = {
    **{col: "float64" for col in NUMERIC_COLS},
    **{col: "object"  for col in CATEGORICAL_COLS},
    **{col: "object"  for col in BINARY_COLS},
}

EDUCATION_ORDER : list[list[str]] = [["primary", "secondary", "tertiary"]]
OHE_COLS        : list[str]       = ["job", "marital", "contact", "poutcome"]
ROBUST_COLS     : list[str]       = ["balance"]
STANDARD_COLS   : list[str]       = ["age", "pdays", "previous", "campaign"]
TARGET_COL      : str             = "deposit"

OUTLIER_CONTINUOUS_COLS: list[str] = ["balance", "campaign", "pdays", "previous"]
OUTLIER_SPECIAL_EXCLUDE: dict      = {"pdays": [-1]}
OUTLIER_TREATMENT_STRATEGY         = None
WINSORIZE_LIMITS                   = (0.01, 0.01)
CLIP_PERCENTILE_LIMITS             = (0.01, 0.99)

CRITICAL_UNIQUE_COLS: list[str] = [
    "job", "marital", "education", "contact", "poutcome",
    "default", "housing", "loan", "deposit",
]
_BINARY_YES_VARIANTS: set[str] = {"yes", "y", "1", "true"}
_BINARY_NO_VARIANTS : set[str] = {"no",  "n", "0", "false"}
_MONTH_MAP: dict[str, int] = {
    "jan": 1, "feb": 2,  "mar": 3,  "apr": 4,
    "may": 5, "jun": 6,  "jul": 7,  "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
EXPECTED_FLAG_COLS: list[str] = [
    "flag_balance_negativo", "flag_outlier_balance",
    "flag_outlier_campaign", "pdays_flag_nuevo_cliente",
    "flag_outlier_pdays",    "flag_outlier_previous",
]

# ── Umbrales de semáforo ──────────────────────────────────────────────────────
THRESHOLDS: dict = {
    # Disponibilidad
    "min_tasa_exito_pct"      : 95.0,
    # Rendimiento (segundos)
    "max_pipeline_secs"       : 120.0,
    "max_ingesta_secs"        : 10.0,
    "max_limpieza_secs"       : 15.0,
    "max_transformacion_secs" : 30.0,
    "max_validacion_secs"     : 20.0,
    "max_carga_secs"          : 5.0,
    # Calidad
    "max_nan_pct_clean"       : 1.0,
    "max_nan_pct_X"           : 0.0,   
    "max_outlier_pct"         : 15.0,
    "min_class_minority_pct"  : 20.0,
    "min_columnas_validas_pct": 90.0,
    # Costo
    "max_costo_usd"           : 0.10,
}

COST_MODEL: dict = {
    "compute_usd_per_hour" : 0.0950,
    "storage_usd_per_gb_mo": 0.020,
    "io_usd_per_gb"        : 0.010,
    "overhead_factor"      : 1.15,
}

