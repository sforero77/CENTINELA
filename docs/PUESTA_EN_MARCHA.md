# Puesta en marcha

Los pasos que **solo puede hacer quien administra el repositorio**, en orden.
Cada uno dice como comprobar que quedó bien y como se ve si fallo.

Estado al empezar: el código funciona y esta probado, pero el sistema no ha
operado nunca solo. Estos cinco pasos son los que lo encienden.

---

## Paso 0 — Herramientas

Hace falta `gh`, el CLI de GitHub. En Windows:

```powershell
winget install --id GitHub.cli
gh auth login          # elige GitHub.com -> HTTPS -> autenticar por navegador
gh auth status         # tiene que decir "Logged in to github.com"
```

`make` **no existe en Windows** y no hace falta: cada objetivo del Makefile es
un comando de una línea, y en esta guía van escritos sueltos.

Comprueba que el entorno local corre:

```powershell
uv sync --python 3.12 --extra dev --extra geo --extra render
uv run pytest -m "not network" -q
```

Si `uv` se queda colgado bajando Python, aislalo: `uv python install 3.12`.

---

## Paso 1 — Fusionar el PR

`main` sigue en el commit inicial; todo el sistema vive en la rama.

```powershell
gh pr checks 1                 # CI en verde antes de nada
gh pr merge 1 --squash --delete-branch
```

**Como comprobarlo:** `git log --oneline origin/main -1` ya no dice
"Initial commit".

**Ojo:** los workflows programados **solo corren desde la rama por defecto**.
Hasta que esto pase, el trigger no se dispara aunque el cron exista.

---

## Paso 2 — Publicar el activo de exposición

`impact.yml` **falla a propósito** si no encuentra un Release `exposure-col-*`.
Es deliberado: operar sin activo produciría un reporte de ceros en vez de un
error, y un reporte de ceros durante un sismo es peor que ningún reporte.

### La vía recomendada: dejar que lo haga CI

```powershell
gh workflow run exposure_quarterly.yml -f iso3=COL
gh run watch
```

Ese workflow construye el activo **y publica el Release** en un solo paso. Es la
vía preferible por tres razones: corre en la red de GitHub (donde el paso lento
—leer Overture en remoto— son minutos y no horas), no depende de tu conexión, y
de paso **prueba el workflow trimestral** antes de que tenga que correr solo.

Requiere haber hecho el paso 1: los workflows solo corren desde la rama por
defecto.

**Como comprobarlo:** `gh release list` muestra el tag `exposure-col-<fecha>`, y
`gh release view <tag>` lista `exposure_h3.parquet` y `admin_lookup.parquet`.
Los **dos** hacen falta: sin `admin_lookup.parquet` el reporte sale con el
código DIVIPOLA en vez del nombre del municipio.

### La vía manual, si la necesitas

Solo si quieres el parquet en tu máquina o CI no esta disponible.

```powershell
uv run centinela country COL
```

Deja el archivo en `data/build/iso3=COL/layer=exposure/`.

**Aviso medido, no teórico:** el paso largo es leer Overture por red, y depende
por completo de tu enlace. En una prueba real a **95 KB/s** cada fichero de
edificaciones tardaba entre 4 y 18 minutos, y con once de edificaciones más los
de vías el build no termina en una tarde. Antes de lanzarlo conviene medir:

```powershell
curl -s -o NUL -w "%{speed_download} B/s`n" --max-time 60 -r 0-10485760 `
  "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com/release/2026-08-19.0/theme=buildings/type=building/part-00013-f54530cc-76c0-5ff4-8e72-6b2b9b844f62-c000.zstd.parquet"
