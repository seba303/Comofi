"""Motor de conciliación: empareja movimientos y clasifica incidencias.

Estrategia en dos pasadas:
  1. Emparejamiento exacto por referencia (ID) cuando existe en ambos lados.
  2. Emparejamiento aproximado por importe + concepto para lo que queda,
     limitado a una ventana de fechas configurable.

Programa creado por Sebastián Romero
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pandas as pd

from comofi import config
from comofi.csv_loader import Movements

# Estados de una pareja conciliada
MATCH_EXACT = "coincidente"
MATCH_AMOUNT_DIFF = "diferencia_importe"
MATCH_DATE_DIFF = "diferencia_fecha"
MATCH_BOTH_DIFF = "diferencia_importe_y_fecha"
MATCH_FUZZY = "coincidente_aproximada"

# Categorías de resultados no emparejados (se reutilizan en el exportador)
CAT_MATCHED = "coincidentes"
CAT_DISCREPANT = "discrepancias"
CAT_DUPLICATES = "duplicados"
CAT_PENDING_BANK = "pendientes_banco"
CAT_PENDING_INTERNAL = "pendientes_interno"


@dataclass
class MatchedPair:
    bank_row: dict
    internal_row: dict
    status: str
    amount_diff: float
    days_diff: int
    score: float = 1.0


@dataclass
class DuplicateGroup:
    source: str          # 'bank' | 'internal'
    key: str             # texto descriptivo del grupo duplicado
    rows: list[dict] = field(default_factory=list)


@dataclass
class ReconciliationResult:
    matched: list[MatchedPair]
    discrepancies: list[MatchedPair]   # parejas emparejadas con diffs de importe/fecha
    duplicates: list[DuplicateGroup]
    pending_bank: list[dict]
    pending_internal: list[dict]

    def summary(self) -> dict[str, int]:
        return {
            CAT_MATCHED: len(self.matched),
            CAT_DISCREPANT: len(self.discrepancies),
            CAT_DUPLICATES: sum(len(g.rows) for g in self.duplicates),
            CAT_PENDING_BANK: len(self.pending_bank),
            CAT_PENDING_INTERNAL: len(self.pending_internal),
        }


def _similarity(a: str, b: str) -> float:
    """Similitud de secuencia normalizada (0..1) entre dos conceptos."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _amount_similarity(a: float, b: float) -> float:
    """1.0 si son iguales dentro de tolerancia; decae con la diferencia relativa."""
    if abs(a - b) <= config.AMOUNT_TOLERANCE:
        return 1.0
    reference = max(abs(a), abs(b))
    if reference == 0:
        return 1.0
    gap = abs(a - b) / reference
    return max(0.0, 1.0 - gap)


def _pair_status(bank: dict, internal: dict) -> tuple[str, float, int]:
    amount_diff = round(bank[config.COL_AMOUNT] - internal[config.COL_AMOUNT], 2)
    days_diff = abs((bank[config.COL_DATE] - internal[config.COL_DATE]).days)
    has_amount = abs(amount_diff) > config.AMOUNT_TOLERANCE
    has_date = days_diff > config.DATE_DIFF_ALERT_DAYS
    if has_amount and has_date:
        status = MATCH_BOTH_DIFF
    elif has_amount:
        status = MATCH_AMOUNT_DIFF
    elif has_date:
        status = MATCH_DATE_DIFF
    else:
        status = MATCH_EXACT
    return status, amount_diff, days_diff


def _find_duplicates(frame: pd.DataFrame, source: str) -> list[DuplicateGroup]:
    """Filas gemelas dentro del mismo origen (misma fecha, importe y concepto)."""
    groups = []
    keys = ["fecha", "importe", "concepto"]
    grouped = frame.groupby(keys, sort=False)
    for _, group in grouped:
        if len(group) > 1:
            rows = group.to_dict("records")
            first = rows[0]
            label = (
                f"{first[config.COL_DATE].isoformat()} | "
                f"{first[config.COL_AMOUNT]:.2f} EUR | {first[config.COL_CONCEPT]}"
            )
            groups.append(DuplicateGroup(source=source, key=label, rows=rows))
    return groups


