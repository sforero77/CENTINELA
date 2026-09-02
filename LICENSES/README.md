# Licencias por cubo

La especificación (§2.4) impone **tres cubos físicamente separados**. No es una
convención de nombres: es la única forma de que el dataset siga siendo
reusable. Una sola capa no comercial filtrada al núcleo bloquearía el reuso de
todo lo demás.

| Cubo | Contenido | Licencia de salida |
|---|---|---|
| `core/` | Dominio público, CC BY 4.0, reuso CE con atribución | **CC BY 4.0** |
| `odbl/` | Todo lo que toque OSM / Overture `buildings` o `transportation` | **ODbL** (share-alike cumplido publicando el derivado bajo ODbL) |
| `nc/` | Vantor, GEM, derivados de xBD | Su licencia original. **No redistribuible** bajo las anteriores |

## Qué consume cada cosa

- **El reporte automático** consume `core/` + `odbl/`. Jamás `nc/`.
- **El visor** puede mostrar capas de contexto de `nc/`, siempre etiquetadas.
- **La brigada de imagen** publica en `core/` si sus pesos tienen linaje limpio
  (entrenados solo con Copernicus EMS y etiquetas propias), y en `nc/` si
  heredan de xBD.

## Cómo se hace cumplir

No con documentación. Con código:

- `pipelines/common/licensing.py` mantiene el registro cerrado de licencias.
  Una licencia desconocida en un manifest es un **error**, no un default
  permisivo.
- `centinela lint-manifests` corre en CI y falla el build ante cualquier
  mezcla.
- `resolve_bucket()` implementa la regla de peor caso: una fuente NC contamina
  el derivado entero; una ODbL le contagia share-alike.
- `resolve_bucket()` también rechaza **dos copyleft incompatibles en el mismo
  derivado**. La regla de los tres cubos no bastaba: ODbL y CC BY-SA 4.0 caen
  las dos del lado «redistribuible», pero cada una exige que el derivado se
  publique bajo ella y no hay licencia que cumpla ambas. El caso no es
  hipotético — los registros colombianos de salud y educación son CC BY-SA 4.0
  y las edificaciones de Overture son ODbL. Detalle en `../VERIFICACIONES.md`.

## Licencias de referencia

- Apache-2.0 (código del proyecto): `../LICENSE`
- ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/
- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
- CC BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/
- CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/
