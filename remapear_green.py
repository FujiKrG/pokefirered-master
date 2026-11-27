
from PIL import Image
from pathlib import Path

base = Path("graphics/object_events")
pics = base / "pics" / "people"
palettes = base / "palettes"

files = {
    "green_normal_a": 13,
    "green_normal_b": 4,
}

for name, transparent_index in files.items():
    source = Image.open(pics / f"{name}.png").convert("P")

    old_palette = source.getpalette()
    old_pixels = list(source.getdata())

    # Índice 0 passa a ser transparente.
    new_pixels = [
        0 if pixel == transparent_index else pixel + 1
        for pixel in old_pixels
    ]

    # Preserva a ordem original das cores.
    new_palette = [255, 255, 255]

    for index in range(16):
        if index < transparent_index:
            offset = index * 3
            new_palette.extend(old_palette[offset:offset + 3])
        else:
            new_palette.extend([0, 0, 0])

    new_palette = new_palette[:48]

    image = Image.new("P", source.size)
    image.putpalette(new_palette)
    image.putdata(new_pixels)
    image.info["transparency"] = 0

    output_name = f"{name}_gba"

    image.save(pics / f"{output_name}.png", transparency=0)

    # Gera a paleta binária RGB555 correspondente.
    gbapal = bytearray()

    for i in range(16):
        r, g, b = new_palette[i * 3:i * 3 + 3]
        color = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
        gbapal.extend(color.to_bytes(2, "little"))

    (palettes / f"{output_name}.gbapal").write_bytes(gbapal)

    print(
        f"{output_name}: {source.size}, "
        f"índices usados: {sorted(set(new_pixels))}, "
        f"transparência: {image.info['transparency']}"
    )

print("\nRemapeamento concluído.")
