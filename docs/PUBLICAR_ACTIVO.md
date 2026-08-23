# Publicar el activo de exposicion

El activo construido no va en git: pesa 17,3 MB por pais y crecera con cada
pais de Fase 1. Va como **Release de GitHub**, y esa copia —no la URL de la
fuente original— es la que sostiene RNF-04.

Por que importa: Overture conserva solo los **dos releases mas recientes** en su
bucket. Pasados unos dos meses la URL que declara el manifest deja de existir, y
sin una copia propia nadie puede rehacer el build de un reporte de hace seis
meses. El Release con su `sha256` es lo que hace re-derivable un numero
publicado.

## Colombia v0.4 — activo vigente

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

## Como publicarlo

```bash
gh release create exposure-col-20260823 exposure_h3.parquet \
  --title "Activo de exposicion COL — 2026-08-23" \
  --notes-file data/manifests/COL.yaml
```

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
