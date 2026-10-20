"""Generación de archivos CSV ficticios para probar Comofi.

Los datos son inventados: no contienen información bancaria real.
Incluyen a propósito los casos que el motor debe detectar (coincidencias,
diferencias de importe y fecha, duplicados y pendientes).

Programa creado por Sebastián Romero
"""

import csv
from pathlib import Path

from comofi import config

# Cada tupla: (fecha, referencia, concepto, importe)
BANK_ROWS = [
    ("2026-03-02", "TRX-1001", "Transferencia cliente Alpha SL", "1500.00"),
    ("2026-03-02", "TRX-1002", "Domiciliacion proveedor Beta SA", "-480.75"),
    ("2026-03-03", "TRX-1003", "Alquiler oficina marzo", "-1200.00"),
    ("2026-03-04", "TRX-1004", "Transferencia cliente Gamma SL", "2750.00"),
    ("2026-03-05", "TRX-1005", "Comision mantenimiento cuenta", "-15.00"),
    ("2026-03-05", "TRX-1006", "Nomina plantilla marzo", "-5430.20"),
    ("2026-03-06", "TRX-1007", "Transferencia cliente Delta SL", "980.00"),
    ("2026-03-09", "TRX-1008", "Domiciliacion luz Iberbasica", "-213.40"),
    ("2026-03-10", "TRX-1009", "Ingreso venta online lote 24", "645.90"),
    ("2026-03-11", "TRX-1010", "Transferencia proveedor Epsilon SL", "-1340.00"),
    # Duplicado exacto en el banco (misma fecha, importe y concepto)
    ("2026-03-11", "TRX-1011", "Reintegro efectivo caja fuerte", "-300.00"),
    ("2026-03-11", "TRX-1012", "Reintegro efectivo caja fuerte", "-300.00"),
    # Pendiente: sin contrapartida interna (comision no registrada)
    ("2026-03-12", "TRX-1013", "Comision transferencia internacional", "8.50"),
    # Coincidencia aproximada: la interna usa otro concepto (venta online)
    ("2026-03-13", "TRX-1014", "Pago software contable mensual", "-59.99"),
]

# Conceptos con naming distinto a propósito, para que el emparejamiento
# aproximado por similitud (difflib.SequenceMatcher + umbral FUZZY_MIN_SCORE
# de config.py) sea el único modo de encontrarles contrapartida.
INTERNAL_ROWS = [
    ("2026-03-02", "OP-1001", "Cobro Alpha SL factura 2026-014", "1500.00"),
    ("2026-03-02", "OP-1002", "Pago Beta SA factura F-2291", "-480.75"),
    # Diferencia de importe: registrado -1200.50 frente a -1200.00 del banco
    ("2026-03-03", "OP-1003", "Alquiler oficina marzo", "-1200.50"),
    # Referencia distinta (OP- vs TRX-) y concepto propio: queda pendiente interno
    ("2026-03-04", "OP-9004", "Cobro Gamma SL factura 2026-015", "2750.00"),
    ("2026-03-05", "OP-1006", "Nomina plantilla marzo", "-5430.20"),
    # Diferencia de fecha: interno registrado dos dias despues
    ("2026-03-08", "OP-1007", "Cobro Delta SL factura 2026-016", "980.00"),
    ("2026-03-09", "OP-1008", "Factura luz marzo", "-213.40"),
    ("2026-03-10", "OP-1009", "Venta online lote 24", "645.90"),
    ("2026-03-11", "OP-1010", "Pago Epsilon SL pedido 553", "-1340.00"),
    # Duplicado interno: mismo apunte apuntado dos veces
    ("2026-03-11", "OP-1011", "Reintegro caja chica", "-300.00"),
    ("2026-03-11", "OP-1012", "Reintegro caja chica", "-300.00"),
    # Pendiente interno: cobro registrado pero aun no recibido en el banco
    ("2026-03-14", "OP-1015", "Anticipo cliente Zeta SL", "3000.00"),
    # Coincidencia aproximada con el concepto bancario (software contable)
    ("2026-03-13", "OP-1014", "Suscripcion software contabilidad", "-59.99"),
]


def _write(path: Path, header: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def generate_samples() -> tuple[Path, Path]:
    """Escribe los dos CSV de ejemplo y devuelve sus rutas."""
    bank_path = config.SAMPLES_DIR / config.BANK_SAMPLE_NAME
    internal_path = config.SAMPLES_DIR / config.INTERNAL_SAMPLE_NAME
    _write(bank_path, config.BANK_REQUIRED_COLUMNS, BANK_ROWS)
    _write(internal_path, config.INTERNAL_REQUIRED_COLUMNS, INTERNAL_ROWS)
    return bank_path, internal_path
