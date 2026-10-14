"""QFF 2026 Basic track: common processor definitions (single-file edition).

Geometry-aware quantum cloud challenge, Qiskit Fall Fest 2026. Original prompt by
Steven Rayan (quanTA, University of Saskatchewan).

Put this file in the same folder as your notebook or script, install the packages in
requirements.txt, and import it:

    from qff_basic_benchmark import load_model, SHOTS
    m = load_model("2016")          # or "contemporary", "hyperbolic"
    m.ports                         # (0, 4): port A, port B (physical qubits)
    m.backend                       # noisy AerSimulator whose target enforces the graph
    m.ideal_backend                 # same target, no noise

Every team uses these definitions unchanged for the nine core cases, so results can be
compared across teams. See README.md for the full description.

Three processor models
----------------------
"2016"          Five-node reference graph of the original prompt (a hub qubit coupled to
                three others, one of which is coupled to a fifth). Qiskit ships no 2016
                calibration data; several IBM five-qubit devices (Burlington, Ourense,
                Vigo, ...) used exactly this graph, and the model uses the oldest such
                snapshot, FakeBurlingtonV2 (calibrated 2020-06-11), with the noise model
                Qiskit Aer builds from its calibration data.
"contemporary"  IBM Heron-style processor: the FakeFez snapshot from qiskit-ibm-runtime,
                with the noise model Qiskit Aer builds from its calibration data.
"hyperbolic"    Hypothetical processor whose coupling graph is a finite patch of the
                {7,3} hyperbolic tiling, with a synthetic circuit-level noise model at
                FakeFez's median error rates.

Two noise variants
------------------
noise="native"  (default) Each model with its own gate set and noise: the nine core cases.
noise="common"  Same gate set (cz, rz, sx, x) and the same synthetic noise on all three
                graphs, so the only remaining difference is the coupling graph (Task 6).

License: Apache License 2.0.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field

import matplotlib.pyplot as plt
import numpy as np
import rustworkx as rx
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap, Target
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from rustworkx.visualization import mpl_draw

__version__ = "1.0.0"

__all__ = [
    "ERRORS_CONTEMPORARY_MEDIAN",
    "FAKE_BACKENDS",
    "MODEL_NAMES",
    "PINNED_QISKIT_IBM_RUNTIME",
    "PORTS",
    "SHOTS",
    "ProcessorModel",
    "depolarizing_parameter",
    "draw_model",
    "fake_backend",
    "hyperbolic_patch",
    "load_all_models",
    "load_model",
    "synthetic_noise_model",
]


# ======================================================================================
# Hyperbolic {7,3} patch
# ======================================================================================

# Construction of a finite patch of the {7,3} hyperbolic tiling.
#
# The hyperbolic-inspired processor model uses the vertices of a finite piece of
# the {p, q} = {7, 3} tiling as qubits and its edges as two-qubit couplers.
# {7, 3} means: every face is a heptagon (p = 7) and three faces meet at every
# vertex (q = 3). Because (p - 2)(q - 2) = 5 > 4, the tiling lives in the
# hyperbolic plane, not the Euclidean plane.
#
# Construction (geometric, in the Poincare disk model)
# ----------------------------------------------------
# 1. Place one regular heptagon centred at the origin of the Poincare disk.
#    For a regular {p, q} tiling the hyperbolic circumradius R of a face obeys
#
#        cosh(R) = cot(pi / p) * cot(pi / q)
#
#    and a point at hyperbolic distance R from the origin sits at Euclidean
#    radius tanh(R / 2) in the Poincare disk.
# 2. Reflect the central heptagon across each of its 7 edges. In the Poincare
#    disk, the hyperbolic line through two points is a circle orthogonal to the
#    unit circle, and reflecting across that line is an inversion in that circle.
#    This gives the 7 heptagons that share an edge with the central one.
# 3. Merge vertices that coincide (to 1e-9) and collect the polygon edges.
#
# For {7, 3} the 7 edge-neighbours already contain every heptagon that touches a
# central vertex (3 faces meet at a vertex: the central one and two
# edge-neighbours), so this is the full "first ring".
#
# Expected counts, derived by hand and checked by the organizers' test suite:
#     vertices = 7 (central) + 7 (where two neighbours meet) + 7 * 3 (boundary) = 35
#     edges    = 7 (central) + 7 (spokes) + 7 * 4 (outer edges)                 = 42
#     degrees  = 14 vertices of degree 3, 21 boundary vertices of degree 2
#     faces    = 8 heptagons, every bounded face has length 7
#
# Vertex numbering is deterministic: the central heptagon is 0..6 going
# anticlockwise from the positive real axis; the remaining vertices are numbered
# in the order they are first met while walking the reflected heptagons.

# Tolerance used to decide that two floating-point vertex positions are the
# same point. The construction involves only a few inversions, so round-off is
# around 1e-15; 1e-9 is a safe margin and far below the smallest vertex spacing.
_MERGE_TOL = 1e-9


def _poincare_vertex_radius(p: int, q: int) -> float:
    """Euclidean radius, in the Poincare disk, of the vertices of a central {p, q} face.

    Uses cosh(R) = cot(pi/p) cot(pi/q) for the hyperbolic circumradius R and the
    Poincare-disk map r = tanh(R / 2).
    """
    if (p - 2) * (q - 2) <= 4:
        raise ValueError(f"{{{p},{q}}} is not a hyperbolic tiling")
    cosh_r = 1.0 / (math.tan(math.pi / p) * math.tan(math.pi / q))
    return math.tanh(math.acosh(cosh_r) / 2.0)


def _reflect_across_geodesic(z: complex, a: complex, b: complex) -> complex:
    """Reflect point z across the hyperbolic line through a and b (Poincare disk).

    The hyperbolic line through a and b is the circle with centre c and radius r
    that passes through a and b and is orthogonal to the unit circle. Orthogonality
    means |c|^2 = r^2 + 1. Passing through a gives |c - a|^2 = r^2. Subtracting:

        2 Re(c * conj(a)) = |a|^2 + 1,   and likewise for b,

    which is a 2x2 linear system for (Re c, Im c). The reflection is then the
    inversion z -> c + r^2 / conj(z - c).
    """
    lhs = 2.0 * np.array([[a.real, a.imag], [b.real, b.imag]])
    rhs = np.array([abs(a) ** 2 + 1.0, abs(b) ** 2 + 1.0])
    cx, cy = np.linalg.solve(lhs, rhs)
    c = complex(cx, cy)
    r2 = abs(c) ** 2 - 1.0
    return c + r2 / np.conj(z - c)


def hyperbolic_patch(p: int = 7, q: int = 3):
    """Build the central {p, q} face plus its edge-neighbours.

    Returns
    -------
    num_vertices : int
    edges : list[tuple[int, int]]
        Undirected edges (u, v) with u < v, sorted.
    positions : dict[int, tuple[float, float]]
        Poincare-disk coordinates of every vertex, used for drawing.
    faces : list[list[int]]
        Vertex indices of each heptagonal face, central face first.
    """
    radius = _poincare_vertex_radius(p, q)
    central = [radius * np.exp(2j * math.pi * k / p) for k in range(p)]

    polygons = [central]
    for k in range(p):
        a, b = central[k], central[(k + 1) % p]
        polygons.append([_reflect_across_geodesic(z, a, b) for z in central])

    points: list[complex] = []

    def vertex_id(z: complex) -> int:
        # Linear search is fine: at most a few dozen vertices.
        for idx, w in enumerate(points):
            if abs(w - z) < _MERGE_TOL:
                return idx
        points.append(complex(z))
        return len(points) - 1

    faces: list[list[int]] = []
    edge_set: set[tuple[int, int]] = set()
    for poly in polygons:
        ids = [vertex_id(z) for z in poly]
        faces.append(ids)
        for i in range(p):
            u, v = ids[i], ids[(i + 1) % p]
            edge_set.add((min(u, v), max(u, v)))

    positions = {i: (z.real, z.imag) for i, z in enumerate(points)}
    return len(points), sorted(edge_set), positions, faces


# ======================================================================================
# Synthetic noise model
# ======================================================================================

# Synthetic noise model for the hyperbolic-inspired processor and the "common" variant.
#
# The 2016 and contemporary processors use the noise model that Qiskit Aer builds
# from a fake backend's calibration data (AerSimulator.from_backend). The hyperbolic
# processor is not a real device, so it gets a simple, fully specified circuit-level
# noise model built here from three numbers (the "common" variant applies the same
# model to all three graphs):
#
#     one_qubit  : average gate error of every sx and x gate
#     two_qubit  : average gate error of every two-qubit gate (cx or cz)
#     readout    : probability that a measured bit is flipped (same for 0->1 and 1->0)
#
# rz gates are noiseless, as on IBM hardware where rz is implemented in software
# ("virtual Z"). There is no idle or decoherence noise: this is a circuit-level
# model only.
#
# From average gate error to Aer's depolarizing parameter
# -------------------------------------------------------
# Aer's depolarizing_error(lam, n) is the channel
#
#     E(rho) = (1 - lam) rho + lam * Tr(rho) * I / d,    d = 2**n.
#
# Its average gate fidelity is F_avg = 1 - lam * (d - 1) / d, so an average gate
# error e = 1 - F_avg needs
#
#     lam = e * d / (d - 1).
#
# Example: a two-qubit gate error of 3% gives lam = 0.03 * 4 / 3 = 0.04.
# The organizers' test suite checks this with qiskit.quantum_info.average_gate_fidelity.

def depolarizing_parameter(average_gate_error: float, num_qubits: int) -> float:
    """Convert an average gate error into Aer's depolarizing parameter lam = e * d / (d - 1)."""
    d = 2**num_qubits
    return average_gate_error * d / (d - 1)


