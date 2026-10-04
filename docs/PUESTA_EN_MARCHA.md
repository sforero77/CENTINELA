# Puesta en marcha

Los pasos que **solo puede hacer quien administra el repositorio** para que
CENTINELA opere solo, en orden. Cada uno dice cómo comprobar que quedó bien.

**El sistema ya está operando**, así que esta guía no describe un pendiente: es
lo que hay que rehacer para encenderlo en un repositorio nuevo (un fork, una
organización distinta) o para volver a levantarlo si alguna pieza se apagó. Lo
que hay que vigilar con el sistema ya encendido está en
[`OPERACION.md`](OPERACION.md), y lo que garantiza y lo que no, en
[`GARANTIAS.md`](GARANTIAS.md).

*Reescrita el 3-oct-2026. La versión anterior era del 23-ago: su Paso 1
fusionaba un PR que llevaba semanas fusionado, publicaba a mano un solo país y
cerraba esperando el primer sismo real, que ya llegó y se procesó solo. La
auditoría del 5-sep lo marcó (hallazgo 150).*

---

## Paso 0: Herramientas y entorno local

Hacen falta `uv` y `gh`, el CLI de GitHub. En Windows:

```powershell
winget install --id GitHub.cli
gh auth login          # GitHub.com -> HTTPS -> autenticar por navegador
gh auth status         # tiene que decir "Logged in to github.com"
```

`make` **no existe en Windows** y no hace falta: cada objetivo del `Makefile`
es un comando de una línea, y en esta guía van escritos sueltos.

Comprueba que el entorno corre, con los mismos extras y la misma selección de
pruebas que `ci.yml`:

```powershell
uv sync --python 3.12 --extra dev --extra geo --extra render
uv run pytest -m "not network and not visor" -q
```

Las pruebas que abren el visor en un navegador van aparte, porque arrastran un
Chromium; las corre `visor.yml` cuando cambia `site/` o `reports/`:

```powershell
uv sync --python 3.12 --extra dev --extra visor
uv run playwright install chromium
uv run pytest -m visor -q
```

Si `uv` se queda colgado bajando Python, aíslalo: `uv python install 3.12`.

---

## Paso 1: Que los workflows corran en este repositorio

Dos condiciones, y las dos fallan en silencio.

**Los programados y los de `repository_dispatch` solo corren desde la rama por
defecto.** Todo lo que vigila tiene que estar en `main`.

**La mayoría de los workflows llevan una guarda de repositorio:**

```yaml
if: github.repository == 'sforero77/CENTINELA'
```

Existe para que un fork no publique reportes por su cuenta (RNF-07). En un
repositorio con otro nombre esos jobs **se saltan sin error**: el vigía, el
repaso, la reconstrucción de activos, el keepalive. Si este es el repositorio
nuevo que tiene que operar, cambia la guarda en todos:

```powershell
Select-String -Path .github\workflows\*.yml -Pattern "github.repository =="
```

La URL de `repository_dispatch` del Paso 5 y la de la página del Paso 2 llevan
también el nombre del repositorio.

**Cómo comprobarlo:** `gh workflow run keepalive.yml` y luego
`gh run list --workflow keepalive.yml --limit 1`. Tiene que salir en verde y
**con el job ejecutado**, no saltado. Es inocuo: solo commitea la fecha en
`.keepalive`.

---

## Paso 2: Habilitar GitHub Pages

`Settings -> Pages -> Build and deployment -> Source: GitHub Actions`.

Es por interfaz; no hay comando. Sin esto el visor y `/status` no se publican y
`site.yml` falla en cada push a `main` que toque `site/`, `reports/` o los
manifests.

```powershell
gh workflow run site.yml
gh run watch
```

**Cómo comprobarlo:** `https://sforero77.github.io/CENTINELA/` muestra el
visor y `/status.html` la página de estado. Después, `frescura.yml` vigila sola
que la página no se quede detrás del repositorio.

---

## Paso 3: Publicar los activos de exposición