```

Por debajo de ~1 MB/s, usa la vía de CI.

**Cuenta con ~1 GB de descarga, no con los "20 minutos" que decía la
documentación vieja.** Medido sobre la corrida real de Colombia — 89 archivos,
**1.053 MB**:

| Fuente | Descarga | Nota |
|---|---|---|
| WorldPop age-sex | **~570 MB** | 10 rasters de ~57 MB (4 bandas de 0-14, 6 de 65+) |
| COD-AB de OCHA | 117 MB | ZIP con los cuatro niveles administrativos |
| MGN del DANE | ~100 MB | extraidos por rango de un ZIP de 3,39 GB |
| GHS-POP | 93 MB | 9 teselas de 375 |
| GHS-BUILT-S | ~90 MB | 9 teselas, misma retícula que GHS-POP |
| HOTOSM + healthsites + OurAirports | ~80 MB | |
| Overture | **0** | se lee en remoto, no toca disco |

En el runner de GitHub Actions eso son minutos; en una conexión domestica la
descarga sola paso de media hora. El tiempo lo domina WorldPop.

Después de la descarga viene el cómputo. Tiempos medidos en la misma corrida:

| Paso | Tiempo | Nota |
|---|---|---|
| Crosswalk hex↔municipio | ~1 min | 1,5 M de celdas, 1.122 municipios |
| Agregación de ~29 rasters | ~2 min | 2-6 s por ráster |
| Capas de puntos (salud, educación) | segundos | |
| **Lectura remota de Overture** | **la mayor parte** | ~4 min por fichero, 11 de edificaciones más los de vías |

Overture no se descarga a disco, pero **si se lee por red**, y ese es el paso
largo. Cuenta con que un build completo pase de la hora en conexión domestica.

**Un aviso que costo un build entero:** `http_timeout` de DuckDB viene en 30
segundos y un fichero de Overture tarda minutos. El sistema ya lo sube a diez
minutos con cinco reintentos (`HTTPFS_SETTINGS`), pero si ves
`_duckdb.Error: Timeout was reached` en una red especialmente lenta, ahí esta
la perilla.

**Se puede cortar y reanudar.** Cada descarga salta lo que ya esta en disco, y
se escribe primero en un `.parcial` que solo se renombra al terminar: un corte
de red no deja un ráster a medias que la siguiente corrida daría por bueno.
Volver a lanzar el comando continua donde iba.

**Que esperar en el log**, en este orden: plan de construcción resuelto ->
GHS-POP descargado (9 teselas) -> bandas etarias descargadas -> recursos de HDX
-> geometría administrativa cargada (**1.122 municipios**) -> crosswalk
construido -> ficheros de Overture seleccionados (**11**) -> activo ensamblado
-> "todas las capas requeridas aportan al activo" -> activo escrito.

**Si falla**, el mensaje dice que hacer. Los dos casos previstos:

- `El activo no pasa los asserts de calidad: La capa 'X' no aporto nada` — una
  capa se construyó vacía. **No publiques ese activo**: es exactamente el cero
  silencioso que el assert existe para atrapar.
- `Ningun fichero de buildings del release ... toca la caja de COL` — el release
  de Overture caduco. Overture solo conserva **dos** releases, así que cada
  ~2 meses hay que actualizar el `vintage` en `data/manifests/COL.yaml`. La
  prueba nocturna avisa de esto antes de que te pase aquí.

Y publicalo a mano:

```powershell
cd data\build\iso3=COL\layer=exposure
gh release create exposure-col-20260823 exposure_h3.parquet admin_lookup.parquet `
  --title "Activo de exposicion COL - 2026-08-23" `
  --notes-file ..\..\..\..\data\manifests\COL.yaml
cd ..\..\..\..
```

Fija los digests de insumos que midió el build, que cierran la trazabilidad de
RNF-04 y hoy están vacios:

```powershell
centinela fijar-insumos COL
```

Lee el bloque `insumos` de `medicion.json` —el que se publica en el Release al
lado del parquet— y escribe cada `insumos_sha256` en su fuente del manifest, sin
tocar la prosa. A partir de ahí, un insumo republicado por un tercero detiene el
build en la descarga en vez de fallar dos horas después. No se anota a mano: con
194 fuentes en diecinueve países, copiar a mano no es tedioso, es que no ocurre.

### Se puede reanudar

Da igual por que vía: **una descarga cortada no se repite**. Las seis rutas
saltan lo que ya esta en disco y escriben primero en un `.parcial` que solo se
renombra al terminar, así que un ráster a medias nunca se da por bueno. Volver
a lanzar el comando continua donde iba.

---

## Paso 3 — Habilitar GitHub Pages

`Settings -> Pages -> Build and deployment -> Source: GitHub Actions`.

Es por interfaz; no hay comando. Sin esto el visor y `/status` no se publican y
`site.yml` falla en cada push a `main`.

**Como comprobarlo:**

```powershell
gh workflow run site.yml
gh run watch
```

Al terminar, `https://sforero77.github.io/CENTINELA/` muestra el visor y
`/status.html` la página de latencia.

---

## Paso 4 — Monitor externo

Este paso parece burocrático y es el que más protege el proyecto.

**GitHub desactiva los workflows programados tras 60 días sin actividad en el
repositorio.** Para un sistema que puede pasar meses sin un sismo mayor, esa
desactivacion silenciosa es el modo de falla más probable de todo el proyecto:
no falla nada, simplemente deja de mirar. `keepalive.yml` late el día 1 y el 15
para prevenirlo; el monitor externo avisa si aun así se cae.

