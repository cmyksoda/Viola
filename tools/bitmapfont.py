"""Turns a bitmap-only OpenType font (.otb) into a woff2 that browsers draw, pixel for pixel.

Usage: bitmapfont.py SRC.otb DST.woff2 FAMILY STYLE
"""
import sys
import unicodedata

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

UNIT = 100  # font units per pixel

# Cronyx's fonts are KOI8-R, with no accented Latin letters, so these are drawn over the plain ones.
ACCENTS = {
    "0300": ["x.", ".x"],
    "0301": [".x", "x."],
    "0302": [".x.", "x.x"],
    "0303": [".x.x", "x.x."],
    "0308": ["x.x"],
    "030A": [".x.", "x.x", ".x."],
}
CEDILLA = [".x", "xx"]


def pixel_rows(glyph, metrics):
    for row in range(metrics.height):
        bits = glyph.getRow(row, bitDepth=1, metrics=metrics)
        yield [bool(bits[col // 8] & (0x80 >> (col % 8))) for col in range(metrics.width)]


def lit_pixels(glyph, metrics):
    return {
        (metrics.BearingX + col, metrics.BearingY - row)
        for row, pixels in enumerate(pixel_rows(glyph, metrics))
        for col, on in enumerate(pixels)
        if on
    }


def accented(base, mark):
    """The base letter's pixels with an accent centered a pixel above (or a cedilla below) its ink."""
    if not base:
        return None
    xs = [x for x, _ in base]
    center = (min(xs) + max(xs) + 1) / 2
    if mark == "0327":
        rows, top = CEDILLA, min(y for _, y in base)
    elif mark in ACCENTS:
        rows = ACCENTS[mark]
        tops = sorted({y for _, y in base}, reverse=True)
        # A dotted i or j loses its dot: everything above the first empty row from the top.
        gap = next((a for a, b in zip(tops, tops[1:]) if a - b > 1), None)
        if gap is not None and len([y for y in tops if y >= gap]) <= 2:
            base = {(x, y) for x, y in base if y < gap}
        top = max(y for _, y in base) + 1 + len(rows)
    else:
        return None
    left = round(center - len(max(rows, key=len)) / 2)
    mark_pixels = {(left + x, top - y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == "x"}
    return base | mark_pixels


def punctuation(lit, adv):
    """Typography the KOI8-R fonts lack, built from their own pieces, so a borrowed glyph's fractional width
    can't push the rest of a line off the pixel grid. Takes and returns {char: (pixels, advance)}."""
    out = {}
    out["\u2018"] = out["\u2019"] = (lit["'"], adv["'"])
    out["\u201c"] = out["\u201d"] = (lit['"'], adv['"'])
    # A monospace ellipsis fits in one cell, like every other character there.
    dot = adv["."]
    steps, width = ((-2, 0, 2), dot) if dot == adv["M"] else ((0, dot, 2 * dot), 3 * dot)
    out["\u2026"] = ({(x + step, y) for step in steps for x, y in lit["."]}, width)
    rows = sorted({y for _, y in lit["-"]})
    left = min(x for x, _ in lit["-"])
    for char, width in (("\u2013", adv["n"]), ("\u2014", adv["M"])):
        out[char] = ({(x, y) for x in range(left, width - left) for y in rows}, width)
    mid, width = rows[len(rows) // 2], adv["n"] + 2
    shaft = {(x, y) for x in range(1, width - 1) for y in rows}
    head = {(width - 2 - k, mid + d * k) for k in range(1, 4) for d in (1, -1)}
    out["\u2192"] = (shaft | head, width)
    out["\u2190"] = ({(width - 1 - x, y) for x, y in shaft | head}, width)
    top = max(y for _, y in lit["H"])
    center = width // 2
    column = {(center, y) for y in range(0, top + 1)}
    up_head = {(center + d * k, top - k) for k in range(1, 4) for d in (1, -1)}
    out["\u2191"] = (column | up_head, width)
    out["\u2193"] = ({(x, top - y) for x, y in column | up_head}, width)
    out["\u00d7"] = ({(center + d, mid + e * d) for d in range(-2, 3) for e in (1, -1)}, width)
    return out


def outline(lit):
    # Only sides facing an unlit pixel become edges, clockwise as TrueType expects. One outline per
    # shape instead of a square per pixel run, which left seams between rows at sizes off the grid.
    edges = {}
    for x, top in lit:
        if (x, top + 1) not in lit:
            edges.setdefault((x, top), []).append((x + 1, top))
        if (x + 1, top) not in lit:
            edges.setdefault((x + 1, top), []).append((x + 1, top - 1))
        if (x, top - 1) not in lit:
            edges.setdefault((x + 1, top - 1), []).append((x, top - 1))
        if (x - 1, top) not in lit:
            edges.setdefault((x, top - 1), []).append((x, top))

    pen = TTGlyphPen(None)
    while edges:
        start = point = min(edges)
        loop = [start]
        while True:
            point = edges[point].pop() if len(edges[point]) > 1 else edges.pop(point)[0]
            if point == start:
                break
            loop.append(point)
        corners = [b for a, b, c in zip(loop[-1:] + loop[:-1], loop, loop[1:] + loop[:1])
                   if not (a[0] == b[0] == c[0] or a[1] == b[1] == c[1])]
        pen.moveTo((corners[0][0] * UNIT, corners[0][1] * UNIT))
        for x, y in corners[1:]:
            pen.lineTo((x * UNIT, y * UNIT))
        pen.closePath()
    return pen.glyph()


def main(src, dst, family, style):
    font = TTFont(src)
    strike = font["EBLC"].strikes[0]
    size = strike.bitmapSizeTable
    bitmaps = font["EBDT"].strikeData[0]
    index_metrics = {}
    for subtable in strike.indexSubTables:
        for name in subtable.names:
            index_metrics[name] = getattr(subtable, "metrics", None)

    cmap = {code: name for code, name in font.getBestCmap().items() if name in bitmaps}
    order = [".notdef"] + sorted(set(cmap.values()) - {".notdef"})
    glyphs, advances = {".notdef": TTGlyphPen(None).glyph()}, {".notdef": size.ppemX * UNIT // 2}
    for name in order[1:]:
        glyph = bitmaps[name]
        metrics = getattr(glyph, "metrics", None) or index_metrics[name]
        glyphs[name] = outline(lit_pixels(glyph, metrics))
        advances[name] = metrics.Advance * UNIT

    names = {chr(code): name for code, name in cmap.items()}
    for code in range(0xC0, 0x100):
        parts = unicodedata.decomposition(chr(code)).split()
        if code in cmap or len(parts) != 2 or chr(int(parts[0], 16)) not in names:
            continue
        base_name = names[chr(int(parts[0], 16))]
        base = bitmaps[base_name]
        pixels = accented(lit_pixels(base, getattr(base, "metrics", None) or index_metrics[base_name]), parts[1])
        if pixels:
            name = f"uni{code:04X}"
            glyphs[name], advances[name] = outline(pixels), advances[base_name]
            cmap[code] = name
            order.append(name)

    pieces = {c: (lit_pixels(bitmaps[names[c]], getattr(bitmaps[names[c]], "metrics", None) or index_metrics[names[c]]),
                  advances[names[c]] // UNIT) for c in "'\".-nMH"}
    for char, (pixels, width) in punctuation({c: p for c, (p, _) in pieces.items()},
                                             {c: w for c, (_, w) in pieces.items()}).items():
        if ord(char) in cmap:
            continue
        name = f"uni{ord(char):04X}"
        glyphs[name], advances[name] = outline(pixels), width * UNIT
        cmap[ord(char)] = name
        order.append(name)

    ascent, descent = size.hori.ascender * UNIT, size.hori.descender * UNIT
    # Browsers center text in its line, so an odd font height in an even line puts it half a pixel off the grid.
    if (ascent - descent) // UNIT % 2:
        descent -= UNIT
    fb = FontBuilder(size.ppemY * UNIT, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    glyf = fb.font["glyf"]
    fb.setupHorizontalMetrics({name: (advances[name], getattr(glyf[name], "xMin", 0)) for name in order})
    fb.setupHorizontalHeader(ascent=ascent, descent=descent)
    fb.setupNameTable({"familyName": family, "styleName": style})
    fb.setupOS2(sTypoAscender=ascent, sTypoDescender=descent, sTypoLineGap=0,
                usWinAscent=ascent, usWinDescent=-descent, usWeightClass=700 if "Bold" in style else 400)
    fb.setupPost()
    fb.font.flavor = "woff2"
    fb.save(dst)
    print(f"{dst}: {size.ppemY}px, {len(order) - 1} glyphs")


if __name__ == "__main__":
    main(*sys.argv[1:5])