`impact.yml` elige el país por el epicentro y baja el Release
`exposure-<iso3>-*` más reciente. **Si no hay ninguno, falla a propósito**:
operar sin activo produciría un reporte de ceros en vez de un error, y un
reporte de ceros durante un sismo es peor que ningún reporte.

Hay un activo por cada manifest de `data/manifests/`. Lo construye CI, que lo
publica como Release en el mismo paso:

```powershell
gh workflow run exposure_quarterly.yml -f iso3=COL
gh run watch
```

Para todos los países de golpe, cuando aún no hay ninguno publicado:

```powershell
Get-ChildItem data\manifests\*.yaml | ForEach-Object {
  gh workflow run exposure_quarterly.yml -f iso3=$($_.BaseName)
  Start-Sleep -Seconds 5
}
```

Con `iso3` vacío reconstruye **los que ya tienen Release**, así que en un
repositorio recién creado no construiría nada.

Mejor en CI que en local: corre en la red de GitHub, donde la lectura remota de
Overture es rápida, y no depende de tu conexión. El mismo workflow fija los
`insumos_sha256` que midió (`centinela fijar-insumos`), compara el activo con
el publicado antes de dar por buena la reconstrucción y recalcula
`site/cobertura.json`.

**Cómo comprobarlo:** `gh release list` muestra un `exposure-<iso3>-<fecha>`
por país, y `gh release view <tag>` lista `exposure_h3.parquet` y
`admin_lookup.parquet`. Los **dos** hacen falta: sin `admin_lookup.parquet` el
reporte sale con el código municipal en vez del nombre.

**Si falla**, el mensaje dice qué hacer; el caso que más importa es
`El activo no pasa los asserts de calidad: La capa 'X' no aporto nada`. **No
publiques ese activo a mano**: es el cero silencioso que el assert existe para
atrapar.

### La vía local, si la necesitas

```powershell
uv run centinela country COL
```

Deja el parquet en `data/build/iso3=COL/layer=exposure/`. El paso largo es leer
Overture por red, y en una conexión doméstica lenta no termina en una tarde.
Se puede cortar y reanudar: cada descarga salta lo que ya está en disco y
escribe primero en un `.parcial` que solo se renombra al terminar. Cómo
publicarlo a mano y con qué licencia, en
[`PUBLICAR_ACTIVO.md`](PUBLICAR_ACTIVO.md).

### Lo que ya no hay que hacer a mano

Mantenerlos al día. Los martes, `exposure_quarterly.yml` reconstruye los países
que van detrás del último release de Overture (`centinela overture-al-dia
--atrasados`) y commitea el manifest solo si el activo nuevo se publicó; el
primer día de cada trimestre los reconstruye todos. Overture conserva muy pocos
releases, y sin esto un país que no se reconstruye se queda sin camino de vuelta
a sus propias fuentes.

---

## Paso 4: Monitor externo

Este paso parece burocrático y es el que más protege el proyecto.

**GitHub desactiva los workflows programados tras 60 días sin actividad en el
repositorio.** Para un sistema que puede pasar meses sin un sismo mayor, esa
desactivación silenciosa es el modo de falla más probable: no falla nada,
simplemente deja de mirar. `keepalive.yml` late el día 1 y el 15 para
prevenirlo; el monitor externo avisa si aun así se para.

