# Atribuciones

Toda salida de CENTINELA (mapa, reporte, CSV, GeoParquet, PMTiles) lleva
estas atribuciones. No es cortesía: es condición de licencia (§2.4 de la
especificación) y se verifica en CI.

**«Se verifica en CI» era falso hasta el 6-sep-2026.** No existía una sola
prueba que comparase este archivo con las licencias de los manifiestos, y por
ese hueco ESA WorldCover llevaba meses publicando su dato sin aparecer aquí, sin
estar en el pie del visor y sin salir en ningún crédito. Ahora la lista de
créditos es **dato** —`pipelines/common/atribucion.py`, con una entrada por
fuente y las superficies donde su crédito es obligatorio— y
`tests/unit/test_la_atribucion_viaja_con_el_dato.py` recorre los diecinueve
manifiestos exigiendo que cada fuente aparezca aquí, en el pie de los mapas y en
el pie del visor. Una fuente nueva sin crédito ya no es un olvido: es rojo.

## Datos de evento

- **USGS Earthquake Hazards Program**: feeds GeoJSON en tiempo real, ShakeMap,
  Ground Failure y PAGER. Obra del gobierno de los Estados Unidos, dominio
  público.

## Capas de exposición

- **JRC / Comisión Europea**: GHS-POP R2023A (GHSL).
  Schiavina, M., Freire, S., MacManus, K. (2023). *GHS-POP R2023A*.
  European Commission, Joint Research Centre. doi:10.2905/2FF68A52
  Reuso permitido con atribución.
- **WorldPop** (School of Geography and Environmental Science, University of
  Southampton): estructura por edad y sexo, y totales de contraste.
  CC BY 4.0.
- **Overture Maps Foundation**: temas `buildings`, `transportation` y
  `divisions`. ODbL.
- **© OpenStreetMap contributors**: datos incluidos en Overture y consultas
  directas de equipamiento. ODbL. https://www.openstreetmap.org/copyright
- **Departamento Administrativo Nacional de Estadística - DANE:
  www.dane.gov.co**: Marco Geoestadístico Nacional (MGN), base del crosswalk
  hex↔DIVIPOLA en Colombia. CC BY 4.0 (esta es la fórmula de atribución que el
  propio Geoportal DANE pide).
- **OCHA, Common Operational Datasets (COD-AB)**, publicados en el
  Humanitarian Data Exchange. Límites administrativos adm1/adm2 de todos los
  países salvo Colombia, que usa el MGN. **CC BY-IGO**, que exige atribución.
  https://data.humdata.org/dataset/cod-ab-<iso3>
- **Humanitarian OpenStreetMap Team (HOT)**: extractos
  `hotosm_<iso>_health_facilities` y `hotosm_<iso>_education_facilities`,
  publicados en HDX. ODbL, derivados de OpenStreetMap.
- **healthsites.io**: publicación en HDX, complemento de la capa de salud.
  ODbL.
- **ESA WorldCover 2021 v200** (Zanaga, D. et al., 2022): cobertura del suelo
  a 10 m. **CC BY 4.0**, que exige atribución. Alimenta las columnas
  `lulc_*_pct` del activo y el bloque `suelo` de `site/incendios.json`, que el
  visor pinta en el panel de fuego. https://esa-worldcover.org/
- **OurAirports**: aeropuertos. Dominio público.

## Fuego activo (P5)

- **NASA FIRMS / LANCE**: detecciones de foco de calor VIIRS a 375 m
  (S-NPP y NOAA-20/21). Obra del gobierno de los Estados Unidos, dominio
  público; NASA pide citar el servicio.
  https://firms.modaps.eosdis.nasa.gov/
  No aparece en ningún manifiesto porque P5 no construye un activo: su crédito
  y su licencia viven en `pipelines/common/atribucion.py`, que es lo que hace
  que `resolve_bucket` la vea. Antes no la veía ninguno de los dos.

### Referencias de población usadas en los asserts de calidad

No entran al activo: son la cifra oficial contra la que se valida el total
nacional (§6.4).

- **DANE**: proyecciones CNPV-2018 (Colombia).
- **Naciones Unidas, División de Población**: *World Population Prospects*
  (Venezuela y, en adelante, los países sin censo reciente). Se cita a la ONU
  como fuente; la serie se consulta por la API abierta del Banco Mundial
  (`SP.POP.TOTL`), que la republica sin credenciales, porque el endpoint de
  datos de la propia ONU exige un token y eso incumpliria O4.

## Fuentes de referencia, fuera del activo redistribuible

Estas no alimentan `exposure_h3` y viven en una tabla aparte bajo CC BY-SA 4.0,
porque su copyleft es incompatible con la ODbL de Overture (ver
`VERIFICACIONES.md`):

- **MinSalud (Colombia)**: REPS, Registro Especial de Prestadores y Sedes de
  Servicios de Salud. CC BY-SA 4.0.
- **MEN (Colombia)**: directorio de establecimientos educativos. CC BY-SA 4.0.

## Capas de contexto (cubo `nc/`, fuera del reporte automático)

- **GEM Foundation**: Global Seismic Hazard Map. CC BY-NC-SA. **Solo visor.**
- **Vantor (Maxar) Open Data**: imagen VHR por evento. CC BY-NC 4.0.
- **xBD / xView2**: pre-entrenamiento. CC BY-NC-SA 4.0.

## Brigada de imagen

- **Copernicus EMS Rapid Mapping**: vectores de grading, usados como etiquetas
  de entrenamiento y verdad de validación. Atribución a la Comisión Europea.
- **OpenAerialMap**: imagen aérea y de dron comunitaria. CC BY 4.0.
- **Umbra / Capella Open Data**: SAR.
- **Microsoft AI for Good**: toolkit `building-damage-assessment` (MIT) y
  GeoPackage de referencia.

## Código

CENTINELA es software libre bajo **Apache-2.0**. Ver `LICENSE`.

## Datos derivados

Medido con `resolve_bucket` sobre los diecinueve manifiestos: **los diecinueve
resuelven a `odbl`**. Todos fijan Overture `buildings` y `transportation` bajo
ODbL, y salud/educación bajo ODbL vía HOT. O sea que hoy no existe un activo de
CENTINELA que se publique bajo CC BY 4.0, y el pie del visor lo afirmaba.

- Núcleo redistribuible, cuando lo haya: **CC BY 4.0**.
- Capas que incorporan OSM / Overture `buildings` o `transportation`: **ODbL**,
  por share-alike.
- Derivados de fuentes NC: **no redistribuibles** bajo las licencias anteriores;
  viven en el cubo `nc/` con su licencia original.
