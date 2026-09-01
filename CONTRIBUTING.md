# Como contribuir

Gracias por venir. Este proyecto existe porque a la región le falto capacidad
propia dos veces en dos meses. Toda ayuda cuenta.

## Arranque rápido

```bash
git clone https://github.com/sforero77/CENTINELA
cd centinela
make setup     # instala todo con uv (Python 3.12)
make check     # lint + mypy + pruebas: debe pasar antes de abrir PR
```

No hace falta activar entornos a mano ni tener credenciales de nada. Si algo
del arranque no funciona en tu máquina, eso **es** un bug: abre un issue.

## Antes de abrir un PR

```bash
make format     # ruff --fix + formato
make check      # lo mismo que corre CI
```

- Las pruebas no tocan la red. La única excepción esta marcada `network` y solo
  la corre el workflow nocturno.
- Si cambias una cifra publicada, actualiza los golden tests **en el mismo PR**
  y explica por que la cifra cambio.
- Si agregas una fuente de datos, agregala también al manifest del país y al
  registro de licencias. `make manifests` te dirá si algo no cuadra.

## Formas de ayudar

### Mantenedor por país

El rol más útil del proyecto. **El manifest de tu país ya existe**: los 19 de
LATAM hispanohablante más Brasil están escritos, con sus fuentes verificadas una
por una y su caja envolvente medida. Lo que falta no se puede hacer desde fuera
del país:

1. **Construir y medir.** `uv run centinela country <ISO3>` (~1 GB de descarga).
   El manifest lleva una `tolerancia_pct` **provisional del 5 %** que no es una
   medición: al terminar, anota el desvío real como `medido_ghs_pop` y ajusta la
   tolerancia, explicando el cambio en el PR. Colombia, que si esta medida, usa
   1 %.
2. **Validar los topónimos y su codificacion.** Salen impresos en el reporte y
   en el hilo. En Venezuela el COD-AB los devuelve mal codificados («Falc?n» por
   «Falcón») y hay que resolverlo antes de publicar nada.
3. **Decidir si hay una referencia de población mejor que la ONU.** Todos los
   manifests nuevos usan World Population Prospects por uniformidad regional,
   pero un instituto nacional con censo reciente es mejor para su propio país
   — Colombia usa el DANE. Cambiarla es tuya.
4. **Sustituir fuentes nacionales donde mejoren a las regionales**, si existen
   con coordenadas y con licencia compatible. Ojo con las dos trampas ya
   documentadas: un registro sin coordenadas no se puede asignar a una celda, y
   CC BY-SA no se puede mezclar con la ODbL de Overture.
5. **Revisar el primer reporte real de tu país** y reportar lo que este mal.

No requiere ser programador. Requiere conocer los datos de tu país.

### Verificaciones pendientes

`ESPECIFICACION.md` §8 lista las tareas de verificación abiertas (T0.4 a T3.1).
Cada una es un PR pequeño y autocontenido. Son un buen primer aporte.

### Brigada de imagen

Se activa por evento. Si te interesa el etiquetado de daño en imagen satelital,
abre un issue y te avisamos en la proxima activacion.

## Estilo

Lo esencial cabe aquí; el detalle, con el caso real que justifica cada regla,
esta en [`docs/CLEAN_CODE.md`](docs/CLEAN_CODE.md).

- **Código en inglés, dominio en español.** Los nombres de columnas, estados y
  campos del reporte están en español porque son parte del producto; el resto
  sigue las convenciones de Python.
- `ruff` y `mypy --strict` no son negociables. Si un tipo no cuadra, hablalo en
  el PR antes de silenciarlo con `# type: ignore`.
- Los comentarios explican **por que**, no **que**. El código ya dice que hace.
  Aquí la vara es más alta que la habitual: casi todos los bugs de este
  repositorio producen **cifras plausibles**, así que un comentario justifica
  una decisión con la evidencia que la motivo, o sobra.
- **Si escribes una función, conectala.** Es el fallo que este proyecto más
  veces ha tenido que cazar —el reporte preliminar, el epicentro del mapa, tres
  capas del activo, los asserts de §6.4— y todas las veces la función estaba
  probada. `tests/unit/test_funciones_conectadas.py` falla si una función
  pública se queda sin llamador.
- **Código muerto se borra**, no se comenta ni se guarda por si acaso. Git se
  acuerda. Conservar algo sin llamador exige declararlo con su motivo, y «esta
  probada» no es un motivo.

## Lo que no aceptamos

- Nada que requiera un servidor vivo en el camino crítico.
- Nada que requiera credenciales privadas para reproducir un resultado.
- Nada que mezcle fuentes no comerciales en el núcleo redistribuible.
- Nada que acerque el sistema a emitir alertas, estimar víctimas o dictaminar
  daño. Esas son las líneas rojas de `DISCLAIMER.md`.

## Código de conducta

Trata a quien contribuye como tratarias a alguien que se ofrece a ayudar
gratis en medio de una emergencia. Porque es exactamente eso.
