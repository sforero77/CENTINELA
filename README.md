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

**Fase 0, semana 4 — el sistema esta operando.** Desde el 24-ago-2026 el
trigger vigila el feed de USGS cada 10 minutos y el visor esta publicado en
https://sforero77.github.io/CENTINELA/. Lo que ya funciona y lo que falta:

| Componente | Estado |
|---|---|
| P1 trigger (feed, filtro, dedupe, `event_state`) | ✅ operando cada 10 min |
| Contratos USGS (feed + productos) y su validacion | ✅ funcional |
| Decision de impacto e idempotencia por version | ✅ funcional |
| Reporte preliminar sin ShakeMap (RF-03) | ✅ funcional |
| Changelog de deltas al re-emitir (RF-04) | ✅ funcional |
| Modelo y render del reporte (json, md, CSV, mapas, hilo) | ✅ funcional |
| Asserts de calidad §6.4 sobre el corte, en P0 y en P2 | ✅ funcional |
| Regla de los tres cubos y lint de manifests | ✅ funcional, corre en CI |
| Deriva de licencia de la fuente, contrastada en cada build | ✅ funcional |
| Golden tests G1/G2/G3 con productos reales congelados | ✅ corren |
| P0 pipeline completo: descarga → crosswalk → nueve capas → parquet | ✅ funcional |
| P2 contornos MMI → celdas → Ground Failure → join en DuckDB | ✅ funcional |
| Enrutado del evento al activo del pais correcto | ✅ funcional, con reintento |
| Toponimos en espanol (RF-06) | ✅ funcional |
| **Catalogo historico regional** | ✅ **21 reportes en 15 paises** |
| **Activo de exposicion construido y publicado** | ✅ **18 de 19 paises** |
| Visor con cobertura regional y filtro por pais | ✅ funcional |
| Visor y `/status`, con latido del trigger publicado | ✅ funcional |
| Reconstruccion trimestral de todos los activos publicados | ✅ funcional |
| Activo de Brasil | ⏳ desbloqueado; falta correrlo en CI (`PENDIENTES.md` §2.1d) |
| Coropletas r7/r6 del visor en PMTiles | ⏳ el resto del visor funciona |
| P4 brigada de imagen | ⏳ Fase 2 |

**601 pruebas** sin red (mas 8 nocturnas contra las fuentes vivas), ninguna
saltada, `ruff` y `mypy --strict` limpios. Medido el 25-ago-2026.

Las etapas pendientes fallan de forma ruidosa y explicita — nunca devuelven un
cero que acabaria publicado como cifra. `tests/unit/test_pendientes.py` es el
inventario vivo de esa deuda, y hoy esta vacio.

Y hay una segunda guardia, de otra clase.
`tests/unit/test_funciones_conectadas.py` recorre el grafo de llamadas y falla
si una funcion publica se queda **sin llamador**. Existe porque el fallo que
mas veces ha cazado este proyecto no es un calculo mal hecho sino una pieza
correcta que nadie invoca: el reporte preliminar, el epicentro del mapa
estatico, tres capas del activo, los asserts de §6.4. Todas estaban probadas —
por eso la cobertura las daba por verdes— y ninguna estaba conectada.

El cero silencioso tiene ademas su propia guardia. Una capa que no se construye
entra vacia al ensamblaje, el `LEFT JOIN` la vuelve ceros y el activo se
escribiria sin que nada proteste: el assert de total nacional solo mira
poblacion. `validate_layer_coverage` detiene el build si **cualquier** capa
requerida suma cero en todo el pais — es preferible no publicar activo que
publicar uno que informa cero donde no midio nada.

Los golden tests corren contra **productos reales congelados** de los dos
eventos que motivan el proyecto: Chocó (`us6000tjl2`) y el doble mainshock de
Venezuela (`us6000t7zp`, `us6000t7zc`). Ya cazaron dos bugs que ninguna prueba
sintetica habria encontrado — ver `tests/fixtures/golden/README.md`.

### El backtest del Chocó

`reports/us6000tjl2/` es la respuesta a la pregunta que motiva el proyecto:
**esto es lo que el pais habria sabido el 10 de agosto**, en vez de esperar dias.

| Indicador | Cifra |
|---|---|
| Personas en MMI≥6 | **6.960.086** |
| Personas en MMI≥7 | **2.415.793** |
| De ellas, 65 anos o mas | **289.257** |
| Edificaciones en MMI≥7 | **444.424** |
| Sedes de salud en MMI≥7 | **518** |
| Sedes educativas en MMI≥7 | **998** |
| Kilometros de via en MMI≥7 | **8.503** |
| De ellos, primarias y secundarias | **985** |
| Personas en zona de licuefaccion alta | **1.600.028** |
| Municipios alcanzados | **297** |

Las cifras salen de `reports/us6000tjl2/report.json`, y
`tests/unit/test_cifras_del_readme.py` falla si esta tabla se separa de el.
Cinco de estas filas estuvieron desactualizadas hasta el 25-ago-2026 —los km de
via, por un factor de seis— porque se copiaron a mano y el activo se
reconstruyo despues. Una tabla de cifras escrita a mano se desincroniza; una
tabla con prueba, no.

