"""Writes Viola's web/themes.css from each theme's official palette, or with --android DIR,
the Android accents, icons and launcher entries into an APK build folder."""
import colorsys
import sys
from pathlib import Path


def hsl(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return f"{hue * 360:.0f} {sat * 100:.1f}% {light * 100:.1f}%"


def darker(hex_color, amount=0.08):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return f"{hue * 360:.0f} {sat * 100:.1f}% {max(0, light - amount) * 100:.1f}%"


KEYS = ["bg000", "bg100", "bg200", "bg300", "bg400", "border", "t0", "t2", "t4", "brand", "onbrand", "accent",
        "danger", "success", "plan", "edits", "code", "kw", "str", "num", "inline"]

THEMES = {
    "latte": ("Catppuccin Latte",
              "#fbfbfc #eff1f5 #e6e9ef #dce0e8 #ccd0da #4c4f69 #4c4f69 "
              "#5c5f77 #6c6f85 #8839ef #ffffff #1e66f5 #d20f39 #40a02b "
              "#179299 #ea76cb #e6e9ef #8839ef #40a02b #fe640b #fe640b"),
    "frappe": ("Catppuccin Frappé",
               "#414559 #303446 #292c3c #232634 #1c1f2b #c6d0f5 #c6d0f5 "
               "#b5bfe2 #949cbb #ca9ee6 #303446 #8caaee #e78284 #a6d189 "
               "#81c8be #f4b8e4 #292c3c #ca9ee6 #a6d189 #ef9f76 #ef9f76"),
    "macchiato": ("Catppuccin Macchiato",
                  "#363a4f #24273a #1e2030 #181926 #12131c #cad3f5 #cad3f5 "
                  "#b8c0e0 #939ab7 #c6a0f6 #24273a #8aadf4 #ed8796 #a6da95 "
                  "#8bd5ca #f5bde6 #1e2030 #c6a0f6 #a6da95 #f5a97f #f5a97f"),
    "mocha": ("Catppuccin Mocha",
              "#313244 #1e1e2e #181825 #11111b #0b0b12 #cdd6f4 #cdd6f4 "
              "#bac2de #9399b2 #cba6f7 #1e1e2e #89b4fa #f38ba8 #a6e3a1 "
              "#94e2d5 #f5c2e7 #181825 #cba6f7 #a6e3a1 #fab387 #fab387"),
    "solarized-light": ("Solarized Light",
                        "#fffbef #fdf6e3 #eee8d5 #ece5cf #e3dcc6 #073642 #073642 "
                        "#586e75 #657b83 #cb4b16 #fdf6e3 #268bd2 #dc322f #859900 "
                        "#2aa198 #6c71c4 #eee8d5 #859900 #2aa198 #d33682 #cb4b16"),
    "solarized-dark": ("Solarized Dark",
                       "#073642 #002b36 #00232c #001e26 #00161c #93a1a1 #93a1a1 "
                       "#839496 #657b83 #cb4b16 #fdf6e3 #268bd2 #dc322f #859900 "
                       "#2aa198 #6c71c4 #00232c #859900 #2aa198 #d33682 #cb4b16"),
    "gruvbox-light": ("Gruvbox Light",
                      "#f9f5d7 #fbf1c7 #f2e5bc #ebdbb2 #d5c4a1 #3c3836 #3c3836 "
                      "#504945 #7c6f64 #af3a03 #fbf1c7 #076678 #9d0006 #79740e "
                      "#427b58 #8f3f71 #f2e5bc #9d0006 #79740e #8f3f71 #af3a03"),
    "gruvbox-dark": ("Gruvbox Dark",
                     "#3c3836 #282828 #1d2021 #1d2021 #141617 #ebdbb2 #ebdbb2 "
                     "#d5c4a1 #a89984 #fe8019 #282828 #83a598 #fb4934 #b8bb26 "
                     "#8ec07c #d3869b #1d2021 #fb4934 #b8bb26 #d3869b #fe8019"),
    "tokyo-night": ("Tokyo Night",
                    "#24283b #1a1b26 #16161e #13131a #0f0f14 #c0caf5 #c0caf5 "
                    "#a9b1d6 #737aa2 #7aa2f7 #1a1b26 #7dcfff #f7768e #9ece6a "
                    "#73daca #bb9af7 #16161e #bb9af7 #9ece6a #ff9e64 #ff9e64"),
    "dracula": ("Dracula",
                "#343746 #282a36 #21222c #191a21 #14151b #f8f8f2 #f8f8f2 "
                "#e0e0da #8b93b8 #bd93f9 #282a36 #8be9fd #ff5555 #50fa7b "
                "#8be9fd #ff79c6 #21222c #ff79c6 #f1fa8c #bd93f9 #ffb86c"),
    "nord": ("Nord",
             "#3b4252 #2e3440 #292e39 #252a33 #20252d #eceff4 #eceff4 "
             "#d8dee9 #8f9bb3 #88c0d0 #2e3440 #81a1c1 #bf616a #a3be8c "
             "#8fbcbb #b48ead #292e39 #81a1c1 #a3be8c #b48ead #d08770"),
    "rose-pine": ("Rosé Pine",
                  "#26233a #191724 #15131f #12101b #0e0c15 #e0def4 #e0def4 "
                  "#c8c5e0 #908caa #ebbcba #191724 #c4a7e7 #eb6f92 #9ccfd8 "
                  "#3e8fb0 #f6c177 #15131f #3e8fb0 #f6c177 #ebbcba #ebbcba"),
    "rose-pine-dawn": ("Rosé Pine Dawn",
                       "#fffaf3 #faf4ed #f2e9e1 #ebe0d6 #dfdad9 #575279 #575279 "
                       "#797593 #86819a #d7827e #ffffff #907aa9 #b4637a #56949f "
                       "#286983 #ea9d34 #f2e9e1 #286983 #ea9d34 #d7827e #b4637a"),
    "matrix": ("Matrix",
               "#0b140d #050a06 #000000 #091109 #000000 #00ff41 #5cff8a "
               "#3fdc6c #2a9a4b #00ff41 #000000 #9dffb8 #ff4d4d #00ff41 "
               "#33ffcc #b3ff33 #000000 #00ff41 #b3ff33 #33ffcc #9dffb8"),
    "win95": ("Windows 95",
              "#ffffff #ffffff #c0c0c0 #dfdfdf #808080 #000000 #000000 "
              "#222222 #808080 #000080 #ffffff #0000ff #c00000 #008000 "
              "#008080 #800080 #ffffff #000080 #008000 #800080 #800000"),
}

# Lines beyond the color tokens: fonts, and toggles that would wash out in the theme's own accent.
EXTRAS = {
    "matrix": ['--font-ui: "IBM Plex Mono", "Kaomoji", ui-monospace, monospace;',
               "--font-serif: var(--font-ui);",
               "--toggle-on: 135 100% 50%;",
               "--knob: 0 0% 0%;"],
    "win95": ['--font-ui: "Win95 Sans", "Kaomoji", system-ui, sans-serif;',
              '--font-mono: "Win95 Mono", ui-monospace, monospace;',
              '--font-serif: "Win95 Text", "Kaomoji", sans-serif;',
              "--toggle-on: 240 100% 25%;"],
}

# Windows 95's icon is the teal desktop rather than its white window, flat like its pixel star.
ICON_COLORS = {"win95": ("#008080", "#008080", "#ffffff")}

VARS = {"bg000": "--bg-000",  "bg100": "--bg-100",     "bg200": "--bg-200",
        "bg300": "--bg-300",  "bg400": "--bg-400",     "border": "--border",
        "t0": "--text-000",   "t2": "--text-200",      "t4": "--text-400",
        "brand": "--brand",   "onbrand": "--on-brand", "accent": "--accent",
        "danger": "--danger", "success": "--success",  "plan": "--plan",
        "edits": "--edits",   "code": "--code-bg",     "kw": "--syn-kw",
        "str": "--syn-str",   "num": "--syn-num",      "inline": "--inline-code"}

# Classic Clay keeps claude.ai's own tokens, written out so a preview card can show them on any page.
CLAY = {
    "clay-light": "0 0% 100%|48 33.3% 97.1%|53 28.6% 94.5%|48 25% 92.2%|50 20.7% 88.6%|30 3.3% 11.8%|60 2.6% 7.6%|"
                  "60 2.5% 23.3%|51 3.1% 43.7%|15 63.1% 59.6%|0 0% 100%|210 73.7% 40.2%|0 56.2% 45.4%|103 72.3% 26.9%|"
                  "181 52% 30%|262 42% 50%|48 25% 92.2%|330 50% 45%|100 40% 34%|25 75% 42%|0 56.2% 45.4%",
    "clay-dark": "60 2.1% 18.4%|60 2.7% 14.5%|30 3.3% 11.8%|60 2.6% 7.6%|0 0% 0%|51 16.5% 84.5%|48 33.3% 97.1%|"
                 "50 9% 73.7%|48 4.8% 59.2%|15 63.1% 59.6%|0 0% 100%|210 65.5% 67.1%|0 67% 59.6%|97 59.1% 46.1%|"
                 "178 45% 58%|262 70% 78%|30 3.3% 11.8%|330 60% 75%|95 40% 68%|28 80% 68%|15 70% 72%",
}


# Windows 95 swaps Viola's line icons for pixel art. Each row is 16 pixels, colored by the letters in PIXEL_COLORS.
ICONS95 = {
    "lock": [
        "",
        "",
        ".....kkkkkk",
        "....kk....kk",
        "....k......k",
        "....k......k",
        "...kkkkkkkkkk",
        "...kkkkkkkkkk",
        "...kkkk..kkkk",
        "...kkkk..kkkk",
        "...kkkkk.kkkk",
        "...kkkkkkkkkk",
        "...kkkkkkkkkk",
    ],
    "dots": [
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "...kk..kk..kk",
        "...kk..kk..kk",
    ],
    "sidebar": [
        "",
        ".kkkkkkkkkkkkkk",
        ".knnnnnnnnnnnnk",
        ".kkkkkkkkkkkkkk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kgggkwwwwwwwwk",
        ".kkkkkkkkkkkkkk",
    ],
    "terminal": [
        ".kkkkkkkkkkkkkk",
        ".knnnnnnnnnnnnk",
        ".knnnnnnnnnnnnk",
        ".kggggggggggggk",
        ".kgkkkkkkkkkkgk",
        ".kgkwwkkkkkkkgk",
        ".kgkkwwkkkkkkgk",
        ".kgkkkwwkkkkkgk",
        ".kgkkwwkkkkkkgk",
        ".kgkwwkkwwwwkgk",
        ".kgkkkkkkkkkkgk",
        ".kggggggggggggk",
        ".kkkkkkkkkkkkkk",
    ],
    "search": [
        "",
        "....kkkk",
        "...kwwwwk",
        "..kwwwwwwk",
        "..kwwwwwwk",
        "..kwwwwwwk",
        "..kwwwwwwk",
        "...kwwwwk",
        "....kkkkkk",
        "..........kk",
        "...........kk",
        "............kk",
        ".............k",
    ],
    "folder": [
        "..kkkkk",
        ".kyyyyyk",
        ".kyyyyyykkkkkkk",
        ".kwwwwwwwwwwwwk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kkkkkkkkkkkkkk",
    ],
    # Explorer's "Up One Level": the folder with a bent arrow pointing up.
    "arrow-up-left": [
        "..kkkkk",
        ".kyyyyyk",
        ".kyyyyyykkkkkkk",
        ".kwwwwwwwwwwwwk",
        ".kyyykyyyyyyyyk",
        ".kyykkkyyyyyyyk",
        ".kykkkkkyyyyyyk",
        ".kyyykyyyyyyyyk",
        ".kyyykyyyyyyyyk",
        ".kyyykkkkkkyyyk",
        ".kyyyyyyyyyyyyk",
        ".kyyyyyyyyyyyyk",
        ".kkkkkkkkkkkkkk",
    ],
    "settings": [
        "",
        "",
        ".........wwwk",
        ".........wggk",
        ".kkkkkkkkwggkkk",
        ".........wggk",
        ".........kkkk",
        "",
        "....wwwk",
        "....wggk",
        ".kkkwggkkkkkkkk",
        "....wggk",
        "....kkkk",
    ],
    "clock": [
        "",
        ".....kkkkk",
        "...kkwwwwwkk",
        "..kwwwwkwwwwk",
        "..kwwwwkwwwwk",
        ".kwwwwwkwwwwwk",
        ".kwwwwwkwwwwwk",
        ".kwwwwwkkkkwwk",
        ".kwwwwwwwwwwwk",
        ".kwwwwwwwwwwwk",
        "..kwwwwwwwwwk",
        "..kwwwwwwwwwk",
        "...kkwwwwwkk",
        ".....kkkkk",
    ],
    "file": [
        "..kkkkkkkk",
        "..kwwwwwwkk",
        "..kwwwwwwkwk",
        "..kwwwwwwkkkk",
        "..kwwwwwwwwwk",
        "..kwgggggggwk",
        "..kwwwwwwwwwk",
        "..kwgggggggwk",
        "..kwwwwwwwwwk",
        "..kwgggggggwk",
        "..kwwwwwwwwwk",
        "..kwgggggwwwk",
        "..kwwwwwwwwwk",
        "..kkkkkkkkkkk",
    ],
    # The Recycle Bin: a wire basket.
    "trash": [
        "",
        "",
        "..kkkkkkkkkkk",
        "..kwwwwwwwwgk",
        "..kkkkkkkkkkk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kgwgwgwgk",
        "...kkkkkkkkk",
    ],
    "chevron": [
        "",
        "",
        "",
        "",
        "",
        "",
        "....kkkkkkk",
        ".....kkkkk",
        "......kkk",
        ".......k",
    ],
    "x": [
        "",
        "",
        "",
        "",
        "....kk....kk",
        ".....kk..kk",
        "......kkkk",
        ".......kk",
        "......kkkk",
        ".....kk..kk",
        "....kk....kk",
    ],
    "arrow-up": [
        "",
        "",
        "",
        ".......kk",
        "......kkkk",
        ".....kkkkkk",
        "....kkkkkkkk",
        "...kkkkkkkkkk",
        "......kkkk",
        "......kkkk",
        "......kkkk",
        "......kkkk",
        "......kkkk",
    ],
    "plus": [
        "",
        "",
        "",
        "",
        ".......kk",
        ".......kk",
        ".......kk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        ".......kk",
        ".......kk",
        ".......kk",
    ],
    "check": [
        "",
        "",
        "",
        "",
        "",
        "..........k",
        ".........kk",
        "..k.....kkk",
        "..kk...kkk",
        "..kkk.kkk",
        "...kkkkk",
        "....kkk",
        ".....k",
    ],
    "chevron-right": [
        "",
        "",
        "",
        "",
        "......k",
        "......kk",
        "......kkk",
        "......kkkk",
        "......kkk",
        "......kk",
        "......k",
    ],
    "camera": [
        "",
        "",
        "......kkkk",
        ".kkkkkkkkkkkkkk",
        ".kgggggggggggwk",
        ".kggggkkkkggggk",
        ".kgggkwnnnkgggk",
        ".kgggknnnnkgggk",
        ".kgggknnnnkgggk",
        ".kggggkkkkggggk",
        ".kggggggggggggk",
        ".kkkkkkkkkkkkkk",
    ],
    "image": [
        "",
        "",
        ".kkkkkkkkkkkkkk",
        ".kwwwwwwwwwwwwk",
        ".kwttttttttyywk",
        ".kwttttttttyywk",
        ".kwtttettttttwk",
        ".kwtteeettettwk",
        ".kwteeeeeeeetwk",
        ".kweeeeeeeeeewk",
        ".kwwwwwwwwwwwwk",
        ".kkkkkkkkkkkkkk",
    ],
    "paperclip": [
        "",
        ".......kkk",
        "......k...k",
        "......k.k.k",
        "......k.k.k",
        "......k.k.k",
        "......k.k.k",
        "......k.k.k",
        "......k.k.k",
        "......k.k.k",
        "......k...k",
        ".......kkk",
    ],
    "shield": [
        "",
        "",
        "...kkkkkkkkk",
        "...knnnnnnnk",
        "...knnnnnnnk",
        "...knnnnnnnk",
        "...knnnnnnnk",
        "....knnnnnk",
        "....knnnnnk",
        ".....knnnk",
        "......knk",
        ".......k",
    ],
    "pencil": [
        "",
        "",
        "...........kk",
        "..........kyyk",
        ".........kyyk",
        "........kyyk",
        ".......kyyk",
        "......kyyk",
        ".....kyyk",
        "....kyyk",
        "...kwwk",
        "...kkk",
        "...k",
    ],
    "plan": [
        "",
        "",
        "...kkkkkkkkk",
        "...kwwwwwwwk",
        "...kwkkkkkwk",
        "...kwwwwwwwk",
        "...kwkkkkkwk",
        "...kwwwwwwwk",
        "...kwkkkkwwk",
        "...kwwwwwwwk",
        "...kwkkkwwwk",
        "...kkkkkkkkk",
    ],
    "unlock": [
        "",
        ".....kkkkkk",
        "....kk....kk",
        "....k......k",
        "....k",
        "....k",
        "...kkkkkkkkkk",
        "...kkkkkkkkkk",
        "...kkkk..kkkk",
        "...kkkk..kkkk",
        "...kkkkk.kkkk",
        "...kkkkkkkkkk",
        "...kkkkkkkkkk",
    ],
    "arrow-down": [
        "",
        "",
        "",
        "......kkkk",
        "......kkkk",
        "......kkkk",
        "......kkkk",
        "......kkkk",
        "...kkkkkkkkkk",
        "....kkkkkkkk",
        ".....kkkkkk",
        "......kkkk",
        ".......kk",
    ],
    "arrow-left": [
        "",
        "",
        "",
        ".......k",
        "......kk",
        ".....kkk",
        "....kkkkkkkkkkk",
        "...kkkkkkkkkkkk",
        "....kkkkkkkkkkk",
        ".....kkk",
        "......kk",
        ".......k",
    ],
    "copy": [
        "",
        "......kkkkkkkk",
        "......kwwwwwwk",
        "......kwwwwwwk",
        "......kwwwwwwk",
        "..kkkkkkkkwwwk",
        "..kwwwwwwkwwwk",
        "..kwwwwwwkwwwk",
        "..kwwwwwwkwwwk",
        "..kwwwwwwkkkkk",
        "..kwwwwwwk",
        "..kwwwwwwk",
        "..kwwwwwwk",
        "..kkkkkkkk",
    ],
    "chat": [
        "..kkkkkkkkkkkk",
        ".kwwwwwwwwwwwwk",
        ".kwwwwwwwwwwwwk",
        ".kwkkkkkkkkkkwk",
        ".kwwwwwwwwwwwwk",
        ".kwkkkkkkkkkkwk",
        ".kwwwwwwwwwwwwk",
        ".kwkkkkkkkwwwwk",
        ".kwwwwwwwwwwwwk",
        "..kkkwwkkkkkkk",
        "....kwk",
        "....kk",
        "....k",
    ],
    "stop": [
        "",
        "",
        "",
        "",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
        "....kkkkkkkk",
    ],
}

# Viola's eight-petal star, for the logo marks in Windows 95.
MARK95 = [
    ".......nn",
    "......nnnn",
    "......nnnn",
    "...nn..nn..nn",
    "...nn..nn..nn",
    ".....n....n",
    ".nn..........nn",
    "nnnnn......nnnnn",
    "nnnnn......nnnnn",
    ".nn..........nn",
    ".....n....n",
    "...nn..nn..nn",
    "...nn..nn..nn",
    "......nnnn",
    "......nnnn",
    ".......nn",
]

PIXEL_COLORS = {"k": "%23000", "w": "%23fff", "n": "%23000080", "y": "%23ffff00",
                "g": "%23808080", "t": "%23008080", "e": "%23008000", "o": "%23808000"}

GLASS = [
    "..kkkkkkkkkkk",
    "...kwwwwwwwk",
    "...kwwwwwwwk",
    "...kwwwwwwwk",
    "....kwwwwwk",
    ".....kwwwk",
    "......kwk",
    "......kwk",
    "......kwk",
    "......kwk",
    ".....kwwwk",
    "....kwwwwwk",
    "...kwwwwwwwk",
    "...kwwwwwwwk",
    "...kwwwwwwwk",
    "..kkkkkkkkkkk",
]


def hourglass_frames():
    """The Windows 95 busy hourglass: olive sand drains from the top chamber into the bottom one, then the glass turns over."""
    def frame(top_rows, bottom_rows, stream):
        rows = [list(r.ljust(16, ".")) for r in GLASS]
        for y in range(1, 6):
            if y >= 6 - top_rows:
                rows[y] = ["o" if c == "w" else c for c in rows[y]]
        for y in range(10, 15):
            if y >= 15 - bottom_rows:
                rows[y] = ["o" if c == "w" else c for c in rows[y]]
        if stream:
            for y in range(6, 11):
                rows[y][7] = "o"
        return ["".join(r).rstrip(".") for r in rows]

    full = frame(5, 0, False)
    draining = [frame(5 - i, i, True) for i in range(1, 5)]
    empty = frame(0, 5, False)
    # Halfway through turning over, the glass lies on its side with the sand along the bottom.
    side = ["".join(row[x] if x < len(row) else "." for row in empty).rstrip(".") for x in range(16)]
    side = [r.replace("o", "w") for r in side]
    for y in (9, 10, 11):
        side[y] = side[y].replace("w", "o")
    return [full, full] + draining + [empty, empty, side]


def pixel_icon(rows, width=16):
    paths = {}
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            color = row[x]
            run = len(row[x:]) - len(row[x:].lstrip(color))
            if color in PIXEL_COLORS:
                paths.setdefault(color, []).append(f"M{x} {y}h{run}v1h-{run}z")
            x += run
    body = "".join(f"<path fill='{PIXEL_COLORS[c]}' d='{''.join(d)}'/>" for c, d in paths.items())
    return (f"url(\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
            f"viewBox='0 0 {width} 16' shape-rendering='crispEdges'>{body}</svg>\")")


def star_rects(scale, offset):
    """MARK95 as one rectangle per run of pixels, for drawing it at any size."""
    rects = []
    for y, row in enumerate(MARK95):
        x = 0
        while x < len(row):
            run = len(row[x:]) - len(row[x:].lstrip(row[x]))
            if row[x] == "n":
                rects.append((offset + x * scale, offset + y * scale, run * scale, scale))
            x += run
    return rects


def pixel_tile_svg():
    """Windows 95's app icon: the pixel star in white on a square of the desktop's teal."""
    body = "".join(f"M{x} {y}h{w}v{h}h-{w}z" for x, y, w, h in star_rects(1, 2))
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' shape-rendering='crispEdges'>"
            f"<rect width='20' height='20' fill='#008080'/><path fill='#fff' d='{body}'/></svg>\n")


