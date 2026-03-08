-- Housing Hunter Database Schema
-- SQLite database for tracking properties in Tacna

-- Zonas/distritos con datos de referencia
CREATE TABLE IF NOT EXISTS zonas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT, -- urbano, semi-rural, rural, centro
    alquiler_min INTEGER, -- soles/mes
    alquiler_max INTEGER,
    precio_m2_min REAL, -- USD/m2 terreno
    precio_m2_max REAL,
    seguridad INTEGER, -- 1-5
    internet INTEGER, -- 1-5
    espacio_mascotas INTEGER, -- 1-5
    servicios_basicos INTEGER, -- 1-5
    notas TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Propiedades encontradas
CREATE TABLE IF NOT EXISTS propiedades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modo TEXT NOT NULL CHECK(modo IN ('alquiler', 'venta')),
    tipo TEXT NOT NULL, -- casa, departamento, terreno, lote
    titulo TEXT NOT NULL,
    zona_id INTEGER REFERENCES zonas(id),
    distrito TEXT,
    direccion TEXT,
    area_m2 REAL,
    habitaciones INTEGER,
    banos INTEGER,
    precio REAL NOT NULL, -- soles para alquiler, USD para venta
    moneda TEXT DEFAULT 'PEN' CHECK(moneda IN ('PEN', 'USD')),
    precio_incluye TEXT, -- servicios incluidos en precio
    servicios_basicos INTEGER DEFAULT 0, -- 1=si, 0=no/desconocido
    internet INTEGER DEFAULT 0,
    acepta_mascotas TEXT DEFAULT 'desconocido' CHECK(acepta_mascotas IN ('si', 'no', 'desconocido', 'negociable')),
    tiene_patio INTEGER DEFAULT 0,
    estacionamiento INTEGER DEFAULT 0,
    amoblado INTEGER DEFAULT 0,
    titulo_saneado TEXT DEFAULT 'desconocido', -- para venta
    habilitacion_urbana TEXT DEFAULT 'desconocido', -- para venta
    score INTEGER, -- 0-100
    clase TEXT CHECK(clase IN ('A', 'B+', 'B', 'B-', 'C+', 'C', 'D')),
    estado TEXT DEFAULT 'nueva' CHECK(estado IN ('nueva', 'contactada', 'visitada', 'negociando', 'descartada', 'cerrada')),
    motivo_descarte TEXT,
    fuente TEXT, -- portal, facebook, periodico, contacto, clasificado
    fuente_detalle TEXT, -- nombre del grupo FB, portal, periodico
    url TEXT,
    contacto_nombre TEXT,
    contacto_telefono TEXT,
    contacto_tipo TEXT CHECK(contacto_tipo IN ('dueno', 'inmobiliaria', 'corredor', 'desconocido')),
    notas TEXT,
    destacado TEXT, -- por que destaca
    fecha_publicacion TEXT,
    fecha_encontrada TEXT DEFAULT (date('now')),
    fecha_contacto TEXT,
    fecha_visita TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Historial de busquedas
CREATE TABLE IF NOT EXISTS busquedas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT DEFAULT (date('now')),
    fuente TEXT NOT NULL, -- urbania, adondevivir, facebook, periodico, etc.
    modo TEXT CHECK(modo IN ('alquiler', 'venta', 'ambos')),
    propiedades_encontradas INTEGER DEFAULT 0,
    propiedades_nuevas INTEGER DEFAULT 0,
    notas TEXT
);

-- Programas de gobierno evaluados
CREATE TABLE IF NOT EXISTS programas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT, -- bono, credito, subsidio
    monto_beneficio TEXT,
    requisito_ingreso_max REAL, -- soles/mes
    requisitos TEXT,
    elegible TEXT DEFAULT 'por evaluar' CHECK(elegible IN ('si', 'no', 'por evaluar', 'parcial')),
    notas TEXT,
    url TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Contactos (duenos, corredores, inmobiliarias)
CREATE TABLE IF NOT EXISTS contactos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tipo TEXT CHECK(tipo IN ('dueno', 'inmobiliaria', 'corredor', 'notaria', 'otro')),
    telefono TEXT,
    email TEXT,
    facebook TEXT,
    notas TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_propiedades_modo ON propiedades(modo);
CREATE INDEX IF NOT EXISTS idx_propiedades_estado ON propiedades(estado);
CREATE INDEX IF NOT EXISTS idx_propiedades_distrito ON propiedades(distrito);
CREATE INDEX IF NOT EXISTS idx_propiedades_precio ON propiedades(precio);
CREATE INDEX IF NOT EXISTS idx_propiedades_score ON propiedades(score);

-- Vistas utiles
CREATE VIEW IF NOT EXISTS v_alquileres_activos AS
SELECT p.*, z.nombre as zona_nombre, z.seguridad, z.internet as zona_internet
FROM propiedades p
LEFT JOIN zonas z ON p.zona_id = z.id
WHERE p.modo = 'alquiler' AND p.estado NOT IN ('descartada', 'cerrada')
ORDER BY p.score DESC;

CREATE VIEW IF NOT EXISTS v_ventas_activas AS
SELECT p.*, z.nombre as zona_nombre, z.seguridad, z.internet as zona_internet
FROM propiedades p
LEFT JOIN zonas z ON p.zona_id = z.id
WHERE p.modo = 'venta' AND p.estado NOT IN ('descartada', 'cerrada')
ORDER BY p.score DESC;

CREATE VIEW IF NOT EXISTS v_resumen_por_zona AS
SELECT z.nombre,
    COUNT(CASE WHEN p.modo = 'alquiler' THEN 1 END) as alquileres,
    COUNT(CASE WHEN p.modo = 'venta' THEN 1 END) as ventas,
    AVG(CASE WHEN p.modo = 'alquiler' THEN p.precio END) as avg_alquiler,
    MIN(CASE WHEN p.modo = 'venta' THEN p.precio END) as min_venta,
    MAX(CASE WHEN p.modo = 'venta' THEN p.precio END) as max_venta
FROM zonas z
LEFT JOIN propiedades p ON p.zona_id = z.id AND p.estado NOT IN ('descartada')
GROUP BY z.id;
