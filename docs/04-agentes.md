# 04 · Agentes

## Roles

| Agente | Archivo | Hace | No hace |
|---|---|---|---|
| Orquestador | (sesión principal) | Planifica, reparte lotes, mergea, pide OK | Clasificar en masa |
| `classifier` | `.claude/agents/classifier.md` | Etiqueta un lote de miniaturas → JSONL | Escribir en SQLite, decidir roles de proyecto |
| `curator` | `.claude/agents/curator.md` | Revisa clusters, elige keepers, propone stacks y antes/después | Borrar archivos |
| `style-analyst` | `.claude/agents/style-analyst.md` | Mide videos de referencia → `STYLE.md` | Copiar contenido ajeno |
| `editor` | `.claude/agents/editor.md` | Arma shortlist, EDL, contact sheet y primer corte | Elegir la música final |

## Dos formas de correr la clasificación (fase 4)

**A. Batch API (recomendada para +500 archivos).** Un script arma un request por miniatura desde SQLite, lo manda en lote y valida las respuestas. Más barato y reproducible.

**B. Subagentes de Claude Code.** El orquestador reparte lotes:

> Lanzá N subagentes `classifier` en paralelo, uno por lote de ~120–150 archivos de `catalog/batches/`. Cada uno escribe `catalog/out/batch_XX.jsonl`. Cuando terminen, validá contra `schema/asset.schema.json`, reencolá los inválidos y mergeá a SQLite en un solo paso.

Reglas de coordinación:
- Los subagentes **no escriben en SQLite**; solo el paso de merge, para evitar conflictos.
- Cada lote es una lista de rutas de miniaturas + metadatos ya calculados (fecha, orientación, métricas), para que el modelo no los recalcule.
- Los archivos no-keeper de un cluster heredan tags del keeper sin pasar por la API.

## Puntos de control

1. Después de la muestra de 50: el usuario revisa y se ajusta el prompt.
2. Después del dedup: galería HTML de clusters.
3. Después del etiquetado: revisión de todo lo `hero` y `sensitive`.
4. Después del EDL: contact sheet numerada → keep/kill.
5. Después del primer corte: feedback por timecode.

## Prompt base del clasificador

El prompt completo está en `.claude/agents/classifier.md`. Se completa en tiempo de ejecución con:
- la lista de `era` del usuario,
- las categorías opcionales que haya definido (`vibe`, `estilo_visual`, `temas_personales`),
- las exclusiones de privacidad.

Todo eso sale de `private/answers/`.

## Feedback eficiente

- Por número: "keep 1–14, kill 15, 22, 30".
- Por timecode: "00:08–00:12 más rápido".
- Por regla: "nunca más de 3 memes seguidos" → va a `STYLE.md`.
