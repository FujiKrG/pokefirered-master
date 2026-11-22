from PIL import Image
import glob
import os

base = "graphics/object_events/pics/people/"
files = sorted(glob.glob(base + "red_*.png.bak"))

if len(files) != 8:
    raise ValueError(f"Esperados 8 backups, encontrados {len(files)}.")

# Usa a paleta original do backup do Red.
reference = Image.open(base + "red_normal.png.bak")

if reference.mode != "P" or reference.info.get("transparency") != 14:
    raise ValueError("Backup de referência inválido.")

old_palette = reference.getpalette()[:45]

if len(old_palette) != 45:
    raise ValueError("Paleta original incompleta.")

# Índice 0 transparente; cores antigas passam para 1 até 14.
new_palette = [0, 0, 0] + old_palette[:42] + [0, 0, 0]

if len(new_palette) != 48:
    raise ValueError("A nova paleta não possui 16 cores.")

converted = []

for filepath in files:
    original = Image.open(filepath)

    if original.mode != "P":
        raise ValueError(f"{filepath}: modo diferente de P.")

    if original.info.get("transparency") != 14:
        raise ValueError(f"{filepath}: transparência diferente de 14.")

    pixels = list(original.getdata())
    used = set(pixels)

    if 14 not in used or 15 in used:
        raise ValueError(
            f"{filepath}: índices inesperados: {sorted(used)}"
        )

    if original.getpalette()[:42] != old_palette[:42]:
        raise ValueError(f"{filepath}: paleta incompatível.")

    output = Image.new("P", original.size)
    output.putpalette(new_palette)

    # Cores 0–13 passam para 1–14.
    # Transparência 14 passa para 0.
    output.putdata([
        0 if index == 14 else index + 1
        for index in pixels
    ])

    converted.append((filepath[:-4], output))

# Só grava depois de validar todos os backups.
for filepath, output in converted:
    output.save(filepath, transparency=0)
    print("Convertido:", os.path.basename(filepath))

print(f"Conversão concluída: {len(converted)} sprites.")