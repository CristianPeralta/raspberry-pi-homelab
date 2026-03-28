#!/usr/bin/env python3
"""benchmark-cli.py — CLI for logging and reporting OpenClaw vs nanobot benchmark data."""

import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark.db")

CATEGORIES = ["simple", "skill", "reasoning", "multi-step"]


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def prompt_int(label, required=False):
    while True:
        val = input(f"  {label}: ").strip()
        if not val:
            if required:
                print("    (requerido)")
                continue
            return None
        try:
            return int(val)
        except ValueError:
            print("    (número inválido)")


def prompt_choice(label, options, default=None):
    hint = "/".join(options)
    if default:
        hint = hint.replace(default, default.upper())
    while True:
        val = input(f"  {label} [{hint}]: ").strip().lower()
        if not val and default:
            return default
        if val in options:
            return val
        print(f"    (opciones: {', '.join(options)})")


def determine_winner(csat_oc, csat_nb, oc_time, nb_time):
    """Auto-determine winner based on CSAT, then time as tiebreaker."""
    if csat_oc and csat_nb:
        if csat_oc > csat_nb:
            return "openclaw"
        elif csat_nb > csat_oc:
            return "nanobot"
    if oc_time and nb_time:
        if oc_time < nb_time:
            return "openclaw"
        elif nb_time < oc_time:
            return "nanobot"
    return "tie"


# --- Commands ---

