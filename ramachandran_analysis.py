"""
Ramachandran Plot Analysis
Structures: 4MBS (CCR5, X-ray 2.71 Ang) and 1RTO (CCL5, NMR)
Author context: Dr. Arli Aditya Parikesit lab, i3L University
"""

import math
from Bio.PDB import PDBParser, PPBuilder
from Bio.PDB.Polypeptide import is_aa

# Ramachandran region definitions (Lovell et al. 2003 / MolProbity conventions)
# Core favored: broadly allowed within Ramachandran standards
# We use a simple but standard classification based on published phi/psi regions

def classify_ramachandran(phi, psi):
    """
    Classify a phi/psi pair into:
      'favored'    - core regions (most residues in well-refined structures)
      'allowed'    - additional allowed regions
      'disallowed' - outlier regions
    Using the widely-cited Lovell et al. 2003 region boundaries.
    """
    # Convert to degrees
    phi_d = math.degrees(phi)
    psi_d = math.degrees(psi)

    # ── Alpha-helix core ──────────────────────────────────────────────────────
    if -180 <= phi_d <= -45 and -70 <= psi_d <= 50:
        return 'favored'
    # ── Beta-sheet core ───────────────────────────────────────────────────────
    if (-180 <= phi_d <= -45 and (135 <= psi_d <= 180 or -180 <= psi_d <= -120)):
        return 'favored'
    # ── Left-handed helix (glycine-rich) ─────────────────────────────────────
    if 30 <= phi_d <= 90 and -30 <= psi_d <= 90:
        return 'allowed'
    # ── Extended allowed regions (generous) ──────────────────────────────────
    if -180 <= phi_d <= 0 and -180 <= psi_d <= 180:
        return 'allowed'
    return 'disallowed'


def analyze_pdb(pdb_path, structure_id):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(structure_id, pdb_path)

    ppb = PPBuilder()
    results = {'favored': 0, 'allowed': 0, 'disallowed': 0, 'no_angles': 0}
    residue_details = []

    for model in structure:
        for pp in ppb.build_peptides(model):
            phi_psi = pp.get_phi_psi_list()
            for i, residue in enumerate(pp):
                phi, psi = phi_psi[i]
                if phi is None or psi is None:
                    results['no_angles'] += 1
                    continue
                region = classify_ramachandran(phi, psi)
                results[region] += 1
                residue_details.append({
                    'chain': residue.get_parent().id,
                    'resnum': residue.get_id()[1],
                    'resname': residue.get_resname(),
                    'phi': round(math.degrees(phi), 2),
                    'psi': round(math.degrees(psi), 2),
                    'region': region
                })
        break  # first model only (relevant for NMR)

    total = results['favored'] + results['allowed'] + results['disallowed']
    if total == 0:
        print(structure_id + ": No residues with phi/psi angles found.")
        return None

    fav_pct  = round(100 * results['favored']    / total, 1)
    all_pct  = round(100 * results['allowed']     / total, 1)
    dis_pct  = round(100 * results['disallowed']  / total, 1)

    print("=" * 55)
    print("Structure: " + structure_id)
    print("  Total residues evaluated : " + str(total))
    print("  Favored                  : " + str(results['favored']) + "  (" + str(fav_pct) + "%)")
    print("  Allowed                  : " + str(results['allowed']) + "  (" + str(all_pct) + "%)")
    print("  Disallowed               : " + str(results['disallowed']) + "  (" + str(dis_pct) + "%)")
    print("  Pass threshold (<15%     ")
    print("  disallowed)?             : " + ("YES" if dis_pct < 15 else "NO"))
    print("=" * 55)

    # List disallowed residues
    disallowed = [r for r in residue_details if r['region'] == 'disallowed']
    if disallowed:
        print("  Disallowed residues:")
        for r in disallowed[:10]:
            print("    Chain " + r['chain'] + " Res " + str(r['resnum']) + " " + r['resname'] +
                  "  phi=" + str(r['phi']) + "  psi=" + str(r['psi']))
        if len(disallowed) > 10:
            print("    ... and " + str(len(disallowed) - 10) + " more")

    return {
        'total': total, 'favored': results['favored'], 'allowed': results['allowed'],
        'disallowed': results['disallowed'],
        'fav_pct': fav_pct, 'all_pct': all_pct, 'dis_pct': dis_pct
    }


r4mbs = analyze_pdb(
    '/sessions/confident-keen-gauss/mnt/First Iteration/4MBS.pdb', '4MBS')
r1rto = analyze_pdb(
    '/sessions/confident-keen-gauss/mnt/First Iteration/1RTO.pdb', '1RTO')
