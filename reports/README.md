# reports/

Salidas publicadas, un directorio por evento (`<usgs_id>/`):

| Archivo | Que es |
|---|---|
| `report.json` | Fuente de verdad. Esquema `centinela/report/1.0` |
| `report.md` | Reporte legible, espanol neutro, < 500 KB con el PNG |
| `adm2.csv` | Tabla municipal con cifras exactas y cabecera HXL |
| `hilo.txt` | Borrador para redes. **Publicarlo requiere accion humana** (RF-07) |
| `mapa.png` | Mapa estatico, variantes `general` y `prensa` |

Ningun renderizador recalcula cifras: todos derivan de `report.json`. Si el
markdown y el hilo pudieran divergir, divergirian en el peor momento.
