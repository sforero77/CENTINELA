"""P5: focos de calor activos cruzados con la exposicion.

El activo de exposicion es **agnostico a la amenaza**: cada celda H3 sabe cuanta
poblacion, edificio, via, hospital y colegio contiene, y desde la Fase 1 tambien
que hay debajo — bosque, pastizal, cultivo. Lo unico sismico del sistema es el
campo de amenaza que se cruza contra el. Cambia el campo y la maquinaria sirve
igual.

**Lo que este pipeline NO hace, y conviene leerlo antes que nada:**

- **No estima area quemada.** El propio FIRMS lo desaconseja explicitamente: son
  detecciones puntuales con muestreo espacial y temporal irregular. La
  afirmacion honesta es "hubo detecciones en esta celda", nunca "ardieron N
  hectareas".
- **No hay un ShakeMap del fuego.** El MMI es un campo de intensidad modelado y
  publicado por un tercero, con bandas estandar. Aqui hay puntos y potencia
  radiativa. Estimar "intensidad a distancia" exigiria modelar dispersion, y
  este proyecto no modela: cruza amenaza publicada con exposicion medida.
- **No agrupa detecciones en incendios.** Un sismo ocurre en un instante y tiene
  identidad estable; un incendio arde dias, crece, se parte y se fusiona. Darle
  identidad persistente entre dias es un problema de verdad y no se finge
  resuelto contando puntos.

Lo que si hace: decir cuanta gente y cuanta infraestructura hay en las celdas
donde los satelites vieron fuego en las ultimas horas, y sobre que tipo de
suelo. Eso es poco comparado con un reporte sismico, y es cierto.
"""

from __future__ import annotations

from .firms import Foco, feed_url, fetch_focos, parse_csv

__all__ = ["Foco", "feed_url", "fetch_focos", "parse_csv"]
