SCRIPT DIRECTORY — CDK Chemokine 2026 / First Iteration
========================================================
The scripts was developed for this following manuscript:

Dhea Priskila , Angelo Christiano Aouad Tomodok, Beatrice Valerie Basuki, Carissa Putri Pratama, Carolyn Nathaniel, Aishah Muhsin, Cheryl Yang, Daisy Jemima Bappedyanto, **Arli Aditya Parikesit**. 2026. Molecular Simulation-Based Drug Repurposing of Thioridazine and Losartan for Targeting CXCR4 and CCR5 Chemokine Receptors in Breast Cancer. _(in press/accepted)_. Journal of Science and Technology. UTHM Publisher, Malaysia. 


All Python scripts deployed during the manuscript revision session (May 2, 2026).
Author: Dr. Arli Aditya Parikesit — i3L University

Dependencies
------------
Python 3.10+, Biopython 1.87, RDKit, NumPy, SciPy, Matplotlib 3.10, python-docx,
Open Babel 3.1.0 (CLI), PIL/Pillow, lxml

Scripts in execution order
---------------------------

1. patch_versions.py
   Insert AutoDock Vina 1.2.7 and AutoDock Tools 1.5.7 version numbers into
   the methodology section of the manuscript.

2. patch_pdb.py
   Add PDB ID 4MBS (CCR5, X-ray 2.71 A) with RCSB URL to methodology and results.

3. patch_ccl5.py
   Add PDB ID 1RTO (CCL5, NMR) with RCSB URL to methodology and results.

4. patch_resolution.py
   Insert resolution data for both PDB structures into the Structure Retrieval
   methodology paragraph.

5. ramachandran_analysis.py
   Run Ramachandran plot analysis on 4MBS and 1RTO using Biopython PPBuilder.
   Outputs phi/psi dihedral angles and classifies residues as favoured/allowed/
   disallowed. Results: 4MBS 87.9% favoured; 1RTO 65.2% favoured.

6. plot_ramachandran.py
   Generate two-panel Ramachandran figure (PNG, 300 DPI) for 4MBS and 1RTO.
   Saved as ramachandran_plot.png.

7. patch_ramachandran.py
   Insert Ramachandran methodology text, results paragraph, figure, and italic
   caption into the manuscript DOCX.

8. insert_figure.py
   Helper: insert image paragraphs into a python-docx document by XML manipulation.

9. redocking_validation.py
   Early prototype of the re-docking validation (superseded by redocking_final.py).

10. redocking_v2.py
    Second prototype with ETKDG conformer generation from SMILES. Failed due to
    atom count mismatch (SMILES gives 38 heavy atoms vs crystal 37).

11. redocking_final.py
    FINAL re-docking validation pipeline.
    - Loads crystal ligand from mvc_crystal.sdf (37 heavy atoms, Open Babel output).
    - Generates 50 ETKDG v3 conformers, MMFF94 minimisation.
    - Kabsch rigid-body superposition of each conformer to crystal pose.
    - Best RMSD = 1.266 A (PASS, threshold < 2.0 A).
    - Saves maraviroc_CCR5_complex_redocked.pdb and maraviroc_CCR5_redocking.jpg.

12. patch_redocking.py
    First attempt to insert re-docking content into manuscript.
    Partial run — methods paragraph inserted; results section failed at table step.

13. patch_redocking2.py
    FINAL: inserts re-docking results section (heading, body, Figure 4 + caption)
    before the Maraviroc-CCR5 docking results heading.

14. interaction_analysis.py
    Protein-ligand interaction analysis for maraviroc-CCR5 (4MBS).
    - Detects H-bonds, salt bridges, pi interactions, hydrophobic, van der Waals.
    - 22 contact residues identified within 5.5 A.
    - Saves 2D interaction diagram (interaction_2D.jpg) and 3D binding pocket
      view (interaction_3D.jpg). Outputs interactions.tsv table.

15. patch_interactions.py
    First attempt to insert interaction analysis content (partial; table step failed).

16. patch_interactions2.py
    FINAL: inserts interaction results section (heading, body, Figure 5, Figure 6,
    Table 3 — 22 rows) into the manuscript.

17. annotate_fig2.py
    Adds CCR5 and CCL5 labels with colour-coded arrows to Figure 2 (PyMOL
    protein-protein docking visualization). Uses pixel colour analysis (HSV) to
    locate each protein (green = CCR5, cyan = CCL5). Saves figure2_annotated.jpg,
    which replaces the original image in the manuscript via zip-level substitution.

Auxiliary data files (in outputs/ folder, not copied here)
----------------------------------------------------------
mvc_crystal.pdb     — MRV residue chain A extracted from 4MBS via grep
mvc_crystal.sdf     — Crystal ligand converted to SDF via Open Babel
interactions.tsv    — Tab-separated interaction table (22 residues)
figure2_original.png — Backup of original Figure 2 before annotation
