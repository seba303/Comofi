from datetime import date

import pandas as pd
import pytest

from comofi import config
from comofi.csv_loader import CsvValidationError, load_movements
from comofi.reconciler import Movements, reconcile


def test_load_movements_normalizes_csv(tmp_path):
    csv_path = tmp_path / "movimientos.csv"
    csv_path.write_text(
        "fecha,referencia,concepto,importe\n"
        "03/03/2026,TRX-1003,Alquiler oficina marzo,-1.200,00\n"
        "2026-03-05,TRX-1004,Nomina,-350.00\n",
        encoding="utf-8",
    )

    movements = load_movements(csv_path, "bank")

    assert movements.source_name == "movimientos.csv"
    assert list(movements.frame.columns) == [
        config.COL_DATE,
        config.COL_ID,
        config.COL_CONCEPT,
        config.COL_AMOUNT,
    ]
    assert movements.frame.iloc[0][config.COL_DATE] == date(2026, 3, 3)
    assert movements.frame.iloc[0][config.COL_AMOUNT] == -1200.0


def test_load_movements_rejects_invalid_columns(tmp_path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("fecha,importe\n2026-03-01,100\n", encoding="utf-8")

    with pytest.raises(CsvValidationError):
        load_movements(csv_path, "bank")


def test_reconcile_detects_exact_match_and_discrepancy():
    bank_df = pd.DataFrame(
        [
            {
                config.COL_DATE: date(2026, 3, 3),
                config.COL_ID: "TRX-1001",
                config.COL_CONCEPT: "Alquiler oficina",
                config.COL_AMOUNT: -1200.0,
            },
            {
                config.COL_DATE: date(2026, 3, 4),
                config.COL_ID: "TRX-1002",
                config.COL_CONCEPT: "Nomina",
                config.COL_AMOUNT: 2500.0,
            },
        ]
    )
    internal_df = pd.DataFrame(
        [
            {
                config.COL_DATE: date(2026, 3, 3),
                config.COL_ID: "TRX-1001",
                config.COL_CONCEPT: "Alquiler oficina",
                config.COL_AMOUNT: -1200.0,
            },
            {
                config.COL_DATE: date(2026, 3, 4),
                config.COL_ID: "TRX-1002",
                config.COL_CONCEPT: "Nomina",
                config.COL_AMOUNT: 2400.0,
            },
        ]
    )

    result = reconcile(Movements("bank.csv", bank_df), Movements("internal.csv", internal_df))

    assert len(result.matched) == 1
    assert len(result.discrepancies) == 1
    assert result.pending_bank == []
    assert result.pending_internal == []


def test_reconcile_detects_pending_transactions():
    bank_df = pd.DataFrame(
        [
            {
                config.COL_DATE: date(2026, 3, 3),
                config.COL_ID: "TRX-9001",
                config.COL_CONCEPT: "Pago servicio",
                config.COL_AMOUNT: -50.0,
            }
        ]
    )
    internal_df = pd.DataFrame(
        [
            {
                config.COL_DATE: date(2026, 3, 6),
                config.COL_ID: "OP-9002",
                config.COL_CONCEPT: "Pago servicio",
                config.COL_AMOUNT: -50.0,
            }
        ]
    )

    result = reconcile(Movements("bank.csv", bank_df), Movements("internal.csv", internal_df))

    assert len(result.pending_bank) == 1
    assert len(result.pending_internal) == 1
