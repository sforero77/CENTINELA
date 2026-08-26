"""La ventana de cinco dias de lo que se vio y no se despacho.

Nace del M4,9 de Jordan, Santander, el 26-ago-2026: el sistema lo vio a los
doce minutos y decidio bien, pero la decision solo existia en un log de CI. Un
vigia que no puede demostrar que estuvo mirando no se distingue de uno apagado.

Lo que estas pruebas protegen no es que el archivo se escriba —eso es facil—
sino las tres reglas que hacen que la capa sea honesta: que no invente
mediciones, que no se convierta en un sismografo mundial, y que caduque.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipelines.common.geo import LATAM_BBOX
from pipelines.p1_trigger.feed import EventCandidate
from pipelines.p1_trigger.filters import evaluate
from pipelines.p1_trigger.observados import (
    DIAS_OBSERVADOS,
    EventoObservado,
    fusionar,
    leer,
    podar,
    write_observados,
)
from pipelines.p1_trigger.run import _solo_le_falto_magnitud


def _candidato(
    mag: float = 4.9,
    lon: float = -73.05,
    lat: float = 6.80,
    tipo: str = "earthquake",
) -> EventCandidate:
    """El sismo de Jordan, con lo que haga falta cambiado."""
    return EventCandidate(
        usgs_id="us7000tbzn",
        mag=mag,
        lon=lon,
        lat=lat,
        depth_km=160.0,
        lugar="4 km E of Jordan, Colombia",
        origen_utc="2026-08-26T16:45:00Z",
        detail_url="",
        tipo=tipo,
        estado_revision="reviewed",
        actualizado_utc="2026-08-26T16:45:00Z",
    )


def _evento(usgs_id: str = "us7000tbzn", *, hace_dias: float = 0.0) -> EventoObservado:
    cuando = datetime.now(UTC) - timedelta(days=hace_dias)
    return EventoObservado(
        usgs_id=usgs_id,
        mag=4.9,
        lon=-73.05,
        lat=6.80,
        depth_km=160.0,
        lugar="4 km al E de Jordan, Colombia",
        origen_utc=cuando.strftime("%Y-%m-%dT%H:%M:%SZ"),
        razon="M4.9 < umbral M5.5",
    )


# --- La regla que mas importa: no inventar una medicion ---------------------


def test_el_esquema_no_tiene_un_solo_campo_de_impacto() -> None:
    """Publicar ``pop_mmi7p: 0`` seria un falso negativo con aspecto de dato.

    Quien lo leyera lo tomaria por una medicion, y no lo es: nadie midio nada.
    Ausencia de medicion no es medicion de cero. Por eso son dos colecciones y
    no un reporte degradado.
    """
    prohibidos = ("pop", "bld", "built", "salud", "edu", "vias", "mmi", "totales")

    for campo in EventoObservado.__dataclass_fields__:
        assert not any(p in campo for p in prohibidos), (
            f"{campo!r} es un campo de impacto: esto dejaria de ser un registro"
        )


def test_el_archivo_dice_en_texto_que_no_es_una_medicion(tmp_path: Path) -> None:
    """El esquema lo garantiza para una maquina; la nota, para una persona."""
    write_observados([_evento()], site_dir=tmp_path)
    datos = json.loads((tmp_path / "observados.json").read_text(encoding="utf-8"))

    assert "no es una estimacion de cero" in datos["nota"]


# --- La ventana caduca ------------------------------------------------------


def test_lo_viejo_se_cae_de_la_ventana() -> None:
    dentro = _evento("us00000001", hace_dias=DIAS_OBSERVADOS - 1)
    fuera = _evento("us00000002", hace_dias=DIAS_OBSERVADOS + 1)

    assert [e.usgs_id for e in podar([dentro, fuera])] == ["us00000001"]


def test_se_poda_al_publicar_y_no_solo_al_leer(tmp_path: Path) -> None:
    """La poda depende del reloj, no de que llegue un sismo.

    Si solo se podara al detectar algo nuevo, un evento caducado seguiria en el
    mapa hasta el siguiente temblor — que es justo cuando nadie esta mirando la
    capa de los pequenos.
    """
    write_observados([_evento("us00000002", hace_dias=DIAS_OBSERVADOS + 1)], site_dir=tmp_path)
    datos = json.loads((tmp_path / "observados.json").read_text(encoding="utf-8"))

    assert datos["eventos"] == []


def test_salen_del_mas_reciente_al_mas_viejo() -> None:
    viejo = _evento("us00000001", hace_dias=3)
    nuevo = _evento("us00000002", hace_dias=1)

    assert [e.usgs_id for e in podar([viejo, nuevo])] == ["us00000002", "us00000001"]


def test_una_fecha_ilegible_no_se_queda_para_siempre() -> None:
    """No se puede saber si caduco, y esa es razon suficiente para no publicarlo."""
    roto = replace(_evento("usroto"), origen_utc="ayer por la tarde")

    assert [e.usgs_id for e in podar([roto, _evento()])] == ["us7000tbzn"]


# --- Reencuentros: el mismo sismo se ve muchas veces ------------------------


def test_el_mismo_sismo_no_se_duplica() -> None:
    """Los feeds se solapan y el vigia corre cada hora."""
    assert len(fusionar([_evento()], [_evento()])) == 1


def test_la_magnitud_revisada_gana_a_la_automatica() -> None:
    """USGS revisa magnitudes horas despues; la ultima lectura es la buena."""
    assert fusionar([_evento()], [replace(_evento(), mag=5.1)])[0].mag == 5.1


# --- Persistencia -----------------------------------------------------------


def test_ida_y_vuelta(tmp_path: Path) -> None:
    write_observados([_evento()], site_dir=tmp_path)

    assert [e.usgs_id for e in leer(site_dir=tmp_path)] == ["us7000tbzn"]


def test_sin_archivo_no_es_un_fallo(tmp_path: Path) -> None:
    assert leer(site_dir=tmp_path) == []


def test_un_archivo_corrupto_se_reconstruye(tmp_path: Path) -> None:
    """El vigia corre cada hora y no puede caerse por un archivo a medio escribir."""
    (tmp_path / "observados.json").write_text("{roto", encoding="utf-8")

    assert leer(site_dir=tmp_path) == []


# --- Solo LATAM, y solo lo pequeno ------------------------------------------


def test_solo_entra_lo_que_unicamente_le_falto_tamano() -> None:
    """Los feeds del USGS son mundiales: sin esto seria un sismografo global.

    De catorce candidatos de una corrida tipica, la mayoria caen fuera del bbox.
    """
    # El de Jordan: pequeno, pero nuestro.
    assert _solo_le_falto_magnitud(_candidato(), LATAM_BBOX)
    # Japon: pequeno y ajeno.
    assert not _solo_le_falto_magnitud(_candidato(lon=140.0, lat=36.0), LATAM_BBOX)
    # Una explosion no es un sismo, por pequena que sea.
    assert not _solo_le_falto_magnitud(_candidato(tipo="explosion"), LATAM_BBOX)


def test_el_ayudante_solo_responde_por_el_tamano() -> None:
    """Su contrato es «¿le sobraba solo la magnitud?», no «¿se despacha?».

    Un M5.5 le da True, y esta bien: a ese no lo descarto el filtro, asi que
    nunca llega hasta aqui. Que no entre en la capa lo garantiza el sitio de
    llamada —``if not decision:``— y eso se prueba en integracion, contra el
    pipeline entero.
    """
    assert _solo_le_falto_magnitud(_candidato(mag=5.5), LATAM_BBOX)


def test_el_sismo_de_jordan_habria_quedado_registrado() -> None:
    """El caso real que motivo todo esto, de punta a punta."""
    jordan = _candidato()
    decision = evaluate(jordan)
    observado = EventoObservado.desde_candidato(jordan, decision.razon)

    assert not decision.relevante, "el umbral de M5.5 no se toca"
    assert observado.razon == "M4.9 < umbral M5.5"
    assert (observado.mag, observado.depth_km) == (4.9, 160.0)


# --- Rellenar la ventana desde el historico ---------------------------------


class _FdsnFalso:
    """Devuelve lo que se le diga y recuerda la URL que le pidieron."""

    def __init__(self, features: list[dict[str, object]]) -> None:
        self.features = features
        self.url = ""

    def get_json(self, url: str) -> dict[str, object]:
        self.url = url
        return {"type": "FeatureCollection", "features": self.features}

    def get_bytes(self, url: str) -> bytes:  # pragma: no cover - no se usa
        raise NotImplementedError


def _feature(
    usgs_id: str = "us7000tbzn",
    *,
    mag: float = 4.9,
    lon: float = -73.05,
    lat: float = 6.80,
    tipo: str = "earthquake",
) -> dict[str, object]:
    return {
        "id": usgs_id,
        "geometry": {"type": "Point", "coordinates": [lon, lat, 160.0]},
        "properties": {
            "mag": mag,
            "place": "4 km E of Jordan, Colombia",
            "time": 1787762714000,
            "updated": 1787762714000,
            "detail": "",
            "type": tipo,
            "status": "reviewed",
        },
    }


def test_rellenar_trae_lo_que_la_capa_no_llego_a_ver() -> None:
    """Recien encendida, la capa decia «1 en 5 dias» y habian sido nueve.

    Un numero falso sobre el mundo es peor que no dar ninguno: quien lo lea
    concluye que la region estuvo tranquila.
    """
    from pipelines.p1_trigger.observados import rellenar

    encontrados = rellenar(_FdsnFalso([_feature()]))

    assert [e.usgs_id for e in encontrados] == ["us7000tbzn"]


def test_rellenar_pide_solo_lo_que_esta_bajo_el_umbral() -> None:
    """Traer tambien los M≥5.5 mezclaria reportes con no-reportes.

    Los que pasan el umbral tienen su propio sitio; aparecer ademas aqui los
    contaria dos veces.
    """
    from pipelines.common.constants import MIN_MAGNITUDE
    from pipelines.p1_trigger.observados import rellenar

    fdsn = _FdsnFalso([])
    rellenar(fdsn)

    assert f"maxmagnitude={MIN_MAGNITUDE - 0.01:.2f}" in fdsn.url
    assert "minmagnitude=4.5" in fdsn.url


def test_rellenar_acota_la_consulta_a_latam() -> None:
    """Sin la caja, FDSN devolveria el planeta entero."""
    from pipelines.common.geo import LATAM_BBOX
    from pipelines.p1_trigger.observados import rellenar

    fdsn = _FdsnFalso([])
    rellenar(fdsn)

    assert f"minlatitude={LATAM_BBOX.lat_min}" in fdsn.url
    assert f"maxlongitude={LATAM_BBOX.lon_max}" in fdsn.url


def test_rellenar_sigue_filtrando_lo_que_no_es_un_sismo() -> None:
    """FDSN acota magnitud y caja, pero no sabe de voladuras de cantera.

    Delegar el criterio a la consulta dejaria dos definiciones de «sismo
    relevante» en el sistema, y la del filtro es la que manda.
    """
    from pipelines.p1_trigger.observados import rellenar

    encontrados = rellenar(_FdsnFalso([_feature(tipo="quarry blast")]))

    assert encontrados == []


def test_rellenar_usa_fdsn_y_no_el_feed_en_vivo() -> None:
    """D7 reserva FDSN para historicos y lo prohibe en el camino critico.

    Esto es un historico —se llama a mano, no desde el cron— y ademas el feed
    en vivo no llega a cinco dias atras.
    """
    from pipelines.common.constants import USGS_FDSN_EVENT
    from pipelines.p1_trigger.observados import rellenar

    fdsn = _FdsnFalso([])
    rellenar(fdsn)

    assert fdsn.url.startswith(USGS_FDSN_EVENT)
