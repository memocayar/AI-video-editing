# 01 · Estrategia

## Principio

Separar **dos trabajos** que suelen mezclarse:

1. **Catalogar** (una vez, caro, reutilizable): saber qué hay en tu material.
2. **Editar** (por video, barato, iterativo): elegir, ordenar y cortar.

Casi todas las herramientas de "editar con IA" asumen pocos clips con voz. Con cientos o miles de fotos, el cuello de botella es encontrar y elegir, no cortar. Por eso el catálogo va primero.

## Fases

| Fase | Qué se hace | LLM | Control humano |
|---|---|---|---|
| 0 · Setup | Cuestionarios, instalar herramientas, muestra de 50 | No | Respuestas a cuestionarios |
| 1 · Ingesta | Hash, metadatos, fechas, normalización, miniaturas, keyframes | No | — |
| 2 · Duplicados | pHash (exactos) + CNN/CLIP (casi duplicados) → clusters | No | Revisar galería de clusters |
| 3 · Métricas | Nitidez, exposición, estética, audio, escenas, transcripción | No | — |
| 4 · Etiquetado | Claude vision sobre miniaturas → JSON validado | Sí | Muestra de 50 + todo lo `hero` y `sensible` |
| 5 · Estilo | Medir videos de referencia → `STYLE.md` | Sí | Aprobar `STYLE.md` |
| 6 · Selección | Shortlist + EDL + contact sheet | Sí | Keep/kill por número |
| 7 · Primer corte | ffmpeg / borrador CapCut / HyperFrames | Opcional | Ver el corte, feedback por timecode |
| 8 · Pulido | Música, beat-sync, color, export | No | Todo |

## Por qué este orden

- **Lo determinista y gratis va antes que lo caro.** Deduplicar antes de etiquetar reduce lo que se manda a la API.
- **El catálogo es general; el proyecto es específico.** Los campos de cada video (orden, rol, tiempo en pantalla, texto) viven aparte, así un mismo archivo sirve para muchos videos.
- **El estilo se mide, no se describe.** "Que se vea lindo" no le sirve a un agente; "0,5 s por foto, caption arriba al 15 %, sin transiciones" sí.
- **El último 20 % es humano.** El gusto, el beat y el color se terminan a mano en un editor.

## Rutas de montaje (fase 7)

| Ruta | Resultado | Cuándo conviene |
|---|---|---|
| ffmpeg | MP4 de corte bruto | Siempre como plan B; rápido para fotos |
| Borrador de CapCut (pyCapCut / VectCutAPI) | Proyecto editable en CapCut | Si terminás en CapCut y querés su look nativo |
| HyperFrames o Remotion | MP4 renderizado desde código | Placas de texto, layouts, loops exactos |
| video-use | MP4 cortado por habla | Solo clips con voz |

Ver `06-herramientas.md`.

## Costos orientativos

Para ~1000 fotos + ~200 videos (≈1800 imágenes contando keyframes), con miniaturas de 768 px y un modelo chico en Batch API: unos pocos dólares. Lo local (hash, dedup, métricas) es gratis. Recalculá con los precios vigentes antes de correr.
