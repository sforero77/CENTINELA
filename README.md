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
| P2 polyfill H3, muestreo de Ground Failure, join DuckDB | ⏳ semana 3 |
| P0 construccion del activo y crosswalk DIVIPOLA | ⏳ semana 2 |
| Mapa estatico del reporte | ⏳ semana 3 (decision T0.8) |
| P4 brigada de imagen | ⏳ Fase 2 |

Las etapas pendientes fallan de forma ruidosa y explicita — nunca devuelven un
cero que acabaria publicado como cifra. `tests/unit/test_pendientes.py` es el
inventario vivo de esa deuda: la lista encogiendo es el indicador de avance.

Los golden tests corren contra **productos reales congelados** de los dos
eventos que motivan el proyecto: Chocó (`us6000tjl2`) y el doble mainshock de
Venezuela (`us6000t7zp`, `us6000t7zc`). Ya cazaron un bug que ninguna prueba
sintetica habria encontrado — ver `tests/fixtures/golden/README.md`.

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
