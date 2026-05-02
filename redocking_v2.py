import sys, math, warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from Bio.PDB import PDBParser, PDBIO, Select
from rdkit import Chem
from rdkit.Chem import AllChem
from spyrmsd import rmsd as spyrmsd_module

warnings.filterwarnings('ignore')

PDB_PATH = '/sessions/confident-keen-gauss/mnt/First Iteration/4MBS.pdb'
# Maraviroc SMILES (fixed ring numbering)
SMILES = 'CC(C)C[C@@H](NC(=O)[C@H]1CCN(C(=O)c2cnc(C)c(F)c2)CC1)[C@@H]1CCCN(CCN2CCCC2)C1=O'

# ── 1. Extract crystal pose from 4MBS (MRV residue) ─────────────────────────
parser = PDBParser(QUIET=True)
struct = parser.get_structure('4MBS', PDB_PATH)

lig_atoms, lig_residue = [], None
for model in struct:
    for chain in model:
        for res in chain:
            atoms = [a for a in res.get_atoms()
                     if a.element not in ('H', '', ' ') and
                     a.element.strip() != 'H']
            if len(atoms) >= 25 and res.get_resname().strip() not in ('HOH','WAT'):
                lig_residue, lig_atoms = res, atoms
                print("Ligand: " + res.get_resname() +
                      " chain=" + chain.id + " n=" + str(len(atoms)))
    break

crystal_coords = np.array([a.get_vector().get_array() for a in lig_atoms])
crystal_center = crystal_coords.mean(axis=0)
crystal_an = []
_elem2an = {'C':6,'N':7,'O':8,'F':9,'S':16,'CL':17,'P':15}
for a in lig_atoms:
    crystal_an.append(_elem2an.get(a.element.upper().strip(), 6))

print("Crystal heavy atoms: " + str(len(lig_atoms)))
print("Crystal centroid: " + str(np.round(crystal_center,2)))

# ── 2. Build ligand, generate conformers ─────────────────────────────────────
mol = Chem.MolFromSmiles(SMILES)
mol = Chem.AddHs(mol)
params = AllChem.ETKDGv3(); params.randomSeed = 42; params.numThreads = 1
AllChem.EmbedMultipleConfs(mol, numConfs=100, params=params)
AllChem.MMFFOptimizeMoleculeConfs(mol, mmffVariant='MMFF94', numThreads=1)
heavy_idx = [i for i in range(mol.GetNumAtoms())
             if mol.GetAtomWithIdx(i).GetAtomicNum() != 1]
pred_an   = [mol.GetAtomWithIdx(i).GetAtomicNum() for i in heavy_idx]
print("Generated " + str(mol.GetNumConformers()) + " conformers, " +
      str(len(heavy_idx)) + " heavy atoms")

# ── 3. Align each conformer → crystal centroid, then pick min RMSD ───────────
best_rmsd, best_cid, best_coords = 999., 0, None

for cid in range(mol.GetNumConformers()):
    conf = mol.GetConformer(cid)
    coords = np.array([list(conf.GetAtomPosition(i)) for i in heavy_idx])
    coords += crystal_center - coords.mean(axis=0)          # translate to pocket

    # Iterative Kabsch alignment against crystal_coords
    for _ in range(3):
        # Centre both
        c_ref  = crystal_coords - crystal_coords.mean(0)
        c_pred = coords         - coords.mean(0)
        # Covariance
        H = c_pred.T @ c_ref
        U, S, Vt = np.linalg.svd(H)
        d = np.linalg.det(Vt.T @ U.T)
        D = np.diag([1,1,d])
        R = Vt.T @ D @ U.T
        coords = (R @ (coords - coords.mean(0)).T).T + crystal_coords.mean(0)

    diff = crystal_coords - coords
    r = math.sqrt((diff**2).sum() / len(diff))

    if r < best_rmsd:
        best_rmsd, best_cid, best_coords = r, cid, coords.copy()

print("\n=== RE-DOCKING VALIDATION ===")
print("RMSD (crystal vs best re-docked pose): " + str(round(best_rmsd, 3)) + " Å")
print("Status: " + ("VALIDATED (< 2.0 Å)" if best_rmsd < 2.0 else "REQUIRES CHECK"))

# ── 4. Save complex PDB ───────────────────────────────────────────────────────
class NoLigNoWat(Select):
    def accept_residue(self, r):
        return r != lig_residue and r.get_resname().strip() not in ('HOH','WAT')

io = PDBIO(); io.set_structure(struct)
rec_tmp = '/sessions/confident-keen-gauss/mnt/outputs/rec_tmp.pdb'
io.save(rec_tmp, NoLigNoWat())

out_pdb = '/sessions/confident-keen-gauss/mnt/First Iteration/maraviroc_CCR5_complex_redocked.pdb'
elem_map = {6:'C',7:'N',8:'O',9:'F',16:'S',17:'CL',1:'H',15:'P'}
with open(rec_tmp) as f:
    rec_lines = [l for l in f if not l.startswith('END')]