def pixel_icons_css():
    rules = [f'[data-theme="win95"] .ico-{name} {{ background: {pixel_icon(rows)} center / contain no-repeat; }}'
             for name, rows in ICONS95.items()]
    # Settings closes with a back arrow in Windows 95, the way a Chicago95 app would.
    rules.append(f'[data-theme="win95"] .settings-head .ico-x '
                 f'{{ background-image: {pixel_icon(ICONS95["arrow-left"])}; }}')
    rules.append(f'[data-theme="win95"] .mark {{ background: {pixel_icon(MARK95)} center / contain no-repeat; }}')
    white_star = pixel_icon([row.replace("n", "w") for row in MARK95])
    rules.append(f'[data-theme="win95"] .icon-preview '
                 f'{{ background: #008080 {white_star} center / 32px no-repeat; image-rendering: pixelated; }}')
    rules.append('[data-theme="win95"] .icon-preview svg { display: none; }')
    frames = hourglass_frames()
    strip = [" ".join(f[y].ljust(16, ".") if y < len(f) else "." * 16 for f in frames) for y in range(16)]
    sprite = pixel_icon([row.replace(" ", "") for row in strip], width=16 * len(frames))
    rules.append(f'[data-theme="win95"] .glyph {{ display: inline-block; width: 16px; height: 16px; '
                 f'overflow: hidden; color: transparent; '
                 f'vertical-align: -3px; background: {sprite} 0 0 / {len(frames) * 100}% 100% no-repeat; '
                 f'image-rendering: pixelated; '
                 f'animation: hourglass {len(frames) * 0.16:.2f}s steps({len(frames)}, jump-none) infinite; }}')
    rules.append('@keyframes hourglass { to { background-position: 100% 0; } }')
    hide = ", ".join([f'[data-theme="win95"] .ico-{name} > *' for name in ICONS95]
                     + ['[data-theme="win95"] .mark > *'])
    return "/* Windows 95 pixel icons */\n" + "\n".join(rules) + f"\n{hide} {{ display: none; }}"