def synthetic_noise_model(
    one_qubit: float,
    two_qubit: float,
    readout: float,
    two_qubit_gate: str,
) -> NoiseModel:
    """Build the circuit-level noise model described in the module docstring.

    Parameters
    ----------
    one_qubit, two_qubit : float
        Average gate errors (1 - average gate fidelity) of sx/x and of the two-qubit gate.
    readout : float
        Symmetric bit-flip probability applied to every measurement.
    two_qubit_gate : str
        Name of the native two-qubit gate that carries the two-qubit error ("cx" or "cz").
    """
    basis_gates = [two_qubit_gate, "rz", "sx", "x"]
    noise_model = NoiseModel(basis_gates=basis_gates)

    # Single-qubit physical gates. rz is deliberately left noiseless (virtual Z).
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(depolarizing_parameter(one_qubit, 1), 1), ["sx", "x"]
    )

    # Native two-qubit gate on every coupled pair.
    noise_model.add_all_qubit_quantum_error(
        depolarizing_error(depolarizing_parameter(two_qubit, 2), 2), [two_qubit_gate]
    )

    # Symmetric readout error. Row i is the distribution of the recorded bit
    # given that the true outcome was i.
    noise_model.add_all_qubit_readout_error(
        ReadoutError([[1.0 - readout, readout], [readout, 1.0 - readout]])
    )
    return noise_model


