# Scripts (roadmap)

Scripts a implementar con Claude Code. Cada uno es idempotente y trabaja sobre `catalog/`.

| Script | Fase | Hace |
|---|---|---|
| `00_check_env.py` | 0 | Verifica ffmpeg, exiftool, Python y dependencias |
| `01_ingest.py` | 1 | Hash, exiftool/ffprobe, fechas (incl. WhatsApp), HEIC→JPG, miniaturas 768 px sin metadatos, keyframes |
| `02_dedup.py` | 2 | imagededup pHash + CNN → clusters; genera `review/clusters.html` |
| `03_metrics.py` | 3 | Nitidez, exposición, puntaje estético, audio, escenas, Whisper solo con voz |
| `04_make_batches.py` | 4 | Arma lotes para subagentes o requests para Batch API |
| `04_batch_api.py` | 4 | Envía, espera y descarga resultados de Batch API |
| `05_merge_validate.py` | 4 | Valida JSONL contra el esquema, mergea a SQLite, escribe sidecars JSON/XMP |
| `06_contact_sheet.py` | 6 | Grilla numerada desde un EDL |
| `07_render_ffmpeg.py` | 7 | Corte bruto MP4 desde el EDL (letterbox, stacks, holds) |
| `07_capcut_draft.py` | 7 | Borrador de CapCut desde el EDL (pyCapCut) |
| `08_music_loop.py` | 8 | Propone tramos de loop con PyMusicLooper/librosa |

Prompt sugerido: `Implementá scripts/01_ingest.py según docs/02-reglas.md y docs/03-clasificacion.md, y probalo con 50 archivos.`
