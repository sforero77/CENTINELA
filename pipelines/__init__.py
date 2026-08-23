"""CENTINELA — pipelines de exposicion sismica automatizada para LATAM.

Sub-paquetes (ver espec tecnica v0.9, §4.1):

* ``p0_exposure`` — construccion trimestral del activo ``exposure_h3`` por pais.
* ``p1_trigger``  — vigilancia del feed USGS y creacion del ``event_state``.
* ``p2_impact``   — cruce ShakeMap/Ground Failure x exposicion -> ``impact_*``.
* ``p3_report``   — ``report.json`` y sus derivados (md/png/csv/parquet/pmtiles).
* ``p4_brigada``  — brigada de imagen satelital (Fase 2, activacion por evento).
"""

__version__ = "0.1.0"

# Version del pipeline que se estampa en cada artefacto publicado (RNF-04).
PIPELINE_VERSION = __version__
