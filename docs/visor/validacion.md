# Validar el visor

43 pruebas de Playwright que abren el visor en un Chromium de verdad.

```bash
uv run --extra dev --extra visor pytest tests/visor -m visor
```

Corren en CI (`visor.yml`) en cada push y PR.

## Qué comprueban que ninguna prueba unitaria puede

```mermaid
flowchart TB
  subgraph unit["Pruebas unitarias — 953"]
    U1["¿el cálculo es correcto?"]
    U2["¿el JSON valida?"]
    U3["¿la función está conectada?"]
  end
  subgraph visor["Pruebas de navegador — 43"]
    V1["¿las pestañas reciben el clic?"]
    V2["¿algún texto se pisa con otro?"]
    V3["¿la leyenda promete lo que dibuja?"]
    V4["¿el enlace profundo encuadra bien?"]
    V5["¿el modo cambia lo que debe?"]
  end

  style visor fill:#e8f0ea,stroke:#0f5636,color:#1c1b1a
```

Ejemplos de fallos que **sólo** el navegador encontró:

- Una tarjeta de capas que creció a 576 px y tapó las pestañas.
- La barra de escala "2000 km" pisando el título de la leyenda en móvil.
- `maplibre-gl.css` declarando `z-index: 2` y ganándole a la regla propia.
- El selector `> * + *` (0,1,0) perdiendo contra `border: 0` (0,2,0).

## La instrumentación, no la captura

Las pruebas leen `window.CENTINELA.pintado`, un registro público de qué capas
se pintaron y con cuántos rasgos:

```python
_esperar_capa(pagina, "incendios")   # espera a que el registro lo confirme
```

**Nunca se mide desde una captura de pantalla.** Una pestaña que corre en
segundo plano tiene `visibilityState: hidden`, y entonces
`requestAnimationFrame` baja a ~1 fps: los vuelos animados de MapLibre no
avanzan y el mapa *parece* vacío cuando está perfectamente pintado.

Reglas que se derivan de eso:

1. Para forzar un repintado, despachar `window.dispatchEvent(new Event('resize'))`
   en bucle antes de medir.
2. La verdad está en `window.CENTINELA.pintado` y en la barra de escala, no en
   el píxel.
3. **Nunca** medir rendimiento ni estados `:focus` en una pestaña oculta.

## La sonda de solapes

`SONDA_SOLAPES` recorre los elementos de texto visibles, mide sus cajas y
falla si dos se pisan. Corre en los tres tamaños y **en los dos modos**:

```python
assert solapes == [], f"en {etiqueta} ({ancho}x{alto}), modo sismos: {solapes}"
# … cambiar a modo fuego …
assert solapes == [], f"en {etiqueta} ({ancho}x{alto}), modo fuego: {solapes}"
```

Es la prueba que encontró que la escala pisaba la leyenda: un fallo que una
persona ve en dos segundos y que ninguna aserción sobre el DOM detecta.

## Reproducir carreras de red

Un fallo que sólo aparece con red lenta no se reproduce en un servidor local,
que responde en microsegundos. Se retrasan **las teselas**, no el estilo:

```python
pg.route("**/tiles.openfreemap.org/**/*.pbf", _lento)   # 1,2 s
```

Retrasar el estilo no sirve: en local `load` llega antes que `styledata` y la
carrera no existe. Con las teselas lentas, sí — y así se reprodujo la
regresión del enlace profundo que reportaba "21 de 21 reportes en el encuadre".

## Un aviso para quien valide a mano

`inner_text()` devuelve el texto **renderizado**, con las versalitas aplicadas:
`"CARGANDO EL MAPA"`, no `"Cargando el mapa"`. Ha mordido tres veces. Comparar
siempre en minúsculas.
