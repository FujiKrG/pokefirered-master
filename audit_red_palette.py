
from PIL import Image
from pathlib import Path
from collections import Counter

base = Path("graphics/object_events/pics/people")

files = [
    "red_vs_seeker_bike.png",
    "red_bike.png",
    "red_fish.png",
    "red_item.png",
    "red_normal.png",
    "red_roller_skates.png",
    "red_surf.png",
    "red_surf_run.png",
]

palettes = {}

for filename in files:
    path = base / filename
    img = Image.open(path).convert("RGBA")

    pixels = [
        (r, g, b)
        for r, g, b, a in img.getdata()
        if a > 0
    ]

    counts = Counter(pixels)

    # Identifica a cor de fundo como a cor mais frequente.
    background = counts.most_common(1)[0][0]

    colors = set(counts.keys())
    colors.discard(background)

    palettes[filename] = colors

    print(f"\n{filename}")
    print(f"  Dimensões: {img.size}")
    print(f"  Fundo estimado: #{background[0]:02X}{background[1]:02X}{background[2]:02X}")
    print(f"  Cores do personagem: {len(colors)}")

    for color in sorted(colors):
        print(f"    #{color[0]:02X}{color[1]:02X}{color[2]:02X}")

reference = palettes["red_normal.png"]

print("\n" + "=" * 50)
print("COMPARAÇÃO COM red_normal.png")
print("=" * 50)

for filename, colors in palettes.items():
    missing = reference - colors
    extra = colors - reference

    if not missing and not extra:
        print(f"[OK] {filename}: paleta idêntica")
    else:
        print(f"[DIFERENTE] {filename}")
        if missing:
            print("  Faltando:", [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in sorted(missing)])
        if extra:
            print("  Extras:", [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in sorted(extra)])
