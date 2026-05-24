import os
import sys
from loguru import logger
from src.config import RUTA_LOGS

# 1. Limpiar configuraciones por defecto del sistema
logger.remove()

# 2. Formato profesional estandarizado para DataOps
FORMATO_LOG = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 3. Salida a consola (Muestra inmediata para el docente en la Demo en vivo)
logger.add(
    sys.stdout,
    format=FORMATO_LOG,
    level="INFO",
    enqueue=True
)

# 4. Salida a archivo físico (Evidencia inmutable exigida por la rúbrica)
# Generará un archivo tipo: logs/pipeline_2026-05-21.log
logger.add(
    os.path.join(RUTA_LOGS, "pipeline_{time:YYYY-MM-DD}.log"),
    format=FORMATO_LOG,
    level="DEBUG",
    rotation="10 MB",     # Si el archivo llega a 10MB, crea otro para no saturar
    retention="10 days",  # Mantiene historial por 10 días
    enqueue=True
)

# Exportar el logger listo para usar
__all__ = ["logger"]