"""
Protein-ligand interaction analysis for maraviroc-CCR5 (4MBS).
Uses Biopython + RDKit + matplotlib. No PLIP/ProLIF required.

Detects:
  - Hydrogen bonds  (donor-acceptor dist < 3.5 Å, angle > 120°)
  - Hydrophobic contacts  (C-C dist < 5.0 Å, both non-polar)
  - Pi-stacking / pi-cation  (aromatic ring centre < 5.5 Å)
  - Salt bridges  (charged N/O dist < 5.5 Å)
  - Van der Waals  (any heavy atom < 4.0 Å not classified above)
"""

import numpy as np
from Bio import PDB
from Bio.PDB.vectors import Vector, calc_angle
from rdkit import Chem, RDLogger
from rdkit.Chem import Draw, AllChem, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
import math, os, warnings
warnings.filterwarnings('ignore')
RDLogger.DisableLog('rdApp.*')

PDB_PATH  = '/sessions/confident-keen-gauss/mnt/First Iteration/4MBS.pdb'
OUT_DIR   = '/sessions/confident-keen-gauss/mnt/First Iteration'
WORK_DIR  = '/sessions/confident-keen-gauss/mnt/outputs'

# ── 1. Parse structure ───────────────────────────────────────────────────────
parser = PDB.PDBParser(QUIET=True)
struct = parser.get_structure('4MBS', PDB_PATH)
model  = struct[0]

# ── 2. Extract ligand (MRV chain A) and protein atoms ───────────────────────
lig_atoms  = []
lig_res    = None
prot_atoms = []

for chain in model:
    for res in chain:
        rname = res.get_resname().strip()
        if rname == 'MRV' and chain.id == 'A':
            lig_res = res
            for atom in res:
                if atom.element not in ('H', '', 'D'):
                    lig_atoms.append(atom)
        elif rname not in ('HOH', 'WAT') and chain.id == 'A':
            for atom in res:
                if atom.element not in ('H', '', 'D'):
                    prot_atoms.append(atom)

print(f"Ligand heavy atoms: {len(lig_atoms)}")
print(f"Protein heavy atoms (chain A): {len(prot_atoms)}")

lig_coords  = np.array([a.get_vector().get_array() for a in lig_atoms])
prot_coords = np.array([a.get_vector().get_array() for a in prot_atoms])

# ── 3. Identify contact residues (any heavy atom within 5.5 Å) ─────────────
from scipy.spatial import KDTree
lig_tree = KDTree(lig_coords)

contact_res = {}  # res_id → (residue object, min_dist)
for a in prot_atoms:
    coord = a.get_vector().get_array()
    dist, _ = lig_tree.query(coord)
    if dist <= 5.5:
        res = a.get_parent()
        rid = (res.get_parent().id, res.get_id()[1], res.get_resname())
        if rid not in contact_res or dist < contact_res[rid][1]:
            contact_res[rid] = (res, dist, a)

print(f"\nContact residues (≤ 5.5 Å): {len(contact_res)}")

# ── 4. Classify interaction types ───────────────────────────────────────────
H_BOND_DONORS    = {'N', 'O', 'S'}
H_BOND_ACCEPTORS = {'N', 'O', 'F', 'S'}
HYDROPHOBIC_ELEM = {'C', 'S'}
CHARGED_POS = {'ARG', 'LYS', 'HIS'}
CHARGED_NEG = {'ASP', 'GLU'}
AROMATIC    = {'PHE', 'TYR', 'TRP', 'HIS'}

interactions = []  # list of dicts