# ======================================================================================
# Processor models
# ======================================================================================

# --------------------------------------------------------------------------------------
# Fixed benchmark constants
# --------------------------------------------------------------------------------------

#: Shots per circuit (per measurement setting) for every core case.
SHOTS: int = 10_000

#: Names accepted by load_model().
MODEL_NAMES: tuple[str, ...] = ("2016", "contemporary", "hyperbolic")

#: Fake backends behind the two real-device models, and the qiskit-ibm-runtime release
#: whose snapshots define the benchmark. Fake-backend calibration data can change between
#: releases, so other versions give different noise.
FAKE_BACKENDS: dict[str, str] = {"2016": "FakeBurlingtonV2", "contemporary": "FakeFez"}
PINNED_QISKIT_IBM_RUNTIME: str = "0.50.0"

#: Median error rates of FakeFez in qiskit-ibm-runtime 0.50.0, rounded to 3 significant
#: figures: median sx error, median cz error, median measurement error. Used for the
#: hyperbolic model (hypothetical hardware with today's typical gate quality) and for the
#: noise="common" variant. The organizers' test suite recomputes them from FakeFez.
ERRORS_CONTEMPORARY_MEDIAN: dict[str, float] = {
    "one_qubit": 2.29e-4,
    "two_qubit": 3.90e-3,
    "readout": 7.57e-3,
}

