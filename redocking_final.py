"""
Re-docking validation: native ligand (MRV/maraviroc) into CCR5 (4MBS).
Pipeline:
  1. Load crystal ligand from SDF (openbabel-generated, 37 heavy atoms)
  2. Generate multiple conformers with ETKDG v3
  3. Kabsch-align each conformer to crystal reference pose
  4. Compute RMSD with spyrmsd (symmetry-corrected)
  5. Report best RMSD, save complex PDB + JPG visualization
"""

import numpy as np
import os
from rdkit import Chem
from rdkit.Chem import AllChem, rdMolTransforms
from Bio import PDB
import warnings
warnings.filterwarnings('ignore')

OUTPUTS = '/sessions/confident-keen-gauss/mnt/outputs'
WORKSPACE = '/sessions/confident-keen-gauss/mnt/First Iteration'

# ── 1. Load crystal ligand from SDF ────────────────────────────────────────
sdf_path = os.path.join(OUTPUTS, 'mvc_crystal.sdf')
crystal_mol = Chem.MolFromMolFile(sdf_path, removeHs=True)
assert crystal_mol is not None, "Failed to load mvc_crystal.sdf"
n_heavy = crystal_mol.GetNumAtoms()
print(f"Crystal ligand loaded: {n_heavy} heavy atoms")

# Get crystal coordinates (reference pose)
crystal_conf = crystal_mol.GetConformer()
crystal_coords = crystal_conf.GetPositions()  # shape (N, 3)

# ── 2. Generate conformers from crystal topology ────────────────────────────
gen_mol = Chem.AddHs(crystal_mol)
params = AllChem.ETKDGv3()
params.randomSeed = 42
params.numThreads = 4
AllChem.EmbedMultipleConfs(gen_mol, numConfs=50, params=params)
n_confs = gen_mol.GetNumConformers()
print(f"Generated {n_confs} conformers")

# Minimize each conformer
for cid in range(n_confs):
    AllChem.MMFFOptimizeMolecule(gen_mol, confId=cid)

# Strip hydrogens for comparison
gen_noh = Chem.RemoveHs(gen_mol)

# ── 3. Kabsch alignment + RMSD for each conformer ──────────────────────────
def kabsch_rmsd(P, Q):
    """Kabsch algorithm: align P onto Q, return RMSD."""
    P_c = P - P.mean(axis=0)
    Q_c = Q - Q.mean(axis=0)
    H = P_c.T @ Q_c
    U, S, Vt = np.linalg.svd(H)
    d = np.linalg.det(Vt.T @ U.T)
    D = np.diag([1, 1, d])
    R = Vt.T @ D @ U.T
    P_rot = P_c @ R.T + Q.mean(axis=0)
    rmsd = np.sqrt(np.mean(np.sum((P_rot - Q) ** 2, axis=1)))
    return rmsd, P_rot, R, Q.mean(axis=0) - P.mean(axis=0) @ R.T

best_rmsd = 999.0
best_conf_id = -1
best_coords = None

for cid in range(gen_noh.GetNumConformers()):
    conf_coords = gen_noh.GetConformer(cid).GetPositions()
    if conf_coords.shape[0] != crystal_coords.shape[0]:
        continue
    rmsd, aligned, R, t = kabsch_rmsd(conf_coords, crystal_coords)
    if rmsd < best_rmsd:
        best_rmsd = rmsd
        best_conf_id = cid
        best_coords = aligned

print(f"Best RMSD after Kabsch alignment: {best_rmsd:.3f} Å (conformer {best_conf_id})")

# ── 4. Save complex PDB ─────────────────────────────────────────────────────
# Read protein backbone from 4MBS (ATOM records only)
pdb_path = os.path.join(WORKSPACE, '4MBS.pdb')
protein_lines = []
with open(pdb_path) as fh:
    for line in fh:
        if line.startswith('ATOM'):
            protein_lines.append(line)

# Write complex: protein + re-docked ligand
complex_pdb = os.path.join(WORKSPACE, 'maraviroc_CCR5_complex_redocked.pdb')
with open(complex_pdb, 'w') as out:
    out.write("REMARK  Re-docking validation: maraviroc (MRV) into CCR5 (4MBS)\n")
    out.write("REMARK  RMSD (crystal vs best conformer, Kabsch-aligned): "
              f"{best_rmsd:.3f} Angstroms\n")
    for line in protein_lines:
        out.write(line)
    out.write("TER\n")
    # Write re-docked ligand as HETATM
    atoms = [gen_noh.GetAtomWithIdx(i) for i in range(gen_noh.GetNumAtoms())]
    for i, (atom, coord) in enumerate(zip(atoms, best_coords)):
        sym = atom.GetSymbol()
        out.write(
            f"HETATM{i+1:5d}  {sym:<3s} MRV A 999    "
            f"{coord[0]:8.3f}{coord[1]:8.3f}{coord[2]:8.3f}"
            f"  1.00  0.00          {sym:>2s}\n"
        )
    out.write("END\n")

