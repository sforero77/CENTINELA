# Atribuciones

Toda salida de CENTINELA — mapa, reporte, CSV, GeoParquet, PMTiles — lleva
estas atribuciones. No es cortesia: es condicion de licencia (§2.4 de la
especificacion) y se verifica en CI.

## Datos de evento

- **USGS Earthquake Hazards Program** — feeds GeoJSON en tiempo real, ShakeMap,
  Ground Failure y PAGER. Obra del gobierno de los Estados Unidos, dominio
  publico.

## Capas de exposicion

- **JRC / Comision Europea** — GHS-POP R2023A (GHSL).
  Schiavina, M., Freire, S., MacManus, K. (2023). *GHS-POP R2023A*.
  European Commission, Joint Research Centre. doi:10.2905/2FF68A52
  Reuso permitido con atribucion.
- **WorldPop** (School of Geography and Environmental Science, University of
  Southampton) — estructura por edad y sexo, y totales de contraste.
  CC BY 4.0.
- **Overture Maps Foundation** — temas `buildings`, `transportation` y
  `divisions`. ODbL.
- **© OpenStreetMap contributors** — datos incluidos en Overture y consultas
  directas de equipamiento. ODbL. https://www.openstreetmap.org/copyright
- **DANE (Colombia)** — Marco Geoestadistico Nacional (MGN), base del crosswalk
  hex↔DIVIPOLA.
- **MinSalud (Colombia)** — REPS, sedes de salud.
- **MEN (Colombia)** — directorio de sedes educativas.
- **OurAirports** — aeropuertos. Dominio publico.

## Capas de contexto (cubo `nc/`, fuera del reporte automatico)

- **GEM Foundation** — Global Seismic Hazard Map. CC BY-NC-SA. **Solo visor.**
- **Vantor (Maxar) Open Data** — imagen VHR por evento. CC BY-NC 4.0.
- **xBD / xView2** — pre-entrenamiento. CC BY-NC-SA 4.0.

## Brigada de imagen

- **Copernicus EMS Rapid Mapping** — vectores de grading, usados como etiquetas
  de entrenamiento y verdad de validacion. Atribucion a la Comision Europea.
- **OpenAerialMap** — imagen aerea y de dron comunitaria. CC BY 4.0.
- **Umbra / Capella Open Data** — SAR.
- **Microsoft AI for Good** — toolkit `building-damage-assessment` (MIT) y
  GeoPackage de referencia.

## Codigo

CENTINELA es software libre bajo **Apache-2.0**. Ver `LICENSE`.

## Datos derivados

- Nucleo redistribuible: **CC BY 4.0**.
- Capas que incorporan OSM / Overture `buildings` o `transportation`: **ODbL**,
  por share-alike.
- Derivados de fuentes NC: **no redistribuibles** bajo las licencias anteriores;
  viven en el cubo `nc/` con su licencia original.
