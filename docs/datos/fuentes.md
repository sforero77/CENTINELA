# Fuentes

Cada fuente con su papel, su licencia, su cadencia y la limitación que el
sistema declara públicamente sobre ella.

## En tiempo real

### USGS — el disparo y la intensidad

| | |
|---|---|
| **Feed** | `earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_hour` y `4.5_day` |
| **Productos** | ShakeMap (`cont_mmi.json`), Ground Failure (rásters) |
| **Licencia** | Dominio público (obra del gobierno de EE. UU.) |
| **Cadencia** | Continua |
| **Limitación** | ShakeMap se revisa muchas veces; el de Venezuela llegó a v14 |

> **FDSN está prohibido en el camino crítico.** El propio USGS recomienda los
> feeds GeoJSON para aplicaciones automatizadas y desaconseja el polling a
> FDSN (D7). `USGS_FDSN_EVENT` existe en el código sólo para backtests.

### NASA FIRMS — los focos activos

| | |
|---|---|
| **Fuente** | CSV regionales de 24 h, tres satélites VIIRS |
| **Satélites** | Suomi-NPP, NOAA-20 (J1), NOAA-21 (J2) |
| **Resolución** | 375 m |
| **Licencia** | Dominio público / uso abierto |
| **Cadencia** | Se consume cada 6 h |
| **Limitación** | Una detección no es un incendio: 2,9 detecciones por celda |

Los CSV **no piden `MAP_KEY`**; la API por bbox sí, y además raciona a 5.000
peticiones por 10 minutos. Verificado el 26-ago-2026.

## Con vintage fijado

### Población

| Fuente | Qué aporta | Licencia | Limitación declarada |
|---|---|---|---|
| **GHS-POP R2023A** ép. 2025 | `pop_total` | EC reuse + atribución | Derivado de GPWv4.11 + volumen construido GHSL. **Modelado, no censal** |
| **WorldPop age-sex R2025A** | `pop_0_14`, `pop_15_64`, `pop_65p` | CC-BY 4.0 | Modelado. Los extremos son conteos; la banda central es el residuo y **absorbe la diferencia entre ambos modelos** |
| **WorldPop constrained R2025** | `pop_alt_worldpop` | CC-BY 4.0 | Sólo alimenta la banda de discrepancia publicada, **nunca la cifra principal** |

La estructura etaria merece una nota. La especificación daba por inevitable el
supuesto de "estructura etaria estable" —repartir `pop_total` con proporciones
de 2020—. **Ya no aplica**: WorldPop publica desglose age-sex para 2025 en
R2025A, y el sistema lo usa.

### Construcción e infraestructura

| Fuente | Qué aporta | Licencia | Limitación |
|---|---|---|---|
| **Overture `buildings`** | `bld_count`, `bld_area_m2` | ODbL 1.0 | Cobertura desigual: donde OSM no mapeó, no hay edificios |
| **GHS-BUILT-S R2023A** | `built_m2` | EC reuse | Superficie vista por satélite |
| **Overture `transportation`** | `road_km_primary/secondary/other` | ODbL 1.0 | Idem OSM |
| **HOTOSM vía HDX** | `health_count`, `edu_count` | ODbL 1.0 | Puntos, no capacidad instalada |
| **OurAirports** | aeropuertos | Dominio público | Capa no requerida |

**`built_m2` contrasta a `bld_count` a propósito**: donde OSM no mapeó el
barrio, el satélite sí lo ve. El reporte avisa cuando la razón entre las dos
pasa de 1,5 — o sea, cuando hay mucha superficie construida y pocos edificios
mapeados, que es la firma de un vacío cartográfico.

Descartadas y por qué: **REPS** (sin geometría utilizable, T0.5);
**healthsites.io** (96,6 % de solape con HOTOSM); **el directorio del MEN** (T0.6).

### Territorio

| Fuente | Qué aporta | Licencia |
|---|---|---|
| **MGN del DANE** | División administrativa de Colombia | CC-BY 4.0 |
| **COD-AB de OCHA** | División administrativa del resto | CC-BY 4.0 |
| **Overture `divisions`** | Complemento | ODbL 1.0 |
| **ESA WorldCover 2021** | `lulc_*_pct`, `lulc_px` | CC-BY 4.0 |

`adm2_id` es **VARCHAR siempre**: el DIVIPOLA colombiano tiene 5 dígitos y como
entero se pierde el cero inicial.

## La verificación de licencia

`verificar_licencia_declarada` contrasta, **en cada build**, la licencia que el
manifest declara contra la que la fuente publica hoy. No es paranoia: las
fuentes cambian sus términos y un activo publicado bajo un supuesto equivocado
es un problema legal, no técnico.

`contract_drift.yml` hace lo análogo con los *formatos* de USGS, cada noche.

## Puerta abierta: embeddings (Fase 3)

La decisión ya está tomada, y es de licencia:

| Fuente | Licencia | ¿Puede entrar al activo? |
|---|---|---|
| **AlphaEarth Foundations** (Google DeepMind) | CC-BY 4.0 | **Sí**, con su atribución. 64 canales, anual 2017-2025 |
| **Major TOM** (ESA Phi-lab) | CC-BY-SA 4.0 | **No**: arrastraría el share-alike al cubo entero. Se consumiría como referencia externa |

Añadirlas es añadir columnas al contrato y al `SELECT` de ensamblaje. No hay
refactor: la clave sigue siendo la celda.