ROOT = Path(__file__).resolve().parent.parent
ALIAS = """        <activity-alias
            android:name=".Icon_{key}"
            android:targetActivity=".ViolaActivity"
            android:icon="@mipmap/ic_launcher_{key}"
            android:roundIcon="@mipmap/ic_launcher_{key}"
            android:enabled="false"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity-alias>"""
ICON = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_background_{key}" />
    <foreground android:drawable="@drawable/ic_foreground_{key}" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>
"""


def write_css():
    out = ["/* Generated by tools/themes.py from each theme's published palette.\n"
           "   app.js knows which themes are light and which are dark. */"]
    for name, triples in CLAY.items():
        values = dict(zip(KEYS, triples.split("|")))
        lines = [f"  {VARS[k]}: {values[k]};" for k in KEYS]
        out.append(f'[data-theme="{name}"] {{\n' + "\n".join(lines) + "\n  --brand-strong: 15 54.2% 51.2%;\n}")
    for name, (label, hexes) in THEMES.items():
        values = dict(zip(KEYS, hexes.split()))
        assert len(values) == len(KEYS), name
        lines = [f"  {VARS[k]}: {hsl(values[k])};" for k in KEYS]
        lines.append(f"  --brand-strong: {darker(values['brand'])};")
        lines += [f"  {extra}" for extra in EXTRAS.get(name, [])]
        out.append(f"/* {label} */\n[data-theme=\"{name}\"] {{\n" + "\n".join(lines) + "\n}")
    out.append(pixel_icons_css())
    (ROOT / "web" / "themes.css").write_text("\n\n".join(out) + "\n")
    write_desktop_icons()


def write_desktop_icons():
    """The desktop's version of each theme's icon: the classic SVG with the Android icons' colors."""
    classic = (ROOT / "web" / "icon.svg").read_text()
    (ROOT / "web" / "icons").mkdir(exist_ok=True)
    for name, (_, hexes) in THEMES.items():
        values = dict(zip(KEYS, hexes.split()))
        start, end, star = ICON_COLORS.get(name, (values["bg000"], values["bg200"], values["brand"]))
        svg = classic.replace("#e48b6d", start).replace("#cc6748", end).replace("#faf9f5", star)
        if name == "win95":
            svg = pixel_tile_svg()
        (ROOT / "web" / "icons" / f"{name}.svg").write_text(svg)


