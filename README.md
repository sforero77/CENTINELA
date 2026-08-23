# CENTINELA

**Sistema abierto de exposicion sismica automatizada para America Latina.**

Ante cualquier sismo relevante en la region, CENTINELA publica en menos de una
hora un reporte de **exposicion**: cuantas personas, edificaciones, escuelas,
hospitales y kilometros de via quedan dentro de cada franja de intensidad
sismica, por municipio y por celda H3, con datos descargables y en espanol.

> **Exposicion no es dano.** Este sistema no es una alerta temprana, no estima
> victimas, no dictamina habitabilidad y no reemplaza a los servicios
> geologicos ni a las unidades de gestion del riesgo. Ver
> [`DISCLAIMER.md`](DISCLAIMER.md).

## Por que existe

En el terremoto del Choco (M7.4, 10 de agosto de 2026) el pais tardo **dias**
en saber cuanta poblacion e infraestructura estaba en la zona de intensidad
fuerte. Las cifras oficiales oscilaron durante semanas. La unica evaluacion de
dano con IA cubrio una sola ciudad, y toda la capacidad analitica vino de fuera
de la region. Siete semanas antes, en Venezuela, paso exactamente lo mismo.

No existe memoria ni capacidad regional pre-posicionada. Este proyecto es esa
capacidad.

## Como funciona

```
[Feed GeoJSON de USGS] ──(cron cada 10 min)──▶ P1 TRIGGER
     filtro bbox LATAM + M≥5.5 + dedupe por event_state
         │
         ▼
     P2 IMPACTO   contornos MMI → celdas H3 r8 ⋈ activo de exposicion
                  rasters de Ground Failure → muestreo por celda
         │
         ▼
     P3 REPORTE   report.json → md + mapa + CSV + parquet + PMTiles + hilo
                  (se re-emite solo cuando aparece ShakeMap v(n+1))

[Trimestral]   P0 EXPOSICION  construye el activo por pais desde fuentes publicas
[Por evento]   P4 BRIGADA     dano por edificacion con IA, cuando hay imagen abierta
```

El principio rector es **~95 % automatico, ~5 % humano**: una comunidad no
opera turnos, mantiene codigo y datos. El unico paso manual permitido en todo
el sistema es dar clic para publicar el hilo en redes.

## Arranque

```bash
make setup                 # instala todo con uv (Python 3.12)
make check                 # lint + mypy + pruebas
make trigger               # P1 en seco contra el feed vivo de USGS
make country ISO=COL       # reconstruye el activo de exposicion de Colombia
```

Sin credenciales, sin servidor, sin cuenta en ningun servicio. Si algo del
arranque no funciona en tu maquina, eso es un bug.

## Estado del proyecto

**Fase 0, semana 1 — andamiaje.** Lo que ya funciona y lo que falta:

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, `event_state`) | ✅ funcional, con pruebas |
| Contratos USGS (feed + productos) y su validacion | ✅ funcional |
| Decision de impacto e idempotencia por version | ✅ funcional |
| Modelo y render del reporte (json, md, CSV, hilo) | ✅ funcional |
| Regla de los tres cubos y lint de manifests | ✅ funcional, corre en CI |
| Golden tests G1/G2/G3 con productos reales congelados | ✅ corren |
| Resolucion de descargas por la API de HDX | ✅ funcional |
| P0 crosswalk DIVIPOLA (1.122 municipios, 1,5 M celdas) | ✅ funcional |
| P0 agregacion raster→H3 y seleccion de fuentes | ✅ funcional |
| P2 polyfill H3 de contornos MMI | ✅ funcional |
| P2 muestreo de Ground Failure | ✅ funcional |
| P2 join de impacto en DuckDB | ✅ funcional |
| **Backtest del 10-ago-2026 end-to-end** | ✅ **reporte publicado** |
| P0 capas de salud, educacion, vias y desglose etario | ✅ funcional |
| P0 ensamblaje, validacion del total y escritura del activo | ✅ funcional |
| P0 `build_country`: encadenar las descargas en un comando | ⏳ pendiente |
| Mapa estatico del reporte | ⏳ decision T0.8 |
| P4 brigada de imagen | ⏳ Fase 2 |

Las etapas pendientes fallan de forma ruidosa y explicita — nunca devuelven un
cero que acabaria publicado como cifra. `tests/unit/test_pendientes.py` es el
inventario vivo de esa deuda: la lista encogiendo es el indicador de avance.

Los golden tests corren contra **productos reales congelados** de los dos
eventos que motivan el proyecto: Chocó (`us6000tjl2`) y el doble mainshock de
Venezuela (`us6000t7zp`, `us6000t7zc`). Ya cazaron dos bugs que ninguna prueba
sintetica habria encontrado — ver `tests/fixtures/golden/README.md`.

### El backtest del Chocó

`reports/us6000tjl2/` es la respuesta a la pregunta que motiva el proyecto:
**esto es lo que el pais habria sabido el 10 de agosto**, en vez de esperar dias.

| | |
|---|---|
| Personas en MMI≥6 | **6.960.086** |
| Personas en MMI≥7 | **2.415.793** |
| De ellas, 65 anos o mas | **270 mil** |
| Edificaciones en MMI≥7 | **444.281** |
| Sedes de salud en MMI≥7 | **512** |
| Sedes educativas en MMI≥7 | **997** |
| Kilometros de via en MMI≥7 | **1.400** |
| Personas en zona de licuefaccion alta | **1.660.190** |
| Municipios alcanzados | **297** |

El activo del que salen: **519.735 celdas**, 52,9 millones de habitantes, 15,4
millones de edificaciones, 9.615 sedes de salud, 43.837 sedes educativas y
44.919 km de via, en los 1.122 municipios del pais. 17,3 MB de GeoParquet.

Y el dato que cambia la conversacion: los municipios mas expuestos no estaban en
Chocó sino en el Eje Cafetero y el Valle — Pereira, Buenaventura, Armenia,
Tuluá, Dosquebradas. La unica evaluacion de dano con IA que existio cubrio una
sola ciudad.

## Estructura

```
pipelines/       p0_exposure, p1_trigger, p2_impact, p3_report, p4_brigada, common
schemas/         JSON Schema del reporte, del estado y de los contratos USGS
data/manifests/  vintages por pais (fuente, url, licencia, hash, fecha)
events/          event_state por evento — la base de datos del sistema, en git
reports/         salidas publicadas (json + md + csv + png)
site/            visor estatico (MapLibre + PMTiles, cero llaves de API)
tests/           unit/, integration/, golden/, fixtures/
```

## Documentacion

- [`ESPECIFICACION.md`](ESPECIFICACION.md) — especificacion tecnica v0.9
- [`VERIFICACIONES.md`](VERIFICACIONES.md) — cierre de las tareas ⚠️ de §8, con metodo y hallazgos
- [`DISCLAIMER.md`](DISCLAIMER.md) — que informa y que no informa el sistema
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — como ayudar (incluye rol de mantenedor por pais)
- [`GOVERNANCE.md`](GOVERNANCE.md) — roles, decisiones, frontera comunidad ↔ empresa
- [`ATTRIBUTION.md`](ATTRIBUTION.md) — creditos obligatorios de cada fuente
- [`LICENSES/`](LICENSES/) — la regla de los tres cubos

## Licencia

Codigo: **Apache-2.0**. Datos derivados: **CC BY 4.0** en el nucleo, **ODbL**
donde entra OpenStreetMap u Overture. Detalle en [`LICENSES/`](LICENSES/).
