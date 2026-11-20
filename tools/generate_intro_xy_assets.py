from pathlib import Path
import subprocess
import struct

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "graphics" / "intro" / "xy"
TITLE_ASSET_DIR = ROOT / "graphics" / "title_screen" / "xy_demake"
CAPA_DIR = ROOT.parent / "assets" / "Capa"
GBA_GFX = ROOT / "tools" / "gbagfx" / "gbagfx.exe"
BACKGROUND_SIZE = (240, 160)
MARK_SIZE = (88, 80)
TRANSPARENT_COLOR = (0, 248, 40)
MARK_PALETTE_BASE = 128
MASK_PALETTE = 15
MASK_TRANSPARENT_TILE = 176
MASK_BLACK_TILE = 177
BORDER_TILE_BASE = 178
BORDER_BLANK_TILE = MASK_TRANSPARENT_TILE
TITLE_OVERLAY_TILE_BASE = 176
TITLE_OVERLAY_PALETTE_BASE = 6
TITLE_LOGO_PALETTE_COUNT = 4
TITLE_BLACK_BARS_PALETTE = TITLE_OVERLAY_PALETTE_BASE + TITLE_LOGO_PALETTE_COUNT
TITLE_XERNEAS_PALETTE = TITLE_BLACK_BARS_PALETTE + 1
TITLE_OVERLAYS = (
    "black_bars",
    "pokemon_x_demake",
    "xerneas",
)


def tiles(image: Image.Image):
    pixels = image.load()
    width, height = image.size
    for tile_y in range(0, height, 8):
        for tile_x in range(0, width, 8):
            for y in range(tile_y, tile_y + 8):
                for x in range(tile_x, tile_x + 8):
                    yield pixels[x, y]


def write_map(path: Path, entries, fmt: str):
    path.write_bytes(b"".join(struct.pack(fmt, entry) for entry in entries))


background = Image.open(ASSET_DIR / "background_source.png").convert("RGB")
if background.size != BACKGROUND_SIZE:
    raise ValueError(f"Expected {BACKGROUND_SIZE} background, got {background.size}")

background_colors = sorted(set(background.get_flattened_data()))
if len(background_colors) > 254:
    raise ValueError("Background must use at most 254 colors")
if len(background_colors) >= TITLE_OVERLAY_PALETTE_BASE * 16:
    raise ValueError("Background colors overlap the title overlay palettes")
background_indices = {color: index + 1 for index, color in enumerate(background_colors)}
background_pixels = bytes(background_indices[color] for color in background.get_flattened_data())

background_indexed = Image.frombytes("P", BACKGROUND_SIZE, background_pixels)
background_palette = [0] * 768
for index, color in enumerate(background_colors, 1):
    background_palette[index * 3:index * 3 + 3] = color
background_indexed.putpalette(background_palette)
background_indexed.save(ASSET_DIR / "background_indexed.png")

background_tiles = bytes(tiles(background_indexed))
(ASSET_DIR / "background.8bpp").write_bytes(background_tiles)

background_map = [0] * (32 * 32)
for y in range(20):
    for x in range(30):
        background_map[y * 32 + x] = y * 30 + x
write_map(ASSET_DIR / "background.bin", background_map, "<H")

mark_source = Image.open(CAPA_DIR / "X.png").convert("RGB")
mark_rgba = Image.new("RGBA", mark_source.size)
mark_rgba.putdata([
    (*color, 0 if color == TRANSPARENT_COLOR else 255)
    for color in mark_source.get_flattened_data()
])
mark_alpha = mark_rgba.getchannel("A")
mark_pixels = list(mark_alpha.get_flattened_data())
mark_width, mark_height = mark_rgba.size
opaque_pixels = {
    index for index, alpha in enumerate(mark_pixels) if alpha != 0
}
if not opaque_pixels:
    raise ValueError("X artwork contains no opaque pixels")
largest_component = set()
while opaque_pixels:
    start = opaque_pixels.pop()
    component = {start}
    pending = [start]
    while pending:
        index = pending.pop()
        x, y = index % mark_width, index // mark_width
        for neighbor_y in range(max(0, y - 1), min(mark_height, y + 2)):
            for neighbor_x in range(max(0, x - 1), min(mark_width, x + 2)):
                neighbor = neighbor_y * mark_width + neighbor_x
                if neighbor in opaque_pixels:
                    opaque_pixels.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
    if len(component) > len(largest_component):
        largest_component = component

