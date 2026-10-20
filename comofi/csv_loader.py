"""Lectura y validación de archivos CSV de movimientos.

Programa creado por Sebastián Romero
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from comofi import config


class CsvValidationError(Exception):
    """El CSV no cumple el formato esperado."""


@dataclass
class Movements:
    """Colección normalizada de movimientos de un origen."""

    source_name: str
    frame: pd.DataFrame

    def __len__(self) -> int:
        return len(self.frame)


def _parse_amount(raw: object) -> float:
    """Convierte '1.234,56', '1234.56' o '(50,00)' a float con signo."""
    text = str(raw).strip()
    if not text:
        raise ValueError("importe vacío")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    # Formato europeo: miles con punto, decimales con coma
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    value = float(text)
    return -value if negative else value


def _parse_date(raw: object) -> date:
    """Intenta los formatos configurados; si ninguno funciona, lanza ValueError."""
    text = str(raw).strip()
    for fmt in config.DATE_FORMATS:
        try:
            return pd.to_datetime(text, format=fmt).date()
        except (ValueError, TypeError):
            continue
    raise ValueError(f"fecha no reconocida: {text!r}")


def _normalize(frame: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Renombra columnas según el mapeo y valida tipos fila a fila."""
    missing = [col for col in mapping if col not in frame.columns]
    if missing:
        raise CsvValidationError(
            f"Faltan columnas esperadas: {missing}. "
            f"Columnas encontradas: {list(frame.columns)}"
        )
    out = frame.rename(columns=mapping)[
        [config.COL_DATE, config.COL_ID, config.COL_CONCEPT, config.COL_AMOUNT]
    ].copy()

    errors = []
    dates, amounts = [], []
    for idx, row in out.iterrows():
        line_no = idx + 2  # +1 por índice base 0, +1 por la cabecera
        try:
            dates.append(_parse_date(row[config.COL_DATE]))
        except ValueError as exc:
            errors.append(f"línea {line_no}: {exc}")
            dates.append(None)
        try:
            amounts.append(_parse_amount(row[config.COL_AMOUNT]))
        except ValueError:
            errors.append(f"línea {line_no}: importe no numérico {row[config.COL_AMOUNT]!r}")
            amounts.append(None)
    if errors:
        raise CsvValidationError("Errores de formato:\n  " + "\n  ".join(errors))

    out[config.COL_DATE] = dates
    out[config.COL_AMOUNT] = amounts
    out[config.COL_ID] = out[config.COL_ID].astype(str).str.strip()
    out[config.COL_CONCEPT] = out[config.COL_CONCEPT].astype(str).str.strip()
    return out.reset_index(drop=True)


def load_movements(path: str | Path, kind: str) -> Movements:
    """Carga un CSV como movimientos de tipo 'bank' o 'internal'.

    kind determina las cabeceras esperadas (ver config).
    """
    path = Path(path)
    if not path.exists():
        raise CsvValidationError(f"No existe el archivo: {path}")

    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    frame.columns = [c.strip().lower() for c in frame.columns]

    if kind == "bank":
        required = config.BANK_REQUIRED_COLUMNS
    elif kind == "internal":
        required = config.INTERNAL_REQUIRED_COLUMNS
    else:
        raise ValueError(f"tipo de origen desconocido: {kind!r}")

    mapping = {required[0]: config.COL_DATE, required[1]: config.COL_ID,
               required[2]: config.COL_CONCEPT, required[3]: config.COL_AMOUNT}
    normalized = _normalize(frame, mapping)
    return Movements(source_name=path.name, frame=normalized)
