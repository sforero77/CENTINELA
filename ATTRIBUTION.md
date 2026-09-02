# Atribuciones

Toda salida de CENTINELA — mapa, reporte, CSV, GeoParquet, PMTiles — lleva
estas atribuciones. No es cortesía: es condición de licencia (§2.4 de la
especificación) y se verifica en CI.

## Datos de evento

- **USGS Earthquake Hazards Program** — feeds GeoJSON en tiempo real, ShakeMap,
  Ground Failure y PAGER. Obra del gobierno de los Estados Unidos, dominio
  público.

## Capas de exposición

- **JRC / Comisión Europea** — GHS-POP R2023A (GHSL).
  Schiavina, M., Freire, S., MacManus, K. (2023). *GHS-POP R2023A*.
  European Commission, Joint Research Centre. doi:10.2905/2FF68A52
  Reuso permitido con atribución.
- **WorldPop** (School of Geography and Environmental Science, University of
  Southampton) — estructura por edad y sexo, y totales de contraste.
  CC BY 4.0.
- **Overture Maps Foundation** — temas `buildings`, `transportation` y
  `divisions`. ODbL.
- **© OpenStreetMap contributors** — datos incluidos en Overture y consultas
  directas de equipamiento. ODbL. https://www.openstreetmap.org/copyright
- **Departamento Administrativo Nacional de Estadística - DANE:
  www.dane.gov.co** — Marco Geoestadístico Nacional (MGN), base del crosswalk
  hex↔DIVIPOLA en Colombia. CC BY 4.0 (esta es la fórmula de atribución que el
  propio Geoportal DANE pide).
- **OCHA — Common Operational Datasets (COD-AB)**, publicados en el
  Humanitarian Data Exchange. Límites administrativos adm1/adm2 de todos los
  países salvo Colombia, que usa el MGN. **CC BY-IGO**, que exige atribución.
  https://data.humdata.org/dataset/cod-ab-<iso3>
- **Humanitarian OpenStreetMap Team (HOT)** — extractos
  `hotosm_<iso>_health_facilities` y `hotosm_<iso>_education_facilities`,
  publicados en HDX. ODbL, derivados de OpenStreetMap.
- **healthsites.io** — publicación en HDX, complemento de la capa de salud.
  ODbL.
- **OurAirports** — aeropuertos. Dominio público.

### Referencias de población usadas en los asserts de calidad

No entran al activo: son la cifra oficial contra la que se valida el total
nacional (§6.4).

- **DANE** — proyecciones CNPV-2018 (Colombia).
- **Naciones Unidas, División de Población** — *World Population Prospects*
  (Venezuela y, en adelante, los países sin censo reciente). Se cita a la ONU
  como fuente; la serie se consulta por la API abierta del Banco Mundial
  (`SP.POP.TOTL`), que la republica sin credenciales, porque el endpoint de
  datos de la propia ONU exige un token y eso incumpliria O4.

## Fuentes de referencia, fuera del activo redistribuible

Estas no alimentan `exposure_h3` y viven en una tabla aparte bajo CC BY-SA 4.0,
porque su copyleft es incompatible con la ODbL de Overture (ver
`VERIFICACIONES.md`):

- **MinSalud (Colombia)** — REPS, Registro Especial de Prestadores y Sedes de
  Servicios de Salud. CC BY-SA 4.0.
- **MEN (Colombia)** — directorio de establecimientos educativos. CC BY-SA 4.0.

## Capas de contexto (cubo `nc/`, fuera del reporte automático)

- **GEM Foundation** — Global Seismic Hazard Map. CC BY-NC-SA. **Solo visor.**
- **Vantor (Maxar) Open Data** — imagen VHR por evento. CC BY-NC 4.0.
- **xBD / xView2** — pre-entrenamiento. CC BY-NC-SA 4.0.

## Brigada de imagen

- **Copernicus EMS Rapid Mapping** — vectores de grading, usados como etiquetas
  de entrenamiento y verdad de validación. Atribución a la Comisión Europea.
- **OpenAerialMap** — imagen aérea y de dron comunitaria. CC BY 4.0.
- **Umbra / Capella Open Data** — SAR.
- **Microsoft AI for Good** — toolkit `building-damage-assessment` (MIT) y
  GeoPackage de referencia.

## Código

CENTINELA es software libre bajo **Apache-2.0**. Ver `LICENSE`.

## Datos derivados

- Núcleo redistribuible: **CC BY 4.0**.
- Capas que incorporan OSM / Overture `buildings` o `transportation`: **ODbL**,
  por share-alike.
- Derivados de fuentes NC: **no redistribuibles** bajo las licencias anteriores;
  viven en el cubo `nc/` con su licencia original.
