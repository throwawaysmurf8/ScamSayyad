"""Draws Anaq (عناق), the Athar Al Anaq mascot: an Arabian caracal, the desert's sharp-eared hunter.

Run:  .venv/Scripts/python tools/make_caracal.py assets/caracal.svg

The whole cat, standing on four long legs, side-on, turning its head to look straight at us: calm and
serious, a hunter that has noticed something. Tall ears with dark rims and the caracal's long black
tufts (the signature), amber eyes with the dark "tear lines" down to the muzzle, black whisker spots,
a pale chin, chest and belly, a short tail with a dark tip. Thin warm outlines and a light rim on the
tufts keep it readable on both the light (sand) and the dark (desert night) theme. Our own drawing.
The side-panel avatar uses the same head on its own.
"""
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/caracal.svg"
TAWNY, TAWNY_LIGHT, TAWNY_DARK = "#D2914F", "#E3AA6C", "#B06F36"
CREAM, WHITE, EAR_RIM, EAR_IN = "#F7ECDD", "#FFF9F1", "#4A2F1E", "#F0D3B2"
INK, LINE, EYE, EYE_DEEP, NOSE = "#24170F", "#6B4423", "#EDB955", "#C98A2E", "#C27866"

DEFS = f"""<defs>
    <radialGradient id="anaq-head" cx="50%" cy="42%" r="62%">
      <stop offset="0" stop-color="{TAWNY_LIGHT}"/><stop offset="0.7" stop-color="{TAWNY}"/>
      <stop offset="1" stop-color="{TAWNY_DARK}"/></radialGradient>
    <linearGradient id="anaq-body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{TAWNY}"/><stop offset="1" stop-color="{TAWNY_DARK}"/></linearGradient>
    <radialGradient id="anaq-eye" cx="45%" cy="40%" r="65%">
      <stop offset="0" stop-color="{EYE}"/><stop offset="1" stop-color="{EYE_DEEP}"/></radialGradient>
  </defs>"""

DARKER = "#9C5F2C"  # the far legs, a shade darker so the body reads in depth
BODY = [
    '<ellipse cx="130" cy="178" rx="70" ry="4" fill="#6B4423" opacity="0.18"/>',  # ground shadow
    # Far legs (behind the body)
    f'<g fill="{DARKER}" stroke="{LINE}" stroke-width="1.4" stroke-linejoin="round">'
    '<path d="M94 126 C96 142 98 158 98 170 Q97 177 103 177 L110 177 Q113 175 108 171 C107 156 106 140 106 128 Z"/>'
    '<path d="M152 120 C154 134 151 146 147 154 C145 160 147 166 149 171 Q148 177 154 177 L161 177 Q164 175 159 170 '
    'C157 164 157 158 160 152 C166 142 168 130 166 118 Z"/></g>',
    # Tail: short, curving down, dark tip
    f'<path d="M188 96 C200 100 208 112 206 128 C205 135 199 137 197 131 C199 118 196 108 186 104 Z" fill="{TAWNY}" '
    f'stroke="{LINE}" stroke-width="1.4" stroke-linejoin="round"/>',
    f'<path d="M198 120 C203 122 206 124 206 128 C205 135 199 137 197 131 C198 127 198 124 198 120 Z" fill="{INK}"/>',
    # Body and neck in one shape
    f'<path d="M92 66 C98 78 104 86 116 90 C138 86 160 86 178 90 C190 93 196 104 194 116 C192 126 186 132 176 133 '
    'C160 134 140 130 124 130 C112 130 100 133 90 131 C78 129 70 120 66 108 C62 98 58 90 56 82 Z" '
    f'fill="url(#anaq-body)" stroke="{LINE}" stroke-width="1.6" stroke-linejoin="round"/>',
    # Pale throat, chest and belly
    f'<path d="M58 86 C64 100 70 112 80 124 C78 108 74 96 70 86 Z" fill="{CREAM}"/>',
    f'<path d="M104 131 C124 127 150 127 172 131 C152 135 124 135 104 131 Z" fill="{CREAM}"/>',
    # Near legs: a front leg and a strong hind leg with its haunch
    f'<g fill="{TAWNY}" stroke="{LINE}" stroke-width="1.5" stroke-linejoin="round">'
    '<path d="M72 118 C74 138 76 156 75 170 Q74 177 81 177 L89 177 Q92 175 88 171 C87 156 88 138 92 124 Z"/>'
    '<path d="M160 98 C178 94 194 104 194 120 C194 132 186 140 182 146 C180 156 182 165 184 171 Q183 177 189 177 '
    'L196 177 Q199 175 194 170 C192 162 192 154 194 148 C200 138 202 120 196 106 C190 96 174 92 160 98 Z"/></g>',
    # Back stripe and a few soft muscle lines
    f'<path d="M120 89 C140 86 160 86 176 90" fill="none" stroke="{TAWNY_DARK}" stroke-width="2" stroke-linecap="round" opacity="0.55"/>',
    f'<path d="M80 106 Q86 116 84 128" fill="none" stroke="{TAWNY_DARK}" stroke-width="1.4" stroke-linecap="round" opacity="0.6"/>',
]

