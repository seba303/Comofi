"""Configuración central de Comofi.

Todos los valores ajustables viven aquí para evitar código quemado en la lógica.

Programa creado por Sebastián Romero
"""

from pathlib import Path

# Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLES_DIR = DATA_DIR / "sample_files"
DB_PATH = DATA_DIR / "comofi.db"

# Nombres de los CSV de ejemplo que se generan con "python main.py generar-ejemplos"
BANK_SAMPLE_NAME = "movimientos_bancarios.csv"
INTERNAL_SAMPLE_NAME = "registros_internos.csv"

# Cabeceras esperadas en cada origen (validación al importar)
BANK_REQUIRED_COLUMNS = ["fecha", "referencia", "concepto", "importe"]
INTERNAL_REQUIRED_COLUMNS = ["fecha", "id_operacion", "detalle", "importe"]

# Columnas internas normalizadas tras la lectura de cualquier CSV
COL_DATE = "fecha"
COL_ID = "referencia"
COL_CONCEPT = "concepto"
COL_AMOUNT = "importe"

# Fechas: formatos aceptados al leer (el primero que funciona gana)
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
EXPORT_DATE_FORMAT = "%Y-%m-%d"

# Tolerancias de conciliación
AMOUNT_TOLERANCE = 0.01          # euros de diferencia máxima para considerar igualdad
DAYS_WINDOW = 5                  # desplazamiento máximo en días entre ambas fechas
DATE_DIFF_ALERT_DAYS = 1         # si difieren más de estos días, se señala como desajuste

# Coincidencia aproximada: pesos para puntuar candidatos
FUZZY_MIN_SCORE = 0.45           # puntuación mínima (0..1) para aceptar un emparejamiento
WEIGHT_AMOUNT = 0.6              # peso de la similitud de importe
WEIGHT_CONCEPT = 0.4             # peso de la similitud de concepto

# Historial de revisiones
MAX_REVISIONS_KEPT = 200         # número máximo de revisiones almacenadas en SQLite

# Exportación
RESULTS_DIR_NAME = "resultados"  # carpeta dentro de data/ donde se escriben los CSV exportados
