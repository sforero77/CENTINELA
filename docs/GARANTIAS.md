# Qué garantiza este sistema, y qué no

Escrito el 27-ago-2026. Separa **lo probado** de **lo supuesto**, porque en un
sistema de vigilancia la diferencia entre las dos cosas es el sistema.

Cada afirmación de aquí abajo dice cómo se comprobó. Si no lo dice, no está
comprobada.

---

## El flujo

```
USGS feed  →  vigía (cron)  →  filtro M5,5  →  despacha P2
                                                   ↓
             ShakeMap + activo del país  →  reporte  →  commit
                                                   ↓
                           republicar visor  →  GitHub Pages
```

En paralelo, cada seis horas: FIRMS → focos H3 → cruce con exposición →
`incendios.json`. Y cada media hora el vigía publica su latido, que es lo que
demuestra que sigue vivo.

---

## Lo que sí está garantizado

### No se pierde un sismo

El vigía lee `4.5_day`, una ventana de **24 horas**. Aunque el cron tarde once
—el peor caso medido—, el evento sigue en el feed cuando llegue.

Esa ventana garantiza que no se pierde un sismo, **no** que se sigan viendo sus
revisiones: pasadas 24 h el evento se cae del feed. De eso se ocupa
`repaso.yml`, que pregunta por los eventos de los últimos 90 días por su
identificador. Hizo falta porque la mediana hasta la última revisión de un
ShakeMap son 63 días, y el de Venezuela llegó a v15 dos meses después.

Solo se perdería con una parada de más de un día, y de eso avisa el monitor
externo en treinta minutos.

**Cómo se sabe:** el feed de respaldo está en `constants.py` desde el diseño, y
`test_enrutado_latam` cubre el caso. La parada larga la detectó de verdad el
healthcheck el 27-ago.

### Lo que está en el repositorio llega a la página

Un push hecho con `GITHUB_TOKEN` no dispara otros workflows, así que cada
workflow que commitea en `site/` o `reports/` lanza `site.yml` explícitamente.

**Cómo se sabe:** se demostró solo el 27-ago a las 03:17 — el vigía commiteó su
latido y republicó el visor sin intervención. `test_el_visor_se_republica`
exige ese paso a todo el que empuje, derivando las rutas del propio `site.yml`.

### La página sirve lo que el repositorio tiene

`frescura` hace **tres** preguntas distintas cada tres horas:

1. ¿Cuánto hace que la página quedó atrás? (`status`, `observados`, `incendios`)
2. ¿Están los mismos reportes en el índice publicado?
3. ¿Cuánto hace que cada fichero no se regenera?

La tercera es la que faltaba: un fichero congelado **no desfasa** —repositorio y
página igual de viejos— y pasaba las dos primeras sin protestar.

### El camino de P2, de punta a punta

`impact.yml` corre entero: calcula el impacto contra el activo del país, escribe
los artefactos, commitea y **republica el visor**.

**Cómo se sabe:** ensayo deliberado el 27-ago con `us6000tjl2`, recalculando un
reporte ya publicado contra el activo reconstruido ese día. Los cinco pasos en
verde, commit `3d59a0b`, y el visor republicado.

Tres cosas que ese ensayo dejó demostradas de paso:

- **Recalcular es determinista.** Las cifras salieron idénticas a las de la
  reconstrucción manual, con un activo distinto por debajo.
- **El changelog de RF-04 no inventa cambios.** Detectó que nada se movía y no
  anunció nada.
- **El desfase de versión es visible.** El reporte declaró `col-v0.5` con
  `COL.yaml` ya en `v0.6`, porque el activo se construyó antes del bump:
  exactamente como estaba escrito. Desde que P2 lee `src_manifest` del propio
  parquet, esa declaración sale del activo consumido y no de un argumento del
  CLI, así que ya no puede desviarse por copia.

Lo que sigue sin ejercitarse es la **cadena completa desde el feed**: que el
vigía detecte un sismo nuevo y despache P2 solo. Eso necesita un M≥5,5 real.

### Una cifra publicada tiene un reporte detrás

`event_latencies` exige que exista `reports/<id>/report.json` antes de contar la
latencia de un evento.

**Por qué existe:** el 26-ago la página sirvió `us7000abcd` —inexistente en
USGS— con una latencia de 20,0 minutos, contado como el único evento real
publicado.

---

## Lo que NO está garantizado

### La latencia

    objetivo del sistema      p50 ≤ 60 min, origen → reporte publicado
    cadencia del vigía sola   p50 95 min · p90 358 · peor 663
                              (27-ago-2026, con el cron de GitHub como
                              único disparador)