HEAD = [
    # Ear tufts: long, tapering, black, with a light rim so they show on the dark theme too
    f'<g fill="{INK}" stroke="{TAWNY_LIGHT}" stroke-width="0.9" stroke-linejoin="round">'
    '<path d="M43 18 C40 8 36 0 30 -9 C39 -4 46 4 50 15 Z"/>'
    '<path d="M117 18 C120 8 124 0 130 -9 C121 -4 114 4 110 15 Z"/></g>',
    # Ears: dark rim outside, pale fur inside
    f'<path d="M36 88 C32 62 36 36 45 12 C57 28 68 46 74 64 Z" fill="{EAR_RIM}" stroke="{LINE}" stroke-width="1.4" '
    'stroke-linejoin="round"/>',
    f'<path d="M124 88 C128 62 124 36 115 12 C103 28 92 46 86 64 Z" fill="{EAR_RIM}" stroke="{LINE}" '
    'stroke-width="1.4" stroke-linejoin="round"/>',
    f'<path d="M42 80 C40 62 42 44 48 27 C56 40 63 52 67 64 Z" fill="{EAR_IN}"/>',
    f'<path d="M118 80 C120 62 118 44 112 27 C104 40 97 52 93 64 Z" fill="{EAR_IN}"/>',
    f'<path d="M46 70 Q50 60 52 50 M50 74 Q55 64 58 56 M114 70 Q110 60 108 50 M110 74 Q105 64 102 56" fill="none" '
    f'stroke="{WHITE}" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>',
    # Head: broad cheeks, soft shading
    f'<path d="M80 56 C104 56 121 66 127 86 C131 101 125 117 112 127 C102 134 92 137 80 137 C68 137 58 134 48 127 '
    f'C35 117 29 101 33 86 C39 66 56 56 80 56 Z" fill="url(#anaq-head)" stroke="{LINE}" stroke-width="1.6"/>',
    # Forehead markings
    f'<path d="M75 62 C74 70 73 76 73 82 M80 60 L80 78 M85 62 C86 70 87 76 87 82" fill="none" stroke="{TAWNY_DARK}" '
    'stroke-width="1.8" stroke-linecap="round" opacity="0.7"/>',
    # Pale brows and cheeks around the eyes
    f'<g fill="{CREAM}"><ellipse cx="63" cy="78.5" rx="6" ry="2.6" transform="rotate(-8 63 78.5)"/>'
    '<ellipse cx="97" cy="78.5" rx="6" ry="2.6" transform="rotate(8 97 78.5)"/></g>',
    f'<path d="M51 94 C56 103 68 103 73 96 C66 100 57 100 51 94 Z" fill="{CREAM}"/>',
    f'<path d="M109 94 C104 103 92 103 87 96 C94 100 103 100 109 94 Z" fill="{CREAM}"/>',
    f'<path d="M52 84 C58 80 66 80 72 85 M108 84 C102 80 94 80 88 85" fill="none" stroke="{TAWNY_DARK}" '
    'stroke-width="2" stroke-linecap="round"/>',
    # Eyes: amber, slightly narrowed, slit pupils: calm and watchful
    f'<path d="M50 89 C55 83 68 82 73 91 C67 97 55 97 50 89 Z" fill="url(#anaq-eye)" stroke="{INK}" '
    'stroke-width="1.7" stroke-linejoin="round"/>',
    f'<path d="M110 89 C105 83 92 82 87 91 C93 97 105 97 110 89 Z" fill="url(#anaq-eye)" stroke="{INK}" '
    'stroke-width="1.7" stroke-linejoin="round"/>',
    f'<ellipse cx="62" cy="90" rx="2.6" ry="5.4" fill="{INK}"/><ellipse cx="98" cy="90" rx="2.6" ry="5.4" fill="{INK}"/>',
    f'<g fill="{WHITE}"><circle cx="64.2" cy="87.6" r="1.3"/>'
    '<circle cx="100.2" cy="87.6" r="1.3"/></g>',
    # Tear lines: from the inner eye corners down to the whisker pads
    f'<path d="M73 93 C74 99 73 104 69 109 M87 93 C86 99 87 104 91 109" fill="none" stroke="{INK}" '
    'stroke-width="2" stroke-linecap="round"/>',
    # Muzzle, whisker spots, chin
    f'<path d="M63 117 C63 107 71 102 80 102 C89 102 97 107 97 117 C97 127 89 132 80 132 C71 132 63 127 63 117 Z" '
    f'fill="{CREAM}"/>',
    f'<g fill="{INK}" opacity="0.85"><ellipse cx="68" cy="115" rx="4.2" ry="3"/><ellipse cx="92" cy="115" rx="4.2" ry="3"/></g>',
    f'<g fill="{CREAM}"><circle cx="66.5" cy="114.5" r="0.9"/><circle cx="69.5" cy="116" r="0.9"/>'
    '<circle cx="93.5" cy="114.5" r="0.9"/><circle cx="90.5" cy="116" r="0.9"/></g>',
    f'<ellipse cx="80" cy="129" rx="9" ry="4.5" fill="{WHITE}"/>',
    # Nose and a level, closed mouth
    f'<path d="M74 105 Q80 102 86 105 Q84 110.5 80 112 Q76 110.5 74 105 Z" fill="{NOSE}" stroke="{INK}" '
    'stroke-width="1.2" stroke-linejoin="round"/>',
    f'<path d="M80 112 L80 116 M80 116 Q76 118 72.5 117.5 M80 116 Q84 118 87.5 117.5" fill="none" stroke="{INK}" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    # Whiskers
    f'<g fill="none" stroke="{LINE}" stroke-width="0.9" stroke-linecap="round" opacity="0.55">'
    '<path d="M64 116 Q50 111 38 112 M64 119 Q51 119 40 123 M96 116 Q110 111 122 112 M96 119 Q109 119 120 123"/></g>',
]

# The head sits on the neck, scaled down and turned to face us.
HEAD_ON_BODY = '<g transform="translate(20.4 4.5) scale(0.62)">' + "".join(HEAD) + "</g>"
svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="32 -4 182 186" role="img" '
       'aria-label="Anaq, the Athar Al Anaq mascot: an Arabian caracal standing on four legs, looking at us">\n  '
       + DEFS + "\n  " + "\n  ".join(BODY) + "\n  " + HEAD_ON_BODY + "\n</svg>\n")
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print("wrote", OUT)

# Avatar for the AI assistant: the same head, on a soft sand disc.
avatar_path = OUT.replace(".svg", "_avatar.svg")
avatar = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="4 -14 152 152" role="img" '
          'aria-label="Anaq, the Athar Al Anaq assistant">\n  ' + DEFS
          + '\n  <circle cx="80" cy="62" r="76" fill="#F2E3CB"/>\n  ' + "\n  ".join(HEAD) + "\n</svg>\n")
with open(avatar_path, "w", encoding="utf-8") as f:
    f.write(avatar)
print("wrote", avatar_path)
