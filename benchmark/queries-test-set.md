# Test Set: 35 queries estandarizadas

Enviar cada query a ambos bots. Registrar con `benchmark-cli.py interactive`.

## simple (10)

| # | Query | Qué mide |
|---|-------|----------|
| 1 | hola | Overhead base, saludo |
| 2 | qué hora es? | Respuesta factual simple |
| 3 | quién eres? | Identidad, tokens de sistema |
| 4 | cuál es tu modelo? | Metadata del modelo |
| 5 | di "ok" y nada más | Respuesta mínima absoluta |
| 6 | cuánto es 2+2? | Razonamiento trivial |
| 7 | qué día es hoy? | Acceso a fecha |
| 8 | repite: "benchmark test" | Echo, sin tools |
| 9 | gracias | Respuesta cortés corta |
| 10 | adiós | Cierre de conversación |

## skill (10)

| # | Query | Skill esperada | Qué mide |
|---|-------|----------------|----------|
| 11 | quién está conectado? | wifi-devices | Invocación tool + parse JSON |
| 12 | escanea bluetooth | bt-devices | BT scan, latencia ~10s |
| 13 | bloquea tiktok | adguard | Escritura AdGuard API |
| 14 | desbloquea tiktok | adguard | Deshacer acción |
| 15 | estado del pi | rpi-health | Health check |
| 16 | muestra las estadísticas de DNS | adguard | Lectura API, formateo |
| 17 | qué dispositivos están registrados? | wifi-devices | Lista devices DB |
| 18 | cuándo fue la última vez que se vio a Roxsy? | wifi-devices | last-seen query |
| 19 | muestra los últimos 10 queries DNS | adguard | querylog |
| 20 | lista los dispositivos bluetooth conocidos | bt-devices | BT list |

## reasoning (5)

| # | Query | Qué mide |
|---|-------|----------|
| 21 | por qué Roxsy no aparece como conectada? | Análisis con datos de scan |
| 22 | analiza el tráfico DNS de hoy, hay algo raro? | Interpretar querylog |
| 23 | qué dispositivo ha estado más tiempo online hoy? | Análisis presencia |
| 24 | la temperatura del Pi está normal para esta hora? | Contextualización |
| 25 | compara la actividad de red de hoy vs ayer | Análisis temporal |

## multi-step (5)

| # | Query | Skills encadenadas | Qué mide |
|---|-------|--------------------|----------|
| 26 | escanea la red y si hay desconocidos dime sus IPs | wifi + razonamiento | Chain + filtro |
| 27 | revisa la salud del pi, si algo está mal avísame | health + razonamiento | Condicional |
| 28 | bloquea youtube de 22 a 8 para Celular-Roxsy | adguard (schedule) | Comando complejo |
| 29 | escanea wifi y bluetooth, dame un resumen combinado | wifi + bt | Dos tools + merge |
| 30 | muestra quién está online y cuántas queries DNS tienen hoy | wifi + adguard | Cross-skill |

## home_search (5)

Queries de razonamiento general sobre búsqueda de departamento en Tacna, Peru. Sin skill dedicada — prueba capacidad base de razonamiento, comparación de opciones y contextualización personal.

| # | Query | Qué mide |
|---|-------|----------|
| 31 | tengo presupuesto de S/800 mensuales para alquiler en Tacna. ¿cuánto debería destinar a gastos fijos (luz, agua, internet) y cuánto queda libre? | Razonamiento numérico con contexto personal |
| 32 | estoy eligiendo entre un depa de S/700 en el centro con agua incluida, o uno de S/600 en el distrito Gregorio Albarracín sin agua. ¿cuál conviene más? | Análisis costo-beneficio, comparación de opciones |
| 33 | qué preguntas le haría al dueño antes de firmar un contrato de alquiler en Peru? | Conocimiento práctico, lista estructurada |
| 34 | mudarse solo vs compartir depa en Tacna a S/800 de presupuesto. dame pros y contras | Razonamiento con trade-offs, respuesta equilibrada |
| 35 | encontré un depa a S/650, el dueño pide 2 meses de garantía + 1 mes adelantado. ¿es normal? ¿cómo negocio? | Razonamiento contextual, consejo práctico |