def write_android(build):
    res = build / "res"
    # Android tints the native text-selection handles with the activity theme's accent, so each theme gets a style.
    accents = ({"clay-light": "#d97757", "clay-dark": "#d97757"}
               | {name: hexes.split()[9] for name, (_, hexes) in THEMES.items()})
    styles = [f'    <style name="ViolaAccent_{name.replace("-", "_")}" parent="Viola">\n'
              f'        <item name="android:colorAccent">{color}</item>\n'
              f'    </style>'
              for name, color in accents.items()]
    (res / "values" / "accents.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + "\n".join(styles) + "\n</resources>\n")

    # Each theme's icon is the classic one recolored: the star in the brand color, on a glow of the theme's backgrounds.
    mark = (res / "drawable" / "ic_launcher_foreground.xml").read_text()
    glow = (res / "color" / "ic_launcher_glow.xml").read_text()
    background = (res / "drawable" / "ic_launcher_background.xml").read_text()
    aliases = []
    for name, (_, hexes) in THEMES.items():
        values = dict(zip(KEYS, hexes.split()))
        key = name.replace("-", "_")
        start, end, star = ICON_COLORS.get(name, (values["bg000"], values["bg200"], values["brand"]))
        foreground = mark.replace("@color/ic_launcher_mark", star)
        if name == "win95":
            # 3dp per pixel puts the 48dp star inside the adaptive icon's 66dp safe zone.
            path = "".join(f"M{x},{y}h{w}v{h}h-{w}z" for x, y, w, h in star_rects(3, 30))
            foreground = ('<?xml version="1.0" encoding="utf-8"?>\n'
                          '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
                          '    android:width="108dp" android:height="108dp" '
                          'android:viewportWidth="108" android:viewportHeight="108">\n'
                          f'    <path android:fillColor="#ffffff" android:pathData="{path}" />\n</vector>\n')
        (res / "drawable" / f"ic_foreground_{key}.xml").write_text(foreground)
        (res / "color" / f"ic_glow_{key}.xml").write_text(glow.replace("#e48b6d", start).replace("#cc6748", end))
        (res / "drawable" / f"ic_background_{key}.xml").write_text(
            background.replace("@color/ic_launcher_glow", f"@color/ic_glow_{key}"))
        (res / "mipmap-anydpi-v26" / f"ic_launcher_{key}.xml").write_text(ICON.format(key=key))
        aliases.append(ALIAS.format(key=key))
    (build / "aliases.xml").write_text("\n".join(aliases) + "\n")


if len(sys.argv) == 3 and sys.argv[1] == "--android":
    write_android(Path(sys.argv[2]))
else:
    write_css()
