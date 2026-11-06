# Instrucciones para Claude Code

Este repo es un kit para clasificar material personal (fotos y videos) y armar videos cortos verticales. Sos el orquestador.

## Orden de lectura al iniciar

1. Este archivo.
2. `docs/02-reglas.md` (reglas duras: tienen prioridad sobre todo lo demás).
3. `private/answers/*.md` si existe: son las respuestas del usuario. **Mandan sobre los defaults** de `docs/`.
4. `projects/<proyecto>/STYLE.md` y `project.md` del proyecto activo, si existen.
5. El resto de `docs/` según la fase en curso.

Si `private/answers/` no existe, ofrecé recorrer los cuestionarios de `questionnaires/` de a uno y guardar las respuestas en `private/answers/`.

## Reglas de trabajo

- Trabajá por fases (`docs/01-estrategia.md`). No saltees los puntos de control humanos.
- Antes de cada fase: decí qué vas a hacer, cuántos archivos toca y el costo estimado si usa la API. Esperá el OK.
- Primera corrida siempre sobre una muestra (default: 50 archivos).
- Nunca modifiques ni borres nada en `media/`. Duplicados y descartes se marcan en el catálogo, no se borran.
- Nunca escribas datos personales fuera de `private/`, `catalog/` o `projects/<proyecto>/`.
- Nunca subas a la API: originales en resolución completa, GPS, ni archivos marcados como sensibles (ver reglas).
- Toda salida de clasificación tiene que validar contra `schema/`. Si no valida, reintentá; no la "arregles a mano".
- Cuando el usuario corrija algo de estilo, actualizá `projects/<proyecto>/STYLE.md` con una regla concreta y medible.
- Pedí feedback por número de ítem o timecode ("del 12 al 18 más rápido"), no en abstracto.

## Idioma

Respondé en el idioma del usuario. Los nombres de campos y tags del catálogo van en minúsculas, sin acentos, con guiones (`setup-escritorio`).
