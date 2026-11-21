"""Run:  .venv/Scripts/python tools/make_dhab.py assets/dhab.svg

Draws Dhab, the ScamSayyad mascot: an Arabian spiny-tailed lizard seen from above,
legs splayed, holding a magnifying glass in its front foot. Writes assets/dhab.svg."""
import math
import sys

OUT = sys.argv[1]
SAND, SAND_DARK, BELLY, LINE, SPOT = "#D9A441", "#C98F34", "#F2D28B", "#7A5218", "#B07A2A"
TEAL = "#0B6B63"
parts = []


def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t**3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def limb(shoulder, elbow, foot, toe_dir, width=7):
    """A bent leg (shoulder -> elbow -> foot) with four splayed toes."""
    d = f"M{shoulder[0]},{shoulder[1]} Q{elbow[0]},{elbow[1]} {foot[0]},{foot[1]}"
    parts.append(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="{width + 3}" stroke-linecap="round"/>')
    parts.append(f'<path d="{d}" fill="none" stroke="{SAND_DARK}" stroke-width="{width}" stroke-linecap="round"/>')
    for k in (-48, -16, 16, 48):
        a = math.radians(toe_dir + k)
        x, y = foot[0] + 8 * math.cos(a), foot[1] + 8 * math.sin(a)
        parts.append(f'<line x1="{foot[0]}" y1="{foot[1]}" x2="{x:.1f}" y2="{y:.1f}" stroke="{LINE}" '
                     f'stroke-width="3.4" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="{LINE}"/>')


# --- Tail: a curving taper with rings of spikes (the dhab's signature) ---------------
P = [(86, 104), (86, 128), (70, 148), (40, 154)]
N = 9
for i in range(N, -1, -1):  # draw from tip back to base so the base overlaps
    t = i / N
    x, y = bezier(*P, t)
    r = 11.5 - 9 * t
    x2, y2 = bezier(*P, min(t + 0.02, 1))
    ang = math.atan2(y2 - y, x2 - x)
    nx, ny = -math.sin(ang), math.cos(ang)
    for side in (1, -1):  # a spike on each side of every ring
        bx, by = x + side * nx * r * 0.8, y + side * ny * r * 0.8
        tip = (x + side * nx * (r + 5 - 2.5 * t) - math.cos(ang) * 3, y + side * ny * (r + 5 - 2.5 * t) - math.sin(ang) * 3)
        b1 = (bx + math.cos(ang) * 3, by + math.sin(ang) * 3)
        b2 = (bx - math.cos(ang) * 3, by - math.sin(ang) * 3)
        parts.append(f'<path d="M{b1[0]:.1f},{b1[1]:.1f} L{tip[0]:.1f},{tip[1]:.1f} L{b2[0]:.1f},{b2[1]:.1f} Z" '
                     f'fill="{SPOT}" stroke="{LINE}" stroke-width="1.2" stroke-linejoin="round"/>')
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{SAND_DARK}" stroke="{LINE}" stroke-width="1.8"/>')

# --- Legs, splayed out like a lizard flat on the sand -------------------------------
limb((70, 92), (50, 100), (44, 116), 120)    # back left
limb((102, 92), (122, 98), (128, 114), 60)   # back right
limb((68, 56), (48, 52), (40, 38), 220)      # front left

# --- Body: wide and flat, with a pale edge and darker spots -------------------------
parts.append(f'<ellipse cx="86" cy="74" rx="26" ry="33" fill="{SAND}" stroke="{LINE}" stroke-width="2.2"/>')
parts.append(f'<ellipse cx="86" cy="74" rx="17" ry="25" fill="none" stroke="{BELLY}" stroke-width="2" opacity="0.7"/>')
for cx, cy, rx, ry in [(77, 62, 4.5, 3), (95, 62, 4.5, 3), (73, 78, 4.5, 3), (99, 78, 4.5, 3),
                       (79, 92, 4, 2.6), (93, 92, 4, 2.6), (86, 70, 3, 2.2), (86, 84, 3, 2.2)]:
    parts.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{SPOT}" opacity="0.9"/>')

# --- Head: round and blunt, eyes on the sides ---------------------------------------
parts.append(f'<path d="M86 52 Q70 50 70 34 Q72 18 86 16 Q100 18 102 34 Q102 50 86 52 Z" '
             f'fill="{SAND}" stroke="{LINE}" stroke-width="2.2"/>')
for ex in (74, 98):
    parts.append(f'<circle cx="{ex}" cy="30" r="5.2" fill="#FFFFFF" stroke="{LINE}" stroke-width="1.6"/>')
    parts.append(f'<circle cx="{ex + (1.6 if ex > 86 else -1.6)}" cy="28.5" r="2.6" fill="#2B1A08"/>')
    parts.append(f'<circle cx="{ex + (2.4 if ex > 86 else -0.8)}" cy="27.6" r="0.9" fill="#FFFFFF"/>')
parts.append(f'<circle cx="82" cy="20" r="1.1" fill="{LINE}"/><circle cx="90" cy="20" r="1.1" fill="{LINE}"/>')

# --- Front right leg holding the magnifying glass up in front of the face -----------
limb((104, 56), (124, 50), (128, 36), 300)
# Handle runs from the foot to the lens, so the foot is clearly gripping it.
parts.append(f'<line x1="128" y1="36" x2="122" y2="22" stroke="{TEAL}" stroke-width="5.5" stroke-linecap="round"/>')
parts.append(f'<circle cx="114" cy="10" r="11" fill="#BFE7E2" fill-opacity="0.6" stroke="{TEAL}" stroke-width="4.5"/>')
parts.append('<path d="M108 6 Q111 2 116 2" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" opacity="0.9"/>')
# Toes wrapped over the handle
parts.append(f'<circle cx="128" cy="36" r="4.5" fill="{SAND_DARK}" stroke="{LINE}" stroke-width="1.8"/>')

svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="20 -6 132 168" role="img" '
       'aria-label="Dhab, the ScamSayyad mascot: an Arabian spiny-tailed lizard seen from above, '
       'holding a magnifying glass">\n  ' + "\n  ".join(parts) + "\n</svg>\n")
open(OUT, "w", encoding="utf-8").write(svg)
print("wrote", OUT, len(svg), "bytes")
