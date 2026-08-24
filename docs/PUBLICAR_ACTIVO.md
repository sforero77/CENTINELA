# Publicar el activo de exposicion

El activo construido no va en git: pesa 17,3 MB por pais y crecera con cada
pais de Fase 1. Va como **Release de GitHub**, y esa copia —no la URL de la
fuente original— es la que sostiene RNF-04.

Por que importa: Overture conserva solo los **dos releases mas recientes** en su
bucket. Pasados unos dos meses la URL que declara el manifest deja de existir, y
sin una copia propia nadie puede rehacer el build de un reporte de hace seis
meses. El Release con su `sha256` es lo que hace re-derivable un numero
publicado.

## Colombia v0.4 — activo publicado

| | |
|---|---|
| Archivo | `exposure_h3.parquet` |
| Peso | 17,3 MB (ZSTD) |
| sha256 | `f206447c5e65f31fe250ea41e5f02bdf24b5873ab1822a0298294d01b75d1fa1` |
| Celdas | 519.735 |
| Poblacion | 52.942.553 |
| Edificaciones | 15.436.442 |
| Sedes de salud | 9.615 |
| Sedes educativas | 43.837 |
| Vias | 44.919 km |
| Municipios | 1.122 de 1.122 |
| Manifest | `col-v0.4` |

## Colombia v0.5 — medido en CI el 24-ago-2026

| Indicador | v0.4 (a mano) | v0.5 (pipeline) |
|---|---:|---:|
| Celdas | 519.735 | **561.244** |
| Poblacion | 52.942.553 | **52.942.553** |
| Edificaciones | 15.436.442 | **15.436.442** |
| Sedes de salud | 9.615 | **9.907** |
| Sedes educativas | 43.837 | **44.021** |
| Kilometros de via | 44.919 | **335.244** |
| Superficie construida | — | **1.600 km²** |
| Municipios | 1.122 | **1.122** |

**Poblacion y edificaciones coinciden hasta el ultimo digito.** Es la mejor
evidencia de que el pipeline reproduce lo que se habia hecho a mano, y de que
las cifras del backtest del Chocó se sostienen. El total nacional queda a
**-0,11 %** de la referencia del DANE.

Las que se mueven, y por que:

- **Salud (+292):** ya no se pierde el aporte real de healthsites.io. Antes o se
  duplicaba o se descartaba entera; ahora entra deduplicada a 20 m.
- **Educacion (+184):** deriva de OSM desde que se construyo el activo anterior.
- **Celdas (+41.509):** las que tienen superficie construida detectada por
  satelite pero ninguna otra capa. Son exactamente el hueco de mapeo que la
  capa nueva existe para hacer visible.
- **Vias (×7,5):** el activo anterior **excluia las calles residenciales**.
  Medido sobre Quibdó, `residential` es el 60 % de la red. No es un error de
  ninguno de los dos: son dos cosas distintas, y por eso el reporte ahora
  publica **vias primarias y secundarias** y **vias locales** por separado en
  vez de un solo numero. Lo que si se corrigio es que las escaleras, senderos y
  aceras ya no cuentan como via — son el 4 % y decian que hay acceso rodado
  donde no lo hay.

## Colombia v0.5 — que cambia en el esquema

El manifest sube a `col-v0.5` porque **el esquema del activo gana una columna**,
`built_m2`: superficie construida vista por satelite (GHS-BUILT-S). No sustituye
al conteo de edificaciones, lo contrasta — y donde OpenStreetMap no mapeo el
barrio, es la unica de las dos que ve algo. De ahi sale la bandera
`construido_no_mapeado` y la advertencia del reporte cuando el conteo se queda
corto.

Dos cifras de v0.4 se mueven ademas por correcciones, no por datos nuevos:

- **Sedes de salud.** HOTOSM y healthsites.io se sumaban sin deduplicar, y el
  96,6 % de los puntos de la segunda resulto estar a menos de 20 m de uno de la
  primera. Las 9.615 de v0.4 salieron de usar solo HOTOSM; con las dos fuentes
  ya deduplicadas la cifra sube en unas 290 sedes reales. Sin el arreglo habria
  sido 18.061, casi el doble.
- **Limites municipales.** El recurso del COD-AB que se descargaba eran
  secciones urbanas del MGN, no municipios. Ahora va fijado con `hdx_resource`.

Al republicar hay que actualizar la tabla de arriba con las cifras que imprima
el build y el `sha256` nuevo.

## Como publicarlo

```bash
gh release create exposure-col-20260823 exposure_h3.parquet admin_lookup.parquet \
  --title "Activo de exposicion COL — 2026-08-23" \
  --notes-file data/manifests/COL.yaml
```

Los **dos** archivos: sin `admin_lookup.parquet` el reporte sale con el codigo
DIVIPOLA en vez del nombre del municipio.

El workflow `exposure_quarterly.yml` lo hace solo cada trimestre. La publicacion
manual es para el primer activo y para reconstrucciones fuera de cadencia.

## Licencia del activo

**ODbL.** El cubo resultante es share-alike porque incorpora edificaciones y
vias de Overture, que incluyen OpenStreetMap. Ver `../LICENSES/README.md`.

Atribucion obligatoria en cualquier reuso:

> Intensidad: USGS ShakeMap (dominio publico) · Poblacion: GHS-POP,
> JRC/Comision Europea · Estructura etaria: WorldPop (CC BY 4.0) ·
> Edificaciones, vias, salud y educacion: Overture Maps y HOTOSM,
> © OpenStreetMap contributors (ODbL) · Division administrativa:
> Departamento Administrativo Nacional de Estadistica - DANE: www.dane.gov.co
