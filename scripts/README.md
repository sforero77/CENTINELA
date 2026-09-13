# scripts/

Utilidades que se corren a mano, no en el camino crítico.

| Script | Qué hace |
|---|---|
| `freeze_event.py` | Congela los productos de un evento real como fixture golden (T0.2) |
| `simulacro_sismo.py` | Ensaya P2→P3 con un ShakeMap real mudado sobre población |
| `validar_diagramas.py` | Compila cada diagrama Mermaid de los `.md`; lo corre `ci.yml` en cada push y PR |

Estos scripts si pueden tocar la red y pueden depender de herramientas que no
están en CI (`libcomcat`). Nada de lo que hacen bloquea un reporte.

## `delta_contornos_vs_grid.py`

Mide cuánto se separa el método de contornos del campo continuo de `grid.xml`,
replicando el cómputo real de P2 por los dos caminos sobre el mismo activo.

```
uv run --extra dev python scripts/delta_contornos_vs_grid.py us6000tjl2 COL
```

Descarga ~50 MB por evento, así que vive aquí y no en la suite: es una medición
que se corre cuando se cuestiona el método, no en cada commit.

## `simulacro_sismo.py`

El único hueco que `docs/GARANTIAS.md` declaraba era un evento en vivo que
alcanzara población: los dos que P1 despachó solo se quedaron mar adentro y sus
tablas salieron en ceros.

Esto lo ensaya sin esperar un sismo. Coge el ShakeMap **real** de la fixture
golden del Chocó y lo **traslada** al punto que se le indique, corrigiendo las
longitudes por `cos(lat)` para no deformar la huella. Después corre `run_impact`
de verdad —servidor HTTP local, `HttpFetcher`, `download_products`— contra el
activo de exposición real del país.

```bash
uv run --extra geo --extra render python scripts/simulacro_sismo.py \
    --sobre 3.4516,-76.5320 --iso3 COL --exigir-poblacion 1000000
```

**Escribe en `work/simulacro/<id>/`, nunca en `events/` ni en `reports/`.** El
script se niega a arrancar si `--salida` apunta dentro o por encima de
cualquiera de los dos, y deja un `LEEME-SIMULACRO.md` en la carpeta. El segundo
cierre es `tests/unit/test_ningun_simulacro_publicado.py`, que vigila el árbol
versionado y no depende de que nadie use el script.

Por qué tanto candado: el paquete que sale es **idéntico en formato** a uno
real, `hilo.txt` incluido, que está escrito para pegarse en una red social y
empieza con «Sismo M7,4». Fuera de esa carpeta eso es desinformación sobre una
emergencia, y no se recoge.

Lo que **no** ensaya: P1 (el evento no está en el feed de USGS) ni la física
(trasladar un ShakeMap no es modelarlo).

## `validar_diagramas.py`

Compila con `mermaid-cli` cada bloque Mermaid de los `.md` versionados, y da
`fichero:línea` de cada uno que no compile.

```bash
python3 scripts/validar_diagramas.py            # compila todos: red y Chromium
python3 scripts/validar_diagramas.py --listar   # dice dónde está cada uno, sin red
```

Un diagrama roto no rompe nada que la suite vea: GitHub lo publica como un
recuadro de error justo donde tenía que estar la explicación. Y leerlo no basta:
el 12-sep-2026 el `timeline` de `docs/acciones/por-reloj.md` se leía bien y no
compilaba, porque las horas `05:37` chocaban con los dos puntos que Mermaid usa
como separador.

Es el único de esta carpeta que corre en CI: el job `diagramas` de `ci.yml`, en
cada push y en cada PR. No está en la suite porque necesita Node y Chromium, y
la suite corre sin red. Sale con 2, y no con 0, si no encuentra ningún diagrama
o no compila ninguno: no poder mirar no es estar en verde.
