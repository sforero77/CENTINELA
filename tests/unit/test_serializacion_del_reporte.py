"""Todo campo del modelo llega al `report.json`, y el esquema lo exige.

`Totales.to_dict` era una lista escrita a mano de doce claves sobre un dataclass
de diecinueve campos. Las siete que faltaban —las de la banda MMI>=6— se
calculan en el SQL, viajan en `ImpactTotals`, salen en el `adm2.csv` con su
etiqueta HXL y las pinta el `report.md`, pero nunca llegaban al JSON.

Tres guardias podian haberlo visto y ninguno podia:

* El esquema declaraba las diecinueve propiedades y no tenia `required`, asi que
  `{"totales": {}}` era un `report.json` valido.
* La prueba de ida y vuelta comparaba `to_dict()` contra `to_dict()`, que es
  ciega justo a lo unico que `to_dict` puede hacer mal.
* `test_funciones_conectadas` vigila funciones sin llamador, no campos sin
  serializador.

Consecuencia medida: ocho de los reportes publicados titulan en MMI>=6, y el
visor —que solo lee el JSON— pintaba "0 sedes de salud" al lado de hasta 4,75
millones de personas dentro de la banda.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from pipelines.p3_report.model import Evento, Inputs, MunicipioTop, Totales

RAIZ = Path(__file__).parent.parent.parent
ESQUEMA = json.loads((RAIZ / "schemas" / "report-1.0.schema.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("clase", [Totales, Evento, Inputs, MunicipioTop])
def test_to_dict_emite_todos_los_campos(clase: type) -> None:
    """Ninguna de las cuatro estructuras de cifras puede callarse un campo."""
    campos = {c.name for c in fields(clase)}
    kwargs = {c.name: c.default for c in fields(clase) if c.default is not None}
    faltan = {c.name for c in fields(clase)} - set(kwargs)
    # Los campos sin default se rellenan con algo del tipo adecuado.
    for nombre in faltan:
        tipo = next(c.type for c in fields(clase) if c.name == nombre)
        kwargs[nombre] = "" if "str" in str(tipo) else 0
    emitidas = set(clase(**kwargs).to_dict())
    assert emitidas == campos, (
        f"{clase.__name__}.to_dict no emite {sorted(campos - emitidas)}; "
        f"emite de mas {sorted(emitidas - campos)}. Derivarlo de dataclasses.fields()."
    )


def test_el_esquema_exige_las_diecinueve_cifras() -> None:
    """Sin `required`, `{"totales": {}}` era un report.json valido."""
    totales = ESQUEMA["properties"]["totales"]
    exigidas = set(totales.get("required", []))
    campos = {c.name for c in fields(Totales)}
    assert exigidas == campos, (
        f"el esquema no exige {sorted(campos - exigidas)}; "
        f"exige lo que no existe: {sorted(exigidas - campos)}"
    )


def test_el_esquema_declara_lo_mismo_que_el_modelo() -> None:
    declaradas = set(ESQUEMA["properties"]["totales"]["properties"])
    assert declaradas == {c.name for c in fields(Totales)}


def test_el_esquema_cierra_la_puerta_a_claves_inventadas() -> None:
    """`additionalProperties: false` es lo que hace que el contrato sea contrato."""
    assert ESQUEMA["properties"]["totales"]["additionalProperties"] is False


def _objetos(nodo: Any, ruta: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    """Todo objeto declarado del esquema, con su ruta, por profundo que este."""
    if isinstance(nodo, dict):
        if nodo.get("type") == "object" and "properties" in nodo:
            yield ruta or "(raiz)", nodo
        for clave, valor in nodo.items():
            yield from _objetos(valor, f"{ruta}.{clave}" if ruta else clave)
    elif isinstance(nodo, list):
        for i, valor in enumerate(nodo):
            yield from _objetos(valor, f"{ruta}[{i}]")


def test_ningun_objeto_del_esquema_queda_abierto() -> None:
    """`ground_failure_usgs`, `licencia` y sus atribuciones aceptaban cualquier clave.

    Un contrato cerrado por todas partes menos tres sitios no es un contrato:
    un `ls_alerta` mal escrito —sin `_usgs`— validaba, y el visor lo leia como
    ausente. Se recorre el esquema entero en vez de enumerar objetos, para que
    uno nuevo no pueda nacer abierto sin que esto lo diga.
    """
    objetos = list(_objetos(ESQUEMA))
    assert len(objetos) >= 9, "el recorrido no encuentra los objetos del esquema"
    abiertos = [ruta for ruta, nodo in objetos if nodo.get("additionalProperties") is not False]
    assert not abiertos, f"objetos del esquema sin additionalProperties:false: {abiertos}"


def test_top_municipios_exige_la_cifra_por_la_que_se_ordena() -> None:
    """Exigia `pop_mmi7p` y dejaba `pop_banda` opcional, justo al reves.

    En los reportes que no alcanzan MMI>=7 —ocho de veintisiete el 6-sep— la
    obligatoria vale cero en todas las filas y la opcional lleva el dato. Un
    consumidor que leyera el contrato para saber que columna usar elegia la de
    los ceros. Se exige todo campo de `MunicipioTop`, que es lo que se emite.
    """
    fila = ESQUEMA["properties"]["top_municipios"]["items"]
    assert set(fila["required"]) == {c.name for c in fields(MunicipioTop)}


def test_todo_reporte_publicado_cumple_el_esquema() -> None:
    """El esquema describe lo que se publica: cerrarlo no puede dejar fuera a nadie.

    `write_report_bundle` valida cada reporte antes de escribirlo, pero contra
    el esquema de ese dia. Un cambio del esquema que dejara fuera a los ya
    publicados —los que el visor y quien integre siguen leyendo— solo lo ve
    esta prueba.
    """
    from jsonschema import Draft202012Validator

    validador = Draft202012Validator(ESQUEMA)
    publicados = sorted((RAIZ / "reports").glob("*/report.json"))
    assert publicados, "no se encontro ningun reporte publicado que validar"
    fuera = {
        p.parent.name: sorted(
            e.message for e in validador.iter_errors(json.loads(p.read_text("utf-8")))
        )
        for p in publicados
    }
    assert not {k: v for k, v in fuera.items() if v}


def test_un_final_con_poblacion_en_banda_no_trae_radios(reporte: Any) -> None:
    """El esquema decia que `radios` era solo de preliminares; no lo es.

    Nueve reportes finales lo traian el 6-sep-2026, y es correcto: cuando ninguna banda
    alcanza poblacion el radio es lo unico que dimensiona el evento. La regla
    real —final con radios implica bandas en cero— ahora la valida el esquema.
    """
    from jsonschema import Draft202012Validator

    validador = Draft202012Validator(ESQUEMA)
    base = reporte.to_dict()
    radios = [{"radio_km": 100, "pop": 610_000.0}]
    ceros = {**base["totales"], "pop_mmi6p": 0.0, "pop_mmi7p": 0.0, "pop_mmi8p": 0.0}

    sin_banda = {**base, "preliminar": False, "radios": radios, "totales": ceros}
    con_banda = {**base, "preliminar": False, "radios": radios}
    preliminar = {**base, "preliminar": True, "radios": radios}

    assert base["totales"]["pop_mmi6p"] > 0, "la fixture tiene que alcanzar MMI>=6"
    assert list(validador.iter_errors(sin_banda)) == []
    assert list(validador.iter_errors(preliminar)) == []
    assert list(validador.iter_errors(con_banda)), (
        "un reporte final con poblacion en banda no puede traer radios"
    )


def test_las_siete_columnas_de_la_banda_6_estan() -> None:
    """El caso concreto, escrito con sus nombres para que se lea en el diff."""
    emitidas = set(Totales().to_dict())
    assert {
        "pop_65p_mmi6p",
        "bld_mmi6p",
        "built_m2_mmi6p",
        "health_mmi6p",
        "edu_mmi6p",
        "road_km_mmi6p",
        "road_km_principal_mmi6p",
    } <= emitidas


def test_un_to_dict_incompleto_rompe_la_ida_y_vuelta() -> None:
    """La propiedad que hace util la prueba de ida y vuelta a nivel de objeto.

    Se reconstruye el serializador viejo —las doce claves de entonces— y se
    comprueba que reconstruir desde el resultado NO devuelve el original. La
    version que comparaba diccionarios no podia distinguir estos dos casos.
    """
    doce_claves = [
        "pop_mmi6p",
        "pop_mmi7p",
        "pop_mmi8p",
        "pop_65p_mmi7p",
        "bld_mmi7p",
        "built_m2_mmi7p",
        "health_mmi7p",
        "edu_mmi7p",
        "road_km_mmi7p",
        "road_km_principal_mmi7p",
        "pop_ls_alta",
        "pop_lq_alta",
    ]
    original = Totales(pop_mmi6p=7_194_540.0, health_mmi6p=1698.0, edu_mmi6p=1570.0)
    recortado = {k: getattr(original, k) for k in doce_claves}

    assert Totales(**recortado) != original, "un serializador incompleto tiene que romper esto"
    # Y con el serializador de verdad, vuelve entero.
    assert Totales(**original.to_dict()) == original
