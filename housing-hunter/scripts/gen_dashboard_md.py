#!/usr/bin/env python3
"""Generate Housing dashboard markdown from DB for Obsidian."""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from config import get_db, BASE_DIR, CIUDAD, DASHBOARD_PRESUPUESTO_ALQUILER, DASHBOARD_PRESUPUESTO_COMPRA, DASHBOARD_FECHA_INICIO

OUTPUT = BASE_DIR / "propiedades.md"


def main():
    conn = get_db()

    # Stats
    total = conn.execute("SELECT COUNT(*) FROM propiedades").fetchone()[0]
    alq_activos = conn.execute("SELECT COUNT(*) FROM propiedades WHERE modo='alquiler' AND estado NOT IN ('descartada','cerrada')").fetchone()[0]
    ven_activos = conn.execute("SELECT COUNT(*) FROM propiedades WHERE modo='venta' AND estado NOT IN ('descartada','cerrada')").fetchone()[0]
    contactadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='contactada'").fetchone()[0]
    visitadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='visitada'").fetchone()[0]
    negociando = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='negociando'").fetchone()[0]
    descartadas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='descartada'").fetchone()[0]
    nuevas = conn.execute("SELECT COUNT(*) FROM propiedades WHERE estado='nueva'").fetchone()[0]

    lines = []
    lines.append("# Seguimiento de Propiedades")
    lines.append("")
    lines.append(f"**Inicio**: {DASHBOARD_FECHA_INICIO}")
    lines.append(f"**Actualizado**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Total**: {total} propiedades ({alq_activos} alquileres activos, {ven_activos} ventas activas, {descartadas} descartadas)")
    lines.append(f"**Presupuesto alquiler**: {DASHBOARD_PRESUPUESTO_ALQUILER}")
    lines.append(f"**Presupuesto compra**: {DASHBOARD_PRESUPUESTO_COMPRA}")
    lines.append("")

    # Pipeline
    lines.append("## Pipeline")
    lines.append("")
    lines.append("| Estado | Cantidad |")
    lines.append("|---|---|")
    lines.append(f"| Nueva | {nuevas} |")
    lines.append(f"| Contactada | {contactadas} |")
    lines.append(f"| Visitada | {visitadas} |")
    lines.append(f"| Negociando | {negociando} |")
    lines.append(f"| Descartada | {descartadas} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # === ALQUILER TABLE ===
    lines.append("## Alquiler")
    lines.append("")
    lines.append("| # | Propiedad | Precio | Area | Hab | Distrito | Patio | Score | Fuente | Estado | Encontrada |")
    lines.append("|---|-----------|--------|------|-----|----------|-------|-------|--------|--------|------------|")

    alquileres = conn.execute(
        "SELECT * FROM propiedades WHERE modo='alquiler' AND estado NOT IN ('descartada','cerrada') "
        "ORDER BY score DESC, precio ASC"
    ).fetchall()
    for r in alquileres:
        precio = f"S/ {r['precio']:,.0f}" if r['precio'] and r['precio'] > 0 else "Por confirmar"
        area = f"{r['area_m2']:.0f} m2" if r['area_m2'] else "--"
        hab = str(r['habitaciones']) if r['habitaciones'] else "--"
        distrito = r['distrito'] or CIUDAD.title()
        patio = "Si" if r['tiene_patio'] else "--"
        score = f"{r['score']}%" if r['score'] else "--"
        fuente = r['fuente_detalle'] or "?"
        estado = r['estado'] or "nueva"
        fecha = r['fecha_encontrada'] or "--"
        lines.append(f"| {r['id']} | {r['titulo'][:40]} | {precio} | {area} | {hab} | {distrito} | {patio} | {score} | {fuente} | {estado} | {fecha} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # === VENTA TABLE ===
    lines.append("## Venta")
    lines.append("")
    lines.append("| # | Propiedad | Precio | Area | Distrito | Titulo SUNARP | Score | Fuente | Estado | Encontrada |")
    lines.append("|---|-----------|--------|------|----------|---------------|-------|--------|--------|------------|")

    ventas = conn.execute(
        "SELECT * FROM propiedades WHERE modo='venta' AND estado NOT IN ('descartada','cerrada') "
        "ORDER BY score DESC, precio ASC"
    ).fetchall()
    for r in ventas:
        precio_val = r['precio']
        moneda = r['moneda'] or 'USD'
        if precio_val and precio_val > 0:
            precio = f"${precio_val:,.0f}" if moneda == 'USD' else f"S/ {precio_val:,.0f}"
        else:
            precio = "Por confirmar"
        area = f"{r['area_m2']:.0f} m2" if r['area_m2'] else "--"
        distrito = r['distrito'] or CIUDAD.title()
        titulo_s = r['titulo_saneado'] if r['titulo_saneado'] and r['titulo_saneado'] != 'desconocido' else "Por verificar"
        score = f"{r['score']}%" if r['score'] else "--"
        fuente = r['fuente_detalle'] or "?"
        estado = r['estado'] or "nueva"
        fecha = r['fecha_encontrada'] or "--"
        lines.append(f"| {r['id']} | {r['titulo'][:40]} | {precio} | {area} | {distrito} | {titulo_s} | {score} | {fuente} | {estado} | {fecha} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # === DETAIL: ALQUILER ===
    lines.append("## Detalle Alquiler")
    lines.append("")
    for r in alquileres:
        precio = f"S/ {r['precio']:,.0f}/mes" if r['precio'] and r['precio'] > 0 else "Precio por confirmar"
        lines.append(f"### {r['id']}. {r['titulo'][:60]}")
        lines.append("")
        lines.append(f"- **Estado**: {r['estado']}")
        lines.append(f"- **Precio**: {precio}")
        area = f"{r['area_m2']:.0f} m2" if r['area_m2'] else "?"
        hab = r['habitaciones'] or "?"
        lines.append(f"- **Area**: {area} | **Habitaciones**: {hab} | **Banos**: {r['banos'] or '?'}")
        lines.append(f"- **Distrito**: {r['distrito'] or CIUDAD.title()} | **Direccion**: {r['direccion'] or '?'}")
        patio = "Si" if r['tiene_patio'] else "No/Desconocido"
        mascotas = r['acepta_mascotas'] or 'desconocido'
        lines.append(f"- **Patio**: {patio} | **Mascotas**: {mascotas}")
        lines.append(f"- **Fuente**: {r['fuente_detalle'] or '?'} | **Score**: {r['score'] or '--'}%")
        if r['contacto_nombre'] or r['contacto_telefono']:
            lines.append(f"- **Contacto**: {r['contacto_nombre'] or '?'} | Tel: {r['contacto_telefono'] or '?'}")
        if r['url']:
            lines.append(f"- **URL**: {r['url']}")
        if r['destacado']:
            lines.append(f"- **Destaca**: {r['destacado']}")
        if r['notas']:
            lines.append(f"- **Notas**: {r['notas']}")
        lines.append(f"- **Timeline**:")
        lines.append(f"  - {r['fecha_encontrada']}: Encontrada via {r['fuente_detalle']}")
        if r['fecha_contacto']:
            lines.append(f"  - {r['fecha_contacto']}: Contactada")
        if r['fecha_visita']:
            lines.append(f"  - {r['fecha_visita']}: Visitada")
        lines.append("")
        lines.append("---")
        lines.append("")

    # === DETAIL: VENTA ===
    lines.append("## Detalle Venta")
    lines.append("")
    for r in ventas:
        precio_val = r['precio']
        moneda = r['moneda'] or 'USD'
        if precio_val and precio_val > 0:
            precio = f"${precio_val:,.0f} USD" if moneda == 'USD' else f"S/ {precio_val:,.0f}"
        else:
            precio = "Precio por confirmar"
        lines.append(f"### {r['id']}. {r['titulo'][:60]}")
        lines.append("")
        lines.append(f"- **Estado**: {r['estado']}")
        lines.append(f"- **Precio**: {precio}")
        area = f"{r['area_m2']:.0f} m2" if r['area_m2'] else "?"
        lines.append(f"- **Area**: {area} | **Tipo**: {r['tipo']}")
        lines.append(f"- **Distrito**: {r['distrito'] or CIUDAD.title()} | **Direccion**: {r['direccion'] or '?'}")
        titulo_s = r['titulo_saneado'] if r['titulo_saneado'] and r['titulo_saneado'] != 'desconocido' else 'Por verificar'
        hab_urb = r['habilitacion_urbana'] if r['habilitacion_urbana'] and r['habilitacion_urbana'] != 'desconocido' else 'Por verificar'
        lines.append(f"- **Titulo SUNARP**: {titulo_s} | **Hab. urbana**: {hab_urb}")
        lines.append(f"- **Fuente**: {r['fuente_detalle'] or '?'} | **Score**: {r['score'] or '--'}%")
        if r['contacto_nombre'] or r['contacto_telefono']:
            lines.append(f"- **Contacto**: {r['contacto_nombre'] or '?'} | Tel: {r['contacto_telefono'] or '?'}")
        if r['url']:
            lines.append(f"- **URL**: {r['url']}")
        if r['destacado']:
            lines.append(f"- **Destaca**: {r['destacado']}")
        if r['notas']:
            lines.append(f"- **Notas**: {r['notas']}")
        lines.append(f"- **Timeline**:")
        lines.append(f"  - {r['fecha_encontrada']}: Encontrada via {r['fuente_detalle']}")
        if r['fecha_contacto']:
            lines.append(f"  - {r['fecha_contacto']}: Contactada")
        if r['fecha_visita']:
            lines.append(f"  - {r['fecha_visita']}: Visitada")
        lines.append("")
        lines.append("---")
        lines.append("")

    # === DESCARTADAS ===
    descartadas_rows = conn.execute(
        "SELECT id, modo, titulo, precio, moneda, motivo_descarte FROM propiedades WHERE estado='descartada' ORDER BY modo, id"
    ).fetchall()
    if descartadas_rows:
        lines.append("## Descartadas")
        lines.append("")
        for r in descartadas_rows:
            moneda = r['moneda'] or 'PEN'
            sym = "S/" if moneda == "PEN" else "$"
            precio = f"{sym}{r['precio']:,.0f}" if r['precio'] else "?"
            motivo = r['motivo_descarte'] or "Sin motivo"
            lines.append(f"- ~~#{r['id']} {r['titulo'][:50]} ({precio})~~ — {motivo}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # === PROGRAMAS ===
    programas = conn.execute("SELECT * FROM programas").fetchall()
    lines.append("## Programas de Gobierno")
    lines.append("")
    lines.append("| Programa | Beneficio | Elegible | Notas |")
    lines.append("|----------|-----------|----------|-------|")
    for p in programas:
        lines.append(f"| {p['nombre']} | {p['monto_beneficio']} | {p['elegible']} | {p['notas'] or '--'} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # === ESTADOS ===
    lines.append("## Estados de referencia")
    lines.append("")
    lines.append("| Estado | Descripcion |")
    lines.append("|---|---|")
    lines.append("| nueva | Encontrada, pendiente de revisar |")
    lines.append("| contactada | Se contacto al dueno/publicador |")
    lines.append("| visitada | Se visito la propiedad |")
    lines.append("| negociando | En negociacion de precio/condiciones |")
    lines.append("| descartada | Descartada por precio, ubicacion u otro motivo |")
    lines.append("| cerrada | Trato cerrado |")

    conn.close()

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated: {OUTPUT} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
