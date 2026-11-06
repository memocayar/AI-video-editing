#!/usr/bin/env python3
"""Fase 0: verifica que estén las herramientas y dependencias del pipeline."""
import importlib
import importlib.metadata
import shutil
import subprocess
import sys

MIN_PYTHON = (3, 10)

BINARIES = {
    "ffmpeg": (["ffmpeg", "-version"], "brew install ffmpeg"),
    "ffprobe": (["ffprobe", "-version"], "brew install ffmpeg"),
    "exiftool": (["exiftool", "-ver"], "brew install exiftool"),
}

# módulo importable -> nombre del paquete en pip
PY_REQUIRED = {
    "jsonschema": "jsonschema",
    "PIL": "Pillow",
    "pillow_heif": "pillow-heif",
}

# Fases posteriores: se informan pero no fallan el chequeo.
PY_OPTIONAL = {
    "cv2": ("opencv-python", "fase 3: nitidez/exposición"),
    "imagededup": ("imagededup", "fase 2: duplicados"),
    "scenedetect": ("scenedetect", "fase 3: escenas"),
    "anthropic": ("anthropic", "fase 4: etiquetado"),
}


def first_line(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception as e:
        return f"error: {e}"


def module_version(name, pkg):
    importlib.import_module(name)
    try:
        return importlib.metadata.version(pkg)
    except importlib.metadata.PackageNotFoundError:
        return "ok"


def main():
    missing = []

    py_ok = sys.version_info >= MIN_PYTHON
    mark = "OK " if py_ok else "FALTA"
    print(f"[{mark}] python {sys.version.split()[0]} ({sys.executable})")
    if not py_ok:
        missing.append(f"Python >= {'.'.join(map(str, MIN_PYTHON))} (brew install python, luego python3 -m venv .venv)")

    for name, (cmd, hint) in BINARIES.items():
        if shutil.which(name):
            print(f"[OK ] {name}: {first_line(cmd)}")
        else:
            print(f"[FALTA] {name}")
            missing.append(f"{name}: {hint}")

    for mod, pkg in PY_REQUIRED.items():
        try:
            print(f"[OK ] {pkg} {module_version(mod, pkg)}")
        except ImportError:
            print(f"[FALTA] {pkg}")
            missing.append(f"{pkg}: pip install -r requirements.txt")

    for mod, (pkg, why) in PY_OPTIONAL.items():
        try:
            print(f"[OK ] {pkg} {module_version(mod, pkg)} (opcional, {why})")
        except ImportError:
            print(f"[ -- ] {pkg} no instalado (opcional, {why})")

    if missing:
        print("\nFalta instalar:")
        for m in dict.fromkeys(missing):
            print(f"  - {m}")
        return 1
    print("\nEntorno listo para la fase 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
