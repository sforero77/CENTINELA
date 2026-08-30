# Agregaciones

Cómo se convierte cada fuente en una columna de la celda. Es la parte del
sistema donde un error no se ve: una agregación mal hecha produce una cifra
perfectamente plausible.

## Las cuatro familias

```mermaid
flowchart TB
  subgraph R["Ráster continuo → celda"]
    R1["GHS-POP · GHS-BUILT<br/>WorldPop"] --> R2["suma de píxeles<br/>100 m que caen<br/>en la celda"]
  end
  subgraph RC["Ráster categórico → celda"]
    RC1["ESA WorldCover"] --> RC2["% de píxeles<br/><b>clasificados</b><br/>por clase"]
  end
  subgraph P["Puntos → celda"]
    P1["HOTOSM salud/edu<br/>OurAirports"] --> P2["conteo de puntos<br/>por celda"]
  end
  subgraph L["Líneas y polígonos → celda"]
    L1["Overture vías"] --> L2["longitud <b>recortada</b><br/>por celda, en<br/>proyección equiárea"]
    L3["Overture edificios"] --> L4["conteo y área<br/>por celda del<br/><b>centroide</b>"]
  end

  style RC2 fill:#f4f1e8,stroke:#8a8578
  style L2 fill:#f4f1e8,stroke:#8a8578
```

## Las decisiones que no son obvias

### Vías: recortadas, no asignadas al centroide

Una carretera de 40 km cruza muchas celdas. Asignarla entera a la celda de su
centroide daría 40 km en una celda y 0 en las vecinas. Se **recorta el segmento
por celda** y se mide cada trozo en proyección equiárea local.

> Esta cifra estuvo mal en el README por un factor de seis, porque se copió a
> mano y el activo se reconstruyó después. Hoy `test_cifras_del_readme.py`
> falla si la tabla del README se separa de `report.json`.

### Edificaciones: por centroide, y se asume

Un edificio pertenece a la celda de su centroide, aunque cruce el borde. A
5,2 km² por celda, el error es despreciable frente al de la propia cobertura
de OSM.

### Cobertura del suelo: el porcentaje es sobre lo clasificado

```mermaid
flowchart LR
  C["Una celda costera"] --> P1["40 % píxeles<br/>de tierra"]
  C --> P2["60 % píxeles<br/>de mar"]
  P1 --> CALC["los porcentajes<br/>se calculan<br/><b>sobre el 40 %</b>"]
  P2 -.->|"el mar<br/>no cuenta"| CALC
  CALC --> PX["<b>lulc_px = 40</b><br/>dice cuánta evidencia<br/>hay detrás"]

  style PX fill:#e8f0ea,stroke:#0f5636
```

En la costa media celda es mar, y el mar no es una clase de cobertura. Los
porcentajes van sobre los píxeles **clasificados**, y `lulc_px` publica cuántos
eran: *"una celda con nueve píxeles y otra con ciento cuarenta no merecen la
misma confianza"*.

### Estructura etaria: la banda central es el residuo

```
pop_0_14   ← conteo de WorldPop
pop_65p    ← conteo de WorldPop
pop_15_64  ← pop_total − pop_0_14 − pop_65p
```

`pop_total` viene de GHS-POP y los extremos de WorldPop: son dos modelos
distintos. La banda central, al ser el residuo, **absorbe toda la diferencia
entre ambos**. Es una decisión declarada, no un descuido, y la banda de
discrepancia publicada la acota.

### Población: suma dasimétrica

No se reparte población por área: se suman los píxeles de 100 m de GHS-POP,
que ya está desagregado dasimétricamente usando volumen construido. La celda
hereda la desagregación de la fuente en vez de inventar la suya.

## De la celda al reporte

```mermaid
flowchart TB
  CELDAS[("celdas del corte<br/>impact_h3")] --> B6["Σ donde mmi ≥ 6"]
  CELDAS --> B7["Σ donde mmi ≥ 7"]
  CELDAS --> B8["Σ donde mmi ≥ 8"]
  CELDAS --> ADM["GROUP BY adm2_id<br/>→ top 15 municipios"]
  B7 --> EDAD["desglose etario<br/><i>sólo para MMI ≥ 7</i>"]

  style EDAD fill:#f4f1e8,stroke:#8a8578
```

**Las bandas son acumulativas**: "personas en MMI ≥ 7" incluye a las de MMI 8.
El desglose por edad se publica **sólo para MMI ≥ 7**
(`MMI_BAND_AGE_BREAKDOWN = 7`): más abajo la incertidumbre del modelo etario
sería mayor que la señal.

### Ground Failure

Se muestrea el ráster de probabilidad por celda. Una probabilidad ≥ **0,10**
cuenta como "alta" para el conteo de población expuesta. `NaN` significa fuera
de la huella del modelo — no cero, no "sin riesgo".

## La banda de discrepancia

El sistema publica dos poblaciones de la misma celda: `pop_total` (GHS-POP) y
`pop_alt_worldpop` (WorldPop). La segunda **nunca es la cifra principal**: su
único trabajo es acotar cuánto podrían diferir dos modelos razonables sobre el
mismo territorio, y esa banda se publica en `incertidumbre`.

Es el reconocimiento explícito de que la cifra tiene un intervalo, en un
producto cuyo riesgo principal es que alguien lea un número redondo como si
fuera un censo.

## Ocho de diecinueve eventos no llegan a MMI ≥ 7

Correr el catálogo regional entero enseñó algo que ninguna prueba sintética
habría encontrado: **ocho de los diecinueve eventos no alcanzan MMI ≥ 7 sobre
población**. Son los profundos y los de mar adentro, que en esta región son la
mitad. Tehuantepec 2017 —M8,2, 98 muertos— tiene su máximo sobre población
mexicana en **MMI 6,5**.

Hasta que se corrieron, el producto daba por supuesto que MMI ≥ 7 era *la*
banda y publicaba para esos ocho un titular de "0 personas" con una tabla de
municipios ordenada alfabéticamente. Ahora **se titula con la banda que el
evento alcanzó de verdad**.
