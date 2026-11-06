# 07 · Formatos y montaje

Defaults pensados para videos cortos verticales. Cada proyecto los ajusta en su `STYLE.md`.

## Lienzo

- 1080×1920 (9:16), 30 fps, fondo negro.
- Escala **fit**, no fill: nada se recorta salvo que se pida.

## Layouts

| Layout | Uso | Notas |
|---|---|---|
| `full` | Vertical que llena la pantalla | |
| `letterbox` | Horizontal sola, con bandas negras | Look tendencia; no rellenar con blur salvo que se pida |
| `stack2` | 2 horizontales apiladas | ~1215 px de alto, centradas |
| `stack3` | 3 horizontales 16:9 apiladas | 3 × 608 px ≈ 1824 px; separadores finos |
| `before-after` | Misma situación en dos épocas, apiladas | Antes arriba, después abajo |

Variante de stack: las fotos aparecen de a una, cada una en un beat.

Agrupá los tramos horizontales por sección; alternar foto a foto entre `full` y `letterbox` se ve desprolijo.

### Comandos de referencia

Letterbox:
```bash
ffmpeg -i in.jpg -vf "scale=1080:-2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" out.jpg
```

Stack de 3:
```bash
ffmpeg -i a.jpg -i b.jpg -i c.jpg -filter_complex \
"[0]scale=1080:608:force_original_aspect_ratio=increase,crop=1080:608[a];\
[1]scale=1080:608:force_original_aspect_ratio=increase,crop=1080:608[b];\
[2]scale=1080:608:force_original_aspect_ratio=increase,crop=1080:608[c];\
[a][b][c]vstack=3,pad=1080:1920:0:(oh-ih)/2:black" stack.jpg
```

## Ritmo

| Rol | Tiempo en pantalla |
|---|---|
| filler (ráfaga) | 0,4–0,8 s (1 beat a 90–130 BPM) |
| support | 1–1,5 s |
| hero | 1,5–3 s |
| stack3 | 1–1,5 s |
| clip con audio | lo que dure el mejor segmento (2–4 s) |
| cierre | 1,5–2,5 s |

- Duración total típica: 15–35 s.
- Los tiempos se ajustan a múltiplos de beat cuando se elige la música.
- Ritmo que acelera hacia el final da sensación de progreso.
- Memes: uno cada 6–10 ítems, nunca más de 2 seguidos (default).

## Orden

Cronológico por `era`, con inserciones (memes, antes/después) según `STYLE.md`.

## Texto

- Una tipografía, un estilo.
- Marcadores de etapa opcionales: chicos, en una esquina.
- Caption principal: posición y tamaño medidos de las referencias.

## Loop

Para que el video se vuelva a ver sin notar el corte:
- Primer y último frame: el mismo asset.
- Caption partido: primera mitad al inicio, segunda al final, de modo que en el loop se lea como una frase continua.
- Sin fade a negro, placa final ni fade out de audio.
- Opcional: terminar un clip en movimiento justo antes de donde empieza.

## Música

- Se elige al final.
- Para loop: duración del video = número entero de compases, corte en downbeat, tramo que termine donde la canción "vuelve" al inicio. Herramientas: PyMusicLooper, librosa.
- Si usás audio de la biblioteca de la plataforma, el loop lo maneja la app. Para loop exacto, subí el audio montado (con derechos de uso).
- Clips con sonido: música con ducking al 30–40 %.

## Transiciones

Cortes secos por defecto. Si se usan, como máximo 2–3 en todo el video (zoom suave, flash corto), siempre en momentos clave.
