# 06 · Herramientas

Estado a fines de 2026. Verificá versiones y licencias antes de usar.

## Base (obligatorias)

| Herramienta | Para qué |
|---|---|
| Claude Code | Orquestador y subagentes |
| ffmpeg / ffprobe | Cortes, letterbox, stacks, concatenación, metadatos de video |
| exiftool | Metadatos y fechas; escribir XMP; limpiar miniaturas |
| Python 3 | Scripts del pipeline |

## Catálogo y análisis

| Herramienta | Para qué | Nota |
|---|---|---|
| imagededup (idealo) | Duplicados: pHash/dHash y CNN | Local, gratis |
| PySceneDetect | Partir videos en tomas | `detect-adaptive` por defecto |
| OpenCV | Nitidez (varianza del Laplaciano), exposición | |
| LAION Aesthetic Predictor | Puntaje estético para **ordenar** | Tiene sesgos conocidos; no decide |
| Whisper | Transcribir clips con voz | Solo donde hay voz |
| claude-real-video (crv) | Keyframes por escena + transcripción, para que Claude "vea" un video | Útil para referencias |
| Immich / digiKam | Ver y buscar el catálogo; reconocimiento facial local | Leen XMP |
| Claude Message Batches API | Etiquetado masivo con descuento | No elegible para Zero Data Retention |

## Montaje

| Herramienta | Qué es | Pros | Contras |
|---|---|---|---|
| HyperFrames (HeyGen) | Video desde HTML/CSS/GSAP, con skills para agentes | Apache 2.0, determinista, fácil para agentes | Renders lentos en algunos casos |
| Remotion | Video desde React, con Agent Skills oficiales | El más usado, mucho material | Licencia paga para empresas de 4+ personas |
| video-use (browser-use) | Edita material crudo cortando por habla | Muy bueno con voz; memoria en `project.md` | Poco útil para fotos; pide key de ElevenLabs |
| pyCapCut | Librería Python que genera borradores de CapCut | Resultado editable en CapCut | No oficial; CapCut para Windows; formatos pueden cambiar |
| VectCutAPI | Servidor + MCP que genera borradores de CapCut | Usable como MCP desde Claude | No oficial; posible fricción con términos de CapCut |
| PyMusicLooper / librosa | Puntos de loop y beats de la música | Loops exactos | — |

## Referencias de estilo

- `yt-dlp` para bajar videos de referencia propios o públicos **solo para análisis**, nunca para republicar.
- Si una plataforma bloquea la descarga, grabá la pantalla.

## Recomendación por defecto

- Catálogo: scripts propios + Batch API + SQLite/XMP.
- Montaje de fotos: ffmpeg (rápido) o borrador de CapCut.
- Textos, stacks y loops exactos: HyperFrames.
- Clips con voz: video-use o Whisper + ffmpeg.
- Terminación: editor manual.
