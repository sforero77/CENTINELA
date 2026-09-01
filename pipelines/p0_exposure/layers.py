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
        titulo="Estructura etaria/sexo — WorldPop age-sex constrained R2025A, epoca 2025",
        license="CC-BY-4.0",
        columnas=("pop_0_14", "pop_15_64", "pop_65p"),
        agregacion="suma de la serie combinada por edad -> celda r8; 15-64 es el residuo",
        limitacion=(
            "Modelado, como toda la cadena. El supuesto de estructura etaria "
            "estable que la espec daba por inevitable ya no aplica: WorldPop "
            "publica desglose age-sex para 2025 en el release R2025A. "
            "Los extremos (0-14 y 65+) son conteos de WorldPop; la banda "
            "central es lo que queda de pop_total tras restarlos, asi que "
            "absorbe la diferencia entre ambos modelos de poblacion — que la "
            "banda de discrepancia publicada acota."
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
            "Se publica el flag 'revisar', no se oculta el vacio (§6.4). "
            "Desde col-v0.5 el hueco ademas se mide: 'built_m2' viene de satelite "
            "y no depende de que alguien haya mapeado el barrio."
        ),
    ),
    LayerSpec(
        id="built_ghsl",
        titulo="Superficie construida — GHS-BUILT-S R2023A epoca 2025",
        license="EC-reuse-attribution",
        columnas=("built_m2",),
        agregacion="suma de superficie construida por pixel 100 m -> celda r8",
        limitacion=(
            "Mide cuanto hay construido, NO cuantas edificaciones son ni de que "
            "tipo: 40.000 m² pueden ser una bodega o cien viviendas. No sustituye "
            "a Overture, lo contrasta. Su valor esta en que se deriva de "
            "Sentinel-2 y Landsat, asi que **no hereda los huecos de OSM en "
            "asentamientos informales y zona rural dispersa** — justo donde vive "
            "la poblacion mas expuesta y donde el conteo de edificaciones falla."
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
        titulo="Salud — HOTOSM (HDX) + healthsites.io via HDX",
        license="ODbL-1.0",
        columnas=("health_count",),
        agregacion=(
            "conteo de puntos por celda; la segunda fuente aporta solo lo que "
            "no esta a menos de 20 m de un punto de la primera"
        ),
        limitacion=(
            "El REPS de MinSalud no entra aqui: no publica coordenadas (solo "
            "DIVIPOLA y direccion) y es CC BY-SA 4.0, copyleft incompatible con "
            "la ODbL de Overture. Sirve como referencia de completitud "
            "municipal en una tabla aparte, no como conteo por celda. "
            "Tampoco se usa la API de healthsites.io: exige API key y O4 pide "
            "reconstruir el activo sin credenciales privadas."
        ),
    ),
    LayerSpec(
        id="education",
        titulo="Educacion — HOTOSM (HDX)",
        license="ODbL-1.0",
        columnas=("edu_count",),
        agregacion=(
            "conteo de puntos por celda; hoy una sola fuente, y si se anade una "
            "segunda aportara solo lo que no este a menos de 20 m de la primera"
        ),
        limitacion=(
            "El directorio del MEN tampoco publica coordenadas y es CC BY-SA "
            "4.0: mismo tratamiento que el REPS."
        ),
    ),
    LayerSpec(
        id="divisions",
        titulo="Division politico-administrativa — MGN del DANE + COD-AB de OCHA + Overture",
        license="CC-BY-4.0",
        columnas=("iso3", "adm1_id", "adm2_id"),
        agregacion="asignacion por centroide + tabla de fracciones en frontera",
        limitacion=(
            "El MGN es la fuente de verdad del codigo DIVIPOLA y del toponimo "
            "oficial de Colombia. Para el resto, el patron cod-ab-<iso3> de "
            "OCHA da adm1/adm2 de los 19 paises de LATAM con una sola licencia "
            "y una sola forma, en vez de pelear con diecinueve geoportales "
            "nacionales. Verificado pais por pais el 23-ago-2026."
        ),
    ),
    LayerSpec(
        id="landcover",
        titulo="Cobertura del suelo — ESA WorldCover v200 (2021), 10 m",
        license="CC-BY-4.0",
        columnas=(
            "lulc_arbolado_pct",
            "lulc_arbustos_pct",
            "lulc_pastizal_pct",
            "lulc_cultivo_pct",
            "lulc_construido_pct",
            "lulc_humedal_pct",
            "lulc_px",
        ),
        agregacion=(
            "conteo de pixeles por clase sobre la overview /8 (~80 m) -> celda "
            "r8; las fracciones se derivan al final, sobre pixeles clasificados"
        ),
        limitacion=(
            "No se descarga: se leen las overviews del COG por rangos HTTP, asi "
            "que no hay fichero en el manifest ni hash de insumo. Entra igual en "
            "este catalogo porque su ausencia era invisible: sin declararla aqui "
            "ni en `REQUIRED_COVERAGE`, un cambio de version o de bucket en el "
            "origen —las URL son constantes fijas— dejaba `lulc_h3` vacia, el "
            "LEFT JOIN ponia 0.0 en las siete columnas y el activo se publicaba "
            "con '0 % arbolado' pasando todos los asserts. Esos ceros salen a la "
            "calle en los reportes de incendio."
        ),
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
