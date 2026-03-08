-- Seed data: zonas de Tacna
INSERT INTO zonas (nombre, tipo, alquiler_min, alquiler_max, precio_m2_min, precio_m2_max, seguridad, internet, espacio_mascotas, servicios_basicos, notas) VALUES
('Gregorio Albarracin', 'urbano', 750, 1500, 350, 500, 3, 4, 4, 4, 'Distrito mas poblado. Mejor relacion precio-calidad. Urbanizaciones: Las Artes, Villa Caplina, Alfonso Ugarte, Vinani'),
('Ciudad Nueva', 'urbano', 600, 1000, 150, 300, 2, 3, 3, 3, 'Sector popular, mas economico. Mayor incidencia delictiva'),
('Alto de la Alianza', 'urbano', 600, 1200, 150, 350, 2, 3, 3, 3, 'Similar a Ciudad Nueva, sector popular'),
('Pocollay', 'urbano', 1200, 2000, 300, 600, 4, 4, 3, 4, 'Zona residencial tranquila, clase media-alta. Mas caro'),
('Calana', 'semi-rural', 800, 1500, 50, 150, 3, 2, 5, 3, 'Casas huerta, zona campestre. Lotes grandes 480-800m2. Internet limitado'),
('Cercado', 'centro', 900, 1500, NULL, NULL, 3, 5, 2, 5, 'Centro urbano. Pocas casas con patio. Terrenos escasos y caros'),
('Leguia', 'urbano', 800, 1200, NULL, NULL, 3, 3, 3, 3, 'Zona intermedia, poca oferta en portales');

-- Seed data: propiedades de alquiler encontradas 2026-03-08
INSERT INTO propiedades (modo, tipo, titulo, zona_id, distrito, direccion, area_m2, habitaciones, banos, precio, moneda, servicios_basicos, internet, tiene_patio, score, clase, fuente, fuente_detalle, url, destacado) VALUES
('alquiler', 'casa', 'Casa Urb. Los Damascos', 1, 'Gregorio Albarracin', 'Urb. Los Damascos, cerca Colegio Humboldt', NULL, 3, 2, 1500, 'PEN', 1, 0, 1, 85, 'A', 'clasificado', 'Nestoria', 'https://www.nestoria.pe/tacna_peru/casas/alquiler', 'PATIO AMPLIO. 3 hab + estudio. 2 banos. Casa nueva. La mejor opcion para mascotas'),
('alquiler', 'departamento', 'Depto Calle 37 G. Albarracin', 1, 'Gregorio Albarracin', 'Calle Treinta y Siete', 90, 2, 1, 0, 'PEN', 1, 1, 0, 80, 'A', 'clasificado', 'Nestoria', 'https://www.nestoria.pe/tacna_peru/departamentos/alquiler', 'Amoblado con servicios incluidos (wifi, cable, agua caliente). Precio por confirmar'),
('alquiler', 'departamento', 'Depto Las Vinas I', 1, 'Gregorio Albarracin', 'Calle Treinta 8, Las Vinas I', 69, 2, 1, 775, 'PEN', 1, 1, 0, 78, 'B+', 'clasificado', 'Nestoria', NULL, 'Precio mas accesible S/775 total. Buena base temporal'),
('alquiler', 'departamento', 'Depto Pasaje Seis', 1, 'Gregorio Albarracin', 'Pasaje Seis 5', 130, 2, 2, 1500, 'PEN', 1, 1, 0, 75, 'B', 'clasificado', 'Nestoria', NULL, '130m2 amplio. Jacuzzi. Verificar balcon/terraza para perros'),
('alquiler', 'departamento', 'Depto Las Artes II', 1, 'Gregorio Albarracin', 'Urbanizacion Las Artes II', NULL, 3, 2, 1000, 'PEN', 1, 0, 0, 72, 'B', 'clasificado', 'Nestoria', NULL, 'Vigilancia 24h. De estreno. 3 hab'),
('alquiler', 'departamento', 'Depto Av. La Cultura', NULL, 'Tacna', 'Avenida La Cultura', 55, 2, 1, 1000, 'PEN', 1, 1, 0, 68, 'B', 'clasificado', 'Nestoria', NULL, '55m2 pequeno para pareja + 2 perros'),
('alquiler', 'departamento', 'Depto Centro Arias y Araguez 2do', 6, 'Cercado', 'Calle Arias y Araguez', 65, 2, 1, 1300, 'PEN', 1, 1, 0, 70, 'B', 'inmobiliaria', 'Almaper Inversiones', NULL, 'Servicios incluidos. Terraza con parrilla. Centro no ideal para perros'),
('alquiler', 'departamento', 'Depto Centro Arias y Araguez 4to', 6, 'Cercado', 'Calle Arias y Araguez', 70, 2, 1, 1500, 'PEN', 1, 1, 0, 68, 'B', 'inmobiliaria', 'Almaper Inversiones', NULL, 'Similar al 2do piso pero S/200 mas caro'),
('alquiler', 'departamento', 'Depto Av. Collpa Piso 8', NULL, 'Tacna', 'Avenida Collpa 74-106', 70.29, 3, 2, 1100, 'PEN', 1, 0, 0, 65, 'B', 'inmobiliaria', 'MASPROP', NULL, '3 hab, cochera, ascensor. Piso 8 no ideal para perros. Contacto: +51 908 874 713'),
('alquiler', 'departamento', 'Mini depto Centro Bolivar', 6, 'Cercado', 'Calle Bolivar', 45, 1, 1, 900, 'PEN', 1, 0, 0, 45, 'C', 'clasificado', 'Nestoria', NULL, '45m2, 1 hab. Insuficiente para pareja + 2 perros');

