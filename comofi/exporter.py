"""Exportación de resultados de conciliación a CSV.

Se genera un único archivo con todas las filas clasificadas por categoría,
más un CSV aparte por cada categoría para quien prefiera trabajarlas sueltas.

Programa creado por Sebastián Romero
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from comofi import config
from comofi.reconciler import (
    CAT_DISCREPANT,
    CAT_DUPLICATES,
    CAT_MATCHED,
    CAT_PENDING_BANK,
    CAT_PENDING_INTERNAL,
    MATCH_FUZZY,
    ReconciliationResult,
)


def _pair_rows(pairs, category: str) -> list[dict]:
    rows = []
    for p in pairs:
        rows.append(
            {
                "categoria": category,
                "estado": p.status,
                "fecha_banco": p.bank_row[config.COL_DATE],
                "referencia_banco": p.bank_row[config.COL_ID],
                "concepto_banco": p.bank_row[config.COL_CONCEPT],
                "importe_banco": p.bank_row[config.COL_AMOUNT],
                "fecha_interno": p.internal_row[config.COL_DATE],
                "referencia_interno": p.internal_row[config.COL_ID],
                "concepto_interno": p.internal_row[config.COL_CONCEPT],
                "importe_interno": p.internal_row[config.COL_AMOUNT],
                "diferencia_importe": p.amount_diff,
                "diferencia_dias": p.days_diff,
                "puntuacion": round(p.score, 3),
            }
        )
    return rows


def _pending_rows(rows: list[dict], category: str, side: str) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "categoria": category,
                "estado": "sin_contrapartida",
                f"fecha_{side}": r[config.COL_DATE],
                f"referencia_{side}": r[config.COL_ID],
                f"concepto_{side}": r[config.COL_CONCEPT],
                f"importe_{side}": r[config.COL_AMOUNT],
            }
        )
    return out


def _duplicate_rows(result: ReconciliationResult) -> list[dict]:
    out = []
    for group in result.duplicates:
        side = "banco" if group.source == "bank" else "interno"
        for r in group.rows:
            out.append(
                {
                    "categoria": CATEGORY_DUPLICATES,
                    "estado": f"duplicado_en_{group.source}",
                    "grupo": group.key,
                    f"fecha_{side}": r[config.COL_DATE],
                    f"referencia_{side}": r[config.COL_ID],
                    f"concepto_{side}": r[config.COL_CONCEPT],
                    f"importe_{side}": r[config.COL_AMOUNT],
                }
            )
    return out


# Alias de dominio para las categorías exportadas (definidas en reconciler)
CATEGORY_MATCHED = CAT_MATCHED
CATEGORY_DISCREPANCIES = CAT_DISCREPANT
CATEGORY_DUPLICATES = CAT_DUPLICATES
CATEGORY_PENDING_BANK = CAT_PENDING_BANK
CATEGORY_PENDING_INTERNAL = CAT_PENDING_INTERNAL


def build_results_frame(result: ReconciliationResult) -> pd.DataFrame:
    """Convierte el resultado completo en una tabla única con columna 'categoria'."""
    rows = []
    # Las coincidencias aproximadas van al final del bloque de coincidentes
    exact = [p for p in result.matched if p.status != MATCH_FUZZY]
    fuzzy = [p for p in result.matched if p.status == MATCH_FUZZY]
    rows += _pair_rows(exact, CATEGORY_MATCHED)
    rows += _pair_rows(fuzzy, CATEGORY_MATCHED)
    rows += _pair_rows(result.discrepancies, CATEGORY_DISCREPANCIES)
    rows += _duplicate_rows(result)
    rows += _pending_rows(result.pending_bank, CATEGORY_PENDING_BANK, "banco")
    rows += _pending_rows(result.pending_internal, CATEGORY_PENDING_INTERNAL, "interno")
    frame = pd.DataFrame(rows)
    if not frame.empty:
        date_cols = [c for c in frame.columns if c.startswith("fecha_")]
        for col in date_cols:
            frame[col] = pd.to_datetime(frame[col]).dt.strftime(config.EXPORT_DATE_FORMAT)
    return frame


def export_results(result: ReconciliationResult, output_dir: Path | None = None) -> list[Path]:
    """Escribe los resultados en data/resultados/ y devuelve las rutas generadas."""
    target = output_dir or (config.DATA_DIR / config.RESULTS_DIR_NAME)
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    full_frame = build_results_frame(result)
    paths = []

    consolidated = target / f"conciliacion_{stamp}.csv"
    full_frame.to_csv(consolidated, index=False)
    paths.append(consolidated)

    for category in full_frame["categoria"].unique() if not full_frame.empty else []:
        part = target / f"conciliacion_{stamp}_{category}.csv"
        full_frame[full_frame["categoria"] == category].to_csv(part, index=False)
        paths.append(part)

    return paths
