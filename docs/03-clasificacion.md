# 03 · Clasificación

El catálogo tiene **dos capas**:

- **`assets`**: lo que el archivo *es*. General, sirve para cualquier video.
- **`project_items`**: lo que el archivo *hace en un video puntual*. Un archivo puede estar en muchos proyectos con roles distintos.

Esquemas: `schema/asset.schema.json` y `schema/project_item.schema.json`.

## Capa general (assets)

### Técnicos (automáticos, sin LLM)
- `media_type`: `photo`, `video`, `screenshot`, `meme`, `graphic`
- `date`, `date_source`, `date_confidence`
- `orientation`: `vertical`, `horizontal`, `square`
- `quality`: nitidez, exposición, puntaje estético (solo para ordenar, no para decidir)
- `video`: duración, si tiene audio, si hay voz, transcripción, escenas
- `cluster_id`, `is_cluster_keeper`

### Semánticos (Claude vision)
- `era`: etapa de vida. **Lista definida por cada usuario** (ver cuestionario 03).
- `location_type`: casa, estudio o trabajo, exterior, evento, viaje, etc.
- `content_type`: qué muestra (lista base abajo, ampliable).
- `people`: si aparecés vos, cuántas personas más, si son identificables, si hay menores.
- `sensitive`: datos privados en pantalla, ubicación reveladora, contenido no apto.
- `caption`: descripción breve en una línea.
- `pair_key`: situación repetible para antes/después (mismo lugar o pose en épocas distintas).
- `layout_options`: `full`, `letterbox`, `stack-candidate`.
- `tags`: libres, para búsqueda.

### Lista base de `content_type`
`selfie`, `retrato`, `outfit`, `grupo`, `escritorio-setup`, `pantalla`, `estudio`, `trabajo`, `evento`, `logro`, `viaje`, `comida`, `mascota`, `naturaleza`, `ciudad`, `detalle`, `meme`, `captura-chat`, `documento`, `otro`.

Ampliala en `private/answers/02-estilo-y-categorias.md`.

## Categorías opcionales (cada usuario las define)

Estas no vienen predefinidas porque dependen de cada persona y cada proyecto. Se completan en el cuestionario 02 y el clasificador las usa solo si existen:

- **`vibe`**: el tono que transmite la imagen. Ejemplos neutros de formato: `divertida`, `tranquila`, `intensa`. Vos elegís tu propia lista (5–12 valores).
- **`estilo_visual`**: rasgos estéticos que te importan reconocer.
- **`temas_personales`**: hobbies, áreas o proyectos recurrentes que quieras poder buscar.
- **`personas_clave`**: alias (no nombres reales si vas a compartir) de personas que aparecen seguido.

## Capa de proyecto (project_items)

- `narrative_beat`: momento del relato. Los beats los define cada proyecto (ver `templates/project.template.md`).
- `role`: `hero` (para lucirse), `support`, `filler` (ritmo), `meme-insert`, `stack-member`, `before-after`, `discard`.
- `hold_s`: segundos en pantalla.
- `layout`: `full`, `letterbox`, `stack2`, `stack3`.
- `overlay_text`: texto en pantalla, si hay.
- `order`: posición en el EDL.

## Criterios por defecto para `role`

- **hero:** nítida, funciona sola en vertical, expresa claramente una vibe, sirve como momento del relato. Máximo ~10 % de lo elegido.
- **filler:** correcta pero no protagonista; aporta ritmo en ráfagas rápidas.
- **meme-insert:** memes y capturas graciosas para intercalar.
- **discard:** borrosa, repetida sin aporte, o sensible.

## Almacenamiento

- Fuente de verdad: `catalog/catalog.sqlite`.
- Portabilidad: un sidecar `<archivo>.json` por asset, y tags escritos como XMP (`XMP:TagsList`, `XMP:Rating`) para que los lean Immich, digiKam u otros gestores.
- Carpetas por estado, no por tema: `media/` (originales), `catalog/work/` (copias), `catalog/thumbs/`, `projects/<video>/`. Los temas viven en los tags.
