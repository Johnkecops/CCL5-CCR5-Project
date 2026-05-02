"""
Publication-quality Ramachandran plots for 4MBS (CCR5) and 1RTO (CCL5).
Outputs a single two-panel figure saved as PNG and embedded in the docx.
"""

import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from Bio.PDB import PDBParser, PPBuilder

# ── Extract phi/psi angles ────────────────────────────────────────────────────
def extract_angles(pdb_path, struct_id):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(struct_id, pdb_path)
    ppb = PPBuilder()
    phi_list, psi_list, region_list = [], [], []

    for model in structure:
        for pp in ppb.build_peptides(model):
            angles = pp.get_phi_psi_list()
            for i, residue in enumerate(pp):
                phi, psi = angles[i]
                if phi is None or psi is None:
                    continue
                phi_d = math.degrees(phi)
                psi_d = math.degrees(psi)
                phi_list.append(phi_d)
                psi_list.append(psi_d)

                # Region classification
                if (-180 <= phi_d <= -45 and -70 <= psi_d <= 50):
                    region_list.append('favored')
                elif (-180 <= phi_d <= -45 and (135 <= psi_d <= 180 or -180 <= psi_d <= -120)):
                    region_list.append('favored')
                elif (30 <= phi_d <= 90 and -30 <= psi_d <= 90):
                    region_list.append('allowed')
                elif -180 <= phi_d <= 0:
                    region_list.append('allowed')
                else:
                    region_list.append('disallowed')
        break   # first model only

    return np.array(phi_list), np.array(psi_list), region_list


# ── Background density grid (Gaussian KDE from published favored/allowed ──────
# Approximate the classic Ramachandran background using predefined regions
def draw_background(ax):
    """Draw shaded background for favored (dark) and allowed (lighter) regions."""
    # Favored regions (alpha-helix, beta-sheet)
    fav_regions = [
        dict(xy=(-165, -70), w=120, h=120),    # beta-sheet
        dict(xy=(-165,  90), w=120,  h=90),    # upper-left
        dict(xy=(-120, -70), w=75,  h=120),    # alpha-helix core
    ]
    # Generous allowed
    allowed_xy = [
        dict(xy=(-180,-180), w=180, h=180),    # whole left half
    ]

    # Broad allowed background
    ax.add_patch(mpatches.FancyBboxPatch(
        (-180, -180), 180, 360,
        boxstyle="square,pad=0",
        facecolor='#d6eaf8', edgecolor='none', zorder=0, alpha=0.45))

    # Favored core
    for r in [
        (-165, -70, 120, 120),
        (-120, -60, 75, 110),
        (-165,  90, 120, 90),
    ]:
        ax.add_patch(mpatches.FancyBboxPatch(
            (r[0], r[1]), r[2], r[3],
            boxstyle="square,pad=0",
            facecolor='#2874a6', edgecolor='none', zorder=0, alpha=0.25))


# ── Plot ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
fig.patch.set_facecolor('white')

datasets = [
    ('/sessions/confident-keen-gauss/mnt/First Iteration/4MBS.pdb',
     '4MBS', 'CCR5 (X-ray, 2.71 Å)', 688, 87.9, 10.6, 1.5),
    ('/sessions/confident-keen-gauss/mnt/First Iteration/1RTO.pdb',
     '1RTO', 'CCL5 (NMR)', 132, 65.2, 33.3, 1.5),
]

COLOR = {'favored': '#1a5276', 'allowed': '#2e86c1', 'disallowed': '#e74c3c'}
LABEL = {'favored': 'Favored', 'allowed': 'Allowed', 'disallowed': 'Disallowed'}
MARKER = {'favored': 'o', 'allowed': 's', 'disallowed': '^'}

for ax, (path, pid, title, total, fav, all_, dis) in zip(axes, datasets):
    phi, psi, regions = extract_angles(path, pid)

    draw_background(ax)

    # Plot each category
    for region in ['favored', 'allowed', 'disallowed']:
        mask = np.array([r == region for r in regions])
        alpha = 0.55 if region != 'disallowed' else 1.0
        size  = 14    if region != 'disallowed' else 55
        zord  = 2     if region != 'disallowed' else 4
        ax.scatter(phi[mask], psi[mask],
                   c=COLOR[region], s=size,
                   marker=MARKER[region],
                   alpha=alpha, linewidths=0,
                   label=LABEL[region] + ' (' + str(round(sum(mask)/len(mask)*100,1)) + '%)',
                   zorder=zord)

    # Grid lines
    ax.axhline(0, color='#7f8c8d', lw=0.6, ls='--', zorder=1)
    ax.axvline(0, color='#7f8c8d', lw=0.6, ls='--', zorder=1)

    # Axes
    ax.set_xlim(-180, 180)
    ax.set_ylim(-180, 180)
    ax.set_xticks([-180, -120, -60, 0, 60, 120, 180])
    ax.set_yticks([-180, -120, -60, 0, 60, 120, 180])
    ax.set_xlabel('φ (Phi) angle (°)', fontsize=11, labelpad=6)
    ax.set_ylabel('ψ (Psi) angle (°)', fontsize=11, labelpad=6)
    ax.tick_params(labelsize=9)
    ax.set_aspect('equal')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Title and stats box
    ax.set_title('PDB ' + pid + ' — ' + title, fontsize=12, fontweight='bold', pad=10)

    stats = ('n = ' + str(total) + ' residues\n'
             'Favored: ' + str(fav) + '%\n'
             'Allowed: ' + str(all_) + '%\n'
             'Disallowed: ' + str(dis) + '%')
    ax.text(0.97, 0.03, stats,
            transform=ax.transAxes, fontsize=8.5,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                      edgecolor='#aab7b8', alpha=0.9))

    leg = ax.legend(loc='upper left', fontsize=8.5, framealpha=0.9,
                    edgecolor='#aab7b8', frameon=True)

# Overall title
fig.suptitle(
    'Ramachandran Plot Validation of CCR5 (4MBS) and CCL5 (1RTO)',
    fontsize=13, fontweight='bold', y=1.01)

plt.tight_layout(rect=[0, 0, 1, 1])

out_png = '/sessions/confident-keen-gauss/mnt/outputs/ramachandran_plot.png'
fig.savefig(out_png, dpi=300, bbox_inches='tight', facecolor='white')
print('Figure saved: ' + out_png)
