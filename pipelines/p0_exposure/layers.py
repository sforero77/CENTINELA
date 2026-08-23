"""Catalogo de capas del activo de exposicion (§2.2, §3.2).

Cada capa declara de donde sale, bajo que licencia, y a que columnas de
``exposure_h3`` contribuye. Es el registro que consulta el lint de manifest y
el que documenta el sitio: una sola fuente de verdad para las tres cosas.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..common.licensing import Bucket, bucket_for


@dataclass(frozen=True, slots=True)
class LayerSpec:
    """Especificacion de una capa del activo."""

    #: Identificador estable de la capa (clave en los manifests).
    id: str
    titulo: str
    license: str
    #: Columnas de ``exposure_h3`` que produce.
    columnas: tuple[str, ...]
    #: Metodo de agregacion ráster/vector -> celda H3 r8.
    agregacion: str
    #: Limitacion conocida que se declara en los metadatos publicados.
    limitacion: str = ""
    #: True si la capa es obligatoria para emitir un reporte completo.
    requerida: bool = True

    @property
    def bucket(self) -> Bucket:
        return bucket_for(self.license)


#: Capas del activo. El orden es el de construccion: poblacion primero, porque
#: el desglose etario y la banda de discrepancia dependen de ``pop_total``.
LAYERS: tuple[LayerSpec, ...] = (
    LayerSpec(
        id="pop_ghs",
        titulo="Poblacion total — GHS-POP R2023A epoca 2025",
        license="EC-reuse-attribution",
        columnas=("pop_total",),
        agregacion="suma dasimetrica de pixeles 100 m -> celda r8",
        limitacion="Derivado de GPWv4.11 + volumen construido GHSL; modelado, no censal.",
    ),
    LayerSpec(
        id="pop_worldpop_agesex",
        titulo="Estructura etaria/sexo — WorldPop age-sex constrained 2020",
        license="CC-BY-4.0",
        columnas=("pop_0_14", "pop_15_64", "pop_65p"),
        agregacion="proporciones 2020 aplicadas sobre pop_total 2025",
        limitacion=(
            "Supuesto de estructura etaria estable entre 2020 y 2025. "
            "Se declara en los metadatos de cada reporte (§2.2)."
        ),
    ),
    LayerSpec(
        id="pop_worldpop_total",
        titulo="Poblacion total de contraste — WorldPop constrained (R2025)",
        license="CC-BY-4.0",
        columnas=("pop_alt_worldpop",),
        agregacion="suma de pixeles 100 m -> celda r8",
        limitacion="Solo alimenta la banda de discrepancia publicada, nunca la cifra principal.",
    ),
    LayerSpec(
        id="buildings",
        titulo="Edificaciones — Overture Maps theme=buildings",
        license="ODbL-1.0",
        columnas=("bld_count", "bld_area_m2"),
        agregacion="conteo y area por celda del centroide",
        limitacion=(
            "Huecos conocidos en asentamientos informales y zona rural dispersa. "
            "Se publica el flag 'revisar', no se oculta el vacio (§6.4)."
        ),
    ),
    LayerSpec(
        id="roads",
        titulo="Vias — Overture Maps theme=transportation",
        license="ODbL-1.0",
        columnas=("road_km_primary", "road_km_secondary", "road_km_other"),
        agregacion="longitud de segmento recortada por celda, proyeccion equiarea local",
    ),
    LayerSpec(
        id="health",
        titulo="Salud — OSM + healthsites.io + REPS (MinSalud CO)",
        license="ODbL-1.0",
        columnas=("health_count",),
        agregacion="conteo de puntos por celda, deduplicado por proximidad",
        limitacion="Parte del REPS llega sin coordenadas; se geocodifica contra MGN (T0.5).",
    ),
    LayerSpec(
        id="education",
        titulo="Educacion — Sedes educativas MEN + OSM",
        license="gov-open-co",
        columnas=("edu_count",),
        agregacion="conteo de puntos por celda, deduplicado por proximidad",
        limitacion="Dataset MEN con coordenadas pendiente de confirmar (T0.6).",
    ),
    LayerSpec(
        id="divisions",
        titulo="Division politico-administrativa — Overture divisions + MGN DANE",
        license="gov-open-co",
        columnas=("iso3", "adm1_id", "adm2_id"),
        agregacion="asignacion por centroide + tabla de fracciones en frontera",
        limitacion="Terminos exactos de reuso del MGN pendientes de confirmar (T0.4).",
    ),
    LayerSpec(
        id="airports",
        titulo="Aeropuertos — OurAirports",
        license="public-domain",
        columnas=(),
        agregacion="conteo de puntos por celda",
        requerida=False,
    ),
)

LAYERS_BY_ID: dict[str, LayerSpec] = {layer.id: layer for layer in LAYERS}


def required_layers() -> tuple[LayerSpec, ...]:
    """Capas sin las cuales no se emite un reporte completo."""
    return tuple(layer for layer in LAYERS if layer.requerida)
