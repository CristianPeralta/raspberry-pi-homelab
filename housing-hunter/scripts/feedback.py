#!/usr/bin/env python3
"""Housing Hunter — Feedback & metrics system.

Tracks scraper performance, identifies what's working, and suggests improvements.

Usage:
    python3 feedback.py              # Weekly report
    python3 feedback.py snapshot     # Save current metrics snapshot
    python3 feedback.py fuentes      # Performance by source
    python3 feedback.py motivos      # Top discard reasons
    python3 feedback.py evolve       # Suggest improvements
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from config import get_db, CIUDAD


def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def bold(t): return color(t, "1")
def green(t): return color(t, "32")
def yellow(t): return color(t, "33")
def red(t): return color(t, "31")
def dim(t): return color(t, "2")


def show_weekly_report(conn):
    """Show weekly performance report."""
    print(bold("\n📊 HOUSING HUNTER — Weekly Report"))
    print(f"{'='*60}")

    # Overall stats
    total = conn.execute("SELECT COUNT(*) FROM propiedades").fetchone()[0]
    nuevas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='nueva'").fetchone()[0]
    contactadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='contactada'").fetchone()[0]
    visitadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='visitada'").fetchone()[0]
    descartadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='descartada'").fetchone()[0]
    negociando = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='negociando'").fetchone()[0]

    print(f"\n  Total: {bold(str(total))}  |  Pipeline: {nuevas} nueva, {contactadas} contactada, "
          f"{visitadas} visitada, {negociando} negociando, {descartadas} descartada")

    # Conversion funnel
    activas = total - descartadas
    if total > 0:
        tasa_descarte = descartadas / total * 100
        print(f"  Tasa descarte: {tasa_descarte:.0f}%  |  Activas: {activas}")

    # This week
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    nuevas_semana = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE fecha_encontrada >= ?", (week_ago,)
    ).fetchone()[0]
    print(f"  Nuevas esta semana: {green(str(nuevas_semana))}")

    # By source
    print(bold("\n  Rendimiento por fuente:"))
    rows = conn.execute("""
        SELECT fuente_detalle,
               COUNT(*) as total,
               SUM(CASE WHEN estado != 'descartada' THEN 1 ELSE 0 END) as activas,
               SUM(CASE WHEN estado = 'descartada' THEN 1 ELSE 0 END) as descartadas,
               SUM(CASE WHEN estado IN ('contactada','visitada','negociando') THEN 1 ELSE 0 END) as avanzadas
        FROM propiedades
        GROUP BY fuente_detalle
        ORDER BY activas DESC
    """).fetchall()

    print(f"  {'Fuente':<25} {'Total':>5} {'Activ':>5} {'Desc':>5} {'Avanz':>5} {'Tasa':>6}")
    print(f"  {'-'*25} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*6}")
    for r in rows:
        tasa = r["activas"] / r["total"] * 100 if r["total"] > 0 else 0
        tasa_str = f"{tasa:.0f}%"
        if tasa >= 70:
            tasa_str = green(tasa_str)
        elif tasa >= 40:
            tasa_str = yellow(tasa_str)
        else:
            tasa_str = red(tasa_str)
        print(f"  {r['fuente_detalle'] or '?':<25} {r['total']:>5} {r['activas']:>5} "
              f"{r['descartadas']:>5} {r['avanzadas']:>5} {tasa_str:>6}")

    # Searches log
    print(bold("\n  Busquedas recientes (7 dias):"))
    searches = conn.execute("""
        SELECT fuente, SUM(propiedades_encontradas) as encontradas,
               SUM(propiedades_nuevas) as nuevas, COUNT(*) as ejecuciones
        FROM busquedas WHERE fecha >= ?
        GROUP BY fuente ORDER BY nuevas DESC
    """, (week_ago,)).fetchall()

    if searches:
        for s in searches:
            eficiencia = s["nuevas"] / s["encontradas"] * 100 if s["encontradas"] > 0 else 0
            print(f"  {s['fuente'][:30]:<30} {s['ejecuciones']}x | "
                  f"encontradas: {s['encontradas']} | nuevas: {s['nuevas']} | "
                  f"efic: {eficiencia:.0f}%")
    else:
        print(dim("  Sin datos de busqueda esta semana"))

    print()


def show_fuentes(conn):
    """Show detailed source performance."""
    print(bold("\nRendimiento por fuente — detallado"))
    print(f"{'='*60}")

    rows = conn.execute("""
        SELECT fuente_detalle,
               modo,
               COUNT(*) as total,
               AVG(CASE WHEN score IS NOT NULL THEN score ELSE NULL END) as avg_score,
               SUM(CASE WHEN estado = 'descartada' THEN 1 ELSE 0 END) as descartadas,
               MIN(fecha_encontrada) as primera,
               MAX(fecha_encontrada) as ultima
        FROM propiedades
        GROUP BY fuente_detalle, modo
        ORDER BY total DESC
    """).fetchall()

    for r in rows:
        avg = f"{r['avg_score']:.0f}%" if r['avg_score'] else "--"
        desc_rate = r['descartadas'] / r['total'] * 100 if r['total'] > 0 else 0
        print(f"\n  {bold(r['fuente_detalle'] or '?')} ({r['modo']})")
        print(f"    Total: {r['total']} | Avg score: {avg} | Descarte: {desc_rate:.0f}%")
        print(f"    Rango: {r['primera']} — {r['ultima']}")


def show_motivos(conn):
    """Show top discard reasons."""
    print(bold("\nMotivos de descarte"))
    print(f"{'='*60}")

    rows = conn.execute("""
        SELECT motivo_descarte, COUNT(*) as c
        FROM propiedades WHERE estado='descartada' AND motivo_descarte IS NOT NULL
        GROUP BY motivo_descarte ORDER BY c DESC
    """).fetchall()

    if rows:
        for r in rows:
            print(f"  {r['c']:>3}x  {r['motivo_descarte']}")
    else:
        print(dim("  Sin motivos registrados. Usa: dashboard.py descartar N 'motivo'"))

    # Properties without discard reason
    no_reason = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE estado='descartada' AND motivo_descarte IS NULL"
    ).fetchone()[0]
    if no_reason > 0:
        print(yellow(f"\n  {no_reason} descartadas sin motivo — agrega motivos para mejor feedback"))

    print()


def suggest_improvements(conn):
    """Analyze data and suggest improvements."""
    print(bold("\nSugerencias de mejora"))
    print(f"{'='*60}")

    suggestions = []

    # Check if any source has 0 results recently
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    dead_sources = conn.execute("""
        SELECT fuente, MAX(fecha) as ultima
        FROM busquedas
        GROUP BY fuente
        HAVING MAX(fecha) < ? OR SUM(propiedades_encontradas) = 0
    """, (week_ago,)).fetchall()

    for s in dead_sources:
        suggestions.append(f"Fuente '{s['fuente']}' sin resultados desde {s['ultima']} — verificar si sigue activa")

    # Check high discard rate sources
    high_discard = conn.execute("""
        SELECT fuente_detalle,
               COUNT(*) as total,
               SUM(CASE WHEN estado='descartada' THEN 1 ELSE 0 END) as desc
        FROM propiedades
        GROUP BY fuente_detalle
        HAVING total >= 3 AND CAST(desc AS FLOAT)/total > 0.7
    """).fetchall()

    for s in high_discard:
        rate = s['desc'] / s['total'] * 100
        suggestions.append(
            f"'{s['fuente_detalle']}' tiene {rate:.0f}% descarte ({s['desc']}/{s['total']}) "
            f"— revisar filtros o calidad de fuente"
        )

    # Check for stale "nueva" properties
    stale = conn.execute("""
        SELECT COUNT(*) FROM propiedades
        WHERE estado='nueva' AND fecha_encontrada < date('now', '-3 days')
    """).fetchone()[0]

    if stale > 0:
        suggestions.append(
            f"{stale} propiedades llevan 3+ dias como 'nueva' sin revisar — priorizar revision"
        )

    # Check if FB cookies exist
    from pathlib import Path
    cookies = Path(__file__).parent / "fb_cookies.txt"
    if not cookies.exists():
        suggestions.append("Facebook cookies no configuradas — 7 grupos inactivos. Exportar cookies para activar.")

    # Check for properties without score
    no_score = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE score IS NULL AND estado NOT IN ('descartada','cerrada')"
    ).fetchone()[0]
    if no_score > 0:
        suggestions.append(f"{no_score} propiedades activas sin score — considerar scoring automatico")

    # Check budget effectiveness
    over_budget_alq = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE modo='alquiler' AND estado='descartada' "
        "AND motivo_descarte LIKE '%precio%'"
    ).fetchone()[0]
    total_alq_desc = conn.execute(
        "SELECT COUNT(*) FROM propiedades WHERE modo='alquiler' AND estado='descartada'"
    ).fetchone()[0]
    if total_alq_desc > 0 and over_budget_alq / total_alq_desc > 0.5:
        suggestions.append(
            f"{over_budget_alq}/{total_alq_desc} alquileres descartados por precio — "
            f"los filtros de presupuesto podrían ser más estrictos en los scrapers"
        )

    if suggestions:
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")
    else:
        print(green("  Todo bien — sin mejoras urgentes detectadas"))

    print()


def save_snapshot(conn):
    """Save current metrics snapshot for trend tracking."""
    fecha = datetime.now().strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT fuente_detalle,
               COUNT(*) as total,
               SUM(CASE WHEN estado != 'descartada' THEN 1 ELSE 0 END) as activas,
               SUM(CASE WHEN estado = 'descartada' THEN 1 ELSE 0 END) as descartadas,
               SUM(CASE WHEN estado IN ('contactada','visitada','negociando') THEN 1 ELSE 0 END) as avanzadas
        FROM propiedades
        GROUP BY fuente_detalle
    """).fetchall()

    for r in rows:
        tasa = r["avanzadas"] / r["total"] if r["total"] > 0 else 0
        conn.execute(
            "INSERT INTO metricas_fuente (fuente, fecha, total_encontradas, total_nuevas, "
            "contactadas, descartadas, tasa_conversion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r["fuente_detalle"], fecha, r["total"], r["activas"],
             r["avanzadas"], r["descartadas"], tasa),
        )

    conn.commit()
    print(green(f"Snapshot guardado: {fecha} ({len(rows)} fuentes)"))


def main():
    conn = get_db()
    args = sys.argv[1:]

    if not args:
        show_weekly_report(conn)
        show_motivos(conn)
        suggest_improvements(conn)
    elif args[0] == "snapshot":
        save_snapshot(conn)
    elif args[0] == "fuentes":
        show_fuentes(conn)
    elif args[0] == "motivos":
        show_motivos(conn)
    elif args[0] == "evolve":
        suggest_improvements(conn)
    else:
        print("Uso:")
        print("  feedback.py              — Reporte semanal completo")
        print("  feedback.py snapshot     — Guardar metricas actuales")
        print("  feedback.py fuentes      — Rendimiento por fuente")
        print("  feedback.py motivos      — Motivos de descarte")
        print("  feedback.py evolve       — Sugerencias de mejora")

    conn.close()


if __name__ == "__main__":
    main()
