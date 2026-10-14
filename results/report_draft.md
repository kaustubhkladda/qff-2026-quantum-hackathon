# Report draft (auto-generated from the notebook run)

Settings: Qiskit 2.4.2, Aer 0.17.2, qiskit-ibm-runtime 0.50.0; 10000 shots per setting; seed_transpiler=1; seed_simulator=1; optimization_level=2.

## Core nine cases

| case | model | scenario | F | sigma_F | F_minus_2sigma | verified | depth | two_qubit_gates | swaps | physical_qubits | accept_frac | discarded_shots |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2016 | Ideal baseline | 1.0000 | 0.0000 | 1.0000 | True | 7 | 7 | 2 | 4 | 1.0000 | 0 |
| 2 | 2016 | Noisy baseline | 0.8387 | 0.0027 | 0.8333 | True | 7 | 7 | 2 | 4 | 1.0000 | 0 |
| 3 | 2016 | Noisy + protection (ZZ check) | 0.8383 | 0.0029 | 0.8325 | True | 13 | 10 | 3 | 5 | 0.8862 | 3414 |
| 4 | contemporary | Ideal baseline | 1.0000 | 0.0000 | 1.0000 | True | 14 | 7 | 2 | 4 | 1.0000 | 0 |
| 5 | contemporary | Noisy baseline | 0.9460 | 0.0016 | 0.9428 | True | 14 | 7 | 2 | 4 | 1.0000 | 0 |
| 6 | contemporary | Noisy + protection (ZZ check) | 0.9704 | 0.0012 | 0.9680 | True | 23 | 10 | 3 | 5 | 0.9594 | 1219 |
| 7 | hyperbolic | Ideal baseline | 1.0000 | 0.0000 | 1.0000 | True | 14 | 7 | 2 | 4 | 1.0000 | 0 |
| 8 | hyperbolic | Noisy baseline | 0.9520 | 0.0015 | 0.9490 | True | 14 | 7 | 2 | 4 | 1.0000 | 0 |
| 9 | hyperbolic | Noisy + protection (ZZ check) | 0.9543 | 0.0015 | 0.9513 | True | 29 | 10 | 3 | 4 | 0.9677 | 968 |

## Builder variants (protected, noisy)

| model | scenario | ancilla | F | sigma_F | F_gain_vs_baseline | accept_frac | depth | two_qubit_gates | swaps | physical_qubits |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | ZZ check, worst ancilla position | [1] | 0.8412 | 0.0029 | 0.0025 | 0.8678 | 14 | 12 | 3 | 4 |
| 2016 | ZZ check, best ancilla position | [2] | 0.8383 | 0.0029 | -0.0004 | 0.8862 | 13 | 10 | 3 | 5 |
| 2016 | ZZ + XX double check | [2, 3] | 0.8259 | 0.0032 | -0.0128 | 0.7470 | 17 | 17 | 4 | 5 |
| contemporary | ZZ check, worst ancilla position | [131] | 0.9558 | 0.0015 | 0.0098 | 0.9561 | 31 | 15 | 4 | 6 |
| contemporary | ZZ check, best ancilla position | [137] | 0.9704 | 0.0012 | 0.0244 | 0.9594 | 23 | 10 | 3 | 5 |
| contemporary | ZZ + XX double check | [137, 125] | 0.9421 | 0.0017 | -0.0039 | 0.9442 | 40 | 16 | 5 | 6 |
| hyperbolic | ZZ check, worst ancilla position | [22] | 0.9448 | 0.0017 | -0.0072 | 0.9644 | 31 | 15 | 4 | 6 |
| hyperbolic | ZZ check, best ancilla position | [2] | 0.9543 | 0.0015 | 0.0023 | 0.9677 | 29 | 10 | 3 | 4 |
| hyperbolic | ZZ + XX double check | [2, 12] | 0.9655 | 0.0013 | 0.0134 | 0.9314 | 37 | 14 | 4 | 5 |

## Graph-only comparison (common noise)

| model | scenario | F | sigma_F | depth | two_qubit_gates | swaps | accept_frac |
|---|---|---|---|---|---|---|---|
| 2016 | Noisy baseline (common noise) | 0.9520 | 0.0015 | 14 | 7 | 2 | 1.0000 |
| 2016 | Noisy + ZZ check (common noise) | 0.9577 | 0.0015 | 23 | 10 | 3 | 0.9700 |
| contemporary | Noisy baseline (common noise) | 0.9520 | 0.0015 | 14 | 7 | 2 | 1.0000 |
| contemporary | Noisy + ZZ check (common noise) | 0.9672 | 0.0013 | 28 | 10 | 3 | 0.9608 |
| hyperbolic | Noisy baseline (common noise) | 0.9520 | 0.0015 | 14 | 7 | 2 | 1.0000 |
| hyperbolic | Noisy + ZZ check (common noise) | 0.9543 | 0.0015 | 29 | 10 | 3 | 0.9677 |

Figures are in results/figures. Write the interpretation (Task 6) and the recommendation (Task 7) from the notebook's final section.
