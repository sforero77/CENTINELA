# events/

Un archivo JSON por evento (`<usgs_id>.json`), versionado en git.

Este directorio **es** la base de datos del sistema. La decisión (D: "Estado",
§4.2) es deliberada: archivos auditables por `git log` en vez de un servidor
vivo. El costo es cero, el historial es gratis, y la idempotencia ante
reinicios del runner sale sola.

Esquema: [`schemas/event-state.schema.json`](../schemas/event-state.schema.json).

No editar a mano salvo para corregir un evento mal clasificado — y en ese caso,
con PR y explicación en el campo `notas`.