#: Designated ports (port A, port B). Port A receives the Hadamard. In every model the
#: ports are exactly 3 couplers apart. Rule used on the two fake-backend models: among all
#: pairs 3 couplers apart, the pair whose shortest path has a mean two-qubit-gate error
#: closest to the device median. The organizers' test suite re-applies this rule.
PORTS: dict[str, tuple[int, int]] = {
    # FakeBurlingtonV2 graph: 0-1, 1-2, 1-3, 3-4 (qubit 1 is the hub). Both 3-apart pairs,
    # (0, 4) and (2, 4), lie on a path through 1 and 3; the rule picks (0, 4).
    "2016": (0, 4),
    # FakeFez: the rule picks (126, 129), avoiding the best and worst parts of the chip.
    "contemporary": (126, 129),
    # Opposite vertices of the central heptagon (0 and 3, three edges apart).
    "hyperbolic": (0, 3),
}

#: Gates of each model's native gate set (as compiled circuits use them). "id" is also
#: accepted by the two fake backends and "measure" by all models.
_NATIVE_BASIS: dict[str, tuple[str, ...]] = {
    "2016": ("cx", "u1", "u2", "u3"),
    "contemporary": ("cz", "rz", "sx", "x"),
    "hyperbolic": ("cz", "rz", "sx", "x"),
}
_COMMON_BASIS: tuple[str, ...] = ("cz", "rz", "sx", "x")

#: Drawing coordinates of the 2016 graph, laid out like the reference figure of the
#: original prompt: hub qubit 1 on top, 0 left, 2 right, 3 below 1, 4 below 3.
_POSITIONS_2016 = {1: (0.0, 2.0), 0: (-1.0, 1.4), 2: (1.0, 1.4), 3: (0.0, 1.0), 4: (0.0, 0.0)}


# --------------------------------------------------------------------------------------
# Model container
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcessorModel:
    """Everything a team needs for one processor model.

    Attributes
    ----------
    name : str
        "2016", "contemporary" or "hyperbolic".
    noise_variant : str
        "native" or "common".
    num_qubits : int
    edges : tuple of (int, int)
        Undirected coupling graph, each edge once with u < v.
    ports : (int, int)
        Physical qubits of port A and port B.
    basis_gates : tuple of str
        Native gates the circuits are compiled to (measure is always allowed).
    backend : AerSimulator
        Noisy simulator. Its ``target`` enforces the coupling graph and gate set, so
        ``transpile(circuit, model.backend)`` or
        ``generate_preset_pass_manager(target=model.target, ...)`` produce valid circuits.
    ideal_backend : AerSimulator
        Same target, no noise. Use it for the ideal baseline.
    noise_model : NoiseModel
        The noise model inside ``backend``.
    noise_source : str
        Where the noise comes from: a fake backend name, or "synthetic".
    error_rates : dict or None
        The three numbers behind a synthetic noise model; None for fake-backend noise.
    positions : dict or None
        Node coordinates for drawing; None for the contemporary model (drawn with
        qiskit.visualization.plot_gate_map instead).
    shots : int
        Shots per circuit for the core cases.
    """

    name: str
    noise_variant: str
    num_qubits: int
    edges: tuple[tuple[int, int], ...]
    ports: tuple[int, int]
    basis_gates: tuple[str, ...]
    backend: AerSimulator = field(repr=False)
    ideal_backend: AerSimulator = field(repr=False)
    noise_model: NoiseModel = field(repr=False)
    noise_source: str = "synthetic"
    error_rates: dict | None = None
    positions: dict | None = field(default=None, repr=False)
    shots: int = SHOTS

    @property
    def target(self) -> Target:
        """Compilation target (coupling graph + gate set). Same for backend and ideal_backend."""
        return self.backend.target

    @property
    def coupling_map(self) -> CouplingMap:
        """Directed coupling map (both directions of every edge)."""
        return CouplingMap(_both_directions(self.edges))

    def graph(self) -> rx.PyGraph:
        """Undirected rustworkx graph of the couplers; node index = physical qubit."""
        g = rx.PyGraph()
        g.add_nodes_from(range(self.num_qubits))
        g.add_edges_from_no_data(list(self.edges))
        return g

    def port_distance(self) -> int:
        """Number of couplers on the shortest path between the two ports."""
        a, b = self.ports
        return int(rx.distance_matrix(self.graph())[a, b])