def cmd_log(args):
    conn = get_db()
    winner = args.winner
    if winner == "auto":
        winner = determine_winner(args.csat_oc, args.csat_nb, args.oc_time, args.nb_time)

    cur = conn.execute("""
        INSERT INTO queries (query_text, category, oc_time_ms, nb_time_ms,
            oc_tokens_in, oc_tokens_out, nb_tokens_in, nb_tokens_out,
            oc_model, nb_model, csat_oc, csat_nb, winner, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        args.query, args.category, args.oc_time, args.nb_time,
        args.oc_tokens_in, args.oc_tokens_out, args.nb_tokens_in, args.nb_tokens_out,
        args.oc_model, args.nb_model, args.csat_oc, args.csat_nb, winner, args.notes,
    ))
    conn.commit()
    print(f"Guardado query #{cur.lastrowid}")
    conn.close()


def cmd_interactive(_args):
    print("=== Benchmark: Registro interactivo ===\n")
    query = input("  Query: ").strip()
    if not query:
        print("Query vacía, cancelado.")
        return

    category = prompt_choice("Categoría", CATEGORIES, default="simple")
    oc_time = prompt_int("OpenClaw response time (ms, enter=skip)")
    nb_time = prompt_int("nanobot response time (ms, enter=skip)")
    oc_tokens_in = prompt_int("OpenClaw tokens in (enter=skip)")
    oc_tokens_out = prompt_int("OpenClaw tokens out (enter=skip)")
    nb_tokens_in = prompt_int("nanobot tokens in (enter=skip)")
    nb_tokens_out = prompt_int("nanobot tokens out (enter=skip)")
    csat_oc = prompt_int("CSAT OpenClaw (1-5, enter=skip)")
    csat_nb = prompt_int("CSAT nanobot (1-5, enter=skip)")

    winner_input = prompt_choice("Winner", ["openclaw", "nanobot", "tie", "auto"], default="auto")
    if winner_input == "auto":
        winner_input = determine_winner(csat_oc, csat_nb, oc_time, nb_time)

    notes = input("  Notas (enter=skip): ").strip() or None

    conn = get_db()
    cur = conn.execute("""
        INSERT INTO queries (query_text, category, oc_time_ms, nb_time_ms,
            oc_tokens_in, oc_tokens_out, nb_tokens_in, nb_tokens_out,
            csat_oc, csat_nb, winner, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (query, category, oc_time, nb_time,
          oc_tokens_in, oc_tokens_out, nb_tokens_in, nb_tokens_out,
          csat_oc, csat_nb, winner_input, notes))
    conn.commit()
    print(f"\n  Guardado query #{cur.lastrowid}")
    conn.close()


def cmd_csat(args):
    conn = get_db()
    row = conn.execute("SELECT id FROM queries WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"Query #{args.id} no encontrada.")
        return

    updates, params = [], []
    if args.oc is not None:
        updates.append("csat_oc = ?")
        params.append(args.oc)
    if args.nb is not None:
        updates.append("csat_nb = ?")
        params.append(args.nb)

    if not updates:
        print("Nada que actualizar. Usa --oc y/o --nb.")
        return

    params.append(args.id)
    conn.execute(f"UPDATE queries SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    print(f"CSAT actualizado para query #{args.id}")
    conn.close()


def cmd_report(args):
    conn = get_db()

    if args.winners:
        rows = conn.execute("""
            SELECT winner, COUNT(*) as wins FROM queries
            WHERE winner IS NOT NULL GROUP BY winner ORDER BY wins DESC
        """).fetchall()
        print("\n=== Winners ===")
        for r in rows:
            print(f"  {r['winner']:12s} {r['wins']} wins")
        total = sum(r["wins"] for r in rows)
        print(f"  {'total':12s} {total}")
        conn.close()
        return

    if args.by == "category":
        rows = conn.execute("""
            SELECT category, COUNT(*) as n,
                ROUND(AVG(oc_tokens_in + oc_tokens_out)) as oc_tok,
                ROUND(AVG(nb_tokens_in + nb_tokens_out)) as nb_tok,
                ROUND(AVG(oc_time_ms)) as oc_ms,
                ROUND(AVG(nb_time_ms)) as nb_ms,
                ROUND(AVG(csat_oc), 1) as oc_csat,
                ROUND(AVG(csat_nb), 1) as nb_csat
            FROM queries GROUP BY category ORDER BY category
        """).fetchall()
        print("\n=== Por categoría ===")
        print(f"  {'cat':12s} {'n':>3s} {'oc_tok':>8s} {'nb_tok':>8s} {'oc_ms':>7s} {'nb_ms':>7s} {'oc_csat':>7s} {'nb_csat':>7s}")
        print(f"  {'-'*12} {'-'*3} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
        for r in rows:
            print(f"  {r['category']:12s} {r['n']:3d} {_fmt(r['oc_tok']):>8s} {_fmt(r['nb_tok']):>8s} "
                  f"{_fmt(r['oc_ms']):>7s} {_fmt(r['nb_ms']):>7s} {_fmt(r['oc_csat']):>7s} {_fmt(r['nb_csat']):>7s}")

    elif args.by == "day":
        rows = conn.execute("""
            SELECT DATE(timestamp) as day, COUNT(*) as n,
                ROUND(AVG(oc_tokens_in + oc_tokens_out)) as oc_tok,
                ROUND(AVG(nb_tokens_in + nb_tokens_out)) as nb_tok,
                ROUND(AVG(csat_oc), 1) as oc_csat,
                ROUND(AVG(csat_nb), 1) as nb_csat
            FROM queries GROUP BY day ORDER BY day
        """).fetchall()
        print("\n=== Por día ===")
        print(f"  {'día':12s} {'n':>3s} {'oc_tok':>8s} {'nb_tok':>8s} {'oc_csat':>7s} {'nb_csat':>7s}")
        print(f"  {'-'*12} {'-'*3} {'-'*8} {'-'*8} {'-'*7} {'-'*7}")
        for r in rows:
            print(f"  {r['day']:12s} {r['n']:3d} {_fmt(r['oc_tok']):>8s} {_fmt(r['nb_tok']):>8s} "
                  f"{_fmt(r['oc_csat']):>7s} {_fmt(r['nb_csat']):>7s}")

    else:
        row = conn.execute("""
            SELECT
                COUNT(*) as total,
                ROUND(AVG(oc_tokens_in + oc_tokens_out)) as avg_oc_tokens,
                ROUND(AVG(nb_tokens_in + nb_tokens_out)) as avg_nb_tokens,
                ROUND(AVG(oc_time_ms)) as avg_oc_time,
                ROUND(AVG(nb_time_ms)) as avg_nb_time,
                ROUND(AVG(csat_oc), 2) as avg_csat_oc,
                ROUND(AVG(csat_nb), 2) as avg_csat_nb
            FROM queries
        """).fetchone()

        oc_t = row["avg_oc_tokens"] or 0
        nb_t = row["avg_nb_tokens"] or 0
        savings = round(100 * (1 - nb_t / oc_t), 1) if oc_t > 0 else 0

        print("\n=== Resumen general ===")
        print(f"  Total queries:      {row['total']}")
        print(f"  Avg tokens OC:      {_fmt(row['avg_oc_tokens'])}")
        print(f"  Avg tokens NB:      {_fmt(row['avg_nb_tokens'])}")
        print(f"  Token savings:      {savings}%")
        print(f"  Avg time OC (ms):   {_fmt(row['avg_oc_time'])}")
        print(f"  Avg time NB (ms):   {_fmt(row['avg_nb_time'])}")
        print(f"  Avg CSAT OC:        {_fmt(row['avg_csat_oc'])}")
        print(f"  Avg CSAT NB:        {_fmt(row['avg_csat_nb'])}")

    conn.close()


def cmd_export(args):
    conn = get_db()
    rows = conn.execute("SELECT * FROM queries ORDER BY id").fetchall()

    if not rows:
        print("No hay datos.")
        conn.close()
        return

    columns = rows[0].keys()

    if args.json:
        data = [dict(r) for r in rows]
        output = json.dumps(data, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Exportado {len(rows)} rows a {args.output}")
        else:
            print(output)

    else:  # CSV default
        out = args.output or "benchmark-export.csv"
        with open(out, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for r in rows:
                writer.writerow([r[c] for c in columns])
        print(f"Exportado {len(rows)} rows a {out}")

    conn.close()


def _fmt(val):
    """Format a value, handling None."""
    if val is None:
        return "-"
    if isinstance(val, float):
        if val == int(val):
            return str(int(val))
        return str(val)
    return str(val)


def main():
    parser = argparse.ArgumentParser(description="Benchmark CLI: OpenClaw vs nanobot")
    sub = parser.add_subparsers(dest="command")

    # log
    p_log = sub.add_parser("log", help="Registrar query comparativa")
    p_log.add_argument("--query", "-q", required=True)
    p_log.add_argument("--category", "-c", choices=CATEGORIES, default="simple")
    p_log.add_argument("--oc-time", type=int)
    p_log.add_argument("--nb-time", type=int)
    p_log.add_argument("--oc-tokens-in", type=int)
    p_log.add_argument("--oc-tokens-out", type=int)
    p_log.add_argument("--nb-tokens-in", type=int)
    p_log.add_argument("--nb-tokens-out", type=int)
    p_log.add_argument("--oc-model", type=str)
    p_log.add_argument("--nb-model", type=str)
    p_log.add_argument("--csat-oc", type=int, choices=range(1, 6))
    p_log.add_argument("--csat-nb", type=int, choices=range(1, 6))
    p_log.add_argument("--winner", choices=["openclaw", "nanobot", "tie", "auto"], default="auto")
    p_log.add_argument("--notes", type=str)

    # interactive
    sub.add_parser("interactive", help="Registro interactivo campo por campo")

    # csat
    p_csat = sub.add_parser("csat", help="Actualizar CSAT de una query")
    p_csat.add_argument("--id", type=int, required=True)
    p_csat.add_argument("--oc", type=int, choices=range(1, 6))
    p_csat.add_argument("--nb", type=int, choices=range(1, 6))

    # report
    p_report = sub.add_parser("report", help="Generar reporte")
    p_report.add_argument("--by", choices=["category", "day"])
    p_report.add_argument("--winners", action="store_true")

    # export
    p_export = sub.add_parser("export", help="Exportar datos")
    p_export.add_argument("--csv", action="store_true", default=True)
    p_export.add_argument("--json", action="store_true")
    p_export.add_argument("--output", "-o", type=str)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if not os.path.exists(DB_PATH):
        print(f"DB no encontrada. Ejecuta primero: python3 init-db.py")
        sys.exit(1)

    {"log": cmd_log, "interactive": cmd_interactive, "csat": cmd_csat,
     "report": cmd_report, "export": cmd_export}[args.command](args)


if __name__ == "__main__":
    main()
