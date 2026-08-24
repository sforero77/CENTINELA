# Fixtures golden

Productos reales de ComCat congelados, no sinteticos. Son la unica forma de que
el sistema pueda afirmar «esto habria salido a las 08:3X del 10 de agosto».

| Directorio | Evento | `usgs_id` |
|---|---|---|
| `choco_2026_08_10/` | M7.4, 2026-08-10T12:34:28Z, San José del Palmar, Chocó, 110 km | `us6000tjl2` |
| `venezuela_2026_06_24/` | M7.5, 2026-06-24T22:05:04Z, Catia La Mar, 10 km | `us6000t7zp` |
| | M7.2, 2026-06-24T22:04:31Z, San Felipe, 10 km | `us6000t7zc` |

## Como se obtuvieron

```bash
FD="https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"

# Historial completo de versiones de cada producto
curl "$FD&eventid=us6000tjl2&includesuperseded=true" -o detail_superseded.json

# Reconstruccion del feed que P1 habria visto: consulta FDSN con el bbox LATAM
BBOX="minlatitude=-56&maxlatitude=33&minlongitude=-118&maxlongitude=-34&minmagnitude=5.5"
curl "$FD&starttime=2026-08-10T12:00:00&endtime=2026-08-10T13:30:00&$BBOX" \
  -o feed_reconstruido.json
```

**`includesuperseded=true` funciona directo sobre FDSN.** La espec v0.9 asumia
que hacia falta `libcomcat`; no es asi, y eso quita una dependencia del
procedimiento de congelado.

El feed se reconstruye con una **consulta** FDSN, no con el *detail* del evento:
el detail devuelve un `Feature` suelto y sin la propiedad `detail`, mientras que
una consulta devuelve un `FeatureCollection` con la misma forma que el feed en
tiempo real. Es lo que permite pasar la fixture por `parse_feed` sin trucos.

## Por que estan recortadas

Sin recortar pesan **8,4 MB**; recortadas, **244 KB**. Se conservan solo los
productos que el pipeline consume (`shakemap`, `ground-failure`, `losspager`) y,
dentro de cada version, solo los contenidos que pide por nombre (`cont_mmi.json`,
`grid.xml`, los `.tif` de Ground Failure). Lo demas —`phase-data`,
`moment-tensor`, cientos de archivos auxiliares por version— es peso que pagaria
cada clon del repositorio para siempre sin que nada lo lea.

Se conserva el **historial completo de versiones**: sin el no se puede probar el
changelog entre ShakeMap v(n) y v(n+1) que exige RF-04.

## Lo que ya cazaron

`us6000t7zp` tiene 14 versiones de ShakeMap, y las de junio (v1-v4) declaran
`preferredWeight` **232** mientras la vigente v14, de agosto, declara **228**.
El parser ordenaba por peso y elegia v4: un ShakeMap de hace mes y medio, sin
que ninguna prueba fallara y sin que el reporte diera senal de nada. La leccion
quedo escrita en `pipelines/p2_impact/products.py` y la regresion vive en
`tests/golden/test_g2_venezuela.py::test_no_se_elige_una_version_obsoleta`.
