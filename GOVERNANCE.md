# Gobernanza

## Principio rector

**~95 % pre-computado y automatico, ~5 % humano.** Una comunidad no opera
turnos; mantiene codigo y datos. Toda propuesta que exija vigilancia humana
continua se rechaza por diseno, no por falta de voluntad.

El riesgo numero uno de este proyecto no es tecnico: es el abandono
post-lanzamiento. Cada decision de gobernanza existe para que el sistema siga
funcionando el mes en que nadie lo mire.

## Roles

| Rol | Que hace | Cuantos |
|---|---|---|
| **Mantenedor del nucleo** | Revisa PR a `pipelines/`, `schemas/` y workflows. Custodia los golden tests | 2+ |
| **Mantenedor por pais** | Responsable de las capas nacionales, los toponimos oficiales y el manifest de su pais | 1 por pais |
| **Brigada de imagen** | Se activa por evento. Etiquetado, validacion y publicacion del GeoPackage | variable |
| **Contribuidor** | Cualquiera. PR bienvenidos sin permiso previo | — |

El proyecto no se considera sano mientras dependa de una sola persona. La
puerta de salida de la Fase 1 lo mide explicitamente: **dos o mas mantenedores
por pais que no sean el autor inicial**.

## Decisiones

- **Cambios de codigo:** PR con CI en verde. Un mantenedor del nucleo aprueba.
- **Cambios de metodologia** (umbrales, bandas MMI, formulas de agregacion):
  PR con actualizacion de los golden tests y justificacion escrita. Dos
  aprobaciones.
- **Cambios en los no-objetivos** (§1.2 de la especificacion): requieren
  discusion publica en issue abierto. Son la linea roja del proyecto.
- **Licencias:** agregar una licencia al registro de `pipelines/common/licensing.py`
  es una decision consciente que pasa por PR. No hay default permisivo.

## Frontera comunidad ↔ empresa

INSPOW (u otra empresa vinculada a cualquier contribuidor) puede:

- contribuir codigo, datos abiertos, computo o difusion;
- usar los datos del nucleo bajo sus licencias abiertas, como cualquiera.

INSPOW **no** puede:

- **tocar el cubo `nc/`** ni ningun derivado no comercial a traves del proyecto;
- condicionar la hoja de ruta del proyecto a un interes comercial;
- aparecer como propietaria del sistema en artefactos publicados.

Esta frontera existe para que el proyecto siga siendo creible ante las
instituciones publicas a las que quiere servir.

## Relacion con instituciones

CENTINELA se presenta a la UNGRD, al SGC y a sus pares regionales (CENAPRED,
SENAPRED, INDECI) **como insumo abierto, no como reemplazo**. Los no-objetivos
son publicos y los disclaimers viajan en cada artefacto precisamente para que
esa relacion no se malinterprete.

## Continuidad

- Los workflows programados se desactivan a los 60 dias sin actividad; el
  keepalive lo impide y el monitor externo alerta si algo falla.
- El simulacro mensual corre solo y abre issue si falla.
- Todo el estado vive en git: si el proyecto cambia de manos, el historial
  completo viaja con el repositorio.
