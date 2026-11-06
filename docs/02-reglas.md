# 02 · Reglas

Estas reglas tienen prioridad sobre cualquier otro documento y sobre los defaults de estilo. Las respuestas del usuario en `private/answers/` pueden **endurecerlas**, nunca relajarlas.

## Datos

1. **Los originales no se tocan.** `media/` es solo lectura. Todo trabajo se hace sobre copias en `catalog/work/`.
2. **Nada se borra.** Duplicados y descartes se marcan (`role: discard`, `is_cluster_keeper: false`). Borrar es una decisión manual del usuario.
3. **ID estable:** SHA-256 del archivo original.
4. **Fecha con procedencia:** siempre `date`, `date_source` y `date_confidence`. Prioridad: EXIF > nombre de archivo > sistema de archivos > inferida por el modelo.
5. **Archivos de WhatsApp:** la fecha sale de los 8 dígitos del nombre (`IMG-AAAAMMDD-WA…`). El sufijo `WA0007` no es una hora; usar 12:00:00.
6. **Validación:** toda fila del catálogo valida contra `schema/`.

## Privacidad

1. A la API se mandan **solo miniaturas** (máx. 768 px) **sin metadatos** (`exiftool -all=`).
2. No se mandan a la API archivos marcados como privados en `private/answers/04-material.md` (carpetas, personas, temas).
3. Si aparecen terceros identificables o menores, se marca `people.others_identifiable` / `people.minors`. Esos archivos no se publican sin revisión.
4. Pantallas con datos privados (chats, mails, credenciales, datos de clientes o de trabajo) → `sensitive.screen_has_private_data: true`.
5. Nada personal fuera de `private/`, `catalog/` y `projects/<proyecto>/`. Revisar `git status` antes de cada commit.
6. Si se necesita reconocer tu cara, preferir procesamiento local (por ejemplo Immich) antes que la API.

## Edición (defaults, ajustables por proyecto)

1. Lienzo vertical 1080×1920, 30 fps.
2. El material horizontal **no se recorta**: va con bandas negras (`letterbox`) o apilado (`stack2`, `stack3`). Salvo que `STYLE.md` diga otra cosa.
3. Transiciones: cortes secos por defecto. Máximo 2–3 recursos de transición en todo el video.
4. Una sola tipografía y un solo estilo de texto por video.
5. Sin fades a negro ni placas finales si el video es un loop.
6. La música se elige al final; el corte se arma sobre un BPM provisional.
7. Clips con sonido original se respetan; la música baja (ducking) mientras suenan.

## Proceso

1. Primera corrida de cada fase sobre una muestra.
2. Cada fase termina con un entregable (ver `05-resultados-esperados.md`) y un punto de control humano.
3. Las correcciones de estilo se convierten en reglas en `STYLE.md`.
