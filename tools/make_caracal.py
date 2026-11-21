"""Draws Anaq (عناق), the Athar Al Anaq mascot: an Arabian caracal, the desert's sharp-eared hunter.

Run:  .venv/Scripts/python tools/make_caracal.py assets/caracal.svg

Front-facing head and shoulders: tall ears with the caracal's black tufts (the signature), golden
eyes with the dark "tear lines" down to the muzzle, a pale chin and chest. Our own drawing.
"""
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/caracal.svg"
TAWNY, TAWNY_DARK, CREAM, INK, LINE = "#D08F4E", "#B5733A", "#F6EBDD", "#2B1D14", "#5A3A22"
EAR_IN, EYE, NOSE = "#EFCFAA", "#E8B04B", "#B4645A"

parts = [
    # Shoulders and chest
    f'<path d="M30 160 C30 128 48 112 80 112 C112 112 130 128 130 160 Z" fill="{TAWNY}" stroke="{LINE}" stroke-width="2.4"/>',
    f'<path d="M62 160 C62 136 70 124 80 124 C90 124 98 136 98 160 Z" fill="{CREAM}"/>',
    # Ears: tawny outside, pale inside, dark rim, long black tufts (the caracal signature)
    f'<path d="M36 74 L50 14 L72 56 Z" fill="{TAWNY_DARK}" stroke="{LINE}" stroke-width="2.4" stroke-linejoin="round"/>',
    f'<path d="M124 74 L110 14 L88 56 Z" fill="{TAWNY_DARK}" stroke="{LINE}" stroke-width="2.4" stroke-linejoin="round"/>',
    f'<path d="M44 66 L51 30 L64 56 Z" fill="{EAR_IN}"/>',
    f'<path d="M116 66 L109 30 L96 56 Z" fill="{EAR_IN}"/>',
    f'<path d="M50 14 C48 4 44 -2 40 -6" fill="none" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>',
    f'<path d="M50 14 C50 5 49 0 47 -6" fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round"/>',
    f'<path d="M110 14 C112 4 116 -2 120 -6" fill="none" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>',
    f'<path d="M110 14 C110 5 111 0 113 -6" fill="none" stroke="{INK}" stroke-width="2.4" stroke-linecap="round"/>',
    f'<path d="M50 14 L54 26 M110 14 L106 26" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>',
    # Head
    f'<path d="M80 46 C108 46 124 64 122 88 C120 108 104 122 80 122 C56 122 40 108 38 88 C36 64 52 46 80 46 Z" '
    f'fill="{TAWNY}" stroke="{LINE}" stroke-width="2.4"/>',
    # Pale eye patches and muzzle
    f'<ellipse cx="63" cy="82" rx="12" ry="9" fill="{CREAM}"/>',
    f'<ellipse cx="97" cy="82" rx="12" ry="9" fill="{CREAM}"/>',
    f'<path d="M62 104 C62 94 70 90 80 90 C90 90 98 94 98 104 C98 114 90 118 80 118 C70 118 62 114 62 104 Z" fill="{CREAM}"/>',
    # Dark forehead streaks
    f'<path d="M74 52 L76 66 M80 50 L80 64 M86 52 L84 66" stroke="{TAWNY_DARK}" stroke-width="2.4" stroke-linecap="round"/>',
    # Eyes: golden, vertical pupils, a highlight
    f'<path d="M53 82 Q63 72 73 82 Q63 90 53 82 Z" fill="{EYE}" stroke="{INK}" stroke-width="1.8"/>',
    f'<path d="M87 82 Q97 72 107 82 Q97 90 87 82 Z" fill="{EYE}" stroke="{INK}" stroke-width="1.8"/>',
    f'<ellipse cx="63" cy="81.5" rx="2.2" ry="5" fill="{INK}"/>',
    f'<ellipse cx="97" cy="81.5" rx="2.2" ry="5" fill="{INK}"/>',
    '<circle cx="64.6" cy="79" r="1.3" fill="#FFFFFF"/><circle cx="98.6" cy="79" r="1.3" fill="#FFFFFF"/>',
    # Tear lines from the eyes towards the muzzle
    f'<path d="M71 86 C73 92 72 96 70 99 M89 86 C87 92 88 96 90 99" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>',
    # Nose, mouth, whisker spots
    f'<path d="M73 97 Q80 94 87 97 Q84 103 80 104 Q76 103 73 97 Z" fill="{NOSE}" stroke="{INK}" stroke-width="1.4" stroke-linejoin="round"/>',
    f'<path d="M80 104 L80 108 M80 108 Q75 113 71 110 M80 108 Q85 113 89 110" fill="none" stroke="{INK}" stroke-width="1.8" stroke-linecap="round"/>',
    f'<g fill="{INK}"><circle cx="69" cy="105" r="1.2"/><circle cx="66" cy="108" r="1.2"/><circle cx="91" cy="105" r="1.2"/>'
    f'<circle cx="94" cy="108" r="1.2"/></g>',
    # Whiskers
    f'<g stroke="{LINE}" stroke-width="1.1" stroke-linecap="round" opacity="0.75">'
    '<path d="M64 106 L44 102 M64 109 L45 111 M96 106 L116 102 M96 109 L115 111"/></g>',
]

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="24 -10 112 172" role="img" '
       'aria-label="Anaq, the Athar Al Anaq mascot: an Arabian caracal with black-tufted ears">\n  '
       + "\n  ".join(parts) + "\n</svg>\n")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote", OUT)

# Avatar for the AI assistant: the same head, cropped square on a soft sand disc.
avatar_path = OUT.replace(".svg", "_avatar.svg")
avatar = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 -8 132 132" role="img" '
          'aria-label="Anaq, the Athar Al Anaq assistant">\n  <circle cx="80" cy="58" r="66" fill="#F4E4CC"/>\n  '
          + "\n  ".join(parts[2:]) + "\n</svg>\n")  # parts[2:] = ears, head and face (no shoulders)
with open(avatar_path, "w", encoding="utf-8") as f:
    f.write(avatar)
print("wrote", avatar_path)
