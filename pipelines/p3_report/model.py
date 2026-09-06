"""Modelo de ``report.json`` v1 (§3.4).

Esta estructura es un contrato publico: la consumen el visor, el paquete HDX y
cualquiera que descargue el JSON. Cambiarla incompatiblemente exige subir la
version del schema (``centinela/report/2.0``), no editar en sitio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Self

from .. import PIPELINE_VERSION
from ..common.constants import DISCLAIMERS, REPORT_SCHEMA_ID
from ..common.state import utcnow_iso


@dataclass(frozen=True, slots=True)
class Evento:
    """Identificacion del sismo."""

    usgs_id: str
    mag: float
    depth_km: float
    utc: str
    lugar: str
    #: Nivel PAGER, referencia cruzada. Vacio si el producto no existe.
    pager_alert: str = ""
    #: Epicentro. Iba en el `event_state` y se quedaba ahi, asi que `report.json`
    #: —el artefacto publico— no decia donde fue el sismo mas alla del toponimo.
    #: Quien lo consumia tenia que volver a USGS para ponerlo en un mapa, y el
    #: propio visor no podia dibujarlo. Por defecto (0, 0) para no romper los
    #: reportes ya publicados al releerlos.
    lon: float = 0.0
    lat: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "usgs_id": self.usgs_id,
            "mag": self.mag,
            "depth_km": self.depth_km,
            "utc": self.utc,
            "lugar": self.lugar,
            "pager_alert": self.pager_alert,
            "lon": self.lon,
            "lat": self.lat,
        }


@dataclass(frozen=True, slots=True)
class Inputs:
    """Versiones exactas de los insumos consumidos (RNF-04)."""

    shakemap_version: int
    groundfailure_version: int
    exposure_manifest: str
    #: QUE MODELO PRODUJO CADA CIFRA DE TERRENO.
    #:
    #: El fichero se descargaba con el nombre del modelo **preferido** aunque la
    #: url viniera de las alternativas historicas, y a partir de ahi nada los
    #: distinguia: el mismo `GROUND_FAILURE_HIGH_PROB`, la misma etiqueta de
    #: unidad y solo el numero de version aqui. Y la docstring de ese umbral dice
    #: que no son intercambiables: «Zhu (2017) entrega cobertura areal, que no es
    #: una probabilidad (...) el mismo 0,10 no marca lo mismo en cada una».
    #:
    #: Vacio en los reportes emitidos antes de que esto se registrara, que es una
    #: ausencia honesta y no un modelo equivocado.
    modelo_deslizamiento: str = ""
    modelo_licuefaccion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "shakemap_version": self.shakemap_version,
            "groundfailure_version": self.groundfailure_version,
            "exposure_manifest": self.exposure_manifest,
            "modelo_deslizamiento": self.modelo_deslizamiento,
            "modelo_licuefaccion": self.modelo_licuefaccion,
        }


@dataclass(frozen=True, slots=True)
class Atribuido:
    """Un credito, tal como viaja dentro del artefacto publicado."""

    titulo: str = ""
    licencia: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"titulo": self.titulo, "licencia": self.licencia, "url": self.url}


@dataclass(frozen=True, slots=True)
class Licencia:
    """Bajo que se puede usar este reporte, y a quien hay que citar.

    NINGUN ARTEFACTO PUBLICADO DECIA UNA PALABRA DE LICENCIA.

    `ls reports/us7000kg9g/` daba adm2.csv, celdas.json, contornos.json,
    hilo.txt, dos PNG, report.json y report.md — ni un LICENSE, ni un NOTICE. Y
    las claves de `report.json` no incluian `licencia`, ni `atribucion`, ni
    `cubo`: el unico rastro de procedencia era `inputs.exposure_manifest`, la
    cadena `"dom-v0.2"`, y el cuarto disclaimer remitia a un «manifiesto
    enlazado» que se escribia en texto plano, sin URL.

    Medido con `resolve_bucket` sobre los diecinueve manifests, **los diecinueve
    dan `odbl`**. O sea que todo lo que este sistema publica es un derivado de
    una base ODbL, y la ODbL §4.3 exige que el aviso viaje con la obra producida
    mientras §4.4 exige que el derivado se publique bajo ODbL. Ninguna de las dos
    cosas ocurria en ningun fichero de `reports/`.
    """

    cubo: str = ""
    spdx: str = ""
    texto: str = ""
    #: El enlace que el disclaimer prometia y que se escribia como texto plano.
    manifiesto_url: str = ""
    atribuciones: tuple[Atribuido, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "cubo": self.cubo,
            "spdx": self.spdx,
            "texto": self.texto,
            "manifiesto_url": self.manifiesto_url,
            "atribuciones": [a.to_dict() for a in self.atribuciones],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            cubo=str(data.get("cubo", "")),
            spdx=str(data.get("spdx", "")),
            texto=str(data.get("texto", "")),
            manifiesto_url=str(data.get("manifiesto_url", "")),
            atribuciones=tuple(Atribuido(**a) for a in data.get("atribuciones", [])),
        )

    def como_texto(self) -> str:
        """El `LICENSE.txt` que viaja al lado del reporte.

        Un `report.json` descargado suelto se abre en un editor; un CSV se abre
        en una hoja de calculo. El fichero de licencia es el unico sitio donde
        el aviso se lee sin parsear nada, y es lo que la ODbL §4.3 pide de
        verdad: que acompane a la obra.
        """
        lineas = [
            "CENTINELA — exposicion sismica abierta",
            "",
            self.texto,
            "",
            f"Licencia del derivado: {self.spdx} (cubo `{self.cubo}`)",
            "",
            "Fuentes que hay que citar:",
            "",
        ]
        lineas += [f"  - {a.titulo} — {a.licencia}\n    {a.url}" for a in self.atribuciones]
        if self.manifiesto_url:
            lineas += ["", f"Manifiesto de exposicion: {self.manifiesto_url}"]
        lineas += [
            "",
            "El codigo de CENTINELA es software libre bajo Apache-2.0.",
            "",
        ]
        return "\n".join(lineas)


@dataclass(frozen=True, slots=True)
class Totales:
    """Cifras nacionales por banda de intensidad (RF-05)."""

    pop_mmi6p: float = 0.0
    pop_mmi7p: float = 0.0
    pop_mmi8p: float = 0.0
    pop_65p_mmi7p: float = 0.0
    #: LA BANDA 6, PARA TODO. Hasta el 3-sep-2026 el equipamiento solo se
    #: agregaba en MMI>=7, y trece de veintitres reportes no llegan ahi: salian
    #: "0 hospitales, 0 escuelas" con millones de personas dentro de MMI>=6.
    #: La razon de publicar desde 6 esta citada en `MMI_BANDS_INFRAESTRUCTURA`
    #: (`common/constants.py`); la corta: el USGS pone "Damage slight" en el
    #: grado VI, GDACS deja de dar verde en VI, y la OPS reporta hospitales
    #: desde VI. Las columnas `*_mmi7p` no cambian de significado.
    pop_65p_mmi6p: float = 0.0
    bld_mmi6p: float = 0.0
    built_m2_mmi6p: float = 0.0
    health_mmi6p: float = 0.0
    edu_mmi6p: float = 0.0
    road_km_mmi6p: float = 0.0
    road_km_principal_mmi6p: float = 0.0
    bld_mmi7p: float = 0.0
    #: Superficie construida detectada por satelite. Contrasta a bld_mmi7p:
    #: donde OSM no mapeo el barrio, esta cifra si lo ve.
    built_m2_mmi7p: float = 0.0
    health_mmi7p: float = 0.0
    edu_mmi7p: float = 0.0
    road_km_mmi7p: float = 0.0
    #: Troncal, autopista, primaria y secundaria. El resto —residencial,
    #: service, track— es la diferencia con road_km_mmi7p.
    road_km_principal_mmi7p: float = 0.0
    pop_ls_alta: float = 0.0
    pop_lq_alta: float = 0.0

    @property
    def banda_titular(self) -> int:
        """La banda MMI mas alta que alcanzo poblacion. Cero si ninguna.

        **Casi la mitad de los sismos reales no llegan a MMI≥7 sobre
        poblacion.** Medido sobre los primeros dieciocho reportes del catalogo
        LATAM: ocho, el 44 %. Son los profundos y los que ocurren mar adentro,
        que en esta region son muchos — Tehuantepec 2017 fue un M8,2 y su
        maximo sobre poblacion mexicana es MMI 6,5.

        El producto titulaba siempre con MMI≥7, asi que para esos ocho la cifra
        grande era **0** y la tabla de municipios salia ordenada por una
        columna de ceros, o sea en orden alfabetico. Un cero es cierto y se lee
        como que el sistema fallo, o como que el sismo no fue nada.

        Se titula con la banda mas alta que si alcanzo gente, diciendo cual es.
        """
        if self.pop_mmi8p > 0:
            return 8
        if self.pop_mmi7p > 0:
            return 7
        if self.pop_mmi6p > 0:
            return 6
        return 0

    def poblacion_en(self, banda: int) -> float:
        """Poblacion de la banda pedida. Cero para una banda no publicada."""
        return {6: self.pop_mmi6p, 7: self.pop_mmi7p, 8: self.pop_mmi8p}.get(banda, 0.0)

    @property
    def banda_publicada(self) -> int:
        """La banda por la que este reporte ordena y titula sus municipios.

        **UNA SOLA REGLA, Y ESTE ES EL SITIO.** Habia dos: `build_report`
        seleccionaba los quince primeros en SQL por `banda_titular` —que llega
        a 8— y el markdown, el hilo, el mapa y el visor los reordenaban por
        esta, que nunca pasa de 7. En los tres reportes que alcanzan MMI>=8 el
        SQL recortaba a quince por una columna y la tabla se publicaba ordenada
        por otra, asi que un municipio con mucha gente en MMI>=7 y nadie en
        MMI>=8 no llegaba a entrar.

        Paso de verdad. En `reports/us20005j32` (Muisne) falta **Manta, con
        265.263 personas en MMI>=7** —seria el tercero— y en su lugar se publica
        Eloy Alfaro con 6.605; faltan tambien El Carmen (131.651), El Empalme
        (87.249) y Montecristi (77.993). En `reports/us6000t7zp` faltan Sucre
        (352.686) y Plaza (172.919). Quien reparte ayuda leyendo esa tabla
        despacha al municipio equivocado.

        Se ordena por MMI>=7 —donde estan todas las demas cifras del reporte y
        lo que hace comparables dos eventos— salvo que el evento no alcance esa
        banda sobre poblacion, y entonces por MMI>=6. Nunca por MMI>=8: es una
        banda demasiado estrecha para ordenar, y ordenar por ella esconde a los
        municipios grandes del anillo de al lado.
        """
        return 7 if self.pop_mmi7p > 0 else 6

    def to_dict(self) -> dict[str, Any]:
        """Las cifras, **derivadas de los campos** y no enumeradas a mano.

        Esto era una lista escrita a mano de doce claves sobre un dataclass de
        diecinueve campos. Las siete que faltaban eran las de la banda MMI>=6
        —`pop_65p_mmi6p`, `bld_mmi6p`, `built_m2_mmi6p`, `health_mmi6p`,
        `edu_mmi6p`, `road_km_mmi6p`, `road_km_principal_mmi6p`—, que se
        calculan en el SQL, viajan en `ImpactTotals`, se publican en el
        `adm2.csv` con su etiqueta HXL y las pinta el `report.md`, pero nunca
        llegaban al `report.json`.

        Ocho de los reportes publicados tienen su banda titular en MMI>=6, asi
        que el visor —que solo puede leer el JSON— pintaba "0 sedes de salud, 0
        sedes educativas, 0 edificaciones" al lado de hasta 4,75 millones de
        personas dentro de la banda, mientras el `report.md` del mismo
        directorio decia 1.698 y 1.570.

        Y era peor que un cero: `centinela regenerar-textos`, el comando que
        `docs/OPERACION.md` prescribe como reparacion de rutina, relee el
        `report.json` y reescribe el `report.md`. Ejecutarlo habria convertido
        esas cifras en ceros tambien en el markdown.

        Derivarlo de `fields()` cierra la clase entera de fallo: una cifra que
        se anade al dataclass se publica, sin depender de que alguien se acuerde
        de una segunda lista.
        """
        return {campo.name: getattr(self, campo.name) for campo in fields(self)}


@dataclass(frozen=True, slots=True)
class MunicipioTop:
    """Fila del ranking municipal."""

    adm2_id: str
    nombre: str
    mmi_max: float
    #: Poblacion en MMI≥7. Se publica siempre y con el mismo significado,
    #: porque es lo que hace comparables dos eventos distintos.
    pop_mmi7p: float
    #: Poblacion en la banda por la que **este** reporte ordena
    #: (:attr:`Totales.banda_titular`). Coincide con `pop_mmi7p` cuando el
    #: evento alcanza MMI≥7, y es la cifra util cuando no: sin ella la tabla
    #: sale ordenada por una columna de ceros.
    pop_banda: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "adm2_id": self.adm2_id,
            "nombre": self.nombre,
            "mmi_max": self.mmi_max,
            "pop_mmi7p": self.pop_mmi7p,
            "pop_banda": self.pop_banda,
        }


@dataclass(frozen=True, slots=True)
class Incertidumbre:
    """Banda de discrepancia y notas de calidad.

    "Nunca ocultar el vacio" es una regla del registro de riesgos: los huecos
    de exposicion se publican como notas, no se maquillan.
    """

    #: `None` cuando no se pudo medir. **No es cero.** Ver
    #: `ImpactTotals.discrepancia_pct`: tres reportes publicaban "0,0 %", que se
    #: lee como "los dos productos coinciden" y significaba lo contrario.
    pop_discrepancia_pct: float | None = None
    notas: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pop_discrepancia_pct": self.pop_discrepancia_pct,
            "notas": list(self.notas),
        }


@dataclass(frozen=True, slots=True)
class Descargas:
    """Enlaces a los artefactos publicados."""

    geoparquet: str = ""
    pmtiles: str = ""
    csv_adm2: str = ""
    mapa_png: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "geoparquet": self.geoparquet,
            "pmtiles": self.pmtiles,
            "csv_adm2": self.csv_adm2,
            "mapa_png": self.mapa_png,
        }


@dataclass(frozen=True, slots=True)
class PoblacionEnRadio:
    """Poblacion dentro de un radio del epicentro, para el preliminar (RF-03).

    No es equivalente a una banda de intensidad y no debe presentarse como tal:
    aqui no hay modelo de sacudida, solo distancia. Un M6 superficial y un M6 a
    200 km de profundidad tienen el mismo circulo de 50 km y no se parecen en
    nada, y eso es exactamente lo que el reporte tiene que dejar claro mientras
    USGS no publique el ShakeMap.
    """

    radio_km: int
    pop: float

    def to_dict(self) -> dict[str, Any]:
        return {"radio_km": self.radio_km, "pop": self.pop}


@dataclass(frozen=True, slots=True)
class GroundFailureUSGS:
    """Lo que el propio USGS publica sobre falla de terreno. Referencia cruzada.

    No es una cifra de CENTINELA y no se presenta como tal. Va al lado de la
    nuestra porque **las dos responden preguntas distintas** y sin el contraste
    se leen como si respondieran la misma:

    * CENTINELA cuenta la poblacion de toda celda cuyo valor supera el umbral.
    * USGS pondera la poblacion de cada celda **por** el valor de esa celda.

    Para el Choco eso son 1,6 millones frente a ~460 mil en licuefaccion. El
    numero de USGS no es el nuestro corregido ni al reves: son dos cortes.

    Y resuelve el caso peor. En ese mismo evento el conteo por umbral de
    deslizamiento da **0** —ninguna celda llega al 0,10— junto a una alerta
    naranja de USGS con ~1.400 personas. Un "0" solo se lee como "no hay
    exposicion a deslizamiento", que en un M7,4 sobre la cordillera Occidental
    es falso. La guardia que ya existia protege el NaN de fuera de la huella del
    modelo; el cero por debajo del umbral es el que engana, y lo tapa esto.
    """

    #: ``green`` / ``yellow`` / ``orange`` / ``red``. Vacio si no hay producto.
    ls_alerta_usgs: str = ""
    #: Poblacion expuesta que publica USGS, ya ponderada. Cadena tal cual viene.
    ls_pop_usgs: str = ""
    lq_alerta_usgs: str = ""
    lq_pop_usgs: str = ""

    @property
    def vacio(self) -> bool:
        return not any((self.ls_alerta_usgs, self.lq_alerta_usgs))

    def alerta_viva(self, tipo: str) -> bool:
        """True si USGS declara algo distinto de verde para ese tipo."""
        alerta = self.ls_alerta_usgs if tipo == "ls" else self.lq_alerta_usgs
        return bool(alerta) and alerta.lower() != "green"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ls_alerta_usgs": self.ls_alerta_usgs,
            "ls_pop_usgs": self.ls_pop_usgs,
            "lq_alerta_usgs": self.lq_alerta_usgs,
            "lq_pop_usgs": self.lq_pop_usgs,
        }


@dataclass(frozen=True, slots=True)
class Report:
    """Reporte completo, serializable a ``report.json``."""

    event: Evento
    inputs: Inputs
    totales: Totales
    top_municipios: tuple[MunicipioTop, ...] = ()
    incertidumbre: Incertidumbre = field(default_factory=Incertidumbre)
    descargas: Descargas = field(default_factory=Descargas)
    #: True cuando aun no hay ShakeMap y el corte es por radios (RF-03).
    preliminar: bool = False
    #: Poblacion por radio. Solo se llena en un preliminar, y es lo que se
    #: publica **en lugar** de la tabla por intensidad: enseniar `pop_mmi7p: 0`
    #: en un reporte sin ShakeMap seria una cifra falsa y creible, que es el
    #: unico error que este sistema no puede permitirse.
    radios: tuple[PoblacionEnRadio, ...] = ()
    #: True cuando el evento se reconstruyo despues de ocurrir. Cambia lo que
    #: el reporte puede afirmar, asi que viaja hasta el visor: la poblacion
    #: puede ser de la epoca —GHS-POP publica de 1975 a 2030— pero las
    #: edificaciones, vias y equipamiento son los de hoy, porque OSM y
    #: Overture no guardan el pasado.
    backtest: bool = False
    #: Alertas del propio USGS para Ground Failure. Referencia cruzada.
    ground_failure_usgs: GroundFailureUSGS = field(default_factory=GroundFailureUSGS)
    #: Deltas frente a la version anterior del reporte (RF-04).
    changelog: tuple[str, ...] = ()
    #: Bajo que se publica esto y a quien hay que citar. Ver `Licencia`.
    licencia: Licencia = field(default_factory=Licencia)
    schema: str = REPORT_SCHEMA_ID
    generado_utc: str = field(default_factory=utcnow_iso)
    pipeline_version: str = PIPELINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event": self.event.to_dict(),
            "inputs": self.inputs.to_dict(),
            "preliminar": self.preliminar,
            "radios": [r.to_dict() for r in self.radios],
            "backtest": self.backtest,
            "totales": self.totales.to_dict(),
            "top_municipios": [m.to_dict() for m in self.top_municipios],
            "incertidumbre": self.incertidumbre.to_dict(),
            "ground_failure_usgs": self.ground_failure_usgs.to_dict(),
            "descargas": self.descargas.to_dict(),
            "changelog": list(self.changelog),
            "licencia": self.licencia.to_dict(),
            "disclaimers": list(DISCLAIMERS),
            "generado_utc": self.generado_utc,
            "pipeline_version": self.pipeline_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n"

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            event=Evento(**data["event"]),
            inputs=Inputs(**data["inputs"]),
            totales=Totales(**data["totales"]),
            radios=tuple(PoblacionEnRadio(**r) for r in data.get("radios", [])),
            top_municipios=tuple(MunicipioTop(**m) for m in data.get("top_municipios", [])),
            incertidumbre=Incertidumbre(
                pop_discrepancia_pct=data["incertidumbre"].get("pop_discrepancia_pct"),
                notas=tuple(data["incertidumbre"].get("notas", [])),
            ),
            ground_failure_usgs=GroundFailureUSGS(**data.get("ground_failure_usgs", {})),
            descargas=Descargas(**data.get("descargas", {})),
            preliminar=bool(data.get("preliminar", False)),
            backtest=bool(data.get("backtest", False)),
            changelog=tuple(data.get("changelog", [])),
            licencia=Licencia.from_dict(data.get("licencia") or {}),
            schema=str(data.get("schema", REPORT_SCHEMA_ID)),
            generado_utc=str(data.get("generado_utc", "")),
            pipeline_version=str(data.get("pipeline_version", "")),
        )


# --- El ranking municipal, en un solo sitio ---------------------------------


def banda_del_ranking(report: Report) -> int:
    """La banda MMI por la que se ordenan los municipios de este reporte.

    Delega en :attr:`Totales.banda_publicada`, que es donde vive la regla. Se
    conserva la funcion porque la llaman cuatro modulos con un `Report` en la
    mano; lo que no puede haber es una segunda regla.
    """
    return report.totales.banda_publicada


def municipios_del_ranking(report: Report) -> list[MunicipioTop]:
    """Los municipios expuestos, ordenados, **sin ceros**.

    VIVE AQUI PORQUE HAY DOS PLANTILLAS Y TENIAN DOS RANKINGS.

    El `report.md` y el `hilo.txt` del mismo evento nombraban municipios
    distintos: para Muisne, el reporte decia Portoviejo / Esmeraldas / Quinindé
    y el hilo decia Pedernales / Jama / Muisne. El arreglo —ordenar por la banda
    del reporte y descartar los ceros— aterrizo en `markdown.py` y no en
    `social.py`, que seguia leyendo `top_municipios` crudo.

    Dos plantillas que responden la misma pregunta no pueden calcularla cada
    una: la respuesta es del reporte, no de como se dibuje.

    Devuelve lista vacia cuando ningun municipio tiene poblacion expuesta, que
    es un caso real —los sismos mar adentro— y no un error. Quien la use tiene
    que decir por que no hay nadie, en vez de publicar una cabecera sin filas o
    nombrar a los tres primeros de una lista de ceros.
    """
    banda = banda_del_ranking(report)

    def cifra(m: MunicipioTop) -> float:
        return m.pop_mmi7p if banda == 7 else (m.pop_banda or m.pop_mmi7p)

    return sorted((m for m in report.top_municipios if cifra(m) > 0), key=cifra, reverse=True)


def poblacion_del_ranking(report: Report, municipio: MunicipioTop) -> float:
    """La cifra con la que ese municipio entra al ranking."""
    banda = banda_del_ranking(report)
    return municipio.pop_mmi7p if banda == 7 else (municipio.pop_banda or municipio.pop_mmi7p)
