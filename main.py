#!/usr/bin/env python3
"""Comofi - Conciliación de movimientos financieros.

Punto de entrada por línea de órdenes:

    python main.py generar-ejemplos     Crea dos CSV ficticios en data/sample_files/
    python main.py conciliar B I        Concilia los CSV indicados y exporta resultados
    python main.py historial            Muestra las últimas revisiones guardadas
    python main.py web                  Levanta la interfaz web (Flask)

Programa creado por Sebastián Romero
"""

import argparse
import sys

from comofi import config, samples
from comofi.csv_loader import CsvValidationError, load_movements
from comofi.exporter import export_results
from comofi.history import list_revisions, save_revision
from comofi.reconciler import reconcile


def cmd_generate_samples(_: argparse.Namespace) -> int:
    bank_path, internal_path = samples.generate_samples()
    print(f"Ejemplo bancario creado en: {bank_path}")
    print(f"Ejemplo interno creado en:  {internal_path}")
    return 0


def cmd_conciliate(args: argparse.Namespace) -> int:
    try:
        bank = load_movements(args.banco, "bank")
        internal = load_movements(args.interno, "internal")
    except CsvValidationError as exc:
        print(f"Error al importar: {exc}", file=sys.stderr)
        return 1

    result = reconcile(bank, internal)
    summary = result.summary()

    print("=== Resumen de conciliación ===")
    for category, count in summary.items():
        print(f"{category:<22} {count:>4}")

    print("\n--- Discrepancias ---")
    for pair in result.discrepancies:
        print(
            f"[{pair.status}] banco {pair.bank_row[config.COL_ID]} "
            f"({pair.bank_row[config.COL_DATE]} / {pair.bank_row[config.COL_AMOUNT]:.2f}) vs "
            f"interno {pair.internal_row[config.COL_ID]} "
            f"({pair.internal_row[config.COL_DATE]} / {pair.internal_row[config.COL_AMOUNT]:.2f}) | "
            f"dif importe {pair.amount_diff:+.2f} | dif días {pair.days_diff}"
        )

    print("\n--- Duplicados ---")
    if not result.duplicates:
        print("(ninguno)")
    for group in result.duplicates:
        origin = "banco" if group.source == "bank" else "interno"
        print(f"[{origin}] x{len(group.rows)} -> {group.key}")

    print("\n--- Pendientes de conciliación ---")
    print(f"Banco sin contrapartida interna ({len(result.pending_bank)}):")
    for row in result.pending_bank:
        print(f"  {row[config.COL_DATE]} {row[config.COL_ID]} {row[config.COL_CONCEPT]} "
              f"{row[config.COL_AMOUNT]:.2f}")
    print(f"Interno sin contrapartida bancaria ({len(result.pending_internal)}):")
    for row in result.pending_internal:
        print(f"  {row[config.COL_DATE]} {row[config.COL_ID]} {row[config.COL_CONCEPT]} "
              f"{row[config.COL_AMOUNT]:.2f}")

    revision_id = save_revision(result, bank.source_name, internal.source_name)
    paths = export_results(result)
    print(f"\nRevisión #{revision_id} guardada en el historial.")
    print("Archivos exportados:")
    for path in paths:
        print(f"  {path}")
    return 0


def cmd_history(_: argparse.Namespace) -> int:
    revisions = list_revisions()
    if not revisions:
        print("No hay revisiones guardadas todavía.")
        return 0
    print(f"{'ID':>4}  {'Fecha y hora':<20}  {'Banco':<28} {'Interno':<26} Resumen")
    for rev in revisions:
        s = rev["summary"]
        resumen = (f"c={s['coincidentes']} d={s['discrepancias']} "
                   f"dup={s['duplicados']} pend={s['pendientes_banco'] + s['pendientes_interno']}")
        print(f"{rev['id']:>4}  {rev['timestamp']:<20}  {rev['bank_file']:<28} "
              f"{rev['internal_file']:<26} {resumen}")
    return 0


def cmd_web(_: argparse.Namespace) -> int:
    from comofi.web import app

    app.run(debug=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Comofi: conciliación de movimientos financieros")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generar-ejemplos", help="crear CSV ficticios de prueba")
    gen.set_defaults(func=cmd_generate_samples)

    con = sub.add_parser("conciliar", help="conciliar dos archivos CSV")
    con.add_argument("banco", help="CSV del extracto bancario")
    con.add_argument("interno", help="CSV del registro interno")
    con.set_defaults(func=cmd_conciliate)

    his = sub.add_parser("historial", help="listar las últimas revisiones")
    his.set_defaults(func=cmd_history)

    web = sub.add_parser("web", help="iniciar la interfaz web en http://127.0.0.1:5000")
    web.set_defaults(func=cmd_web)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