mark_alpha.putdata([
    255 if index in largest_component else 0
    for index in range(mark_width * mark_height)
])
mark_rgba.putalpha(mark_alpha)
mark_bbox = mark_alpha.getbbox()
mark_rgba = mark_rgba.crop(mark_bbox)

mark_canvas = Image.new("RGBA", MARK_SIZE, (0, 0, 0, 0))
paste_x = (MARK_SIZE[0] - mark_rgba.width) // 2
paste_y = (MARK_SIZE[1] - mark_rgba.height) // 2
mark_canvas.alpha_composite(mark_rgba, (paste_x, paste_y))

mark_colors = sorted({
    pixel[:3]
    for pixel in mark_canvas.get_flattened_data()
    if pixel[3] != 0
})
if len(mark_colors) > 127:
    raise ValueError("Mark must use at most 127 opaque colors")

mark_color_indices = {
    color: MARK_PALETTE_BASE + index
    for index, color in enumerate(mark_colors)
}
mark_pixels = bytes(
    0 if pixel[3] == 0 else mark_color_indices[pixel[:3]]
    for pixel in mark_canvas.get_flattened_data()
)
mark_indexed = Image.frombytes("P", MARK_SIZE, mark_pixels)
mark_palette = [0] * 768
for color, index in mark_color_indices.items():
    mark_palette[index * 3:index * 3 + 3] = color
mark_indexed.putpalette(mark_palette)
mark_indexed.info["transparency"] = 0
mark_indexed.save(ASSET_DIR / "mark_indexed.png")

mark_tiles = bytes(64) + bytes(tiles(mark_indexed))
(ASSET_DIR / "mark.8bpp").write_bytes(mark_tiles)

mark_map = [0] * (32 * 32)
tiles_x = MARK_SIZE[0] // 8
tiles_y = MARK_SIZE[1] // 8
for y in range(tiles_y):
    for x in range(tiles_x):
        mark_map[y * 32 + x] = y * tiles_x + x + 1
(ASSET_DIR / "mark.bin").write_bytes(bytes(mark_map))

palette = [(0, 0, 0)] * 256
for index, color in enumerate(background_colors, 1):
    palette[index] = color
for color, index in mark_color_indices.items():
    palette[index] = color
palette[MASK_PALETTE * 16 + 1] = (0, 0, 0)
palette_data = bytearray()
for red, green, blue in palette:
    gba_color = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
    palette_data.extend(struct.pack("<H", gba_color))
(ASSET_DIR / "palette.gbapal").write_bytes(palette_data)

mask_tiles = bytes(32) + bytes([0x11] * 32)
(ASSET_DIR / "mask.4bpp").write_bytes(mask_tiles)

border_source = Image.open(ASSET_DIR / "border_source.png").convert("RGBA")
if border_source.size != BACKGROUND_SIZE:
    raise ValueError(f"Expected {BACKGROUND_SIZE} border mask, got {border_source.size}")

border_pixels = bytes(
    0 if alpha < 128 else 1
    for _, _, _, alpha in border_source.get_flattened_data()
)
border_tiles = []
border_tile_indices = {}
border_map = [BORDER_BLANK_TILE | (MASK_PALETTE << 12)] * (32 * 32)
for tile_y in range(20):
    for tile_x in range(30):
        tile_pixels = bytes(
            border_pixels[y * BACKGROUND_SIZE[0] + x]
            for y in range(tile_y * 8, tile_y * 8 + 8)
            for x in range(tile_x * 8, tile_x * 8 + 8)
        )
        tile_index = border_tile_indices.get(tile_pixels)
        if tile_index is None:
            tile_index = BORDER_TILE_BASE + len(border_tiles)
            border_tile_indices[tile_pixels] = tile_index
            packed_tile = bytearray(32)
            for pixel_index in range(0, 64, 2):
                packed_tile[pixel_index // 2] = (
                    tile_pixels[pixel_index] | (tile_pixels[pixel_index + 1] << 4)
                )
            border_tiles.append(packed_tile)
        border_map[tile_y * 32 + tile_x] = tile_index | (MASK_PALETTE << 12)

(ASSET_DIR / "border.4bpp").write_bytes(b"".join(border_tiles))
write_map(ASSET_DIR / "border.bin", border_map, "<H")

TITLE_ASSET_DIR.mkdir(parents=True, exist_ok=True)
title_tiles = [bytes(64)]
title_tile_indices = {title_tiles[0]: 0}
title_maps = {}


