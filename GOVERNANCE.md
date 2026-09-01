# Gobernanza

## Principio rector

**~95 % pre-computado y automático, ~5 % humano.** Una comunidad no opera
turnos; mantiene código y datos. Toda propuesta que exija vigilancia humana
continua se rechaza por diseño, no por falta de voluntad.

El riesgo número uno de este proyecto no es técnico: es el abandono
post-lanzamiento. Cada decisión de gobernanza existe para que el sistema siga
funcionando el mes en que nadie lo mire.

## Roles

| Rol | Que hace | Cuantos |
|---|---|---|
| **Mantenedor del núcleo** | Revisa PR a `pipelines/`, `schemas/` y workflows. Custodia los golden tests | 2+ |
| **Mantenedor por país** | Responsable de las capas nacionales, los topónimos oficiales y el manifest de su país | 1 por país |
| **Brigada de imagen** | Se activa por evento. Etiquetado, validación y publicación del GeoPackage | variable |
| **Contribuidor** | Cualquiera. PR bienvenidos sin permiso previo | — |

El proyecto no se considera sano mientras dependa de una sola persona. La
puerta de salida de la Fase 1 lo mide explícitamente: **dos o más mantenedores
por país que no sean el autor inicial**.

## Decisiones

- **Cambios de código:** PR con CI en verde. Un mantenedor del núcleo aprueba.
- **Cambios de metodología** (umbrales, bandas MMI, formulas de agregación):
  PR con actualización de los golden tests y justificación escrita. Dos
  aprobaciones.
- **Cambios en los no-objetivos** (§1.2 de la especificación): requieren
  discusión pública en issue abierto. Son la línea roja del proyecto.
- **Licencias:** agregar una licencia al registro de `pipelines/common/licensing.py`
  es una decisión consciente que pasa por PR. No hay default permisivo.

## Frontera comunidad ↔ empresa

INSPOW (u otra empresa vinculada a cualquier contribuidor) puede:

- contribuir código, datos abiertos, cómputo o difusión;
- usar los datos del núcleo bajo sus licencias abiertas, como cualquiera.

INSPOW **no** puede:

- **tocar el cubo `nc/`** ni ningún derivado no comercial a través del proyecto;
- condicionar la hoja de ruta del proyecto a un interés comercial;
- aparecer como propietaria del sistema en artefactos publicados.

Esta frontera existe para que el proyecto siga siendo creíble ante las
instituciones publicas a las que quiere servir.

## Relación con instituciones

CENTINELA se presenta a la UNGRD, al SGC y a sus pares regionales (CENAPRED,
SENAPRED, INDECI) **como insumo abierto, no como reemplazo**. Los no-objetivos
son publicos y los disclaimers viajan en cada artefacto precisamente para que
esa relación no se malinterprete.

## Continuidad

- Los workflows programados se desactivan a los 60 días sin actividad; el
  keepalive lo impide y el monitor externo alerta si algo falla.
- El simulacro mensual corre solo y abre issue si falla.
- Todo el estado vive en git: si el proyecto cambia de manos, el historial
  completo viaja con el repositorio.