**Con el cron de GitHub solo, la detección se comía más que el presupuesto
entero.** Medido el 27-ago: el repositorio recibe unos pocos turnos de cron **al
día**, repartidos entre los cinco workflows programados. El vigía bajó de `*/10`
a `*/30` para dejar de acaparar una cola que no podía ganar.

La ruta que lo arregla —un cron externo que dispare `repository_dispatch`— está
hecha desde el 31-ago-2026 y despacha cada cinco minutos; el cron de GitHub
quedó de respaldo. Los primeros latidos con el disparador nuevo dan **p50 5,0
min · p90 5,0 · peor 5,0**, o sea la cadencia declarada, exactamente. Son pocos
—la serie se reinició el 1-sep-2026 al re-emitir el catálogo entero— así que
valen como orden de magnitud y no como percentil estable, y la cifra de arriba
se conserva por lo que documenta: lo que daba la cola de GitHub sola.

**La latencia de punta a punta ya está medida, y no se cumple.** Los dos
primeros sismos en vivo, el 2-sep-2026, dan **p50 185,7 min · p95 238,0 · peor
243,8** — tres veces el objetivo. `/status` lo publica.

Dónde se va el tiempo, con los dos únicos casos que hay:

    us7000tdmp   deteccion  21,9 min   total  127,6 min
    us7000tdms   deteccion  24,5 min   total  243,8 min

La detección ya no es el cuello de botella: son veintitantos minutos, y de esos
la mayor parte es lo que tarda USGS en listar el evento en su feed. **Lo que se
come el presupuesto es esperar el ShakeMap**, que es de USGS y no se controla
desde aquí. El primero suma además las veinte corridas que P2 rechazó antes de
distinguir «no alcanza celdas» de «activo equivocado».

Con dos eventos no hay percentil: son dos medidas, no una distribución. Pero ya
son suficientes para decir que **el objetivo de 60 minutos no depende de esta
infraestructura** — depende de cuándo publique USGS. Mientras no se decida
medirlo contra el ShakeMap en vez de contra el origen, el objetivo se declara
aquí como lo que es: no cumplido.

### La corrección de una cifra publicada

Los asserts de §6.4 y el contraste con evaluación de daño externa cubren lo
comprobable. Pero **si P2 publica una cifra equivocada y plausible, nadie avisa**.
Esa es la razón de que el proyecto entero se apoye en no publicar lo que no midió.

---

## El punto débil estructural

**Los vigilantes dependen de la misma cola que vigilan.**

`frescura.yml` pide un turno cada tres horas. El 27-ago corrió **dos veces** —a
las 00:49 y a las 14:15—, así que su detección real fue de trece horas, no de
tres. `incendios.yml` pidió cuatro turnos y no corrió **ninguno**.

El único vigilante independiente es el **monitor externo** (healthchecks.io), y
es el único que ha avisado de verdad. Pero solo vigila una cosa: que el vigía
siga latiendo.

Dicho claro: **si el cron se para del todo, hay alarma. Si algo se rompe de
forma más sutil, la detección depende de la misma cola que se rompió.**

---

## Qué pasa cuando falla cada cosa

| Fallo | Quién avisa | En cuánto | ¿Probado? |
|---|---|---|---|
| El vigía deja de correr | monitor externo | 30 min | **sí**, 27-ago |
| El vigía corre y falla | monitor externo (silencio) | 30 min | no |
| Se publica y no se republica | `frescura` → issue | 3 h nominal, ~13 h real | no |
| Un fichero se congela | `frescura` → issue | igual | no |
| P2 falla en un sismo | issue automático | inmediato | no |
| P2 corre entero y publica | — | — | **sí**, ensayo 27-ago |
| P2 publica una cifra mala | **nadie** | — | — |
| Un tercero cambia el dato | el build falla | al reconstruir | **sí**, ARG 27-ago |

---

## Antes de llamarlo producción

1. ~~Ejercitar P2 de punta a punta.~~ **Hecho el 27-ago.** Queda el tramo que
   no se puede ensayar: que el vigía despache solo ante un sismo nuevo.
2. **Sacar `frescura` de la cola de GitHub** — encadenarla al vigía, o al
   monitor externo. Un vigilante que depende de lo que vigila no es un
   vigilante.
3. **Decidir sobre la latencia:** arreglarla con reloj externo, o publicar el
   objetivo real. Mantener «p50 ≤ 60 min» con una infraestructura que da 95 es
   la clase de cifra que este proyecto no se permite en ningún otro sitio.
