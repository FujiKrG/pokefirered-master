
from PIL import Image
from pathlib import Path

base = Path("graphics/object_events")

files = [
    ("pics/people/green_normal_a.png", "palettes/green_palette_a"),
    ("pics/people/green_normal_b.png", "palettes/green_palette_b"),
]

for image_path, palette_path in files:
    image = Image.open(base / image_path).convert("RGBA")
    colors = image.getcolors(image.width * image.height)

    opaque = sorted({
        rgba[:3] for _, rgba in colors if rgba[3] != 0
    })

    if len(opaque) > 15:
        raise ValueError(f"{image_path}: {len(opaque)} cores opacas.")

    palette = [(255, 255, 255)] + opaque
    palette += [(0, 0, 0)] * (16 - len(palette))

    pal_text = "JASC-PAL\n0100\n16\n"
    pal_text += "".join(
        f"{r} {g} {b}\n" for r, g, b in palette
    )

    pal_file = base / (palette_path + ".pal")
    gbapal_file = base / (palette_path + ".gbapal")

    pal_file.write_text(pal_text, encoding="ascii")

    data = bytearray()
    for r, g, b in palette:
        value = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
        data.extend(value.to_bytes(2, "little"))

    gbapal_file.write_bytes(data)

    print(f"{image_path}: {len(opaque)} cores opacas")
    print(f"  PAL: {pal_file.stat().st_size} bytes")
    print(f"  GBAPAL: {gbapal_file.stat().st_size} bytes")

print("Paletas geradas.")