1. Crea una cuenta gratuita en [healthchecks.io](https://healthchecks.io).
2. Nuevo check `centinela-trigger`, con un periodo acorde a la cadencia con que
   se dispara el vigía (Paso 5) y algo de gracia.
3. Copia su URL de ping y guárdala como secreto:

```powershell
gh secret set HEALTHCHECK_URL --body "https://hc-ping.com/TU-UUID"
gh secret list
```

`trigger.yml` hace ping al terminar cada corrida en verde. Sin el secreto el
paso se salta, sin error: por eso hay que comprobarlo.

**Cómo comprobarlo:** lanza el vigía a mano (Paso 6) y mira que el check pase
a «up».

---

## Paso 5: Cron externo para el vigía

El cron de GitHub no da la cadencia que declara: reparte unos pocos turnos al
día **por repositorio**, y la detección sola se comía el presupuesto de
latencia entero. Está medido en [`OPERACION.md`](OPERACION.md) §1. La salida es
un servicio de cron fuera de GitHub (cron-job.org, un Cloudflare Worker, lo que
sea) que dispare `trigger.yml` por `repository_dispatch` cada pocos minutos:

```
POST https://api.github.com/repos/sforero77/CENTINELA/dispatches
Authorization: Bearer <token>
Accept: application/vnd.github+json

{"event_type": "vigilar"}
```

El token necesita permiso de **escritura sobre contenidos** del repositorio y
vive en el servicio externo, no en un secreto de este repositorio. El
`*/30` de `trigger.yml` se queda como respaldo: si el externo cae, el vigía
sigue corriendo, mal pero corriendo, y el monitor del Paso 4 avisa de que los
latidos se espaciaron.

**Cómo comprobarlo:** `gh run list --workflow trigger.yml --limit 5` muestra
corridas con evento `repository_dispatch` a la cadencia configurada.

---

## Paso 6: Probar el circuito completo

Antes de que llegue un sismo de verdad.

```powershell
gh workflow run trigger.yml -f dry_run=true    # P1 contra el feed vivo, sin escribir estado
gh workflow run simulacro.yml                  # §6.5: el circuito entero, sin publicar
gh run list --limit 5
```

**Cómo comprobarlo:** las dos corridas en verde. El simulacro pasa P1 en seco,
corre los golden y ensaya P2→P3 con un ShakeMap real sobre el activo de
Colombia, y comprueba al final que no tocó nada publicado. Corre solo el día 5
de cada mes; si falla, abre una incidencia.

Para probar que `impact.yml` encuentra los activos, reprocesa un evento que ya
tenga reporte, por ejemplo el del Chocó:

```powershell
gh workflow run impact.yml -f usgs_id=us6000tjl2
```

Contestará `omitir: ya procesado en ShakeMap v<N>`, y ese **es** el resultado
correcto: la idempotencia de RF-02. Que responda eso prueba que el workflow
encontró el Release, bajó el activo y llegó hasta la decisión.

**Ojo:** `impact.yml` **commitea y empuja** a la rama desde la que se despacha.
No lo lances con `--ref` sobre una rama que no quieras ver escrita.

---

## Lo único manual con el sistema encendido

Publicar el hilo de `reports/<id>/hilo.txt` en redes. El sistema lo genera y
**no lo publica solo**, a propósito. Todo lo demás —detectar, calcular,
publicar, re-emitir cuando USGS saca un ShakeMap nuevo, refrescar los activos—
corre sin intervención, y lo que hay que revisar y cada cuánto está en
[`OPERACION.md`](OPERACION.md).

---

## Tareas que no bloquean, cuando tengas tiempo

### Recalibrar las tolerancias

Cada reconstrucción publica su medición (`medicion.json`) en el Release, al
lado del parquet. De ahí sale la recalibración:

```powershell
foreach ($f in Get-ChildItem data\manifests\*.yaml) {
  $iso = $f.BaseName.ToLower()
  $tag = gh release list --limit 200 --json tagName -q '.[].tagName' |
         Select-String "^exposure-$iso-" | Sort-Object | Select-Object -Last 1
  gh release download $tag -p medicion.json --dir "med/$iso" --clobber
}
uv run centinela calibrar (Get-ChildItem med -Recurse -Filter medicion.json).FullName
```

Sin `--escribir` solo enseña lo que cambiaría. **Estrechar la tolerancia es
automático; ensancharla no**: si el desvío medido se sale de la vigente, el
comando lo dice y no toca nada, porque aflojar la alarma para que deje de sonar
es lo que uno hace con prisa y no debe automatizarse.

### T0.10: la cifra exacta del DANE

`COL.yaml` usa el redondeo de la nota técnica como población de referencia. El
valor exacto está en el anexo en Excel de las proyecciones de población del
DANE (Geoportal -> Proyecciones CNPV-2018). Sustituirlo hace que el assert
compare contra un número y no contra un redondeo.
