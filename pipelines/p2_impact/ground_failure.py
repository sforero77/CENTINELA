"""Ground Failure -> probabilidad de deslizamiento y licuefaccion por celda.

Diferenciador clave del sistema (§2.1): USGS publica rasters de probabilidad de
deslizamiento y licuefaccion por evento, versionados como el ShakeMap, y casi
nadie los integra. Cuando el producto no existe para un evento, el reporte
omite la seccion con nota explicita y **no falla** (golden test G3).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..common.constants import GROUND_FAILURE_HIGH_PROB
from ..common.geo import ensure_bundled_proj


@dataclass(frozen=True, slots=True)
class GroundFailureCell:
    """Probabilidades de falla de terreno en una celda."""

    h3_08: int
    #: Probabilidad de deslizamiento del modelo de Jessee (2018), 0-1.
    ls_prob: float
    #: **Cobertura areal** por licuefaccion del modelo de Zhu (2017), 0-1: la
    #: fraccion del area de la celda que se espera cubierta. No es una
    #: probabilidad, aunque el nombre de la columna lo sugiera —se conserva
    #: porque es el nombre del contrato publicado.
    lq_prob: float

    @property
    def sobre_umbral_ls(self) -> bool:
        """Por encima del corte de conteo. **No** es "probabilidad alta": USGS
        no publica esa categoria a este valor. Ver `GROUND_FAILURE_HIGH_PROB`."""
        return self.ls_prob >= GROUND_FAILURE_HIGH_PROB

    @property
    def sobre_umbral_lq(self) -> bool:
        """Idem, sobre cobertura areal y no sobre probabilidad."""
        return self.lq_prob >= GROUND_FAILURE_HIGH_PROB


#: Nombres de contenido de los modelos vigentes dentro del producto USGS.
#: El producto trae varios modelos por tipo; estos son los que USGS presenta
#: como preferidos y los unicos que el reporte consume.
LANDSLIDE_MODEL = "jessee_2018_model.tif"
LIQUEFACTION_MODEL = "zhu_2017_general_model.tif"

#: Alternativas historicas, por si un evento antiguo no trae el modelo vigente.
LANDSLIDE_FALLBACKS = ("nowicki_2014_global_model.tif", "godt_2008_model.tif")
LIQUEFACTION_FALLBACKS = ("zhu_2015_model.tif",)


def sample_rasters(
    landslide_tif: Path | None,
    liquefaction_tif: Path | None,
    cells: list[int],
) -> dict[int, GroundFailureCell]:
    """Muestrea los rasters de Ground Failure en el centroide de cada celda.

    Contrato, verificado contra los rasters reales del evento de Chocó:

    * Ambos productos llegan en **EPSG:4326**, y eso ya no se supone: se
      comprueba antes de muestrear. Las resoluciones difieren entre modelos
      (0,00208° el de deslizamiento, 0,00417° el de licuefaccion), asi que se
      muestrean por separado y no se asume una grilla comun. El valor llega ya
      en [0, 1] con ``nodata = NaN``.
    * El muestreo se hace en el **centroide** de la celda. A r8 (~0,7 km²)
      frente a los ~230 m del raster de deslizamiento, muestrear el centro es
      suficiente y evita leer el raster entero.
    * Un raster ausente (``None``) produce 0.0 en su columna. El reporte
      distingue "probabilidad cero" de "producto no publicado" por la version
      del producto, no por el valor — por eso 0.0 aqui es seguro (golden G3).
    * ``NaN`` fuera de la huella del modelo se convierte a 0.0: el modelo no
      afirma nada ahi, y propagar NaN contaminaria las sumas municipales.

    Requiere el extra ``[geo]``.
    """
    if not cells:
        return {}

    # Antes de tocar GDAL/PROJ: un `PROJ_LIB` del sistema tapa la base que
    # traen las ruedas y ningun CRS se resuelve. Ver `ensure_bundled_proj`.
    ensure_bundled_proj()

    import h3
    import numpy as np
    import rasterio

    puntos = [h3.cell_to_latlng(h3.int_to_str(c)) for c in cells]
    coords = [(lng, lat) for lat, lng in puntos]

    def muestrear(path: Path | None) -> np.ndarray:
        vacio = np.zeros(len(cells), dtype="float64")
        if path is None:
            return vacio
        with rasterio.open(path) as src:
            # EL CRS SE COMPRUEBA, NO SE SUPONE.
            #
            # `coords` son lon/lat. Si el raster no llega en geograficas, cada
            # punto cae fuera de su extension, `sample` devuelve nodata para
            # todos, `nan_to_num` lo convierte en 0.0 y se publica "0 personas
            # en zona de licuefaccion" con la misma cara que una cifra real.
            # No hay assert de cobertura para Ground Failure que lo cace
            # despues, asi que la comprobacion tiene que estar aqui.
            #
            # El contrato esta verificado sobre los modelos vigentes (jessee
            # 2018, zhu 2017) del evento del Choco. Los fallbacks historicos
            # —godt_2008, nowicki_2014, zhu_2015— no se han verificado uno a
            # uno: si alguno llega en otro CRS, este error lo dice en vez de
            # publicar ceros.
            if src.crs is None or not src.crs.is_geographic:
                raise ValueError(
                    f"El raster de Ground Failure {path.name} no llega en coordenadas "
                    f"geograficas (crs={src.crs}). Se muestrea con lon/lat: en otro CRS "
                    "cada punto cae fuera de la extension, el muestreo devuelve nodata "
                    "y el reporte publicaria 0 personas expuestas como si fuera una "
                    "medida. Hay que reproyectar los puntos antes de muestrear."
                )
            valores = np.array([v[0] for v in src.sample(coords, indexes=1)], dtype="float64")
        # NaN = fuera de la huella del modelo. No es "probabilidad desconocida"
        # que haya que propagar: es "el modelo no cubre esto".
        limpio: np.ndarray = np.nan_to_num(valores, nan=0.0, posinf=0.0, neginf=0.0)
        return limpio

    ls = muestrear(landslide_tif)
    lq = muestrear(liquefaction_tif)

    return {
        c: GroundFailureCell(h3_08=c, ls_prob=float(ls[i]), lq_prob=float(lq[i]))
        for i, c in enumerate(cells)
    }
