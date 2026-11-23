# CENTINELA para instituciones

*Documento de presentación. Estado al 1 de septiembre de 2026.*

CENTINELA publica, de forma automática y en abierto, **cuánta población e
infraestructura quedó dentro de cada franja de intensidad** después de un sismo
en América Latina. No sustituye a nadie: es un insumo para quien ya hace el
trabajo.

Este documento existe para que quien lo evalúe pueda hacerlo con cifras y no con
adjetivos. Todo lo que afirma está medido, y dice dónde está la medida.

---

## 1. Qué hace, en una frase

Cuando el USGS publica el ShakeMap de un sismo, CENTINELA cruza sus contornos de
intensidad con una malla hexagonal de ~0,74 km² que ya tiene precargada
población, edificaciones, vías y equipamiento de salud y educación, y publica un
reporte por municipio.

**El reporte sale sin que nadie intervenga**, en markdown legible desde un móvil,
en JSON para máquinas y en CSV con etiquetas HXL para los flujos humanitarios.

## 2. Qué **no** hace

Esto importa más que lo anterior, y está impreso en cada reporte:

- **No es una alerta temprana.** Llega después del sismo, no antes.
- **No estima víctimas.** Ni heridos, ni fallecidos, ni damnificados.
- **No dictamina habitabilidad.** No dice si un edificio se puede ocupar.
- **No mide daño.** Mide exposición, que es una pregunta distinta; ver §6.

## 3. Cobertura y estado

Diecinueve países de América Latina, con el mismo método y las mismas fuentes
para todos. Ningún país tiene un camino especial salvo Colombia, que usa el
Marco Geoestadístico Nacional del DANE en vez del COD-AB de OCHA porque el MGN
es la fuente de verdad del código DIVIPOLA.

<!-- cifra:tabla_estado -->

| | |
|---|---|
| Activos de exposición publicados | **19 de 19** |
| Reportes emitidos de punta a punta | **24**, en 12 países |
| De ellos, disparados en vivo | **6**; los otros 18 son reconstrucciones |
| Personas ya en la malla hexagonal | **649,8 millones** |
| Latencia objetivo, sismo → reporte | p50 ≤ 60 min · lo medido, en `/status` |

<!-- /cifra -->

**El primero en vivo llegó el 2-sep-2026, y no salió como debía.** Un M5,6 a 71 km
al OSO de Puerto Madero, México. El vigía lo detectó y despachó en minutos (esa
mitad de la cadena funcionó a la primera) y P2 lo rechazó veinte veces seguidas:
trataba «el ShakeMap no alcanza ninguna celda» como error incluso con el país
bien enrutado, cuando lo que pasaba es que la sacudida se quedó mar adentro. El
reporte salió cuando se arregló esa distinción. Horas después llegó el segundo,
un M5,9 en la dorsal del Pacífico Oriental (`us7000tdms`).

