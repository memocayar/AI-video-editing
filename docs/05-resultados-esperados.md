# 05 · Resultados esperados

Cada fase termina con un entregable verificable. Si no se cumple el criterio, la fase no está terminada.

| Fase | Entregable | Criterio de aceptación |
|---|---|---|
| 0 · Setup | `private/answers/*.md`, herramientas instaladas | Cuestionarios 01 y 04 respondidos; `ffmpeg`, `exiftool` y Python funcionando |
| 1 · Ingesta | Filas en `catalog.sqlite`, miniaturas, keyframes | 100 % de archivos con ID, fecha y `date_source`; originales sin cambios (hash igual) |
| 2 · Duplicados | Clusters + `catalog/review/clusters.html` | Galería revisada por el usuario; nada borrado |
| 3 · Métricas | Campos `quality` y `video` completos | Sin nulos en nitidez, orientación y audio |
| 4 · Etiquetado | Campos semánticos + sidecars JSON/XMP | 100 % validado contra el esquema; muestra de 50 aprobada; `hero` y `sensitive` revisados |
| 5 · Estilo | `projects/<video>/STYLE.md` | Reglas con números (segundos, porcentajes, cantidades), aprobadas por el usuario |
| 6 · Selección | `shortlist.csv`, `edl.csv`, `contact_sheet.png` | Duración total dentro del objetivo; keep/kill aplicado |
| 7 · Primer corte | `renders/rough_v1.mp4` y/o borrador CapCut | Respeta `STYLE.md`; loop sin salto visible si aplica |
| 8 · Pulido | Video final exportado | Lo decide el usuario |

## Lo que el catálogo debe permitir después

Consultas del estilo de:
- "Todas las fotos de la etapa X donde aparezco, nítidas, verticales."
- "Pares antes/después del mismo lugar."
- "Clips con audio de menos de 3 s, sin voz."
- "Memes y capturas graciosas de tal año."

Si estas consultas no se pueden responder con SQL sobre el catálogo, falta algún campo.