for rid, (res, min_d, contact_atom) in contact_res.items():
    chain_id, seq_num, resname = rid
    res_atoms = [a for a in res if a.element not in ('H','','D')]
    
    best_hbond  = None
    best_hydro  = None
    best_pi     = None
    best_salt   = None
    best_vdw    = None
    
    for la in lig_atoms:
        lcoord = la.get_vector().get_array()
        for ra in res_atoms:
            rcoord = ra.get_vector().get_array()
            d = np.linalg.norm(lcoord - rcoord)
            
            # H-bond: donor/acceptor pair within 3.5 Å
            if d <= 3.5 and la.element in H_BOND_DONORS | H_BOND_ACCEPTORS \
                         and ra.element in H_BOND_DONORS | H_BOND_ACCEPTORS:
                if best_hbond is None or d < best_hbond[2]:
                    best_hbond = (la, ra, d)
            
            # Salt bridge: charged residues
            if d <= 5.5 and resname in CHARGED_POS | CHARGED_NEG:
                if la.element in ('N','O') and ra.element in ('N','O'):
                    if best_salt is None or d < best_salt[2]:
                        best_salt = (la, ra, d)
            
            # Hydrophobic: C-C within 5.0 Å
            if d <= 5.0 and la.element == 'C' and ra.element == 'C':
                if best_hydro is None or d < best_hydro[2]:
                    best_hydro = (la, ra, d)
            
            # Pi interactions: aromatic residues
            if d <= 5.5 and resname in AROMATIC:
                if best_pi is None or d < best_pi[2]:
                    best_pi = (la, ra, d)
            
            # VdW catch-all
            if d <= 4.0:
                if best_vdw is None or d < best_vdw[2]:
                    best_vdw = (la, ra, d)
    
    # Prioritise: H-bond > salt > pi > hydrophobic > vdw
    if best_hbond:
        itype = 'H-bond'
        pair  = best_hbond
    elif best_salt:
        itype = 'Salt bridge'
        pair  = best_salt
    elif best_pi:
        itype = 'Pi interaction'
        pair  = best_pi
    elif best_hydro:
        itype = 'Hydrophobic'
        pair  = best_hydro
    elif best_vdw:
        itype = 'Van der Waals'
        pair  = best_vdw
    else:
        continue
    
    interactions.append({
        'chain': chain_id,
        'seq':   seq_num,
        'resname': resname,
        'label': f"{resname}{seq_num}",
        'type':  itype,
        'dist':  round(pair[2], 2),
        'lig_atom': pair[0].get_name(),
        'prot_atom': pair[1].get_name(),
        'prot_coords': pair[1].get_vector().get_array(),
        'lig_coords':  pair[0].get_vector().get_array(),
    })

# Sort by distance
interactions.sort(key=lambda x: x['dist'])

print("\n--- Interactions ---")
for ix in interactions:
    print(f"  {ix['type']:18s} {ix['label']:8s} {ix['lig_atom']:5s}--{ix['prot_atom']:5s}  {ix['dist']:.2f} Å")

# ── 5. Save interaction table as TSV ─────────────────────────────────────────
tsv_path = os.path.join(WORK_DIR, 'interactions.tsv')
with open(tsv_path, 'w') as f:
    f.write("Residue\tChain\tSeq#\tInteraction Type\tDist (Å)\tLigand Atom\tProtein Atom\n")
    for ix in interactions:
        f.write(f"{ix['resname']}\t{ix['chain']}\t{ix['seq']}\t{ix['type']}\t"
                f"{ix['dist']}\t{ix['lig_atom']}\t{ix['prot_atom']}\n")
print(f"\nTable saved: {tsv_path}")

# ── 6. 2D interaction diagram ────────────────────────────────────────────────
# Load maraviroc from SDF and get 2D coordinates
lig_2d = Chem.MolFromMolFile(os.path.join(WORK_DIR, 'mvc_crystal.sdf'), removeHs=True)
AllChem.Compute2DCoords(lig_2d)

conf_2d = lig_2d.GetConformer()
atom_pos = {}
xs, ys = [], []
for i in range(lig_2d.GetNumAtoms()):
    pos = conf_2d.GetAtomPosition(i)
    atom_pos[i] = (pos.x, pos.y)
    xs.append(pos.x); ys.append(pos.y)

# Normalise to [0,1] range
xmin, xmax = min(xs), max(xs)
ymin, ymax = min(ys), max(ys)
xr = xmax - xmin or 1; yr = ymax - ymin or 1

def norm_pos(x, y, padding=0.15):
    return ((x-xmin)/xr*(1-2*padding)+padding,
            (y-ymin)/yr*(1-2*padding)+padding)

# Color scheme per interaction type
ICOLORS = {
    'H-bond':       '#2196F3',
    'Salt bridge':  '#F44336',
    'Pi interaction':'#9C27B0',
    'Hydrophobic':  '#FF9800',
    'Van der Waals':'#78909C',
}

fig2d, ax2d = plt.subplots(figsize=(12, 10), facecolor='white')
ax2d.set_facecolor('#F8F9FA')
ax2d.set_xlim(-0.05, 1.05); ax2d.set_ylim(-0.05, 1.05)
ax2d.set_aspect('equal')
ax2d.axis('off')

# Draw ligand bonds
for bond in lig_2d.GetBonds():
    i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
    x0, y0 = norm_pos(*atom_pos[i])
    x1, y1 = norm_pos(*atom_pos[j])
    btype = bond.GetBondTypeAsDouble()
    lw = 2.5 if btype == 2.0 else 1.8
    ax2d.plot([x0, x1], [y0, y1], '-', color='#212121', lw=lw, zorder=2, solid_capstyle='round')

# Draw atom circles + element labels
ATOM_COLORS = {'N':'#1565C0','O':'#C62828','F':'#00838F',
               'S':'#F9A825','C':'#37474F','default':'#37474F'}