**La latencia medida está en [`/status`](https://centinela.geoailatam.terrnova.com/status.html),
y aquí no se copia a mano.** Se mueve con cada evento (ya caducó dos veces en un
día) y ahora mismo está **por encima del objetivo**, porque lo que cronometró no
fue la cadena en régimen sino lo que tardó en arreglarse un fallo que sólo podía
aparecer con un sismo real. La primera medida limpia la dará el siguiente evento.

Los otros <!-- cifra:reconstrucciones_en_letras -->dieciocho<!-- /cifra --> reportes siguen siendo reconstrucciones históricas: prueban
que el cálculo funciona sobre eventos reales de USGS, no que la cadena en vivo
esté ejercitada. Ahora está ejercitada <!-- cifra:en_vivo_veces -->seis veces<!-- /cifra -->, y enseñó algo.

## 4. Qué tan buena es la cifra de población

El total nacional del activo se compara contra una referencia oficial. Se usa la
serie de World Population Prospects de Naciones Unidas por uniformidad regional;
un instituto nacional con censo reciente es mejor referencia para su país, y el
mantenedor de país puede sustituirla: Colombia ya usa las proyecciones del DANE.

<!-- cifra:tabla_poblacion -->

| País | Medido | Referencia | Desvío |
|---|---:|---:|---:|
| México | 130.288.322 | 131.946.900 | −1,26 % |
| Chile | 19.690.592 | 19.859.921 | −0,85 % |
| Honduras | 10.915.014 | 11.005.850 | −0,83 % |
| Colombia | 52.620.429 | 53.000.000 (DANE) | −0,72 % |
| Guatemala | 18.622.441 | 18.687.881 | −0,35 % |
| Perú | 34.475.278 | 34.576.665 | −0,29 % |
| Paraguay | 7.019.484 | 7.013.078 | +0,09 % |
| República Dominicana | 11.558.381 | 11.520.487 | +0,33 % |
| Panamá | 4.590.423 | 4.571.189 | +0,42 % |
| Argentina | 46.284.585 | 45.851.378 | +0,94 % |
| El Salvador | 6.442.983 | 6.365.503 | +1,22 % |
| Uruguay | 3.429.034 | 3.384.688 | +1,31 % |
| Ecuador | 18.571.110 | 18.289.896 | +1,54 % |
| Bolivia | 12.804.991 | 12.581.843 | +1,77 % |
| Cuba | 11.152.627 | 10.937.203 | +1,97 % |
| Costa Rica | 5.280.695 | 5.152.950 | +2,48 % |
| Brasil | 218.881.568 | 212.812.405 | +2,85 % |
| Nicaragua | 7.240.789 | 7.007.502 | +3,33 % |
| Venezuela | 29.924.658 | 28.516.896 | +4,94 % |

<!-- /cifra -->

*Esta tabla y las cifras de §3 no se copian a mano: las reescribe
`centinela cifras` desde los manifests y el catálogo de reportes, y el workflow
`datos.yml` lo hace solo después de cada publicación.*

*Brasil entró en esta tabla el 28-ago-2026, cuando se cerró el fallo que lo
declaraba con `poblacion_medida: 0` (219 millones de personas de menos en una
cifra pública) con el activo en el Release desde el 26. Su casilla de reportes
sigue vacía por otra razón: sus doce sismos M≥5,5 desde 2000 están todos entre
534 y 645 km de profundidad, y el ShakeMap de USGS no modela intensidad de
MMI 5 o más en superficie para ninguno. Paraguay y Uruguay no tienen reporte
porque no registran un solo sismo M≥5,5 desde el año 2000;
`tests/integration/test_silencio_de_paises_live.py` lo vuelve a comprobar
contra USGS.*

**Venezuela es el caso que conviene mirar de frente.** Su desvío de +4,94 % es
el mayor de la región y tiene una causa conocida: GHS-POP desagrega la ronda
censal de 2010 y no modela la emigración venezolana posterior. No es un fallo
del pipeline, es el límite de la fuente, y el manifest del país lo dice.

**La tolerancia de cada país se estrecha con lo medido, nunca se ensancha
sola.** Si un desvío se sale de su tolerancia, el sistema falla el build y pide
una decisión humana. Aflojar la alarma para que deje de sonar es lo que uno hace
con prisa, y es lo único que este proyecto no automatiza.

## 5. Contraste con PAGER, en las mismas bandas

Es la primera objeción que recibe un sistema como este, y conviene resolverla
antes de que la haga nadie: ¿cuadra con lo que publica el USGS?

**Desde `report/2.0` (21-nov-2026) las dos usan la misma convención.** PAGER
agrupa por MMI *redondeado* —su fila «VII» es todo lo que cae entre 6,5 y 7,49— y
CENTINELA cuenta por clases con ese mismo corte: VI desde 5,5, VII desde 6,5,
VIII desde 7,5. Acumulando las filas de PAGER de arriba abajo, cada cifra de
CENTINELA tiene su pareja exacta.

Hasta la versión 1.0 no era así: CENTINELA usaba bandas *literales* (MMI≥7 era
7,0 o más) y su cifra del Chocó en MMI≥7 —2.434.710— quedaba a casi un factor de
tres de la fila de PAGER, 7.089.614. No subcontaba: contaba otra cosa, y la única
comparación posible era comprobar que cada cifra cayera *entre* dos filas de
PAGER. Con el corte del USGS esa explicación sobra, y la misma cifra pasa a ser
6.389.281.

> **Las dos columnas no son del mismo ShakeMap, y no se puede arreglar.** El
> reporte se re-emitió con el **v10** y el **v11**, y
> **USGS no ha vuelto a publicar PAGER desde el v9.** Comprobado contra ComCat el
> 21-sep-2026 y otra vez el 27-oct-2026: el producto `losspager` tiene diez
> entregas y la última es del 7-sep 22:58 UTC, la que acompañó al ShakeMap v9. La
> tabla de abajo compara, por tanto, **CENTINELA v11 contra PAGER v9**, y los
> encabezados lo dicen. La procedencia, con la URL exacta del producto, está en
> `pager_exposures.origen.json`.

| Clase de intensidad | PAGER (ShakeMap v9) | CENTINELA (ShakeMap v11) | Diferencia |
|---|---:|---:|---:|
| VI o más (MMI ≥ 5,5) | 9.329.268 | **7.948.990** | −15 % |
| VII o más (MMI ≥ 6,5) | 7.089.614 | **6.389.281** | −10 % |
| VIII o más (MMI ≥ 7,5) | 1.647.927 | **888.980** | −46 % |

**CENTINELA queda por debajo en las tres, y por tres razones conocidas.** Cada
celda lleva la isolínea que contiene su centro, así que su intensidad es una cota
inferior: nunca sobreestima. PAGER usa LandScan y CENTINELA GHS-POP, dos modelos
de población distintos. Y las dos columnas no leen el mismo ShakeMap: el v10
retiró el contorno de MMI 7 de una parte de Cali y el v11 lo redibujó. La clase
VIII es la más sensible a las dos primeras: es la franja más estrecha, y medio
grado de diferencia en el borde mueve una fracción grande de su población.

Lo que el sistema afirma de su propio muestreo lo imprime cada reporte: «el sesgo
que introduce no está medido: puede quedarse corto o pasarse». Es el primer sitio
donde el método de contornos se ve desde fuera del proyecto.
`tests/unit/test_contraste_con_pager.py` fija el estado exacto —clase contra
clase, y de qué versión es cada columna— para que un cambio en cualquiera de
los dos lados salte.

## 6. Exposición no es daño: la diferencia, y cómo se comprueba

Es la confusión más costosa que puede provocar un reporte de este tipo, así que
el proyecto no la explica: la contrasta contra fuentes independientes.

El Microsoft AI for Good Lab publicó en HDX evaluaciones de daño por imagen
satelital para dos de los sismos que CENTINELA reconstruyó (Cali, del sismo de
San José del Palmar, y La Guaira, del de Catia La Mar), las dos **CC BY** y las
dos sobre **las mismas huellas de edificación de Overture** que usa este
proyecto. Eso hace la comparación interpretable y no anecdótica.

El contraste corre sobre las **mismas celdas H3**, no sobre áreas dibujadas a
ojo: cada edificación evaluada se lleva a su celda r8 por el centroide, igual
que hace el activo. Así la única diferencia entre las dos cifras es lo que cada
uno metió en la celda, no cómo se recortó el mapa. Dos cosas salen de ahí:

1. **Cuántas celdas evaluadas faltan del activo.** Cualquier valor mayor que
   cero es un hueco de cobertura, y el comando sale con código 7 —uno propio,
   que no se confunde con un error de uso— para que un workflow pueda pararse. Es la verificación de cobertura más exigente que se
   le puede hacer al activo, porque la lista de celdas la pone otro.
2. **Qué fracción de lo expuesto resultó dañada**, en cada zona. Es la respuesta
   corta a por qué una cifra de exposición no se lee como una de daño.

Se reproduce así, con el activo del país descargado del Release:

```
uv run centinela contraste <url-del-vector-de-dano> \
  --exposure 'data/exposure/COL/*.parquet' \
  --crs EPSG:32618 --etiqueta "Microsoft AI for Good · Cali" \
  --salida data/contrastes/cali.json
```

**Esta sección no publica todavía la tabla de resultados.** La publicó hasta el
1-sep-2026 (con cifras de edificaciones evaluadas, dañadas y celdas fuera del
activo) y ninguna de ellas apuntaba a un fichero del repositorio: el comando
imprimía su resultado y lo perdía. En un documento que abre diciendo que todo lo
que afirma está medido y dice dónde está la medida, eso no se sostiene. El
comando ya persiste su salida (`--salida`); la tabla vuelve cuando el
`data/contrastes/*.json` de cada zona esté en el repositorio y se pueda enlazar
fila por fila.

## 7. Cómo consumirlo

Todo es estático y público. No hay API que se caiga, ni llave que pedir, ni
cuota que agotar.

| Artefacto | Para qué |
|---|---|
| `report.md` | Leer en un móvil con 3G. Menos de 500 KB con el mapa. |
| `report.json` | Integrar. Esquema versionado y validado. |
| `adm2.csv` | Cruzar. Etiquetas **HXL** en la segunda fila, coordenadas incluidas. |
| `exposure_h3.parquet` | Reanalizar. El activo completo del país, por celda. |
| Visor web | Mirar. Mapa por municipio, sin backend. |

**Licencias.** El código es Apache-2.0. Los datos del núcleo, CC BY 4.0, con la
atribución de cada fuente propagada: GHS-POP y GHS-BUILT-S del JRC de la Comisión
Europea, WorldPop, Overture Maps sobre OpenStreetMap (ODbL), COD-AB de OCHA,
ShakeMap y Ground Failure del USGS (dominio público).

El proyecto **no mezcla cubos de licencia**: ODbL, CC BY y CC BY-SA se mantienen
separados y hay una comprobación automática que lo impide. Por eso, por ejemplo,
la evaluación de escombros de UNEP/OCHA, excelente y CC BY-SA, se consume como
referencia externa y no entra en el activo.

## 8. Reproducibilidad

Cualquiera puede reconstruir el activo de un país desde fuentes públicas, sin
credenciales:

```
uv run centinela country COL
```

Cada país tiene un **manifest** que fija la versión exacta de cada fuente (nunca
«la última») con su licencia y su fecha. Un reporte publicado dice contra qué
manifest se calculó.

## 9. Límites conocidos

Están publicados porque son parte de la cifra:

- **El mapeo de OpenStreetMap es desigual.** Donde falta, el conteo de
  edificaciones se queda corto. El reporte lo detecta comparando contra la
  superficie construida que ve el satélite y **lo dice en el propio reporte**
  cuando la diferencia pasa de 1,5 veces.
- **La detección depende del cron de GitHub.** El vigía declara `*/30` (bajó
  de `*/10` el 27-ago-2026, cuando se midió que GitHub reparte turnos por
  repositorio y no por workflow) y entrega mucho menos: sobre 23 latidos entre
  el 25 y el 30 de agosto, **p50 157 min, p90 462 y peor caso 766 (12,8 h)**.
  Con un objetivo de 60 minutos extremo a extremo, **la detección sola se come
  el presupuesto entero**. La salida documentada es un disparador externo, ya
  declarado en el workflow y pendiente de conectar.
- **Un reporte sin ShakeMap publica radios, no intensidades.** Y lo advierte:
  un radio no es una banda de intensidad.
- **Una reconstrucción histórica mezcla épocas.** La población puede ser de la
  época del sismo; las edificaciones y vías son las de hoy, porque
  OpenStreetMap no guarda el pasado. El reporte lo dice y esos eventos no
  cuentan para la latencia.

## 10. Qué se pide

Nada obligatorio. Lo que más valor añadiría, en orden:

1. **Un mantenedor por país** que valide topónimos y decida si su instituto
   nacional debe sustituir a la ONU como referencia de población.
2. **Que se señale dónde la cifra no cuadra** con lo que la institución sabe.
   Cada desacuerdo señalado es un fallo encontrado; hoy el sistema conoce sus
   límites porque se han ido midiendo así.
3. **Que se use como insumo**, no como autoridad. La cifra oficial la da quien
   tiene el mandato.

---

*Código, datos y el registro completo de verificaciones:*
<https://github.com/sforero77/CENTINELA> · *Reportes:*
<https://centinela.geoailatam.terrnova.com/>

---

## La evidencia de que la pieza del medio falta

No es un argumento del proyecto: es lo que hicieron **a mano** otros, sin ella.

El sitrep de **OIM/DTM del 17 de agosto de 2026** fusionó manualmente los
productos de daño de **Copernicus EMS** con las huellas de edificación de
**Microsoft AI for Good** sobre la base de **Overture**: exactamente las tres
piezas que este activo ya trae unidas, ensambladas de urgencia durante una
emergencia y para un solo evento.

Que un equipo con recursos tuviera que hacer ese join a mano, una semana después
del sismo, dice mejor que cualquier justificación por qué el activo tiene que
estar construido **antes**.
