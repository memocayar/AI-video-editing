# reel-story-kit

Kit para armar **videos cortos verticales** (TikTok, Reels, Shorts) a partir de **bibliotecas grandes de fotos y videos personales**, usando **Claude Code** como orquestador.

La idea: clasificar tu material **una sola vez** en un catálogo reutilizable y, después, armar todos los videos que quieras sobre ese catálogo. Las reglas, el estilo y las decisiones viven en archivos versionados, no en un chat que se pierde.

## Para qué sirve

- Ordenar cientos o miles de fotos y clips: fechas, duplicados, calidad, contenido y etiquetas.
- Guardar todo en un catálogo que sirve para cualquier video futuro (recap del año, "day in my life", historia personal, antes y después, etc.).
- Elegir el material de un video puntual con un shortlist y un EDL (lista ordenada con tiempos y textos).
- Generar un primer corte automático (ffmpeg, borrador de CapCut o HyperFrames) y terminarlo a mano.
- Enseñarle tu estilo a Claude con videos de referencia medidos, no con adjetivos.

## Para qué NO sirve

- No genera video con IA: no inventa imágenes ni escenas. Edita tu material real.
- No reemplaza tu criterio: hay puntos de control humanos en cada fase.

## Cómo funciona

```
media/ (originales, intactos)
   │
   ▼  Fase 1: ingesta determinista (hash, metadatos, fechas, miniaturas)
   ▼  Fase 2: duplicados y clusters
   ▼  Fase 3: métricas automáticas (nitidez, estética, audio, escenas)
   ▼  Fase 4: etiquetado semántico con Claude vision (subagentes o Batch API)
catalog/ (SQLite + sidecars JSON/XMP)  ← reutilizable para cualquier video
   │
   ▼  Fase 5: estilo (referencias medidas → STYLE.md)
   ▼  Fase 6: shortlist + EDL + contact sheet → revisión humana
   ▼  Fase 7: primer corte (ffmpeg / CapCut / HyperFrames)
   ▼  Fase 8: pulido manual (música, beat-sync, color, export)
projects/<video>/ (shortlist, EDL, renders)
```

## Estructura

```
CLAUDE.md                 Reglas para el agente (lo lee Claude Code al abrir el repo)
docs/
  01-estrategia.md        Pipeline completo y por qué de cada fase
  02-reglas.md            Reglas duras de datos, privacidad y edición
  03-clasificacion.md     Taxonomía general + categorías opcionales
  04-agentes.md           Cómo lanzar y coordinar los agentes
  05-resultados-esperados.md  Entregables y criterios de aceptación por fase
  06-herramientas.md      Stack recomendado, links y advertencias
  07-formatos-y-montaje.md    Lienzo, layouts, ritmo, loops, música
questionnaires/           Preguntas para definir tu proyecto (en blanco)
templates/                Plantillas de STYLE.md, proyecto y EDL
schema/                   Esquemas JSON de assets e ítems de proyecto
.claude/agents/           Definiciones de subagentes
.claude/skills/           Skill que resume el flujo
scripts/                  Scripts del pipeline (ver roadmap)
projects/                 Un subdirectorio por video
private/                  Tus respuestas y datos personales (no se versiona)
media/  catalog/          Tu material y el catálogo (no se versionan)
```

## Quick start

1. Cloná el repo y poné tu material en `media/` (o configurá la ruta en `private/answers/04-material.md`).
2. Copiá `questionnaires/` a `private/answers/` y respondé lo que quieras. Todo es opcional salvo lo marcado como **requerido**.
3. Abrí Claude Code en la carpeta y decile: `Leé CLAUDE.md y arrancá la fase 0.`
4. Probá con **50 archivos** antes de procesar todo.

## Privacidad

`private/`, `media/`, `catalog/` y los renders están en `.gitignore`. Antes de compartir, revisá con `git status` que no se cuele nada personal. Ver `docs/02-reglas.md`.

## Estado

Este repo contiene la estrategia, las reglas, los esquemas y las definiciones de agentes. Los scripts están descritos en `scripts/README.md` como roadmap para implementar con Claude Code.

## Licencia

MIT. Ver `LICENSE`.
