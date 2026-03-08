#!/usr/bin/env python3
"""Housing Hunter — Dashboard CLI.

Muestra propiedades activas para investigar o descartar.
Uso:
    python3 dashboard.py              # Vista general
    python3 dashboard.py alquiler     # Solo alquileres
    python3 dashboard.py venta        # Solo ventas
    python3 dashboard.py descartar 5  # Descartar propiedad #5
    python3 dashboard.py contactar 1  # Marcar #1 como contactada
    python3 dashboard.py detalle 3    # Ver detalle de #3
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_db


def color(text, code):
    return f"\033[{code}m{text}\033[0m"

def green(t): return color(t, "32")
def yellow(t): return color(t, "33")
def red(t): return color(t, "31")
def cyan(t): return color(t, "36")
def bold(t): return color(t, "1")
def dim(t): return color(t, "2")


def show_overview(conn):
    """Show general stats."""
    total = conn.execute("SELECT COUNT(*) FROM propiedades").fetchone()[0]
    alq = conn.execute("SELECT COUNT(*) FROM propiedades WHERE modo='alquiler' AND estado NOT IN ('descartada','cerrada')").fetchone()[0]
    ven = conn.execute("SELECT COUNT(*) FROM propiedades WHERE modo='venta' AND estado NOT IN ('descartada','cerrada')").fetchone()[0]
    desc = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='descartada'").fetchone()[0]
    cont = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='contactada'").fetchone()[0]
    hoy = conn.execute("SELECT COUNT(*) FROM propiedades WHERE fecha_encontrada = date('now')").fetchone()[0]

    print(bold("HOUSING HUNTER — Dashboard"))
    print(f"{'='*60}")
    print(f"  Total: {bold(str(total))}  |  Alquiler activos: {green(str(alq))}  |  Venta activos: {green(str(ven))}")
    print(f"  Contactadas: {cyan(str(cont))}  |  Descartadas: {dim(str(desc))}  |  Nuevas hoy: {yellow(str(hoy))}")
    print()

    # Sources
    print(bold("Por fuente:"))
    for r in conn.execute("SELECT fuente_detalle, COUNT(*) c FROM propiedades WHERE estado NOT IN ('descartada') GROUP BY fuente_detalle ORDER BY c DESC"):
        print(f"  {r[0]}: {r[1]}")
    print()


def show_listings(conn, modo=None):
    """Show active property listings."""
    where = "WHERE estado NOT IN ('descartada','cerrada')"
    if modo:
        where += f" AND modo='{modo}'"

    rows = conn.execute(f"""
        SELECT id, modo, titulo, precio, moneda, area_m2, habitaciones,
               distrito, score, clase, estado, fuente_detalle, tiene_patio,
               acepta_mascotas, url, fecha_encontrada
        FROM propiedades {where}
        ORDER BY modo, score DESC, precio ASC
    """).fetchall()

    current_modo = None
    for r in rows:
        if r["modo"] != current_modo:
            current_modo = r["modo"]
            header = "ALQUILER" if current_modo == "alquiler" else "VENTA"
            print(bold(f"\n{'='*60}"))
            print(bold(f"  {header}"))
            print(bold(f"{'='*60}"))

        # Format price
        sym = "S/" if r["moneda"] == "PEN" else "$"
        precio = f"{sym}{r['precio']:,.0f}" if r["precio"] else "????"
        if r["modo"] == "alquiler":
            precio += "/mes"

        # Status color
        estado = r["estado"]
        if estado == "contactada":
            estado_str = cyan(f"[{estado}]")
        elif estado == "visitada":
            estado_str = green(f"[{estado}]")
        elif estado == "negociando":
            estado_str = yellow(f"[{estado}]")
        else:
            estado_str = dim(f"[{estado}]")

        # Score badge
        score = r["score"]
        if score and score >= 80:
            score_str = green(f"{score}%")
        elif score and score >= 65:
            score_str = yellow(f"{score}%")
        elif score:
            score_str = dim(f"{score}%")
        else:
            score_str = dim("--")

        # Icons
        patio = " PATIO" if r["tiene_patio"] else ""
        mascotas = ""
        if r["acepta_mascotas"] == "si":
            mascotas = green(" MASCOTAS-OK")
        elif r["acepta_mascotas"] == "negociable":
            mascotas = yellow(" MASCOTAS-?")

        area = f"{r['area_m2']:.0f}m2" if r["area_m2"] else ""
        hab = f"{r['habitaciones']}hab" if r["habitaciones"] else ""
        detalles = " | ".join(filter(None, [area, hab]))

        pid = r['id']
        print(f"\n  {bold(f'#{pid}')} {estado_str} {r['titulo'][:55]}")
        print(f"     {bold(precio)}  {detalles}{patio}{mascotas}")
        print(f"     {r['distrito']} | Score: {score_str} | {dim(r['fuente_detalle'])} | {dim(r['fecha_encontrada'])}")
        if r["url"]:
            print(f"     {dim(r['url'][:70])}")


def show_detail(conn, prop_id):
    """Show full detail of a property."""
    r = conn.execute("SELECT * FROM propiedades WHERE id=?", (prop_id,)).fetchone()
    if not r:
        print(red(f"Propiedad #{prop_id} no encontrada"))
        return

    print(bold(f"\n{'='*60}"))
    print(bold(f"  #{r['id']} — {r['titulo']}"))
    print(f"{'='*60}")
    sym = "S/" if r["moneda"] == "PEN" else "$"
    precio_val = r['precio']
    print(f"  Modo: {r['modo']}  |  Tipo: {r['tipo']}  |  Estado: {r['estado']}")
    print(f"  Precio: {bold(f'{sym}{precio_val:,.0f}')}")
    print(f"  Area: {r['area_m2'] or '?'} m2  |  Habitaciones: {r['habitaciones'] or '?'}  |  Banos: {r['banos'] or '?'}")
    print(f"  Distrito: {r['distrito']}  |  Direccion: {r['direccion'] or '?'}")
    print(f"  Servicios: {'Si' if r['servicios_basicos'] else '?'}  |  Internet: {'Si' if r['internet'] else '?'}")
    print(f"  Mascotas: {r['acepta_mascotas']}  |  Patio: {'Si' if r['tiene_patio'] else 'No'}")
    print(f"  Amoblado: {'Si' if r['amoblado'] else 'No'}  |  Estacionamiento: {'Si' if r['estacionamiento'] else 'No'}")
    if r["modo"] == "venta":
        print(f"  Titulo SUNARP: {r['titulo_saneado']}  |  Hab. urbana: {r['habilitacion_urbana']}")
    print(f"  Score: {r['score'] or '--'}%  |  Clase: {r['clase'] or '--'}")
    print(f"  Fuente: {r['fuente']} ({r['fuente_detalle']})")
    print(f"  Contacto: {r['contacto_nombre'] or '?'} | Tel: {r['contacto_telefono'] or '?'} | Tipo: {r['contacto_tipo'] or '?'}")
    print(f"  URL: {r['url'] or 'N/A'}")
    print(f"  Encontrada: {r['fecha_encontrada']}  |  Contactada: {r['fecha_contacto'] or '--'}  |  Visitada: {r['fecha_visita'] or '--'}")
    if r["destacado"]:
        print(f"\n  {bold('Por que destaca:')}")
        print(f"  {r['destacado']}")
    if r["notas"]:
        print(f"\n  {bold('Notas:')}")
        print(f"  {r['notas']}")


def update_estado(conn, prop_id, nuevo_estado, motivo=None):
    """Update property status."""
    r = conn.execute("SELECT titulo, estado FROM propiedades WHERE id=?", (prop_id,)).fetchone()
    if not r:
        print(red(f"Propiedad #{prop_id} no encontrada"))
        return

    updates = {"estado": nuevo_estado}
    if nuevo_estado == "descartada" and motivo:
        updates["motivo_descarte"] = motivo
    if nuevo_estado == "contactada":
        updates["fecha_contacto"] = "date('now')"

    set_clause = ", ".join(f"{k} = ?" for k in updates if k != "fecha_contacto")
    values = [v for k, v in updates.items() if k != "fecha_contacto"]

    if nuevo_estado == "contactada":
        set_clause += ", fecha_contacto = date('now')"

    conn.execute(f"UPDATE propiedades SET {set_clause} WHERE id=?", values + [prop_id])
    conn.commit()
    print(green(f"#{prop_id} '{r['titulo'][:40]}': {r['estado']} -> {nuevo_estado}"))


def main():
    conn = get_db()
    args = sys.argv[1:]

    if not args:
        show_overview(conn)
        show_listings(conn)
    elif args[0] == "alquiler":
        show_overview(conn)
        show_listings(conn, "alquiler")
    elif args[0] == "venta":
        show_overview(conn)
        show_listings(conn, "venta")
    elif args[0] == "detalle" and len(args) > 1:
        show_detail(conn, int(args[1]))
    elif args[0] == "descartar" and len(args) > 1:
        motivo = " ".join(args[2:]) if len(args) > 2 else None
        update_estado(conn, int(args[1]), "descartada", motivo)
    elif args[0] == "contactar" and len(args) > 1:
        update_estado(conn, int(args[1]), "contactada")
    elif args[0] == "visitar" and len(args) > 1:
        update_estado(conn, int(args[1]), "visitada")
    elif args[0] == "negociar" and len(args) > 1:
        update_estado(conn, int(args[1]), "negociando")
    else:
        print("Uso:")
        print("  dashboard.py              — Vista general")
        print("  dashboard.py alquiler     — Solo alquileres")
        print("  dashboard.py venta        — Solo ventas")
        print("  dashboard.py detalle N    — Detalle de propiedad #N")
        print("  dashboard.py descartar N [motivo]  — Descartar #N")
        print("  dashboard.py contactar N  — Marcar #N como contactada")
        print("  dashboard.py visitar N    — Marcar #N como visitada")
        print("  dashboard.py negociar N   — Marcar #N en negociacion")

    conn.close()


if __name__ == "__main__":
    main()
