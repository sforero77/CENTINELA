# Licencias por cubo

La especificacion (§2.4) impone **tres cubos fisicamente separados**. No es una
convencion de nombres: es la unica forma de que el dataset siga siendo
reusable. Una sola capa no comercial filtrada al nucleo bloquearia el reuso de
todo lo demas.

| Cubo | Contenido | Licencia de salida |
|---|---|---|
| `core/` | Dominio publico, CC BY 4.0, reuso CE con atribucion | **CC BY 4.0** |
| `odbl/` | Todo lo que toque OSM / Overture `buildings` o `transportation` | **ODbL** (share-alike cumplido publicando el derivado bajo ODbL) |
| `nc/` | Vantor, GEM, derivados de xBD | Su licencia original. **No redistribuible** bajo las anteriores |

## Que consume cada cosa

- **El reporte automatico** consume `core/` + `odbl/`. Jamas `nc/`.
- **El visor** puede mostrar capas de contexto de `nc/`, siempre etiquetadas.
- **La brigada de imagen** publica en `core/` si sus pesos tienen linaje limpio
  (entrenados solo con Copernicus EMS y etiquetas propias), y en `nc/` si
  heredan de xBD.

## Como se hace cumplir

No con documentacion. Con codigo:

- `pipelines/common/licensing.py` mantiene el registro cerrado de licencias.
  Una licencia desconocida en un manifest es un **error**, no un default
  permisivo.
- `centinela lint-manifests` corre en CI y falla el build ante cualquier
  mezcla.
- `resolve_bucket()` implementa la regla de peor caso: una fuente NC contamina
  el derivado entero; una ODbL le contagia share-alike.

## Licencias de referencia

- Apache-2.0 (codigo del proyecto): `../LICENSE`
- ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/
- CC BY 4.0: https://creativecommons.org/licenses/by/4.0/
- CC BY-NC 4.0: https://creativecommons.org/licenses/by-nc/4.0/
- CC BY-NC-SA 4.0: https://creativecommons.org/licenses/by-nc-sa/4.0/
