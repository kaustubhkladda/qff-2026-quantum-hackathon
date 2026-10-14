# Geometry-Aware Quantum Cloud Challenge

**Qiskit Fall Fest 2026 · Basic Track**

This project investigates how processor connectivity and noise affect Bell-state preparation, and whether a simple error-detection strategy improves fidelity enough to justify its added circuit cost.

## Presentation

**YouTube walkthrough:** https://youtu.be/VdPdHXaqCYo

## Project overview

The goal is to prepare and verify the Bell state

$$
|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt{2}}
$$

on three processor models. The project compares ideal and noisy simulations, applies a ZZ parity check with post-selection, and evaluates the trade-off between fidelity, circuit overhead, and accepted measurement shots.

### Processor models

| Model | Qubits | Couplers | Fixed ports | Noise model |
|---|---:|---:|---|---|
| 2016-inspired | 5 | 4 | 0 and 4 | `FakeBurlingtonV2` calibration-derived noise |
| Contemporary IBM-style | 156 | 176 | 126 and 129 | `FakeFez` calibration-derived noise |
| Hyperbolic-inspired | 35 | 42 | 0 and 3 | Synthetic noise set to the median rates of `FakeFez` |

The ports are three couplers apart in each model. Qiskit's transpiler routes the logical Bell circuit through the available connectivity, inserting SWAP operations when needed.

## Methodology

1. Load the three processor models and visualize their coupling graphs.
2. Prepare the Bell state with a Hadamard gate followed by a CNOT gate.
3. Compile the circuit for each processor and record depth, two-qubit gate count, SWAP count, and physical-qubit usage.
4. Estimate Bell-state fidelity from the XX, YY, and ZZ correlations:

   $$F = \frac{1 + \langle XX\rangle - \langle YY\rangle + \langle ZZ\rangle}{4}$$

5. Compare ideal, noisy, and noisy-with-protection results.
6. Apply a ZZ parity check using an ancilla qubit and keep only shots that pass the check.
7. Explore ancilla placement, a common-noise comparison, and sensitivity to two-qubit gate error.

A result is considered verified when its lower confidence bound satisfies `F - 2σF > 0.5`.

## Core results

These are the saved results from the nine-case simulation benchmark. The protected fidelity is conditional on shots accepted by the ZZ check.

| Processor | Ideal fidelity | Noisy baseline | Noisy + ZZ check | Accepted shots with check |
|---|---:|---:|---:|---:|
| 2016-inspired | 1.0000 | 0.8387 | 0.8383 | 88.62% |
| Contemporary IBM-style | 1.0000 | 0.9460 | 0.9704 | 95.94% |
| Hyperbolic-inspired | 1.0000 | 0.9520 | 0.9543 | 96.77% |

The unprotected Bell circuit uses **7 two-qubit gates and 2 SWAPs** in each model. With the ZZ check, the compiled circuit uses **10 two-qubit gates and 3 SWAPs**. The added check also increases circuit depth and rejects some shots.

### Main findings

- **Contemporary model:** the clearest improvement in the core results; fidelity rises from 0.9460 to 0.9704.
- **2016-inspired model:** no meaningful improvement in the core results; fidelity changes from 0.8387 to 0.8383.
- **Hyperbolic-inspired model:** only a small increase, from 0.9520 to 0.9543.
- **Ancilla placement matters:** an unfavourable location can add routing overhead and reduce fidelity.
- **More checks are not automatically better:** a second check adds operations and can reject more shots.
- **Common-noise comparison:** using the same gate set and noise assumptions across the three graphs helps isolate the effect of connectivity.

## Figures

When the notebook has been run, its figures can be placed in `results/figures/`. The following paths are suggested; update them if your repository uses different filenames.

- `results/figures/task4_core_comparison.png` — fidelity across the nine core cases.
- `results/figures/compiled_hyperbolic_baseline.png` — compiled baseline Bell circuit.
- `results/figures/compiled_hyperbolic_ZZ.png` — compiled Bell circuit with the ZZ check.
- `results/figures/task5_ancilla_placement.png` — cost by ancilla placement.
- `results/figures/task6_sensitivity.png` — sensitivity to two-qubit gate error.

## Running the project

### Requirements

The saved notebook run used Python 3.11.15, Qiskit 2.4.2, Qiskit Aer 0.17.2, and `qiskit-ibm-runtime` 0.50.0. The runtime version is pinned because fake-backend calibration data can change between releases.

### Setup

1. Place the notebook in the same folder as the organiser-provided `qff_basic_benchmark.py` and `requirements.txt` files.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Open `QFF2026_Basic_Track_Solution.ipynb` in Jupyter or VS Code.
4. Run the notebook from top to bottom. The notebook generates result tables, raw counts, settings, figures, and a draft report in the results folder.

**Hardware note:** the notebook includes an optional IBM Quantum hardware section. Set `RUN_ON_QPU = False` before running all cells unless you intentionally want to submit a hardware job. The core nine-case comparison is simulated.

## Reproducibility

- Shots per measurement setting: `10,000`
- Transpiler seed: `1`
- Simulator seed: `1`
- Transpiler optimization level: `2`
- Reported versions: Python `3.11.15`, Qiskit `2.4.2`, Qiskit Aer `0.17.2`, `qiskit-ibm-runtime` `0.50.0`

The supplied benchmark definitions and requirements should remain unchanged where required by the challenge rules.

## Suggested repository structure

```text
.
├── README.md
├── requirements.txt
├── qff_basic_benchmark.py
├── QFF2026_Basic_Track_Solution.ipynb
├── report.md                 # or report.pdf
└── results/
    ├── core_nine_cases.csv
    ├── task5_builder_variants.csv
    ├── task6_common_noise.csv
    ├── task6_native_vs_common.csv
    ├── task6_sensitivity_sweep.csv
    ├── counts.json
    ├── settings.json
    └── figures/
```

Include only files that are actually present in your repository and adjust the structure above to match your final submission.

## Limitations

The core comparison uses simulated noise models, one designated port pair per model, and a fixed transpiler/simulator seed. The hyperbolic processor is hypothetical and uses synthetic noise. These results are evidence for the tested configurations; they do not establish that one processor geometry is universally superior.

## Acknowledgements

This project follows the **Geometry-aware quantum cloud challenge** prepared by Steven Rayan (quanTA, University of Saskatchewan) for the Qiskit Fall Fest 2026 Basic Track, provided by IBM Quantum.

Hackathon information: https://events.iitj.ac.in/qff/#hackathon
