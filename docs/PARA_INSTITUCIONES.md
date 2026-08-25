# CENTINELA para instituciones

*Documento de presentación. Estado al 25 de agosto de 2026.*

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
- **No mide daño.** Mide exposición, que es una pregunta distinta — ver §5.

## 3. Cobertura y estado

Diecinueve países de América Latina, con el mismo método y las mismas fuentes
para todos. Ningún país tiene un camino especial salvo Colombia, que usa el
Marco Geoestadístico Nacional del DANE en vez del COD-AB de OCHA porque el MGN
es la fuente de verdad del código DIVIPOLA.

| | |
|---|---|
| Activos de exposición publicados | 18 de 19 |
| Reportes emitidos de punta a punta | 3 (reconstrucciones históricas) |
| Tiempo de cálculo, evento completo | **27 segundos** |
| Latencia objetivo, sismo → reporte | p50 ≤ 60 min |

## 4. Qué tan buena es la cifra de población

El total nacional del activo se compara contra una referencia oficial. Se usa la
serie de World Population Prospects de Naciones Unidas por uniformidad regional;
un instituto nacional con censo reciente es mejor referencia para su país, y el
mantenedor de país puede sustituirla — Colombia ya usa las proyecciones del DANE.

| País | Medido | Referencia | Desvío |
|---|---:|---:|---:|
| México | 130.288.322 | 131.946.900 | −1,26 % |
| Chile | 19.690.592 | 19.859.921 | −0,85 % |
| Honduras | 10.915.014 | 11.005.850 | −0,83 % |
| Colombia | 52.620.466 | 53.000.000 (DANE) | −0,72 % |
| Guatemala | 18.622.441 | 18.687.881 | −0,35 % |
| Perú | 34.475.278 | 34.576.665 | −0,29 % |
| Paraguay | 7.019.481 | 7.013.078 | +0,09 % |
| Rep. Dominicana | 11.558.381 | 11.520.487 | +0,33 % |
| Panamá | 4.590.423 | 4.571.189 | +0,42 % |
| Argentina | 46.282.965 | 45.851.378 | +0,94 % |
| El Salvador | 6.442.983 | 6.365.503 | +1,22 % |
| Uruguay | 3.429.034 | 3.384.688 | +1,31 % |
| Ecuador | 18.571.110 | 18.289.896 | +1,54 % |
| Bolivia | 12.804.990 | 12.581.843 | +1,77 % |
| Cuba | 11.152.627 | 10.937.203 | +1,97 % |
| Costa Rica | 5.280.695 | 5.152.950 | +2,48 % |
| Nicaragua | 7.240.789 | 7.007.502 | +3,33 % |
| Venezuela | 29.924.657 | 28.516.896 | +4,94 % |

*Brasil pendiente de reconstrucción; su cifra se publicará medida, no
estimada.*

**Venezuela es el caso que conviene mirar de frente.** Su desvío de +4,94 % es
el mayor de la región y tiene una causa conocida: GHS-POP desagrega la ronda
censal de 2010 y no modela la emigración venezolana posterior. No es un fallo
del pipeline, es el límite de la fuente, y el manifest del país lo dice.

**La tolerancia de cada país se estrecha con lo medido, nunca se ensancha
sola.** Si un desvío se sale de su tolerancia, el sistema falla el build y pide
una decisión humana. Aflojar la alarma para que deje de sonar es lo que uno hace
con prisa, y es lo único que este proyecto no automatiza.

## 5. Exposición no es daño: la diferencia, medida

Es la confusión más costosa que puede provocar un reporte de este tipo, así que
está medida contra fuentes independientes.

El Microsoft AI for Good Lab publicó evaluaciones de daño por imagen satelital
para dos de los sismos que CENTINELA reconstruyó, usando además **las mismas
huellas de edificación de Overture**. Comparadas sobre las mismas celdas:

| | Cali, sismo del Chocó | La Guaira, sismo de Catia La Mar |
|---|---:|---:|
| Edificaciones evaluadas | 97.351 | 26.143 |
| **Con daño detectado** | **266 (0,27 %)** | **965 (3,69 %)** |
| Edificaciones en el activo | 107.252 | 35.611 |
| Celdas evaluadas fuera del activo | **0** | **0** |

Dos lecturas.

**La cobertura del activo es completa.** Ninguna de las 402 celdas que Microsoft
evaluó falta del activo, en dos países y dos sismos distintos. La lista de celdas
la puso otro, así que es la verificación de cobertura más exigente que se le ha
hecho.

**Y el factor de trece entre 0,27 % y 3,69 %** es la respuesta corta a por qué
una cifra de exposición no se puede leer como una cifra de daño: son dos zonas
del mismo rango de exposición con resultados que no se parecen.

## 6. Cómo consumirlo

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
la evaluación de escombros de UNEP/OCHA —excelente y CC BY-SA— se consume como
referencia externa y no entra en el activo.

## 7. Reproducibilidad

Cualquiera puede reconstruir el activo de un país desde fuentes públicas, sin
credenciales:

```
uv run centinela country COL
```

Cada país tiene un **manifest** que fija la versión exacta de cada fuente —nunca
«la última»— con su licencia y su fecha. Un reporte publicado dice contra qué
manifest se calculó.

## 8. Límites conocidos

Están publicados porque son parte de la cifra:

- **El mapeo de OpenStreetMap es desigual.** Donde falta, el conteo de
  edificaciones se queda corto. El reporte lo detecta comparando contra la
  superficie construida que ve el satélite y **lo dice en el propio reporte**
  cuando la diferencia pasa de 1,5 veces.
- **La detección depende del cron de GitHub.** Declarado cada 10 minutos, la
  mediana real medida sobre 22 corridas es de **45,7 minutos** y el peor caso
  73,3. Con un objetivo de 60 minutos extremo a extremo, la detección sola puede
  consumir el presupuesto. La salida documentada es un disparador externo.
- **Un reporte sin ShakeMap publica radios, no intensidades.** Y lo advierte:
  un radio no es una banda de intensidad.
- **Una reconstrucción histórica mezcla épocas.** La población puede ser de la
  época del sismo; las edificaciones y vías son las de hoy, porque
  OpenStreetMap no guarda el pasado. El reporte lo dice y esos eventos no
  cuentan para la latencia.

## 9. Qué se pide

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
<https://sforero77.github.io/CENTINELA/>
