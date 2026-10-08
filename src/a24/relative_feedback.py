"""Counted source-anchored relative feedback and frozen affine current ROM.

The deployable cache never stores an inverse of the full background matrix.
Low-rank feedback is prepared using primal/adjoint background actions, with
zero power iterations.  The F arm solves at the currently supplied material.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field

import numpy as np
import scipy.linalg as la

from .contracts import NumericalFailure, guard_core, mass_unpack, pack, unpack
from .physics import Physics2D, as_columns


@dataclass(slots=True)
class LocalBlocks:
    """Disjoint local operator; dense conversion is explicit verification only."""
    n: int
    indices: tuple = ()
    blocks: tuple = ()

    @property
    def shape(self):
        return (self.n, self.n)

    def apply(self, value, *, adjoint=False):
        v, vector = as_columns(value, self.n, "local_feedback")
        out = np.zeros_like(v)
        for ind, block in zip(self.indices, self.blocks):
            out[ind] = (block.conj().T if adjoint else block) @ v[ind]
        return out[:, 0] if vector else out

    def __matmul__(self, value):
        return self.apply(value)

    def to_dense(self):
        out = np.zeros((self.n, self.n), dtype=np.complex128)
        for ind, block in zip(self.indices, self.blocks):
            out[np.ix_(ind, ind)] = block
        return out


@dataclass(slots=True)
class LowRankFeedback:
    Ug: np.ndarray
    Vg: np.ndarray
    D: LocalBlocks
    singular_values: np.ndarray
    metadata: dict

    @property
    def rank(self):
        return self.Ug.shape[1]


@dataclass(slots=True)
class CurrentROMBasis:
    V: np.ndarray
    GV: np.ndarray
    SV: np.ndarray
    LbV: np.ndarray
    Bb: np.ndarray
    metadata: dict

    @property
    def rank(self):
        return self.V.shape[1]


@dataclass(slots=True)
class RelativeState:
    chi: np.ndarray
    h: np.ndarray
    data: np.ndarray
    w: np.ndarray
    field: np.ndarray
    margins: dict
    extra: dict = dataclass_field(default_factory=dict, repr=False)


class ReferenceCache:
    def __init__(self, physics: Physics2D, chi_b, book=None, config=None):
        self.physics = physics
        self.book = physics.book if book is None else book
        self.physics.bind_book(self.book)
        self.config = {**physics.config, **dict(config or {})}
        self.chi_b = physics.validate_material(chi_b).copy()
        self.ab = physics.material_to_a(self.chi_b)
        self._lowrank = {}
        self._rom = {}
        self._locals = {}
        self._descriptor = self._make_descriptor()
        with self.book.span("reference_cache_build", reference_cache_builds=1):
            self.state_b = physics.full_state(self.chi_b)
            self.eb, self.yb = self.state_b.field, self.state_b.data
            receiver_identity = np.eye(physics.q, dtype=np.complex128)
            receiver_load = physics.observe(receiver_identity, adjoint=True)
            self.Z = self.solve_ref(receiver_load, adjoint=True)
            self.Db = np.ascontiguousarray(self.Z.conj().T)
            self.book.counts["receiver_cache_array_bytes"] += (
                receiver_identity.nbytes + self.Db.nbytes
            )
            self.book.counts["reference_cache_retained_bytes"] += (
                self.chi_b.nbytes + self.ab.nbytes + self.state_b.L.nbytes
                + self.state_b.factor[0].nbytes + self.state_b.factor[1].nbytes
                + self.state_b.current.nbytes + self.eb.nbytes + self.yb.nbytes
                + self.Z.nbytes + self.Db.nbytes
            )
            for array in (self.chi_b, self.ab, self.state_b.chi, self.state_b.current,
                          self.state_b.field, self.state_b.data, self.state_b.L,
                          self.state_b.factor[0], self.state_b.factor[1], self.Z, self.Db):
                array.flags.writeable = False

    def bind_book(self, book):
        self.book = book
        self.physics.bind_book(book)
        return self

    def _sync_book(self):
        self.physics.bind_book(self.book)

    def _make_descriptor(self):
        g = self.physics.geometry
        return {
            "adapter": "a24_2d_tm_a2",
            "geometry": {"grid": g.n, "side": g.side, "n_tx": g.n_tx,
                         "n_rx": g.n_rx, "radius_tx": g.radius_tx,
                         "radius_rx": g.radius_rx, "aperture": g.aperture},
            "frequency_hz": self.physics.frequency_hz,
            "precision": "complex128",
            "material_law": "scalar_chi",
            "current_normalization": "sqrt_cell_volume",
            "cell_volume": self.physics.volume,
            "background": np.c_[self.chi_b.real, self.chi_b.imag].tolist(),
        }

    @property
    def descriptor(self):
        return deepcopy(self._descriptor)

    def validate(self, descriptor):
        if descriptor != self._descriptor or self._make_descriptor() != self._descriptor:
            raise NumericalFailure("REFERENCE_CACHE_DESCRIPTOR_MISMATCH")
        return True

    def solve_ref(self, rhs, *, adjoint=False):
        self._sync_book()
        return self.physics.solve_factor(self.state_b.factor, rhs, adjoint=adjoint,
                                         role="reference")

    def apply_ref_L(self, rhs, *, adjoint=False):
        self._sync_book()
        return self.physics.apply_matrix(self.state_b.L, rhs, adjoint=adjoint,
                                         role="reference_L")

    def gb(self, rhs, *, adjoint=False):
        self._sync_book()
        if adjoint:
            return self.solve_ref(self.physics.green(rhs, adjoint=True), adjoint=True)
        return self.physics.green(self.solve_ref(rhs))

    def apply_db(self, rhs, *, adjoint=False):
        v, vector = as_columns(rhs, self.physics.q if adjoint else self.physics.n, "Db")
        label = "Db_adjoint" if adjoint else "Db"
        with self.book.span(label + "_cached_apply", **{label + "_actions": v.shape[1]}):
            out = (self.Db.conj().T if adjoint else self.Db) @ v
            self.book.counts["receiver_cache_result_bytes"] += out.nbytes
        return out[:, 0] if vector else out

    def apply_local(self, D, rhs, *, adjoint=False):
        v, vector = as_columns(rhs, self.physics.n, "D")
        if not D.blocks:
            return np.zeros_like(v[:, 0] if vector else v)
        label = "local_feedback_adjoint" if adjoint else "local_feedback"
        with self.book.span(label + "_apply", **{label + "_rhs": v.shape[1],
                                                "local_block_multiply_rhs":
                                                len(D.blocks) * v.shape[1]}):
            out = D.apply(v, adjoint=adjoint)
            self.book.counts["local_result_bytes"] += out.nbytes
        return out[:, 0] if vector else out

    def _local_operator(self, local):
        if not local:
            return LocalBlocks(self.physics.n)
        if "2x2" in self._locals:
            self.book.counts["local_operator_cache_hits"] += 1
            return self._locals["2x2"]
        indices, blocks, margins = [], [], []
        grid = self.physics.grid
        with self.book.span("local_background_build", local_background_builds=1):
            for i in range(0, grid, 2):
                for j in range(0, grid, 2):
                    ind = np.asarray([ii * grid + jj
                                      for ii in range(i, min(i + 2, grid))
                                      for jj in range(j, min(j + 2, grid))], dtype=int)
                    gloc = self.physics.G[np.ix_(ind, ind)]
                    local_L = np.eye(len(ind), dtype=np.complex128) - self.ab[ind, None] * gloc
                    with self.book.span("local_background_core_guard", core_guards=1):
                        margins.append(guard_core(local_L, self.config, "local_background"))
                    factor = self.physics.factor_matrix(local_L, role="local_background")
                    # A right-side solve, not a selected block of the full R_b.
                    with self.book.span("local_background_right_solve", linear_solve_rhs=len(ind),
                                        local_background_forward_RHS=len(ind)):
                        block = la.lu_solve(factor, gloc.T, trans=1, check_finite=False).T
                        if not np.isfinite(block).all():
                            raise NumericalFailure("NONFINITE_LOCAL_BACKGROUND_BLOCK")
                        self.book.counts["local_background_array_bytes"] += (
                            ind.nbytes + gloc.nbytes + local_L.nbytes + block.nbytes
                        )
                    indices.append(ind)
                    blocks.append(block)
                    ind.flags.writeable = False
                    block.flags.writeable = False
            D = LocalBlocks(self.physics.n, tuple(indices), tuple(blocks))
            self._locals["2x2"] = D
            self.local_background_margins = margins
        return D

    def prepare_lowrank(self, rank=16, local=False, seed=241008, oversampling=8):
        self._sync_book()
        rank, oversampling, seed = int(rank), int(oversampling), int(seed)
        if not 0 <= rank <= self.physics.n or oversampling < 0:
            raise ValueError("INVALID_FEEDBACK_RANK_OR_OVERSAMPLING")
        key = (rank, bool(local), seed, oversampling)
        if key in self._lowrank:
            self.book.counts["lowrank_cache_hits"] += 1
            prepared = self._lowrank[key]
            self.lowrank = prepared
            self.Ug, self.Vg, self.D = prepared.Ug, prepared.Vg, prepared.D
            return prepared.Ug, prepared.Vg, prepared.D
        with self.book.span("background_feedback_prepare", lowrank_preparations=1):
            D = self._local_operator(bool(local))
            width = min(self.physics.n, rank + oversampling) if rank else 0
            if rank:
                rng = np.random.default_rng(seed)
                omega = (rng.standard_normal((self.physics.n, width))
                         + 1j * rng.standard_normal((self.physics.n, width))) / np.sqrt(2.)
                Y = self.gb(omega) - self.apply_local(D, omega)
                with self.book.span("feedback_probe_QR", background_probe_columns=width):
                    Q, _ = la.qr(Y, mode="economic", check_finite=False)
                B = (self.gb(Q, adjoint=True) - self.apply_local(D, Q, adjoint=True)).conj().T
                with self.book.span("feedback_reduced_SVD", reduced_feedback_SVDs=1):
                    left, singular, right = la.svd(B, full_matrices=False, check_finite=False)
                    threshold=float(self.config.get('orthogonal_rank_rtol',1e-10))
                    retained=min(rank,int(np.sum(singular>threshold*singular[0]))) if len(singular) and singular[0]>0 else 0
                    roots = np.sqrt(singular[:retained])
                    Ug = (Q @ left[:, :retained]) * roots[None, :]
                    Vg = right[:retained].conj().T * roots[None, :]
                    self.book.counts["feedback_preparation_array_bytes"] += (
                        omega.nbytes + Y.nbytes + Q.nbytes + B.nbytes
                        + left.nbytes + singular.nbytes + right.nbytes
                        + Ug.nbytes + Vg.nbytes
                    )
                singular = singular[:retained].copy()
            else:
                Ug = np.empty((self.physics.n, 0), dtype=np.complex128)
                Vg = np.empty_like(Ug)
                singular = np.empty(0, dtype=np.float64)
            prepared = LowRankFeedback(Ug, Vg, D, singular,
                                       {"rank": Ug.shape[1],"requested_rank":rank, "local": bool(local), "seed": seed,
                                        "oversampling": oversampling, "probe_columns": width,
                                        "power_iterations": 0, "construction": "background_actions"})
            self._lowrank[key] = prepared
            self.lowrank = prepared
            self.Ug, self.Vg, self.D = Ug, Vg, D
            for array in (Ug, Vg, singular):
                array.flags.writeable = False
        return Ug, Vg, D

    def prepare_rom(self, rank=32, seed=241008):
        self._sync_book()
        rank, seed = int(rank), int(seed)
        if not 1 <= rank <= self.physics.n:
            raise ValueError("INVALID_CURRENT_ROM_RANK")
        key = (rank, seed)
        if key in self._rom:
            self.book.counts["current_rom_cache_hits"] += 1
            self.rom_basis = self._rom[key]
            return self._rom[key]
        with self.book.span("background_current_rom_prepare", current_rom_preparations=1):
            rng = np.random.default_rng(seed)
            count=int(self.config.get('rom_material_probes',8))
            from scipy.ndimage import gaussian_filter
            with self.book.span('current_rom_material_probes',material_probe_columns=count):
                probes=(rng.standard_normal((self.physics.N,count))
                        +1j*rng.standard_normal((self.physics.N,count)))/np.sqrt(2.)
                for j in range(count):
                    image=probes[:,j].reshape(self.physics.grid,self.physics.grid)
                    probes[:,j]=gaussian_filter(image.real,self.config.get('rom_probe_smoothing_cells',1.),mode='reflect').ravel()+1j*gaussian_filter(image.imag,self.config.get('rom_probe_smoothing_cells',1.),mode='reflect').ravel()
                probes/=la.norm(probes,axis=0)
                injections=(self.eb[:,:,None]*probes[:,None,:]).reshape(self.physics.n,self.physics.s*count)
            raw = self.solve_ref(injections)
            with self.book.span("current_rom_probe_SVD", current_rom_probe_columns=raw.shape[1]):
                left,sv,_=la.svd(raw,full_matrices=False,check_finite=False)
                actual=min(rank,int(np.sum(sv>self.config.get('orthogonal_rank_rtol',1e-10)*sv[0]))) if len(sv) and sv[0]>0 else 0
                V=left[:,:actual]
                if not actual:raise NumericalFailure('ZERO_CURRENT_ROM_RANK')
            GV = self.physics.green(V)
            SV = self.physics.observe(V)
            with self.book.span("current_rom_background_core", current_rom_core_assemblies=1):
                LbV = V - self.ab[:, None] * GV
                Bb = V.conj().T @ LbV
                self.book.counts["current_rom_preparation_array_bytes"] += (
                    probes.nbytes + raw.nbytes + V.nbytes + GV.nbytes + SV.nbytes
                    + LbV.nbytes + Bb.nbytes
                )
            prepared = CurrentROMBasis(V, GV, SV, LbV, Bb,
                                       {"rank": actual, "requested_rank":rank,"seed": seed,
                                        "construction": "background_material_tangent_snapshots",
                                        "material_probes":count,"source_columns":raw.shape[1],
                                        "truth_state_access": False})
            self._rom[key] = prepared
            self.rom_basis = prepared
            for array in (V, GV, SV, LbV, Bb):
                array.flags.writeable = False
        return prepared

    def background_matrix(self):
        """Known-background REAL data Jacobian in material mass coordinates.

        Only receiver-cache/known-field contractions are assembled.  No full
        current-material Jacobian, oracle state, or inverse is constructed.
        """
        p = self.physics
        with self.book.span("background_receiver_material_matrix",
                            background_material_directions=2 * p.N,
                            background_data_source_columns=2 * p.N * p.s):
            B = np.einsum("qn,ns->sqn", self.Db, self.eb) / p.sqrt_volume
            re = np.concatenate((B.real, B.imag), axis=1).reshape(2 * p.q * p.s, p.N)
            im = np.concatenate((-B.imag, B.real), axis=1).reshape(2 * p.q * p.s, p.N)
            result = np.concatenate((re, im), axis=1)
            self.book.counts["background_data_matrix_bytes"] += (
                B.nbytes + re.nbytes + im.nbytes + result.nbytes
            )
        return result


class RelativeFeedbackModel:
    def __init__(self, cache: ReferenceCache, kind="L", rank=16, local=False,
                 seed=241008, config=None, oversampling=8):
        self.cache = cache
        self.physics = cache.physics
        self.config = {**cache.config, **dict(config or {})}
        self.kind = str(kind).upper()
        if self.kind not in {"L", "F", "R", "ROM", "BORN"}:
            raise ValueError("UNKNOWN_RELATIVE_FEEDBACK_KIND")
        self.rank, self.local, self.seed = int(rank), bool(local), int(seed)
        self.Ug = self.Vg = self.D = self.rom = None
        self.Q = None
        if self.kind == "R":
            self.Ug, self.Vg, self.D = cache.prepare_lowrank(
                self.rank, self.local, self.seed, oversampling
            )
            self.rank=self.Ug.shape[1]
        elif self.kind == "ROM":
            rom_rank = int(self.config.get("rom_rank", self.config.get("target_current_rank", 32)))
            self.rom = cache.prepare_rom(rom_rank, self.seed)
            self.Q = self.rom.V
        self.actual_rank = (self.Ug.shape[1] if self.kind == "R" else
                            self.rom.rank if self.kind == "ROM" else 0)

    @property
    def book(self):
        return self.cache.book

    def _state(self, chi, state):
        a = self.physics.validate_material(chi)
        if state is None:
            return self.forward(a)
        if (not np.array_equal(a, state.chi)
                or state.extra.get("model_id") != id(self)):
            raise ValueError("STATE_MATERIAL_OR_MODEL_MISMATCH")
        return state

    def _solve_P(self, rhs, state, *, adjoint=False):
        v, vector = as_columns(rhs, self.physics.n, "P")
        factors = state.extra["P_factors"]
        if not factors:
            result = v[:, 0].copy() if vector else v.copy()
            self.book.counts["identity_local_solve_bytes"] += result.nbytes
            return result
        out = v.copy()
        for ind, factor in factors:
            out[ind] = self.physics.solve_factor(factor, v[ind], adjoint=adjoint,
                                                 role="local_P")
        return out[:, 0] if vector else out

    def _factor_R(self, state):
        h = state.h
        factors, p_margins = [], []
        for ind, block in zip(self.D.indices, self.D.blocks):
            P = np.eye(len(ind), dtype=np.complex128) - h[ind, None] * block
            self.book.counts["local_P_assembly_bytes"] += P.nbytes
            with self.book.span("relative_local_core_guard", core_guards=1):
                p_margins.append(guard_core(P, self.config, "P"))
            factor = self.physics.factor_matrix(P, role="local_P")
            factors.append((ind, factor))
        state.extra["P_factors"] = factors
        state.margins["P"] = p_margins
        if self.rank:
            with self.book.span("feedback_core_assembly", feedback_core_assemblies=1):
                CU = self._solve_P(h[:, None] * self.Ug, state)
                K = np.eye(self.rank, dtype=np.complex128) - self.Vg.conj().T @ CU
                self.book.counts["feedback_core_array_bytes"] += CU.nbytes + K.nbytes
            with self.book.span("relative_global_core_guard", core_guards=1):
                state.margins["K"] = guard_core(K, self.config, "K")
            state.extra["CU"] = CU
            state.extra["K"] = K
            state.extra["K_factor"] = self.physics.factor_matrix(K, role="feedback_K")
        else:
            state.extra["CU"] = np.empty((self.physics.n, 0), dtype=np.complex128)
            state.extra["K"] = np.empty((0, 0), dtype=np.complex128)
            state.extra["K_factor"] = None
            state.margins["K"] = {"name": "K", "rank": 0, "condition": 1.,
                                    "relative_sigma_min": 1., "sigma_min": None,
                                    "sigma_max": None}

    def feedback_apply(self, rhs, *, adjoint=False):
        if self.kind != "R":
            if self.kind in {"L", "BORN"}:
                v, vector = as_columns(rhs, self.physics.n, "feedback_zero")
                return np.zeros_like(v[:, 0] if vector else v)
            if self.kind == "F":
                return self.cache.gb(rhs, adjoint=adjoint)
            raise ValueError("CURRENT_ROM_HAS_NO_FEEDBACK_CLOSURE")
        v, vector = as_columns(rhs, self.physics.n, "feedback")
        out = self.cache.apply_local(self.D, v, adjoint=adjoint)
        if self.rank:
            with self.book.span("lowrank_feedback_adjoint_apply" if adjoint else
                                "lowrank_feedback_apply", lowrank_feedback_rhs=v.shape[1]):
                out += (self.Vg @ (self.Ug.conj().T @ v) if adjoint else
                        self.Ug @ (self.Vg.conj().T @ v))
                self.book.counts["lowrank_feedback_result_bytes"] += out.nbytes
        return out[:, 0] if vector else out

    def solve_A(self, rhs, state):
        self.cache._sync_book()
        v, vector = as_columns(rhs, self.physics.n, "A")
        if state.extra.get("model_id") != id(self):
            raise ValueError("STATE_MODEL_MISMATCH")
        if self.kind in {"L", "BORN"}:
            out = v.copy()
        elif self.kind == "F":
            native = state.extra["native"]
            out = self.cache.apply_ref_L(self.physics.solve_factor(native.factor, v,
                                                                    role="exact_feedback"))
        elif self.kind == "ROM":
            # Projected current tangent lifted into relative-source coordinates.
            c = self.physics.solve_factor(state.extra["ROM_factor"], self.rom.V.conj().T @ v,
                                           role="current_ROM")
            out = self.rom.LbV @ c
        else:
            t = self._solve_P(v, state)
            if self.rank:
                c = self.physics.solve_factor(state.extra["K_factor"], self.Vg.conj().T @ t,
                                               role="feedback_K")
                out = t + state.extra["CU"] @ c
            else:
                out = t
        return out[:, 0] if vector else out

    def solve_A_adjoint(self, rhs, state):
        self.cache._sync_book()
        v, vector = as_columns(rhs, self.physics.n, "A_adjoint")
        if state.extra.get("model_id") != id(self):
            raise ValueError("STATE_MODEL_MISMATCH")
        if self.kind in {"L", "BORN"}:
            out = v.copy()
        elif self.kind == "F":
            native = state.extra["native"]
            out = self.physics.solve_factor(native.factor,
                                           self.cache.apply_ref_L(v, adjoint=True),
                                           adjoint=True, role="exact_feedback")
        elif self.kind == "ROM":
            c = self.physics.solve_factor(state.extra["ROM_factor"], self.rom.LbV.conj().T @ v,
                                           adjoint=True, role="current_ROM")
            out = self.rom.V @ c
        else:
            t = self._solve_P(v, state, adjoint=True)
            if self.rank:
                gamma = self.physics.solve_factor(
                    state.extra["K_factor"], self.Ug.conj().T @ (state.h.conj()[:, None] * t),
                    adjoint=True, role="feedback_K"
                )
                out = t + self._solve_P(self.Vg @ gamma, state, adjoint=True)
            else:
                out = t
        return out[:, 0] if vector else out

    def forward(self, chi):
        self.cache._sync_book()
        chi = self.physics.validate_material(chi).copy()
        h = self.physics.material_to_a(chi) - self.cache.ab
        p = self.physics
        with self.book.span("relative_" + self.kind + "_forward",
                            relative_forward_calls=1, relative_forward_source_rhs=p.s):
            state = RelativeState(chi, h, None, None, None, {}, {"model_id": id(self)})
            if self.kind == "BORN":
                state.field = self.physics.incident
                state.w = h[:, None] * state.field
                state.data = self.cache.yb + self.physics.observe(state.w)
            elif self.kind == "F":
                native = p.full_state(chi)
                state.extra["native"] = native
                state.field = native.field
                state.w = h[:, None] * state.field
                state.data = self.cache.yb + self.cache.apply_db(state.w)
                state.margins["full_backward_residual"] = native.residual
            elif self.kind == "ROM":
                with self.book.span("current_rom_online_assembly", current_rom_core_assemblies=1):
                    B = self.rom.Bb - self.rom.V.conj().T @ (h[:, None] * self.rom.GV)
                    rhs = self.rom.V.conj().T @ (h[:, None] * self.cache.eb)
                    self.book.counts["current_rom_online_array_bytes"] += B.nbytes + rhs.nbytes
                with self.book.span("current_rom_core_guard", core_guards=1):
                    state.margins["ROM"] = guard_core(B, self.config, "ROM")
                state.extra["ROM_factor"] = p.factor_matrix(B, role="current_ROM")
                c = p.solve_factor(state.extra["ROM_factor"], rhs, role="current_ROM")
                with self.book.span("current_rom_cached_outputs", current_rom_output_source_rhs=p.s):
                    state.extra["coefficients"] = c
                    state.w = self.rom.LbV @ c
                    state.field = self.cache.eb + self.rom.GV @ c
                    state.data = self.cache.yb + self.rom.SV @ c
                    self.book.counts["current_rom_output_array_bytes"] += (
                        state.w.nbytes + state.field.nbytes + state.data.nbytes
                    )
            else:
                if self.kind == "R":
                    self._factor_R(state)
                state.w = self.solve_A(h[:, None] * self.cache.eb, state)
                state.field = (self.cache.eb.copy() if self.kind == "L" else
                               self.cache.eb + self.feedback_apply(state.w))
                state.data = self.cache.yb + self.cache.apply_db(state.w)
            self.book.counts["relative_state_array_bytes"] += chi.nbytes + h.nbytes
            if not all(np.isfinite(a).all() for a in (state.w, state.field, state.data)):
                raise NumericalFailure("NONFINITE_RELATIVE_FORWARD")
        return state

    def _mass_directions(self, delta_mass):
        value = np.asarray(delta_mass)
        vector = value.ndim == 1
        if vector:
            value = value[:, None]
        if (np.iscomplexobj(value) or value.ndim != 2
                or value.shape[0] != 2 * self.physics.N or not np.isfinite(value).all()):
            raise ValueError("REAL_MATERIAL_MASS_DIRECTIONS_REQUIRED")
        dchi = np.column_stack([mass_unpack(value[:, j], self.physics.volume)
                                for j in range(value.shape[1])])
        return dchi, vector

    def jvp(self, chi, delta_mass, state=None):
        state = self._state(chi, state)
        dchi, vector = self._mass_directions(delta_mass)
        p, directions = self.physics, dchi.shape[1]
        with self.book.span("relative_" + self.kind + "_jvp",
                            material_tangent_directions=directions,
                            material_tangent_source_rhs=p.s * directions):
            injection = (state.field[:, :, None] * dchi[:, None, :]).reshape(p.n, p.s * directions)
            if self.kind == "BORN":
                data = p.observe(injection)
            elif self.kind == "ROM":
                coefficients = p.solve_factor(state.extra["ROM_factor"], self.rom.V.conj().T @ injection,
                                               role="current_ROM")
                with self.book.span("current_rom_tangent_cached_output",
                                    current_rom_tangent_output_rhs=p.s * directions):
                    data = self.rom.SV @ coefficients
            else:
                data = self.cache.apply_db(self.solve_A(injection, state))
            data = data.reshape(p.q, p.s, directions)
            result = np.column_stack([pack(data[:, :, j]) for j in range(directions)])
            self.book.counts["tangent_array_bytes"] += injection.nbytes + data.nbytes + result.nbytes
        return result[:, 0] if vector else result

    def adjoint(self, chi, packed_REAL_load, state=None):
        state = self._state(chi, state)
        p = self.physics
        load = np.asarray(packed_REAL_load)
        vector = load.ndim == 1
        if vector:
            load = load[:, None]
        if (np.iscomplexobj(load) or load.ndim != 2
                or load.shape[0] != 2 * p.q * p.s or not np.isfinite(load).all()):
            raise ValueError("REAL_PACKED_DATA_LOAD_REQUIRED")
        directions = load.shape[1]
        with self.book.span("relative_" + self.kind + "_adjoint",
                            data_adjoint_directions=directions,
                            data_adjoint_source_rhs=p.s * directions):
            data_load = np.stack([unpack(load[:, j], p.q, p.s)
                                  for j in range(directions)], axis=2).reshape(p.q, p.s * directions)
            if self.kind == "BORN":
                z = p.observe(data_load, adjoint=True)
            elif self.kind == "ROM":
                coefficients = p.solve_factor(state.extra["ROM_factor"], self.rom.SV.conj().T @ data_load,
                                               adjoint=True, role="current_ROM")
                with self.book.span("current_rom_material_adjoint_lift",
                                    current_rom_adjoint_lift_rhs=p.s * directions):
                    z = self.rom.V @ coefficients
            else:
                z = self.solve_A_adjoint(self.cache.apply_db(data_load, adjoint=True), state)
            z = z.reshape(p.n, p.s, directions)
            result = np.column_stack([p.material_pullback(state.field, z[:, :, j])
                                      for j in range(directions)])
            self.book.counts["adjoint_array_bytes"] += data_load.nbytes + z.nbytes + result.nbytes
        return result[:, 0] if vector else result
