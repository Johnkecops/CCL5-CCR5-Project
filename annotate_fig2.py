"""
Add CCR5 / CCL5 labels with arrows to Figure 2.

Spatial analysis result:
  Green (CCR5) — large GPCR — extends across left edge, top, right edge, bottom
  Cyan  (CCL5) — small chemokine — concentrated in center (x:280-540, y:220-430)

Label placement:
  CCR5: label box upper-left (80, 130) → arrow to left-edge green zone (140, 373)
  CCL5: label box right side (590, 250) → arrow to cyan-dominant center (460, 355)
"""

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

src = '/sessions/confident-keen-gauss/mnt/outputs/figure2_original.png'
dst = '/sessions/confident-keen-gauss/mnt/First Iteration/figure2_annotated.jpg'

img = Image.open(src).convert('RGB')
arr = np.array(img)
h_px, w_px = arr.shape[:2]   # 598 x 758

# Figure sized to exact pixel dimensions at 100 dpi
dpi = 100
fig_w = w_px / dpi
fig_h = h_px / dpi

fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
ax.imshow(arr, origin='upper')
ax.set_xlim(0, w_px)
ax.set_ylim(h_px, 0)   # origin='upper' → y increases downward
ax.axis('off')

# ── Annotation style ──────────────────────────────────────────────────────────
LABEL_BBOX = dict(boxstyle='round,pad=0.4', facecolor='white',
                  edgecolor='#333333', linewidth=1.8, alpha=0.92)

ARROW_PROPS = dict(arrowstyle='->', color='white',
                   lw=2.0,
                   connectionstyle='arc3,rad=0.15')

def add_label(ax, label, lx, ly, ax_, ay_, color, bg_color='white'):
    """Place a text label at (lx,ly) with an arrow to (ax_,ay_)."""
    # Arrow
    ax.annotate(
        '',
        xy=(ax_, ay_),          # arrow tip (protein)
        xytext=(lx, ly),        # label anchor
        arrowprops=dict(
            arrowstyle='->',
            color=color,
            lw=2.2,
            connectionstyle='arc3,rad=0.18',
        ),
        annotation_clip=False,
    )
    # Text box
    bbox = dict(boxstyle='round,pad=0.45', facecolor=bg_color,
                edgecolor=color, linewidth=2.0, alpha=0.94)
    ax.text(lx, ly, label,
            fontsize=13, fontweight='bold', color='#111111',
            ha='center', va='center',
            bbox=bbox, zorder=10)

# ── CCR5 label ────────────────────────────────────────────────────────────────
# Green pixels cluster on left edge (x≈94, y≈373) and upper regions.
# Place label at upper-left, arrow pointing to the left green region.
add_label(ax,
          label='CCR5',
          lx=95,  ly=140,     # label position (upper-left)
          ax_=130, ay_=345,   # arrow tip (green left-centre)
          color='#2ecc71',    # match green
          bg_color='#f0fff4')

# ── CCL5 label ────────────────────────────────────────────────────────────────
# Cyan pixels dominate at grid(2,2) centre ≈ (473, 373).
# Place label at right side, arrow pointing to cyan centre.
add_label(ax,
          label='CCL5',
          lx=640, ly=260,     # label position (right side)
          ax_=480, ay_=355,   # arrow tip (cyan-dominant centre)
          color='#00bcd4',    # match cyan
          bg_color='#e0f7fa')

# ── Second CCR5 arrow pointing to right-side green region ────────────────────
# Grid(1,3) center=(663, 224) is another green-only zone.
ax.annotate(
    '',
    xy=(645, 240),       # arrow tip (right-edge green)
    xytext=(95, 140),    # same CCR5 label anchor
    arrowprops=dict(
        arrowstyle='->',
        color='#2ecc71',
        lw=1.6,
        connectionstyle='arc3,rad=-0.25',
        linestyle='dashed',
    ),
    annotation_clip=False,
)

fig.savefig(dst, dpi=dpi, bbox_inches='tight', pad_inches=0, format='jpeg')
plt.close(fig)
print(f"Annotated Figure 2 saved: {dst}")