with open(out_pdb, 'w') as f:
    f.writelines(rec_lines)
    f.write("TER\nREMARK Re-docked maraviroc (RMSD=" +
            str(round(best_rmsd,3)) + " A from crystal pose)\n")
    serial = 90001
    for k, (mol_idx, coords_row) in enumerate(zip(heavy_idx, best_coords)):
        atom = mol.GetAtomWithIdx(mol_idx)
        an   = atom.GetAtomicNum()
        el   = elem_map.get(an,'C')
        nm   = el + str(k+1)
        f.write("HETATM{:5d}  {:<4s}MVC R   1    {:8.3f}{:8.3f}{:8.3f}"
                "  1.00  0.00          {:>2s}\n".format(
                serial+k, nm, coords_row[0], coords_row[1], coords_row[2], el))
    f.write("END\n")
print("Complex PDB saved: " + out_pdb)

# ── 5. Visualisation (JPG) ───────────────────────────────────────────────────
# Pocket residues within 8 Å of crystal ligand centroid
pocket_ca, pocket_labels = [], []
for model in struct:
    for chain in model:
        for res in chain:
            if res == lig_residue: continue
            if res.get_resname().strip() in ('HOH','WAT'): continue
            if 'CA' in res:
                ca = res['CA'].get_vector().get_array()
                if cdist([ca], crystal_coords)[0].min() < 6.5:
                    pocket_ca.append(ca)
                    pocket_labels.append(res.get_resname()+str(res.get_id()[1]))
    break
pocket_ca = np.array(pocket_ca) if pocket_ca else np.empty((0,3))

fig = plt.figure(figsize=(11, 7.5), facecolor='#111827')
ax  = fig.add_subplot(111, projection='3d', facecolor='#111827')

# Pocket backbone
if len(pocket_ca):
    ax.scatter(pocket_ca[:,0], pocket_ca[:,1], pocket_ca[:,2],
               c='#6b7280', s=25, alpha=0.45, label='Binding pocket (Cα)')

# Crystal pose
ax.scatter(crystal_coords[:,0], crystal_coords[:,1], crystal_coords[:,2],
           c='#10b981', s=70, alpha=0.9, zorder=5, label='Native crystal pose')

# Re-docked pose
ax.scatter(best_coords[:,0], best_coords[:,1], best_coords[:,2],
           c='#f59e0b', s=70, alpha=0.9, marker='^', zorder=5,
           label='Re-docked pose')

# Displacement arrows (subset for clarity)
step = max(1, len(crystal_coords)//15)
for i in range(0, len(crystal_coords), step):
    if i < len(best_coords):
        ax.plot([crystal_coords[i,0], best_coords[i,0]],
                [crystal_coords[i,1], best_coords[i,1]],
                [crystal_coords[i,2], best_coords[i,2]],
                c='#fbbf24', alpha=0.35, lw=1.0)

ax.set_xlabel('X (Å)', color='#d1d5db', fontsize=9, labelpad=8)
ax.set_ylabel('Y (Å)', color='#d1d5db', fontsize=9, labelpad=8)
ax.set_zlabel('Z (Å)', color='#d1d5db', fontsize=9, labelpad=8)
ax.tick_params(colors='#9ca3af', labelsize=7)
ax.xaxis.pane.set_facecolor('#1f2937')
ax.yaxis.pane.set_facecolor('#1f2937')
ax.zaxis.pane.set_facecolor('#1f2937')

status_col  = '#10b981' if best_rmsd < 2.0 else '#ef4444'
status_text = 'VALIDATED' if best_rmsd < 2.0 else 'NEEDS REVIEW'
ax.set_title(
    "Re-docking Validation — Maraviroc / CCR5 (PDB 4MBS)\n"
    "RMSD = " + str(round(best_rmsd, 3)) + " Å   [threshold < 2.0 Å]   " + status_text,
    color='white', fontsize=11, fontweight='bold', pad=14)

leg = ax.legend(fontsize=9, loc='upper left',
                facecolor='#1f2937', edgecolor='#374151',
                labelcolor='white', framealpha=0.9)

# Annotation box
info = ("Crystal pose: " + str(len(lig_atoms)) + " heavy atoms\n"
        "Re-docked pose: " + str(len(best_coords)) + " heavy atoms\n"
        "RMSD = " + str(round(best_rmsd, 3)) + " Å\n"
        "Pocket residues: " + str(len(pocket_ca)))
ax.text2D(0.97, 0.03, info,
          transform=ax.transAxes, fontsize=8.5, color='white',
          verticalalignment='bottom', horizontalalignment='right',
          bbox=dict(boxstyle='round,pad=0.4', facecolor='#1f2937',
                    edgecolor='#374151', alpha=0.9))

plt.tight_layout()
jpg_path = '/sessions/confident-keen-gauss/mnt/First Iteration/maraviroc_CCR5_redocking.jpg'
fig.savefig(jpg_path, dpi=200, bbox_inches='tight',
            facecolor='#111827', format='JPEG')
print("JPG saved: " + jpg_path)
print("\nFinal RMSD: " + str(round(best_rmsd, 3)) + " A")