-- Seed data: propiedades de venta encontradas 2026-03-08
INSERT INTO propiedades (modo, tipo, titulo, zona_id, distrito, direccion, area_m2, precio, moneda, servicios_basicos, titulo_saneado, habilitacion_urbana, score, clase, fuente, fuente_detalle, url, destacado) VALUES
('venta', 'terreno', 'Terreno frente Aeropuerto', NULL, 'Tacna', 'Frente al Aeropuerto de Tacna', 120, 16000, 'USD', 1, 'por verificar', 'por verificar', 75, 'B+', 'clasificado', 'LaEncontre', 'https://www.laencontre.com.pe/venta/terrenos/tacna/f_baratos', 'Precio accesible. Servicios disponibles. Posible ruido de aviones'),
('venta', 'lote', 'Lote Aeronova 120m2', NULL, 'Tacna', 'Aeronova Residencial', 120, 27000, 'USD', 1, 'registrado', 'si', 72, 'B', 'inmobiliaria', 'Properati', 'https://www.properati.com.pe/s/tacna/terreno/venta', 'Proyecto formal con habilitacion urbana. Elegible para CSP'),
('venta', 'lote', 'Lote Aeronova 137m2', NULL, 'Tacna', 'Aeronova Residencial', 137, 32000, 'USD', 1, 'registrado', 'si', 70, 'B', 'inmobiliaria', 'Properati', NULL, 'Mas grande que el de 120m2. Mismas ventajas'),
('venta', 'terreno', 'Terreno 96m2 Tacna', NULL, 'Tacna', 'Por confirmar', 96, 16000, 'USD', 0, 'por verificar', 'desconocido', 68, 'B', 'clasificado', 'LaEncontre', NULL, 'Precio accesible. 96m2 suficiente para casa basica. Verificar todo'),
('venta', 'terreno', 'Terrenos Calana Casa Huerta', 5, 'Calana', 'Casa Huerta Santa Rita', 480, 15000, 'USD', 1, 'por verificar', 'desconocido', 65, 'B', 'clasificado', 'Trovit', NULL, 'Terrenos grandes 480-800m2. Ideal para perros. Internet limitado'),
('venta', 'terreno', 'Terreno playa Sama 200m2', NULL, 'Sama', 'Cerca de playa Sama', 200, 13000, 'USD', 0, 'por verificar', 'desconocido', 55, 'C', 'clasificado', 'LaEncontre', NULL, 'Zona playa, no para vivienda principal. Posible inversion'),
('venta', 'casa', 'Casa terreno Heroes Vinani', 1, 'Gregorio Albarracin', 'Heroes de Alto Vinani', 140, 42000, 'USD', 1, 'por verificar', 'desconocido', 60, 'B-', 'inmobiliaria', 'Masprop', 'https://www.maspropinmobiliaria.com/ficha/casa/tacna/corone-gregorio-albarracin/9634/21829880/es/', 'Se vende como terreno. 140m2. Negociable. Ligeramente sobre presupuesto'),
('venta', 'casa', 'Casa Calle El Moral 120m2', 1, 'Gregorio Albarracin', 'Calle El Moral 11, cerca municipalidad', 120, 65000, 'USD', 1, 'por verificar', 'desconocido', 58, 'C+', 'clasificado', 'Nestoria', NULL, 'Casa lista con patio. Sobre presupuesto. Solo viable con financiamiento');

-- Seed data: programas de gobierno
INSERT INTO programas (nombre, tipo, monto_beneficio, requisito_ingreso_max, requisitos, elegible, url) VALUES
('Techo Propio CSP', 'bono', 'S/ 33,000 (S/ 38,520 regiones especiales)', 2706, 'Grupo familiar con dependiente, no propietario, no apoyo previo, terreno propio inscrito SUNARP', 'por evaluar', 'https://www.mivivienda.com.pe'),
('Techo Propio AVN', 'bono', 'Hasta S/ 47,850', 3715, 'Grupo familiar con dependiente, no propietario, no apoyo previo', 'por evaluar', 'https://www.mivivienda.com.pe'),
('Techo Propio MV', 'bono', 'Hasta S/ 12,650', 2706, 'Grupo familiar, vivienda existente para mejorar', 'por evaluar', NULL),
('Nuevo Credito MiVivienda + BBP', 'credito', 'Credito + BBP hasta S/ 27,400', NULL, 'Mayor de edad, no propietario, calificacion crediticia, cuota inicial 7.5%', 'por evaluar', 'https://www.gob.pe/33425');

-- Seed data: busqueda inicial
INSERT INTO busquedas (fecha, fuente, modo, propiedades_encontradas, propiedades_nuevas, notas) VALUES
('2026-03-08', 'nestoria', 'alquiler', 10, 10, 'Primera busqueda. Portales: Nestoria, LaEncontre, Properati, Urbania'),
('2026-03-08', 'nestoria,laencontre,properati', 'venta', 8, 8, 'Primera busqueda de terrenos y casas');