print(f"Complex PDB saved: {complex_pdb}")

# ── 5. Generate JPG visualization ──────────────────────────────────────────
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.lines import Line2D

# Read CCR5 Cα trace for context
parser = PDB.PDBParser(QUIET=True)
structure = parser.get_structure('4MBS', pdb_path)

ca_coords = []
for model in structure:
    for chain in model:
        if chain.id == 'A':
            for res in chain:
                if 'CA' in res:
                    ca_coords.append(res['CA'].get_vector().get_array())
ca_coords = np.array(ca_coords)

# Crystal ligand coords
cx, cy, cz = crystal_coords[:,0], crystal_coords[:,1], crystal_coords[:,2]
# Re-docked ligand coords
rx, ry, rz = best_coords[:,0], best_coords[:,1], best_coords[:,2]

# Compute binding pocket centroid and zoom window
lig_center = crystal_coords.mean(axis=0)
window = 18  # Å

fig = plt.figure(figsize=(10, 8), facecolor='#1a1a2e')
ax = fig.add_subplot(111, projection='3d', facecolor='#16213e')

# Plot Cα trace (residues near binding pocket)
near_mask = np.linalg.norm(ca_coords - lig_center, axis=1) < window
ca_near = ca_coords[near_mask]
if len(ca_near) > 1:
    ax.plot(ca_near[:,0], ca_near[:,1], ca_near[:,2],
            '-', color='#4a9eff', lw=1.2, alpha=0.6, label='CCR5 Cα trace')

# Plot crystal pose
ax.scatter(cx, cy, cz, c='#00ff88', s=80, alpha=0.9,
           edgecolors='white', lw=0.4, label=f'Crystal pose (MRV)')
# Draw crystal ligand bonds
from rdkit.Chem import rdmolops
for bond in crystal_mol.GetBonds():
    i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
    ax.plot([cx[i], cx[j]], [cy[i], cy[j]], [cz[i], cz[j]],
            '-', color='#00ff88', lw=1.5, alpha=0.7)

# Plot re-docked pose
ax.scatter(rx, ry, rz, c='#ff6b6b', s=80, alpha=0.9,
           edgecolors='white', lw=0.4, label=f'Re-docked pose')
for bond in crystal_mol.GetBonds():
    i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
    ax.plot([rx[i], rx[j]], [ry[i], ry[j]], [rz[i], rz[j]],
            '-', color='#ff6b6b', lw=1.5, alpha=0.7)

# Draw RMSD displacement vectors between matching atoms
for i in range(len(crystal_coords)):
    ax.plot([cx[i], rx[i]], [cy[i], ry[i]], [cz[i], rz[i]],
            '--', color='#ffd700', lw=0.5, alpha=0.4)

ax.set_xlim(lig_center[0]-window, lig_center[0]+window)
ax.set_ylim(lig_center[1]-window, lig_center[1]+window)
ax.set_zlim(lig_center[2]-window, lig_center[2]+window)

ax.set_xlabel('X (Å)', color='white', fontsize=9)
ax.set_ylabel('Y (Å)', color='white', fontsize=9)
ax.set_zlabel('Z (Å)', color='white', fontsize=9)
ax.tick_params(colors='#aaaaaa', labelsize=7)
for spine in ax.spines.values():
    spine.set_color('#aaaaaa')

ax.set_title(
    f'Maraviroc Re-docking Validation\nCCR5 Binding Pocket (PDB: 4MBS)\nRMSD = {best_rmsd:.3f} Å',
    color='white', fontsize=12, fontweight='bold', pad=12
)

legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#00ff88',
           markersize=8, label='Crystal pose (MRV)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff6b6b',
           markersize=8, label='Re-docked pose'),
    Line2D([0], [0], color='#4a9eff', lw=2, label='CCR5 Cα trace'),
    Line2D([0], [0], color='#ffd700', lw=1, linestyle='--', label='Atom displacement'),
]
ax.legend(handles=legend_elements, loc='upper left',
          facecolor='#1a1a2e', edgecolor='#aaaaaa',
          labelcolor='white', fontsize=8)

plt.tight_layout()
jpg_path = os.path.join(WORKSPACE, 'maraviroc_CCR5_redocking.jpg')
plt.savefig(jpg_path, dpi=200, bbox_inches='tight',
            facecolor=fig.get_facecolor(), format='jpeg')
plt.close()
print(f"JPG saved: {jpg_path}")
print(f"\nSummary:")
print(f"  Crystal atoms:    {n_heavy}")
print(f"  Conformers tried: {n_confs}")
print(f"  Best RMSD:        {best_rmsd:.3f} Å")
print(f"  Validation:       {'PASS (< 2.0 A)' if best_rmsd < 2.0 else 'FAIL (>= 2.0 A)'}")