1. Crea una cuenta gratuita en [healthchecks.io](https://healthchecks.io).
2. Nuevo check: nombre `centinela-trigger`, **period 30 min**, **grace 15 min**.
3. Copia su URL de ping.
4. Guardala como secreto:

```powershell
gh secret set HEALTHCHECK_URL --body "https://hc-ping.com/TU-UUID"
gh secret list
```

**Como comprobarlo:** lanza el trigger a mano (paso 5) y mira que el check pase
a "up" en healthchecks.io.

---

## Paso 5 — Probar el circuito completo

Antes de que llegue un sismo de verdad.

```powershell
gh workflow run trigger.yml -f dry_run=true    # P1 contra el feed vivo, sin escribir estado
gh workflow run simulacro.yml                  # §6.5: el circuito entero
gh run list --limit 5
```

**Como comprobarlo:** las dos corridas en verde. El simulacro imprime la
latencia de P1 en su resumen y corre los golden tests.

Para probar P2/P3 de punta a punta hace falta un evento con ShakeMap. Se puede
reprocesar el backtest del Chocó, que ya tiene su `event_state`:

```powershell
gh workflow run impact.yml -f usgs_id=us6000tjl2
```

Contestara `omitir: ya procesado en ShakeMap v7` — eso **es** el resultado
correcto: es la idempotencia de RF-02 funcionando. Que responda eso prueba que
el workflow encontró el Release, bajo el activo y llegó hasta la decisión.

---

## Después: lo que cierra Fase 0

Quedan dos requisitos de la puerta de salida, y los dos se cierran con el
**primer sismo M>=5.5 en LATAM**, que con la sismicidad normal de la región es
cuestión de días:

- un reporte real publicado end-to-end sin intervención;
- latencia medida y publicada (`site/status.json` hoy mide 0 eventos porque el
  único que hay esta marcado `backtest: true` y se excluye del p50/p95 a
  propósito).

Cuando ocurra, el único paso manual permitido en todo el sistema es dar clic
para publicar el hilo de `reports/<id>/hilo.txt`. El sistema lo genera pero
**no lo publica solo**.

---

## Tareas que no bloquean, cuando tengas tiempo

### Venezuela — cierra la aserción (b) de G2

El activo ya esta construido y publicado (`exposure-ven-20260824`). Lo que falta
es el **reporte** de los dos mainshocks del 24-jun-2026, que además estrena el
camino P2→P3 en CI: hasta ahora `impact.yml` nunca ha calculado nada, solo ha
devuelto `omitir: ya procesado`.

**Primero hay que reconstruir el activo**, porque el publicado se hizo con el
rescate que invadia al vecino y con el reparto que no veia los multipoligonos:

```powershell
gh workflow run exposure_quarterly.yml -f iso3=VEN
```

Después, los dos eventos:

```powershell
gh workflow run impact.yml -f usgs_id=us6000t7zp -f backtest=true
gh workflow run impact.yml -f usgs_id=us6000t7zc -f backtest=true
```

`-f backtest=true` reconstruye el `event_state` que P1 nunca creo —el feed que
vigila es el de la última hora, no un sismo de hace dos meses— y lo marca como
retrospectivo: su latencia de dos meses no entra en el p50/p95, y el reporte
lleva el aviso de que la población es de la época pero las edificaciones y las
vías son las de hoy.

Cuando los dos reportes estén en `reports/`, la prueba de G2 deja de saltarse
sola y pide congelar la cifra. Ella misma dice cual:

```
Hay reporte de us6000t7zp pero no cifra congelada.
Anota pop_mmi7p=... en POP_MMI7P_ESPERADO.
```

**Sobre la tolerancia de población:** esta en 5 % contra la ONU (28.516.896 para
2025) y es una expectativa, no una verificación. GHS-POP deriva de la ronda
censal de 2010 y no modela la emigración venezolana. Que el assert falle sería
un hallazgo publicable, no un bug: significaria que la cadena poblacional no
sirve igual en un país sin censo reciente, y el reporte tiene que decirlo.

(La codificacion de los topónimos estaba anotada como rota —«Falc?n» por
«Falcón»— y **no lo esta**. Verificado byte a byte sobre el parquet publicado:
`46 61 6c 63 c3 b3 6e`, UTF-8 correcto. Eran los interrogantes de la consola de
Windows.)

### Reconstruir los diecinueve y recalibrar

Toca cada vez que cambia algo del reparto o del rescate. **Corre en CI y no
gasta tus datos**; en local, cada país descarga cerca de un giga.

```powershell
foreach ($iso in "ARG","BOL","BRA","CHL","COL","CRI","CUB","DOM","ECU","GTM",
                 "HND","MEX","NIC","PAN","PER","PRY","SLV","URY","VEN") {
  gh workflow run exposure_quarterly.yml -f iso3=$iso
  Start-Sleep -Seconds 5
}
```

Cuando terminen, la medición de cada uno viaja en su Release —`medicion.json`,
un kilobyte— y de ahí sale la recalibracion:

```powershell
foreach ($iso in "arg","bol","bra","chl","col","cri","cub","dom","ecu","gtm",
                 "hnd","mex","nic","pan","per","pry","slv","ury","ven") {
  $tag = gh release list --limit 100 --json tagName -q '.[].tagName' |
         Select-String "^exposure-$iso-" | Sort-Object | Select-Object -Last 1
  gh release download $tag -p medicion.json --dir "med/$iso" --clobber
}
uv run centinela calibrar (Get-ChildItem med -Recurse -Filter medicion.json).FullName
```

Sin `--escribir` solo enseña lo que cambiaria. **Estrechar la tolerancia es
automático; ensancharla no**: si el desvío medido se sale de la vigente, el
comando lo dice y no toca nada, porque aflojar la alarma para que deje de sonar
es lo que uno hace con prisa y no debe automatizarse.

### T0.10 — la cifra exacta del DANE

`COL.yaml` usa 53.000.000, que es el redondeo de la nota técnica. El valor
exacto esta en el anexo en Excel de las proyecciones de población del DANE
(Geoportal -> Proyecciones CNPV-2018). Sustituirlo hace que el assert compare
contra un número y no contra un redondeo.