def flipped_tile_variants(tile):
    rows = [tile[y * 8:(y + 1) * 8] for y in range(8)]
    for flip_y in (False, True):
        source_rows = rows[::-1] if flip_y else rows
        for flip_x in (False, True):
            candidate = b"".join(
                row[::-1] if flip_x else row
                for row in source_rows
            )
            flips = (0x400 if flip_x else 0) | (0x800 if flip_y else 0)
            yield candidate, flips


logo_source = Image.open(
    TITLE_ASSET_DIR / "pokemon_x_demake_source.png"
).convert("RGB")
if logo_source.size != BACKGROUND_SIZE:
    raise ValueError(f"Expected {BACKGROUND_SIZE} logo, got {logo_source.size}")

logo_pixels = list(logo_source.get_flattened_data())
logo_alpha = [
    0 if color == TRANSPARENT_COLOR else 255
    for color in logo_pixels
]
logo_rgba = Image.new("RGBA", BACKGROUND_SIZE)
logo_rgba.putdata([
    (*color, logo_alpha[index])
    for index, color in enumerate(logo_pixels)
])
logo_rgba.save(TITLE_ASSET_DIR / "pokemon_x_demake.png")
logo_color_tiles = []
for tile_y in range(BACKGROUND_SIZE[1] // 8):
    for tile_x in range(BACKGROUND_SIZE[0] // 8):
        tile_colors = {
            logo_pixels[y * BACKGROUND_SIZE[0] + x]
            for y in range(tile_y * 8, tile_y * 8 + 8)
            for x in range(tile_x * 8, tile_x * 8 + 8)
            if logo_alpha[y * BACKGROUND_SIZE[0] + x] != 0
        }
        if tile_colors:
            logo_color_tiles.append((tile_x, tile_y, tile_colors))

logo_palette_colors = []
logo_tile_palette = {}
for tile_x, tile_y, tile_colors in sorted(
    logo_color_tiles,
    key=lambda tile: (-len(tile[2]), tile[1], tile[0]),
):
    candidates = [
        (len(tile_colors & palette), len(palette | tile_colors), index)
        for index, palette in enumerate(logo_palette_colors)
        if len(palette | tile_colors) <= 15
    ]
    if candidates:
        palette_index = max(candidates)[2]
        logo_palette_colors[palette_index].update(tile_colors)
    else:
        palette_index = len(logo_palette_colors)
        logo_palette_colors.append(set(tile_colors))
    logo_tile_palette[tile_x, tile_y] = palette_index

if len(logo_palette_colors) > TITLE_LOGO_PALETTE_COUNT:
    raise ValueError(
        f"Logo requires {len(logo_palette_colors)} palettes; "
        f"maximum is {TITLE_LOGO_PALETTE_COUNT}"
    )

logo_palette_indices = [
    {color: index + 1 for index, color in enumerate(sorted(colors))}
    for colors in logo_palette_colors
]
logo_gba_palette = bytearray()
for palette_index in range(TITLE_LOGO_PALETTE_COUNT):
    colors = (
        sorted(logo_palette_colors[palette_index])
        if palette_index < len(logo_palette_colors)
        else []
    )
    palette = [(0, 0, 0)] + colors
    palette += [(0, 0, 0)] * (16 - len(palette))
    for red, green, blue in palette:
        gba_color = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
        logo_gba_palette.extend(struct.pack("<H", gba_color))
(TITLE_ASSET_DIR / "pokemon_x_demake.gbapal").write_bytes(logo_gba_palette)

logo_indexed_pixels = bytearray(BACKGROUND_SIZE[0] * BACKGROUND_SIZE[1])
for y in range(BACKGROUND_SIZE[1]):
    for x in range(BACKGROUND_SIZE[0]):
        pixel_index = y * BACKGROUND_SIZE[0] + x
        if logo_alpha[pixel_index] != 0:
            palette_index = logo_tile_palette[x // 8, y // 8]
            logo_indexed_pixels[pixel_index] = logo_palette_indices[palette_index][logo_pixels[pixel_index]]
logo_indexed = Image.frombytes("P", BACKGROUND_SIZE, bytes(logo_indexed_pixels))

for overlay_index, name in enumerate(TITLE_OVERLAYS):
    if name == "pokemon_x_demake":
        indexed = logo_indexed

        def palette_index_for_tile(tile_x, tile_y):
            return TITLE_OVERLAY_PALETTE_BASE + logo_tile_palette.get(
                (tile_x, tile_y), 0
            )
    else:
        source = Image.open(TITLE_ASSET_DIR / f"{name}.png").convert("RGBA")
        if source.size != BACKGROUND_SIZE:
            raise ValueError(f"Expected {BACKGROUND_SIZE} {name}, got {source.size}")

        source_pixels = list(source.get_flattened_data())
        opaque_pixels = [pixel[:3] for pixel in source_pixels if pixel[3] != 0]
        palette_source = Image.new("RGB", (len(opaque_pixels), 1))
        palette_source.putdata(opaque_pixels)
        quantized_palette = palette_source.quantize(
            colors=15,
            method=Image.Quantize.MEDIANCUT,
            dither=Image.Dither.NONE,
        )
        quantized_pixels = list(
            source.convert("RGB")
            .quantize(palette=quantized_palette, dither=Image.Dither.NONE)
            .get_flattened_data()
        )
        indexed_pixels = bytes(
            0 if pixel[3] == 0 else quantized_pixels[index] + 1
            for index, pixel in enumerate(source_pixels)
        )
        indexed = Image.frombytes("P", BACKGROUND_SIZE, indexed_pixels)
        palette_rgb = quantized_palette.getpalette()
        indexed_palette = [0] * 768
        for color_index in range(15):
            indexed_palette[(color_index + 1) * 3:(color_index + 2) * 3] = (
                palette_rgb[color_index * 3:color_index * 3 + 3]
            )
        indexed.putpalette(indexed_palette)
        indexed.info["transparency"] = 0
        indexed.save(TITLE_ASSET_DIR / f"{name}.png", bits=4, transparency=0)

        gba_palette = bytearray()
        for color_index in range(16):
            red, green, blue = indexed_palette[color_index * 3:color_index * 3 + 3]
            gba_color = (red >> 3) | ((green >> 3) << 5) | ((blue >> 3) << 10)
            gba_palette.extend(struct.pack("<H", gba_color))
        (TITLE_ASSET_DIR / f"{name}.gbapal").write_bytes(gba_palette)

        palette_bank = (
            TITLE_BLACK_BARS_PALETTE
            if name == "black_bars"
            else TITLE_XERNEAS_PALETTE
        )
        palette_index_for_tile = lambda tile_x, tile_y: palette_bank

    pixels = indexed.load()
    transparent_entry = (
        TITLE_OVERLAY_TILE_BASE
        | (palette_index_for_tile(0, 0) << 12)
    )
    tilemap = [transparent_entry] * (32 * 32)
    for tile_y in range(20):
        for tile_x in range(30):
            tile = bytes(
                pixels[tile_x * 8 + x, tile_y * 8 + y]
                for y in range(8)
                for x in range(8)
            )
            if not any(tile):
                tile_index = 0
                flips = 0
            else:
                variants = list(flipped_tile_variants(tile))
                canonical = min(candidate for candidate, _ in variants)
                if canonical not in title_tile_indices:
                    title_tile_indices[canonical] = len(title_tiles)
                    title_tiles.append(canonical)
                tile_index = title_tile_indices[canonical]
                flips = next(
                    flags
                    for candidate, flags in variants
                    if candidate == canonical
                )

            tilemap[tile_y * 32 + tile_x] = (
                (TITLE_OVERLAY_TILE_BASE + tile_index)
                | flips
                | (palette_index_for_tile(tile_x, tile_y) << 12)
            )

    title_maps[name] = tilemap

if TITLE_OVERLAY_TILE_BASE + len(title_tiles) > 1024:
    raise ValueError(f"Title overlay tiles exceed the BG tile limit: {len(title_tiles)}")

title_tile_data = bytearray()
for tile in title_tiles:
    for y in range(8):
        for x in range(0, 8, 2):
            title_tile_data.append(tile[y * 8 + x] | (tile[y * 8 + x + 1] << 4))
(TITLE_ASSET_DIR / "layers.4bpp").write_bytes(title_tile_data)
subprocess.run(
    [
        str(GBA_GFX),
        str(TITLE_ASSET_DIR / "layers.4bpp"),
        str(TITLE_ASSET_DIR / "layers.4bpp.lz"),
    ],
    check=True,
)

for name, tilemap in title_maps.items():
    map_path = TITLE_ASSET_DIR / f"{name}.bin"
    write_map(map_path, tilemap, "<H")
    subprocess.run(
        [str(GBA_GFX), str(map_path), str(TITLE_ASSET_DIR / f"{name}.bin.lz")],
        check=True,
    )

print(
    f"Generated intro assets: {len(background_colors)} background colors, "
    f"{len(mark_colors)} mark colors, {len(border_tiles)} border tiles, "
    f"{len(background_tiles)} background bytes; "
    f"title overlays use {len(title_tiles)} shared tiles"
)