# --------------------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------------------


def _both_directions(edges):
    """List each undirected edge in both directions, as Qiskit coupling maps expect."""
    return [(u, v) for u, v in edges] + [(v, u) for u, v in edges]


def _graph_backends(num_qubits, edges, basis_gates, noise_model):
    """Noisy and ideal AerSimulator whose target enforces the given graph and gates.

    Why GenericBackendV2: AerSimulator(coupling_map=...) does not restrict its target
    (a cx between unconnected qubits is still accepted), so it would let unrouted
    circuits through. GenericBackendV2 with noise_info=False builds a proper Target
    with only the listed couplers and no invented calibration data; AerSimulator then
    copies that target and uses our noise model.
    """
    generic = GenericBackendV2(
        num_qubits=num_qubits,
        basis_gates=list(basis_gates),
        coupling_map=_both_directions(edges),
        noise_info=False,
        seed=0,
    )
    noisy = AerSimulator.from_backend(generic, noise_model=noise_model)
    ideal = AerSimulator.from_backend(generic, noise_model=None)
    return noisy, ideal


def fake_backend(name: str):
    """Instantiate the fake backend behind model ``name`` ("2016" or "contemporary").

    Warns if the installed qiskit-ibm-runtime differs from the pinned release, because the
    calibration data (and therefore the benchmark noise) may then differ.
    """
    import qiskit_ibm_runtime
    from qiskit_ibm_runtime import fake_provider

    if qiskit_ibm_runtime.__version__ != PINNED_QISKIT_IBM_RUNTIME:
        warnings.warn(
            f"qiskit-ibm-runtime {qiskit_ibm_runtime.__version__} is installed, but the benchmark "
            f"is defined with {PINNED_QISKIT_IBM_RUNTIME}. Fake-backend calibration data may differ, "
            f"so results will not be comparable. "
            f"Install with: pip install qiskit-ibm-runtime=={PINNED_QISKIT_IBM_RUNTIME}",
            stacklevel=3,
        )
    return getattr(fake_provider, FAKE_BACKENDS[name])()


def _undirected_edges(coupling_map) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({(min(u, v), max(u, v)) for u, v in coupling_map.get_edges()}))


