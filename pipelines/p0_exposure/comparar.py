"""Un activo reconstruido se compara con el que ya esta publicado.

LA PUERTA DE LOS DIGESTS PARABA, PERO NO DECIDIA.

`_verificar_insumos` detiene el build cuando un tercero republica una fuente.
Es lo correcto para saber *que* cambio, y no sirve para saber si el cambio es
bueno: eso quedaba a una persona. El 1-oct-2026 HOT y HDX republicaron las sedes
de salud de cinco paises y los limites de Paraguay, la reconstruccion
trimestral se paro en los seis, y ahi se quedo.

La pregunta que esa persona se haria es medible: ¿el activo nuevo se parece al
publicado? Un listado de sedes de salud que gana o pierde un puñado es una
actualizacion; uno que pierde la mitad, o un pais que cambia un 10 % de
poblacion, es un fallo del tercero o nuestro. Esto compara el ``resumen`` de las
dos ``medicion.json`` capa por capa, con un margen por capa que dice cuanto
puede moverse cada una entre dos versiones legitimas.

Si pasa, el activo se publica y los digests nuevos se fijan solos. Si no, no se
publica nada —el activo anterior sigue sirviendo— y la incidencia dice que capa
se salio y cuanto.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Margen:
    """Cuanto puede caer y cuanto puede crecer una capa, en tanto por uno."""

    caida: float
    crecida: float


#: El margen de cada capa entre dos versiones legitimas de sus fuentes.
#:
#: La poblacion y la malla vienen de GHS-POP, que no cambia entre releases de
#: Overture ni por un listado de sedes: se mueven poco o es que algo se rompio.
#: Las edificaciones y las vias son Overture, que crece release a release. Las
#: sedes de salud y educacion son mapeo comunitario (HOT, healthsites): crecen a
#: saltos y una depuracion puede quitar duplicados, pero perder un tercio no es
#: una depuracion. Los municipios cambian solo con un COD-AB nuevo.
MARGENES: dict[str, Margen] = {
    "pop_total": Margen(caida=0.03, crecida=0.03),
    "celdas": Margen(caida=0.05, crecida=0.05),
    "municipios": Margen(caida=0.10, crecida=0.10),
    "bld_count": Margen(caida=0.10, crecida=0.30),
    "built_m2": Margen(caida=0.10, crecida=0.30),
    "road_km": Margen(caida=0.10, crecida=0.30),
    "health_count": Margen(caida=0.30, crecida=1.00),
    "edu_count": Margen(caida=0.30, crecida=1.00),
}


def comparar_mediciones(anterior: dict[str, Any], nueva: dict[str, Any]) -> list[str]:
    """Las capas del activo nuevo que se salen de su margen frente al publicado.

    Lista vacia es que se parecen lo bastante para publicarlo sin mirar.
    """
    if anterior.get("iso3") != nueva.get("iso3"):
        return [f"se comparan paises distintos: {anterior.get('iso3')} y {nueva.get('iso3')}"]

    antes: dict[str, Any] = anterior.get("resumen") or {}
    despues: dict[str, Any] = nueva.get("resumen") or {}
    problemas = []
    for capa, margen in MARGENES.items():
        if capa not in antes or capa not in despues:
            continue
        a, d = float(antes[capa] or 0), float(despues[capa] or 0)
        if a == 0:
            continue
        if d == 0:
            problemas.append(f"{capa}: {a:,.0f} -> 0, la capa quedo vacia")
            continue
        cambio = (d - a) / a
        if cambio < -margen.caida or cambio > margen.crecida:
            problemas.append(
                f"{capa}: {a:,.0f} -> {d:,.0f} ({cambio:+.1%}); "
                f"margen -{margen.caida:.0%} / +{margen.crecida:.0%}"
            )
    return problemas


def insumos_cambiados(medicion: dict[str, Any]) -> dict[str, str]:
    """``{fuente: digest_nuevo}`` de los insumos republicados que el build acepto."""
    return {
        sid: datos["insumos_sha256"]
        for sid, datos in (medicion.get("insumos") or {}).items()
        if datos.get("fijado_antes") and datos.get("insumos_sha256")
    }