El activo del que salen es el Release `exposure-col-20260824` (manifest
`col-v0.5`): **559.103 celdas**, 52.620.466 habitantes, 15,3 millones de
edificaciones, 9.888 sedes de salud, 45.710 sedes educativas y 307.314 km de
via, en los 1.122 municipios del pais. Su desvio contra la referencia del DANE
es **−0,72 %**, y solo el 0,32 % de la poblacion entra por celdas rescatadas.

Y el dato que cambia la conversacion: los municipios mas expuestos no estaban en
Chocó sino en el Eje Cafetero y el Valle — Pereira, Buenaventura, Armenia,
Tuluá, Dosquebradas. La unica evaluacion de dano con IA que existio cubrio una
sola ciudad.

### El catalogo historico regional

El Chocó no es una demostracion aislada. El sistema reconstruyo **21 sismos de
15 paises** del catalogo real de USGS, cada uno con los productos que USGS
publico entonces, cada uno contra el activo de su pais:

| | |
|---|---|
| Reportes publicados | **21**, en **15 paises** |
| Paises con activo construido y medido | **18 de 19** (falta Brasil) |
| Personas ya en la malla hexagonal | **430,9 millones** |
| Peor desvio contra la cifra oficial de un pais | **+4,94 %** (Venezuela, y esta explicado) |

Los cuatro paises sin reporte —Bolivia, Brasil, Paraguay y Uruguay— **no son
huecos del sistema, y no lo son por el mismo motivo**. Se busco para los cuatro:

* **Paraguay y Uruguay** no registran un solo sismo M≥5,5 desde el ano 2000.
  Su activo esta construido y esperando, que para un sistema de preparacion es
  el estado que se persigue, no una carencia.
* **Bolivia y Brasil** si tienen sismos —22 y 12 desde 2000— pero **todos entre
  359 y 603 km de profundidad**. A esa profundidad la sacudida no alcanza MMI 5
  en superficie: USGS no publica contornos para los brasilenos, y los bolivianos
  que si los traen no producen una sola celda. Un sistema que calcula sobre
  `cont_mmi` no tiene ahi nada que calcular, y decirlo es mas util que forzar un
  reporte de ceros.

Lo que ensena ese catalogo importa mas que su tamano: **ocho de los diecinueve
eventos no alcanzan MMI≥7 sobre poblacion**. Son los profundos y los de mar
adentro, que en esta region son la mitad. Tehuantepec 2017 —M8,2, 98 muertos—
es uno de ellos: su maximo sobre poblacion mexicana es MMI 6,5.

Hasta que se corrieron, el producto entero daba por supuesto que MMI≥7 era *la*
banda, y para esos ocho publicaba un titular de "0 personas" con una tabla de
municipios ordenada alfabeticamente. Ahora se titula con la banda que el evento
alcanzo de verdad. Ninguna cantidad de pruebas sinteticas habria encontrado eso:
hizo falta correr la region entera.

## Estructura

```
pipelines/       p0_exposure, p1_trigger, p2_impact, p3_report, p4_brigada, common
schemas/         JSON Schema del reporte, del estado y de los contratos USGS
data/manifests/  vintages por pais (fuente, url, licencia, hash, fecha) — los 19 de LATAM
events/          event_state por evento — la base de datos del sistema, en git
reports/         salidas publicadas (json + md + csv + png)
site/            visor estatico (MapLibre + PMTiles, cero llaves de API)
tests/           unit/, integration/, golden/, fixtures/
```

## Documentacion

- [`docs/OPERACION.md`](docs/OPERACION.md) — **que vigilar ahora que el sistema opera**
- [`PENDIENTES.md`](PENDIENTES.md) — que falta, quien puede hacerlo y en que orden
- [`docs/AUDITORIA.md`](docs/AUDITORIA.md) — la auditoria del 25-ago-2026: que se encontro y como se cerro
- [`docs/CLEAN_CODE.md`](docs/CLEAN_CODE.md) — las reglas de codigo del proyecto, con el caso real de cada una
- [`ESPECIFICACION.md`](ESPECIFICACION.md) — especificacion tecnica v0.10
- [`docs/PUBLICAR_ACTIVO.md`](docs/PUBLICAR_ACTIVO.md) — como publicar el activo y por que no va en git
- [`VERIFICACIONES.md`](VERIFICACIONES.md) — cierre de las tareas ⚠️ de §8, con metodo y hallazgos
- [`DISCLAIMER.md`](DISCLAIMER.md) — que informa y que no informa el sistema
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — como ayudar (incluye rol de mantenedor por pais)
- [`GOVERNANCE.md`](GOVERNANCE.md) — roles, decisiones, frontera comunidad ↔ empresa
- [`ATTRIBUTION.md`](ATTRIBUTION.md) — creditos obligatorios de cada fuente
- [`LICENSES/`](LICENSES/) — la regla de los tres cubos

## Licencia

Codigo: **Apache-2.0**. Datos derivados: **CC BY 4.0** en el nucleo, **ODbL**
donde entra OpenStreetMap u Overture. Detalle en [`LICENSES/`](LICENSES/).
