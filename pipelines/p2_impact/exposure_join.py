"""Join intensidad x exposicion en DuckDB (D3).

DuckDB con las extensiones ``spatial`` y ``h3`` hace todo el trabajo pesado
dentro del runner de GitHub Actions, leyendo GeoParquet particionado
directamente. Sin servidor, sin credenciales, sin costo (RNF-01).

Las consultas viven aqui como constantes con marcadores nombrados, no armadas
por concatenacion: son parte del contrato revisable del sistema.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Extensiones que P0 y P2 requieren cargadas.
DUCKDB_EXTENSIONS: tuple[str, ...] = ("spatial", "h3")

#: Asserts de calidad de P2 (§6.4). Cada entrada es
#: ``(nombre, consulta que debe devolver 0 filas, bloqueante)``.
#:
#: **Van contra las tablas del corte, no contra el activo entero.** Preguntan
#: por las cifras que se estan a punto de publicar, que es lo unico que este
#: reporte afirma; el activo lo vigila `validate_layer_coverage` en P0, en su
#: propio momento y con sus propias reglas.
#:
#: Y no todos pesan igual, asi que el tercer campo lo dice:
#:
#: * **Bloqueante** significa que las cifras serian falsas. Un reporte que no
#:   sale es un problema; uno que publica poblacion negativa es una mentira, y
#:   ademas creible.
#: * **No bloqueante** significa que la cifra es correcta y esta incompleta.
#:   Se publica como nota de incertidumbre, porque tumbar un reporte durante un
#:   terremoto por un municipio sin nombre es peor que decir que falta.
QUALITY_ASSERTIONS: tuple[tuple[str, str, bool], ...] = (
    (
        "pop_negativa",
        "SELECT h3_08 FROM impact_h3 WHERE pop_total < 0",
        True,
    ),
    (
        "pop_nula",
        "SELECT h3_08 FROM impact_h3 WHERE pop_total IS NULL OR adm2_id IS NULL",
        True,
    ),
    (
        # Un municipio que llega a `impact_adm2` y no esta en `admin_lookup`
        # **desaparece del reporte sin una palabra**: `build_report` cruza las
        # dos con un JOIN interno para sacar el nombre. Puede ser el mas
        # expuesto del evento. Los totales nacionales salen de `impact_h3` y
        # siguen siendo correctos: lo que falta es la fila, no la cifra.
        "crosswalk_incompleto",
        "SELECT adm2_id FROM impact_adm2 WHERE mmi_max >= 6 "
        "AND adm2_id NOT IN (SELECT adm2_id FROM admin_lookup)",
        False,
    ),
)

#: Las banderas de §6.4 —las condiciones que se publican en vez de fallar— se
#: calculan al construir el activo, en `p0_exposure.build.SQL_FLAGS`, y viajan
#: en la columna `flags_calidad` de cada celda. Aqui habia una segunda copia,
#: identica y sin llamador: dos definiciones de la misma regla que solo pueden
#: divergir. La que manda es la de P0.


@dataclass(frozen=True, slots=True)
class JoinInputs:
    """Insumos del join de impacto."""

    usgs_id: str
    shakemap_version: int
    #: Ruta o glob del activo de exposicion (GeoParquet particionado).
    exposure_glob: str
    #: ``h3_08 -> MmiCell`` del polyfill de contornos.
    mmi_cells: dict[int, Any]
    #: ``h3_08 -> GroundFailureCell``. Vacio si el producto no existe (G3).
    gf_cells: dict[int, Any]


def connect(database: Path | None = None) -> Any:
    """Abre una conexion DuckDB con las extensiones cargadas.

    ``database=None`` abre en memoria, que es el modo normal: el estado
    persistente son los parquet, no un archivo de base de datos.
    """
    import duckdb  # import diferido: el trigger no debe pagar este costo

    con = duckdb.connect(str(database) if database else ":memory:")
    # Sin sitio donde volcar, una consulta que no cabe en RAM no se ralentiza:
    # muere. Le paso a Chile: el rescate de sus 59.179 celdas costeras agoto los
    # 12,4 GB del runner y tumbo un build de cuarenta minutos. Con
    # `temp_directory` DuckDB derrama a disco y termina, mas lento pero termina.
    #
    # Es una red de seguridad, no una excusa: la consulta que la provoco tambien
    # se arreglo. Pero un pipeline que corre desatendido sobre diecinueve paises
    # de tamanos muy distintos no puede depender de que ninguno se pase.
    con.execute(f"SET temp_directory = '{tempfile.gettempdir()}'")
    for extension in DUCKDB_EXTENSIONS:
        origen = " FROM community" if extension == "h3" else ""
        con.execute(f"INSTALL {extension}{origen}")
        con.execute(f"LOAD {extension}")
    return con


def register_cells(con: Any, inputs: JoinInputs) -> None:
    """Materializa las celdas de intensidad y de falla de terreno.

    Se pasan por Arrow y no por ``VALUES``: un ShakeMap de M7 alcanza cientos de
    miles de celdas, y armar esa sentencia como texto es lento y fragil.
    """
    import pyarrow as pa

    celdas = list(inputs.mmi_cells.values())
    con.register(
        "mmi_arrow",
        pa.table(
            {
                "h3_08": pa.array([c.h3_08 for c in celdas], pa.uint64()),
                "mmi_mean": pa.array([c.mmi_mean for c in celdas], pa.float64()),
                "mmi_max": pa.array([c.mmi_max for c in celdas], pa.float64()),
            }
        ),
    )
    con.execute("CREATE OR REPLACE TABLE mmi_cells AS SELECT * FROM mmi_arrow")
    con.unregister("mmi_arrow")

    gf = list(inputs.gf_cells.values())
    con.register(
        "gf_arrow",
        pa.table(
            {
                "h3_08": pa.array([c.h3_08 for c in gf], pa.uint64()),
                "ls_prob": pa.array([c.ls_prob for c in gf], pa.float64()),
                "lq_prob": pa.array([c.lq_prob for c in gf], pa.float64()),
            }
        ),
    )
    con.execute("CREATE OR REPLACE TABLE gf_cells AS SELECT * FROM gf_arrow")
    con.unregister("gf_arrow")


class QualityAssertionError(Exception):
    """Un assert bloqueante de §6.4 fallo: las cifras del corte no son fiables."""


@dataclass(frozen=True, slots=True)
class QualityReport:
    """Resultado de correr los asserts de §6.4 sobre un corte."""

    #: Fallos bloqueantes. Con uno solo, el reporte no debe publicarse.
    bloqueantes: tuple[str, ...] = ()
    #: Fallos que se publican como nota de incertidumbre en vez de detener.
    avisos: tuple[str, ...] = ()

    @property
    def limpio(self) -> bool:
        return not self.bloqueantes and not self.avisos

    def raise_if_blocking(self) -> None:
        """Detiene la publicacion si algun assert bloqueante fallo."""
        if self.bloqueantes:
            raise QualityAssertionError(
                "Los asserts de calidad de §6.4 fallaron sobre el corte de este "
                f"evento: {'; '.join(self.bloqueantes)}. Publicar estas cifras "
                f"seria publicar numeros que el propio sistema sabe que estan mal."
            )


def check_quality(con: Any) -> QualityReport:
    """Corre los asserts de §6.4 sobre las tablas del corte.

    La espec pide que estos asserts corran **en P0 y en P2**. En P2 no corrian:
    vivian en una funcion sin llamador, invocada desde otra funcion sin
    llamador cuya docstring afirmaba que si. Un assert que no se ejecuta es
    peor que no tenerlo, porque ocupa el sitio de la vigilancia que no existe.

    Returns:
        El parte de calidad. Quien llama decide: `raise_if_blocking` para no
        publicar cifras falsas, y `avisos` para las notas del reporte.
    """
    bloqueantes: list[str] = []
    avisos: list[str] = []

    for nombre, consulta, bloquea in QUALITY_ASSERTIONS:
        destino = bloqueantes if bloquea else avisos
        try:
            filas = con.execute(consulta).fetchall()
        except Exception as exc:
            # No poder evaluar un assert no es lo mismo que aprobarlo. Se
            # reporta con la severidad del assert que no se pudo correr.
            destino.append(f"{nombre}: no se pudo evaluar ({exc})")
            continue
        if filas:
            destino.append(f"{nombre}: {len(filas)} filas incumplen (ej. {filas[:3]})")

    return QualityReport(bloqueantes=tuple(bloqueantes), avisos=tuple(avisos))