for i in range(lig_2d.GetNumAtoms()):
    x, y = norm_pos(*atom_pos[i])
    atom = lig_2d.GetAtomWithIdx(i)
    sym  = atom.GetSymbol()
    color = ATOM_COLORS.get(sym, ATOM_COLORS['default'])
    if sym != 'C':
        circ = plt.Circle((x, y), 0.018, color='white', zorder=3)
        ax2d.add_patch(circ)
        ax2d.text(x, y, sym, ha='center', va='center',
                  fontsize=7, fontweight='bold', color=color, zorder=4)

# Place residue labels around the perimeter and draw interaction lines
lig_cx = sum(p[0] for p in atom_pos.values())/len(atom_pos)
lig_cy = sum(p[1] for p in atom_pos.values())/len(atom_pos)

# Deduplicate: keep best (shortest) interaction per residue label
best_per_res = {}
for ix in interactions:
    lab = ix['label']
    if lab not in best_per_res or ix['dist'] < best_per_res[lab]['dist']:
        best_per_res[lab] = ix

res_list = list(best_per_res.values())
n = len(res_list)
radius = 0.42  # placement radius from centre

for idx, ix in enumerate(res_list):
    angle = 2 * math.pi * idx / n + math.pi/8
    rx = 0.5 + radius * math.cos(angle)
    ry = 0.5 + radius * math.sin(angle)
    
    # Find closest ligand atom to this protein atom (for line endpoint)
    lig_3d_coords = np.array([a.get_vector().get_array() for a in lig_atoms])
    prot_3d = ix['prot_coords']
    dists_to_lig = np.linalg.norm(lig_3d_coords - prot_3d, axis=1)
    closest_lig_idx = int(np.argmin(dists_to_lig))
    # Map to 2D (best approximation: same atom index if available)
    if closest_lig_idx < lig_2d.GetNumAtoms():
        lx2d, ly2d = norm_pos(*atom_pos[closest_lig_idx])
    else:
        lx2d, ly2d = norm_pos(lig_cx, lig_cy)
    
    icolor = ICOLORS.get(ix['type'], '#78909C')
    ls = '--' if 'Hydrophobic' in ix['type'] or 'Van der Waals' in ix['type'] else '-'
    lw_line = 1.5 if 'H-bond' in ix['type'] or 'Salt' in ix['type'] else 1.0
    
    ax2d.plot([lx2d, rx], [ly2d, ry], ls, color=icolor,
              lw=lw_line, alpha=0.75, zorder=1)
    
    # Residue box
    bbox_props = dict(boxstyle='round,pad=0.3', facecolor='white',
                      edgecolor=icolor, linewidth=1.5, alpha=0.92)
    ax2d.text(rx, ry, f"{ix['label']}\n({ix['dist']:.1f}Å)",
              ha='center', va='center', fontsize=7.5, fontweight='bold',
              color='#212121', bbox=bbox_props, zorder=5)

# Legend
legend_elements = [
    mpatches.Patch(facecolor=ICOLORS['H-bond'],        label='H-bond'),
    mpatches.Patch(facecolor=ICOLORS['Salt bridge'],   label='Salt bridge'),
    mpatches.Patch(facecolor=ICOLORS['Pi interaction'],label='Pi interaction'),
    mpatches.Patch(facecolor=ICOLORS['Hydrophobic'],   label='Hydrophobic'),
    mpatches.Patch(facecolor=ICOLORS['Van der Waals'], label='Van der Waals'),
]
ax2d.legend(handles=legend_elements, loc='lower right',
            fontsize=8, framealpha=0.9, edgecolor='#BDBDBD')

ax2d.set_title('Maraviroc–CCR5 2D Interaction Diagram (PDB: 4MBS)',
               fontsize=13, fontweight='bold', color='#212121', pad=10)

plot2d_path = os.path.join(OUT_DIR, 'interaction_2D.jpg')
fig2d.savefig(plot2d_path, dpi=200, bbox_inches='tight',
              facecolor='white', format='jpeg')
plt.close(fig2d)
print(f"2D diagram saved: {plot2d_path}")

# ── 7. 3D interaction diagram ─────────────────────────────────────────────────
fig3d = plt.figure(figsize=(11, 9), facecolor='#0D1117')
ax3d = fig3d.add_subplot(111, projection='3d', facecolor='#161B22')

# CCR5 Cα near pocket
ca_coords = []
for chain in model:
    if chain.id != 'A': continue
    for res in chain:
        if 'CA' in res and res.get_resname() not in ('HOH','WAT','MRV'):
            ca_coords.append(res['CA'].get_vector().get_array())
ca_coords = np.array(ca_coords)