def load_model(name: str, noise: str = "native") -> ProcessorModel:
    """Return one processor model.

    Parameters
    ----------
    name : {"2016", "contemporary", "hyperbolic"}
    noise : {"native", "common"}
        "native" for the core cases; "common" to give all graphs the same gate set and noise.

    Example
    -------
    >>> from qff_basic_benchmark import load_model
    >>> m = load_model("hyperbolic")
    >>> m.ports, m.port_distance(), m.basis_gates
    ((0, 3), 3, ('cz', 'rz', 'sx', 'x'))
    """
    if name not in MODEL_NAMES:
        raise ValueError(f"name must be one of {MODEL_NAMES}, got {name!r}")
    if noise not in ("native", "common"):
        raise ValueError(f"noise must be 'native' or 'common', got {noise!r}")

    # ---- graph and drawing coordinates -------------------------------------------------
    device = None
    if name == "hyperbolic":
        num_qubits, edge_list, positions, _faces = hyperbolic_patch(7, 3)
        edges = tuple(edge_list)
    else:
        device = fake_backend(name)
        num_qubits, edges = device.num_qubits, _undirected_edges(device.coupling_map)
        positions = dict(_POSITIONS_2016) if name == "2016" else None

    # ---- gate set and noise ------------------------------------------------------------
    if noise == "common" or name == "hyperbolic":
        # Synthetic circuit-level noise at FakeFez's median error rates.
        basis = _COMMON_BASIS
        rates = dict(ERRORS_CONTEMPORARY_MEDIAN)
        nm = synthetic_noise_model(**rates, two_qubit_gate="cz")
        noisy, ideal = _graph_backends(num_qubits, edges, basis, nm)
        source = "synthetic"
    else:
        # Real-device model: Aer's own noise model from the fake backend's calibration data.
        basis = _NATIVE_BASIS[name]
        rates = None
        noisy = AerSimulator.from_backend(device)
        ideal = AerSimulator.from_backend(device, noise_model=None)
        nm = noisy.options.noise_model
        source = FAKE_BACKENDS[name]

    return ProcessorModel(
        name=name,
        noise_variant=noise,
        num_qubits=num_qubits,
        edges=edges,
        ports=PORTS[name],
        basis_gates=basis,
        backend=noisy,
        ideal_backend=ideal,
        noise_model=nm,
        noise_source=source,
        error_rates=rates,
        positions=positions,
    )


def load_all_models(noise: str = "native") -> dict[str, ProcessorModel]:
    """All three models, keyed by name."""
    return {name: load_model(name, noise) for name in MODEL_NAMES}


# ======================================================================================
# Drawing
# ======================================================================================

# Drawing helpers: each coupling graph with its two ports highlighted.
#
# Colours: port A green, port B purple, other qubits grey-blue (as in the original prompt).

PORT_A_COLOUR = "#2ca02c"
PORT_B_COLOUR = "#7b3fe4"
QUBIT_COLOUR = "#9db4d8"


def _node_colours(model):
    colours = [QUBIT_COLOUR] * model.num_qubits
    colours[model.ports[0]] = PORT_A_COLOUR
    colours[model.ports[1]] = PORT_B_COLOUR
    return colours


def draw_model(model, ax=None):
    """Draw one processor model's coupling graph with the ports highlighted.

    The 2016 and hyperbolic graphs are drawn with rustworkx at fixed coordinates
    (the 2016 one laid out like the reference figure of the original prompt, the
    hyperbolic one at its Poincare-disk positions). The contemporary model is
    drawn with Qiskit's own plot_gate_map; for FakeFez that is an automatic graph
    layout, not the physical chip layout, but every qubit and coupler is shown.
    Returns the matplotlib Figure.
    """
    if model.positions is None:
        # Contemporary model: use Qiskit's chip layout for FakeFez.
        from qiskit.visualization import plot_gate_map

        fig = plot_gate_map(
            fake_backend("contemporary"),
            qubit_color=_node_colours(model),
            ax=ax,
            label_qubits=True,
        )
        title_ax = ax if ax is not None else fig.axes[0]
        title_ax.set_title(f"{model.name}: ports {model.ports} (A green, B purple)")
        return fig

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6) if model.num_qubits > 5 else (4, 4))
    else:
        fig = ax.figure

    g = rx.PyGraph()
    g.add_nodes_from(range(model.num_qubits))
    g.add_edges_from_no_data(list(model.edges))
    mpl_draw(
        g,
        pos=model.positions,
        ax=ax,
        with_labels=True,
        labels=str,
        node_color=_node_colours(model),
        node_size=350 if model.num_qubits > 5 else 600,
        font_size=8 if model.num_qubits > 5 else 11,
        edge_color="#5a6b8c",
    )
    if model.name == "hyperbolic":
        # Boundary of the Poincare disk, for orientation.
        ax.add_patch(plt.Circle((0, 0), 1.0, fill=False, ls="--", lw=0.8, color="#aaaaaa"))
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)
    ax.set_aspect("equal")
    ax.set_title(f"{model.name}: ports {model.ports} (A green, B purple)")
    ax.axis("off")
    return fig