def reconcile(bank: Movements, internal: Movements) -> ReconciliationResult:
    """Concilia dos colecciones de movimientos y devuelve todas las categorías."""
    bank_rows = bank.frame.to_dict("records")
    internal_rows = internal.frame.to_dict("records")

    matched: list[MatchedPair] = []
    discrepancies: list[MatchedPair] = []

    used_bank: set[int] = set()
    used_internal: set[int] = set()

    # Pasada 1: emparejamiento exacto por referencia
    internal_by_id: dict[str, list[int]] = {}
    for idx, row in enumerate(internal_rows):
        internal_by_id.setdefault(row[config.COL_ID], []).append(idx)

    for b_idx, b_row in enumerate(bank_rows):
        candidates = internal_by_id.get(b_row[config.COL_ID], [])
        free = [i for i in candidates if i not in used_internal]
        if not free:
            continue
        i_idx = free[0]
        i_row = internal_rows[i_idx]
        status, amount_diff, days_diff = _pair_status(b_row, i_row)
        pair = MatchedPair(b_row, i_row, status, amount_diff, days_diff)
        (matched if status == MATCH_EXACT else discrepancies).append(pair)
        used_bank.add(b_idx)
        used_internal.add(i_idx)

    # Pasada 2: aproximada por importe/concepto sobre los no emparejados
    leftovers_b = [(i, r) for i, r in enumerate(bank_rows) if i not in used_bank]
    leftovers_i = [(i, r) for i, r in enumerate(internal_rows) if i not in used_internal]

    scored = []
    for b_pos, b_row in leftovers_b:
        for i_pos, i_row in leftovers_i:
            days_diff = abs((b_row[config.COL_DATE] - i_row[config.COL_DATE]).days)
            if days_diff > config.DAYS_WINDOW:
                continue
            amount_sim = _amount_similarity(b_row[config.COL_AMOUNT], i_row[config.COL_AMOUNT])
            concept_sim = _similarity(b_row[config.COL_CONCEPT], i_row[config.COL_CONCEPT])
            score = config.WEIGHT_AMOUNT * amount_sim + config.WEIGHT_CONCEPT * concept_sim
            if score >= config.FUZZY_MIN_SCORE:
                scored.append((score, b_pos, i_pos))

    # Mejor candidato primero; cada fila se usa una sola vez
    scored.sort(key=lambda t: t[0], reverse=True)
    for score, b_pos, i_pos in scored:
        if b_pos in used_bank or i_pos in used_internal:
            continue
        b_row, i_row = bank_rows[b_pos], internal_rows[i_pos]
        status, amount_diff, days_diff = _pair_status(b_row, i_row)
        # Si difiere en importe o fecha se marca como discrepancia; si no,
        # se anota como coincidencia aproximada (emparejada sin referencia común).
        if status == MATCH_EXACT:
            status = MATCH_FUZZY
        is_clean_match = status in (MATCH_EXACT, MATCH_FUZZY)
        pair = MatchedPair(b_row, i_row, status, amount_diff, days_diff, score)
        (matched if is_clean_match else discrepancies).append(pair)
        used_bank.add(b_pos)
        used_internal.add(i_pos)

    pending_bank = [r for i, r in enumerate(bank_rows) if i not in used_bank]
    pending_internal = [r for i, r in enumerate(internal_rows) if i not in used_internal]

    duplicates = _find_duplicates(bank.frame, "bank") + _find_duplicates(internal.frame, "internal")

    return ReconciliationResult(
        matched=matched,
        discrepancies=discrepancies,
        duplicates=duplicates,
        pending_bank=pending_bank,
        pending_internal=pending_internal,
    )
