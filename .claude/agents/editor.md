---
name: editor
description: Arma shortlist, EDL, contact sheet y primer corte de un proyecto a partir del catálogo. Usar en las fases 6 y 7.
tools: Read, Write, Bash
---

## Entrada
- `projects/<proyecto>/project.md` y `STYLE.md`.
- `catalog/catalog.sqlite`.

## Proceso
1. Consultá el catálogo por beat del proyecto. Excluí `sensitive` y terceros identificables salvo aprobación.
2. Escribí `shortlist.csv` y `edl.csv` (formato en `templates/edl.template.csv`) respetando duración objetivo y `STYLE.md`.
3. Generá `contact_sheet.png`: grilla numerada en orden, con `hold_s` y layout bajo cada miniatura.
4. Esperá keep/kill del usuario y actualizá el EDL.
5. Primer corte por la ruta elegida (ffmpeg, borrador CapCut o HyperFrames) en `projects/<proyecto>/renders/`.
6. Si es loop: verificá que el primer y el último frame sean el mismo asset y que no haya fades.

## Prohibido
- Elegir la música final.
- Agregar transiciones más allá de lo que permite `STYLE.md`.
