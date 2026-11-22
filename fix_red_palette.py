
from PIL import Image
from pathlib import Path
import shutil

base = Path("graphics/object_events/pics/people")
backup = Path("palette_backup")

files = [
    "red_vs_seeker_bike.png",
    "red_bike.png",
    "red_fish.png",
    "red_item.png",
    "red_roller_skates.png",
]

backup.mkdir(exist_ok=True)

replacements = {
    (176, 176, 208): (209, 209, 222),  # B0B0D0 -> D1D1DE
}

for filename in files:
    path = base / filename

    backup_path = backup / filename
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    img = Image.open(path).convert("RGBA")
    pixels = img.load()
    changed = 0

    mapping = replacements.copy()

    if filename == "red_item.png":
        mapping[(57, 57, 123)] = (56, 56, 120)  # 39397B -> 383878

    for y in range(img.height):
        for x in range(img.width):
            color = pixels[x, y]
            rgb = color[:3]

            if rgb in mapping:
                new_rgb = mapping[rgb]
                pixels[x, y] = (*new_rgb, color[3])
                changed += 1

    img.save(path)
    print(f"{filename}: {changed} pixels corrigidos")

print("\nCorreção concluída. Backups salvos em:", backup)