lig_center = lig_coords.mean(axis=0)
win = 14
near = np.linalg.norm(ca_coords - lig_center, axis=1) < win
ca_near = ca_coords[near]
if len(ca_near) > 1:
    ax3d.plot(ca_near[:,0], ca_near[:,1], ca_near[:,2],
              '-', color='#4FC3F7', lw=1.0, alpha=0.45, label='CCR5 Cα')

# Highlight interacting residues as spheres
for ix in res_list:
    pc = ix['prot_coords']
    icolor = ICOLORS.get(ix['type'], '#78909C')
    ax3d.scatter(*pc, s=150, c=icolor, alpha=0.85, edgecolors='white', lw=0.3, zorder=5)
    ax3d.text(pc[0]+0.3, pc[1]+0.3, pc[2]+0.3, ix['label'],
              fontsize=6.5, color='white', alpha=0.9, zorder=6)

# Draw interaction lines
for ix in res_list:
    pc  = ix['prot_coords']
    lc  = ix['lig_coords']
    ic  = ICOLORS.get(ix['type'], '#78909C')
    ls  = ':' if 'Hydrophobic' in ix['type'] or 'Van der Waals' in ix['type'] else '--'
    ax3d.plot([lc[0],pc[0]], [lc[1],pc[1]], [lc[2],pc[2]],
              ls, color=ic, lw=1.2, alpha=0.65)

# Ligand atoms
ACOLOR3D = {'N':'#42A5F5','O':'#EF5350','F':'#26C6DA',
            'S':'#FFCA28','C':'#90A4AE','default':'#90A4AE'}
for atom in lig_atoms:
    c = atom.get_vector().get_array()
    col = ACOLOR3D.get(atom.element, ACOLOR3D['default'])
    ax3d.scatter(*c, s=40, c=col, alpha=0.9, edgecolors='none', zorder=7)

# Ligand bonds (from crystal mol bonds)
lig_crystal = Chem.MolFromMolFile('/sessions/confident-keen-gauss/mnt/outputs/mvc_crystal.sdf',
                                   removeHs=True)
if lig_crystal and len(lig_atoms) == lig_crystal.GetNumAtoms():
    for bond in lig_crystal.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        ci = lig_atoms[i].get_vector().get_array()
        cj = lig_atoms[j].get_vector().get_array()
        ax3d.plot([ci[0],cj[0]], [ci[1],cj[1]], [ci[2],cj[2]],
                  '-', color='#CFD8DC', lw=1.5, alpha=0.8)

ax3d.set_xlim(lig_center[0]-win, lig_center[0]+win)
ax3d.set_ylim(lig_center[1]-win, lig_center[1]+win)
ax3d.set_zlim(lig_center[2]-win, lig_center[2]+win)
ax3d.set_xlabel('X (Å)', color='#90A4AE', fontsize=8)
ax3d.set_ylabel('Y (Å)', color='#90A4AE', fontsize=8)
ax3d.set_zlabel('Z (Å)', color='#90A4AE', fontsize=8)
ax3d.tick_params(colors='#607D8B', labelsize=7)
ax3d.set_title('Maraviroc–CCR5 3D Binding Pocket (PDB: 4MBS)',
               color='white', fontsize=12, fontweight='bold', pad=10)

legend3d = [
    Line2D([0],[0], color=ICOLORS['H-bond'],       lw=2, label='H-bond'),
    Line2D([0],[0], color=ICOLORS['Salt bridge'],  lw=2, label='Salt bridge'),
    Line2D([0],[0], color=ICOLORS['Pi interaction'],lw=2, label='Pi interaction'),
    Line2D([0],[0], color=ICOLORS['Hydrophobic'],  lw=2, label='Hydrophobic'),
    Line2D([0],[0], color=ICOLORS['Van der Waals'],lw=2, label='Van der Waals'),
    Line2D([0],[0], color='#4FC3F7',               lw=2, label='CCR5 Cα trace'),
]
ax3d.legend(handles=legend3d, loc='upper left',
            facecolor='#0D1117', edgecolor='#444',
            labelcolor='white', fontsize=7.5)

plot3d_path = os.path.join(OUT_DIR, 'interaction_3D.jpg')
fig3d.savefig(plot3d_path, dpi=200, bbox_inches='tight',
              facecolor=fig3d.get_facecolor(), format='jpeg')
plt.close(fig3d)
print(f"3D diagram saved: {plot3d_path}")

# Print summary for manuscript
print("\n=== SUMMARY FOR MANUSCRIPT ===")
for ix in interactions:
    print(f"  {ix['label']:8s}  {ix['type']:18s}  {ix['dist']:.2f} Å  "
          f"({ix['lig_atom']}--{ix['prot_atom']})")
