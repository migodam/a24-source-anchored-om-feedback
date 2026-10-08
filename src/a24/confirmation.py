"""Conditional four-label 3-D Maxwell confirmation over the frozen A20 DDA.

This module is a separate vector adapter; no 2-D TM branch is reused. Runtime
image builders receive observations and known-background operators only.
Scientific gates remain with the caller. All geometry, label, candidate,
validation, core and output actions use the caller's charged ledger.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
import time
import warnings

import numpy as np
from scipy import linalg as la

from a20.backend import Adapter, MaterialChart, Problem, kernel
from a20.costs import BudgetExceeded, write_json
from .contracts import (NumericalFailure, OnlineObservation, guard_core,
                        mass_pack, mass_unpack, online_config, pack, relative_error, unpack)
from .material_updates import prox_tv_box, tv_value
from .pilot import append_failure, write_csv


def _columns(value, n):
    value = np.asarray(value, dtype=np.complex128)
    vector = value.ndim == 1
    if vector:
        value = value[:, None]
    if value.ndim != 2 or value.shape[0] != n or not np.isfinite(value).all():
        raise ValueError("CONFIRMATION_COMPLEX_COLUMNS_REQUIRED")
    return value, vector


def _transverse(direction):
    direction = np.asarray(direction, float)
    axis = np.eye(3)[int(np.argmin(np.abs(direction)))]
    first = np.cross(direction, axis)
    first /= la.norm(first)
    second = np.cross(direction, first)
    second /= la.norm(second)
    return first, second


def _geometry(config):
    grid = int(config.get("confirmation_grid", 6))
    k = float(config.get("confirmation_k", 2.0))
    sources = int(config.get("confirmation_source_count", 6))
    receivers = int(config.get("confirmation_receiver_count", 16))
    if (grid, k, sources, receivers) != (6, 2., 6, 16):
        raise ValueError("CONFIRMATION_FROZEN_GEOMETRY_CHANGED")
    side = 1.5
    axis = -side / 2 + (np.arange(grid) + .5) * (side / grid)
    mesh = np.meshgrid(axis, axis, axis, indexing="ij")
    points = np.column_stack([entry.ravel() for entry in mesh])
    dirs = np.vstack((np.eye(3), -np.eye(3)))
    pols = np.asarray([_transverse(direction)[0] for direction in dirs], complex)
    z = 1 - 2 * (np.arange(receivers) + .5) / receivers
    angle = np.pi * (3 - np.sqrt(5.)) * np.arange(receivers)
    radial = np.sqrt(1 - z * z)
    unit = np.c_[radial * np.cos(angle), radial * np.sin(angle), z]
    receiver_points = 2 * unit
    observation_basis = np.asarray([_transverse(direction) for direction in unit], complex)
    radius = la.norm(points, axis=1)
    background = np.full(len(points), .1 + .04j, dtype=np.complex128)
    background[(radius >= .3) & (radius <= .55)] = 2. + .1j
    return points, (side / grid) ** 3, dirs, pols, receiver_points, observation_basis, background


@dataclass(slots=True)
class Full3DState:
    chi: np.ndarray
    current: np.ndarray
    field: np.ndarray
    data: np.ndarray
    L: np.ndarray
    factor: tuple
    a: np.ndarray
    da: np.ndarray
    residual: float
    native: object


class Physics3D:
    """A20 current c=p/sqrt(v), exciting field E/sqrt(v), and native GS."""
    def __init__(self, config, book):
        self.config, self.book = dict(config), book
        with book.span("confirmation_geometry_contract", confirmation_geometry_builds=1):
            points, volume, dirs, pols, receivers, basis, self.background = _geometry(config)
            self.grid, self.components, self.k = 6, 3, 2.
            self.N, self.n, self.s, self.q = len(points), 3 * len(points), 6, 32
            self.volume, self.sqrt_volume, self.points = volume, np.sqrt(volume), points
            chart = MaterialChart(volume, self.N, None, "full_material_mass")
            problem = Problem(0, points, volume, np.zeros((self.s, self.q), complex),
                              1., self.background.copy(), chart, dirs, pols, receivers, basis, self.k)
            self.adapter = Adapter(problem, device="cpu", book=book, whitening=1.)
            self.model = self.adapter.model
            self.G, self.S = self.model.Goff, self.model.GS
            self.incident = self.model.incident.T / self.sqrt_volume
            book.counts["confirmation_geometry_array_bytes"] += (
                points.nbytes + dirs.nbytes + pols.nbytes + receivers.nbytes
                + basis.nbytes + self.G.nbytes + self.S.nbytes + self.model.GD.nbytes
                + self.model.incident.nbytes + self.incident.nbytes + self.background.nbytes
            )

    def validate_material(self, chi):
        chi = np.asarray(chi, dtype=np.complex128)
        if chi.shape != (self.N,) or not np.isfinite(chi).all():
            raise NumericalFailure("CONFIRMATION_INVALID_MATERIAL_ARRAY")
        tol = float(self.config.get("feasibility_tolerance", 1e-10))
        if (np.any(chi.real < -.5 - tol) or np.any(chi.real > 4. + tol)
                or np.any(chi.imag < -tol) or np.any(chi.imag > .5 + tol)):
            raise NumericalFailure("CONFIRMATION_MATERIAL_DOMAIN_VIOLATION")
        radiation = 3 * self.k ** 3 / (6 * np.pi) * self.volume * chi
        den = chi + 3 - 1j * radiation
        scale = np.abs(chi) + 3 + np.abs(radiation)
        if np.any(np.abs(den) / scale < self.config.get("pole_relative_floor", 1e-10)):
            raise NumericalFailure("CONFIRMATION_CONSTITUTIVE_POLE")
        return chi

    def material(self, chi):
        chi = self.validate_material(chi)
        with self.book.span("confirmation_original_material_law", material_law_evaluations=1):
            a, da = kernel.polarizability(chi, self.volume, self.k)
            if not (np.isfinite(a).all() and np.isfinite(da).all()):
                raise NumericalFailure("CONFIRMATION_NONFINITE_MATERIAL_LAW")
        return a, da

    def green(self, rhs, adjoint=False):
        value, vector = _columns(rhs, self.n)
        label = "confirmation_G_adjoint" if adjoint else "confirmation_G"
        with self.book.span(label, **{label + "_rhs": value.shape[1]}):
            result = self.model.goff_apply(value, adjoint=adjoint)
            self.book.counts["confirmation_green_result_bytes"] += result.nbytes
        return result[:, 0] if vector else result

    def observe(self, rhs, adjoint=False):
        value, vector = _columns(rhs, self.q if adjoint else self.n)
        result = self.adapter.apply_S_adjoint(value) if adjoint else self.adapter.apply_S(value)
        self.book.counts["confirmation_receiver_result_bytes"] += result.nbytes
        return result[:, 0] if vector else result

    def factor(self, matrix, role):
        with self.book.span("confirmation_" + role + "_factor",
                            **{"confirmation_" + role + "_LU_factorizations": 1}):
            if not np.isfinite(matrix).all():
                raise NumericalFailure("CONFIRMATION_NONFINITE_CORE")
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", la.LinAlgWarning)
                    result = self.model.solver.factorize(matrix, label="reduced_" + role)
            except (la.LinAlgError, la.LinAlgWarning, ValueError) as exc:
                raise NumericalFailure("CONFIRMATION_FACTOR_FAILED:" + str(exc)) from exc
            self.book.counts["confirmation_factor_bytes"] += result[1].nbytes + result[2].nbytes
        return result

    def solve(self, factor, rhs, role, adjoint=False):
        value, vector = _columns(rhs, factor[1].shape[0])
        suffix = "_adjoint" if adjoint else "_forward"
        with self.book.span("confirmation_" + role + suffix + "_solve",
                            **{"confirmation_" + role + suffix + "_RHS": value.shape[1]}):
            try:
                result = self.model.solver.solve(factor, value, trans=2 if adjoint else 0,
                                                 label=role + suffix)
            except (la.LinAlgError, ValueError) as exc:
                raise NumericalFailure("CONFIRMATION_SOLVE_FAILED:" + str(exc)) from exc
            if not np.isfinite(result).all():
                raise NumericalFailure("CONFIRMATION_NONFINITE_SOLVE")
            self.book.counts["confirmation_solve_result_bytes"] += result.nbytes
        return result[:, 0] if vector else result

    def full_state(self, chi):
        chi = self.validate_material(chi)
        with self.book.span("confirmation_native_full_state", confirmation_full_forward_calls=1):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", la.LinAlgWarning)
                    native = self.adapter.full_state(chi, reuse=False)
            except (la.LinAlgError, la.LinAlgWarning, ValueError) as exc:
                raise NumericalFailure("CONFIRMATION_NATIVE_FORWARD_FAILED:" + str(exc)) from exc
            with self.book.span("confirmation_native_residual_audit",
                                confirmation_residual_audits=1,
                                confirmation_residual_source_rhs=self.s):
                residual = native.source_residual()
                if not np.isfinite(residual) or residual > self.config.get("backward_residual_tolerance", 1e-10):
                    raise NumericalFailure("CONFIRMATION_NATIVE_BACKWARD_RESIDUAL:" + str(residual))
            field = native.exciting.T / self.sqrt_volume
            current, data = native.current.T, native.field.T
            if not (np.isfinite(field).all() and np.isfinite(current).all() and np.isfinite(data).all()):
                raise NumericalFailure("CONFIRMATION_NONFINITE_NATIVE_STATE")
            self.book.counts["confirmation_full_state_array_bytes"] += (
                native.chi.nbytes + native.a.nbytes + native.da.nbytes + native.A.nbytes
                + native.L.nbytes + native._L_factor[1].nbytes + native._L_factor[2].nbytes
                + native.current.nbytes + native.p.nbytes + native.exciting.nbytes
                + native.field.nbytes + field.nbytes
            )
            # A20's convenience caches are unnecessary here. In particular,
            # an evaluator label must not remain reachable as a runtime cache.
            self.adapter._full_cache = None
            self.adapter._operator_chi = None
            self.adapter._operator_L = None
            self.adapter._operator_gpu = None
        return Full3DState(native.chi, current, field, data, native.L,
                           native._L_factor, native.a, native.da, residual, native)

    def material_pullback(self, field, da, z):
        field, _ = _columns(field, self.n)
        z, _ = _columns(z, self.n)
        if field.shape != z.shape:
            raise ValueError("CONFIRMATION_MATCHED_SOURCES_REQUIRED")
        with self.book.span("confirmation_original_material_pullback",
                            confirmation_material_adjoint_directions=1,
                            confirmation_material_adjoint_source_rhs=field.shape[1]):
            contraction = (np.repeat(da, 3)[:, None] * field).conj() * z
            t = contraction.reshape(self.N, 3, field.shape[1]).sum(axis=(1, 2)) / self.sqrt_volume
            result = np.r_[t.real, t.imag]
            self.book.counts["confirmation_material_pullback_bytes"] += contraction.nbytes + result.nbytes
        return result


class Reference3D:
    def __init__(self, physics):
        self.physics, self.book = physics, physics.book
        self.chi_b = physics.background.copy()
        with self.book.span("confirmation_reference_prepare", confirmation_reference_preparations=1):
            self.state_b = physics.full_state(self.chi_b)
            self.ab = self.state_b.a.copy()
            self.eb, self.yb, self.cb = self.state_b.field, self.state_b.data, self.state_b.current
            identity = np.eye(physics.q, dtype=np.complex128)
            self.Z = self.solve_ref(physics.observe(identity, adjoint=True), adjoint=True)
            self.Db = np.ascontiguousarray(self.Z.conj().T)
            self.book.counts["confirmation_reference_cache_bytes"] += (
                self.chi_b.nbytes + self.ab.nbytes + self.Z.nbytes + self.Db.nbytes
                + self.eb.nbytes + self.yb.nbytes + self.cb.nbytes
                + self.state_b.L.nbytes + self.state_b.factor[1].nbytes
            )
            for array in (self.chi_b, self.ab, self.Z, self.Db, self.eb, self.yb, self.cb,
                          self.state_b.L, self.state_b.factor[1], self.state_b.factor[2]):
                array.flags.writeable = False

    def solve_ref(self, rhs, adjoint=False):
        return self.physics.solve(self.state_b.factor, rhs, "full_reference", adjoint)

    def ref_L(self, rhs, adjoint=False):
        value, vector = _columns(rhs, self.physics.n)
        with self.book.span("confirmation_reference_L_adjoint" if adjoint else
                            "confirmation_reference_L", confirmation_reference_L_rhs=value.shape[1]):
            result = (self.state_b.L.conj().T if adjoint else self.state_b.L) @ value
        return result[:, 0] if vector else result

    def gb(self, rhs, adjoint=False):
        if adjoint:
            return self.solve_ref(self.physics.green(rhs, adjoint=True), adjoint=True)
        return self.physics.green(self.solve_ref(rhs))

    def db(self, rhs, adjoint=False):
        value, vector = _columns(rhs, self.physics.q if adjoint else self.physics.n)
        with self.book.span("confirmation_Db_adjoint" if adjoint else "confirmation_Db",
                            confirmation_Db_rhs=value.shape[1]):
            result = (self.Db.conj().T if adjoint else self.Db) @ value
            self.book.counts["confirmation_Db_result_bytes"] += result.nbytes
        return result[:, 0] if vector else result

    def lowrank(self, seed, rank=16, oversampling=8):
        p = self.physics
        if rank != 16 or oversampling != 8:
            raise ValueError("CONFIRMATION_FROZEN_RANK_CHANGED")
        with self.book.span("confirmation_background_feedback_prepare",
                            confirmation_lowrank_preparations=1):
            width = rank + oversampling
            rng = np.random.default_rng(seed)
            probes = (rng.standard_normal((p.n, width))
                      + 1j * rng.standard_normal((p.n, width))) / np.sqrt(2.)
            Y = self.gb(probes)
            Q, _ = la.qr(Y, mode="economic", check_finite=False)
            B = self.gb(Q, adjoint=True).conj().T
            left, singular, right = la.svd(B, full_matrices=False, check_finite=False)
            root = np.sqrt(singular[:rank])
            Ug = (Q @ left[:, :rank]) * root[None, :]
            Vg = right[:rank].conj().T * root[None, :]
            self.book.counts["confirmation_feedback_prepare_array_bytes"] += (
                probes.nbytes + Y.nbytes + Q.nbytes + B.nbytes + left.nbytes
                + singular.nbytes + right.nbytes + Ug.nbytes + Vg.nbytes
            )
            Ug.flags.writeable = Vg.flags.writeable = False
        return Ug, Vg, singular[:rank].copy()

    def background_matrix(self):
        p = self.physics
        with self.book.span("confirmation_background_receiver_material_matrix",
                            confirmation_background_material_directions=2 * p.N,
                            confirmation_background_data_source_columns=2 * p.N * p.s):
            B = np.einsum("qnc,ncs,n->sqn", self.Db.reshape(p.q, p.N, 3),
                          self.eb.reshape(p.N, 3, p.s), self.state_b.da) / p.sqrt_volume
            real = np.concatenate((B.real, B.imag), axis=1).reshape(2 * p.q * p.s, p.N)
            imag = np.concatenate((-B.imag, B.real), axis=1).reshape(2 * p.q * p.s, p.N)
            result = np.concatenate((real, imag), axis=1)
            self.book.counts["confirmation_background_matrix_bytes"] += (
                B.nbytes + real.nbytes + imag.nbytes + result.nbytes
            )
        return result


@dataclass(slots=True)
class State3D:
    chi: np.ndarray
    h: np.ndarray
    da: np.ndarray
    current: np.ndarray
    field: np.ndarray
    w: np.ndarray
    data: np.ndarray
    margins: dict
    extra: dict = dataclass_field(default_factory=dict, repr=False)


class Relative3D:
    """Complete material source and D=0 feedback, using original a and a'."""
    def __init__(self, cache, kind, seed):
        self.cache, self.physics, self.book = cache, cache.physics, cache.book
        self.kind = kind
        if kind not in {"L", "F", "R16"}:
            raise ValueError("CONFIRMATION_UNKNOWN_ARM")
        self.Ug = self.Vg = self.singular = None
        if kind == "R16":
            self.Ug, self.Vg, self.singular = cache.lowrank(seed)

    def solve_A(self, rhs, state, adjoint=False):
        value, vector = _columns(rhs, self.physics.n)
        if state.extra.get("model_id") != id(self):
            raise ValueError("CONFIRMATION_STATE_MODEL_MISMATCH")
        if self.kind == "L":
            result = value.copy()
        elif self.kind == "F":
            native = state.extra["native"]
            if adjoint:
                result = self.physics.solve(native.factor, self.cache.ref_L(value, adjoint=True),
                                             "full_exact_feedback", adjoint=True)
            else:
                result = self.cache.ref_L(self.physics.solve(native.factor, value,
                                                             "full_exact_feedback"))
        elif adjoint:
            gamma = self.physics.solve(state.extra["factor"],
                                        self.Ug.conj().T @ (state.h.conj()[:, None] * value),
                                        "reduced_feedback", adjoint=True)
            result = value + self.Vg @ gamma
        else:
            gamma = self.physics.solve(state.extra["factor"], self.Vg.conj().T @ value,
                                        "reduced_feedback")
            result = value + state.extra["HU"] @ gamma
        return result[:, 0] if vector else result

    def forward(self, chi):
        p = self.physics
        chi = p.validate_material(chi).copy()
        a, da = p.material(chi)
        h = np.repeat(a - self.cache.ab, 3)
        with self.book.span("confirmation_" + self.kind + "_forward",
                            confirmation_relative_forward_source_rhs=p.s):
            extra, margins = {"model_id": id(self)}, {}
            state = State3D(chi, h, da, None, None, None, None, margins, extra)
            if self.kind == "F":
                native = p.full_state(chi)
                extra["native"] = native
                state.field, state.current = native.field, native.current
                state.w = h[:, None] * state.field
                margins["full_backward_residual"] = native.residual
            else:
                if self.kind == "R16":
                    HU = h[:, None] * self.Ug
                    K = np.eye(16, dtype=np.complex128) - self.Vg.conj().T @ HU
                    with self.book.span("confirmation_feedback_core_guard", confirmation_core_guards=1):
                        margins["K"] = guard_core(K, p.config, "confirmation_K")
                    extra.update(HU=HU, K=K, factor=p.factor(K, "feedback_K"))
                    self.book.counts["confirmation_online_core_bytes"] += HU.nbytes + K.nbytes
                state.w = self.solve_A(h[:, None] * self.cache.eb, state)
                if self.kind == "R16":
                    with self.book.span("confirmation_feedback_field_apply",
                                        confirmation_lowrank_feedback_source_rhs=p.s):
                        state.field = self.cache.eb + self.Ug @ (self.Vg.conj().T @ state.w)
                else:
                    state.field = self.cache.eb.copy()
                # Requested current output is an explicit, charged R_b action.
                state.current = self.cache.cb + self.cache.solve_ref(state.w)
            state.data = self.cache.yb + self.cache.db(state.w)
            self.book.counts["confirmation_relative_state_array_bytes"] += (
                chi.nbytes + h.nbytes + da.nbytes + state.w.nbytes
                + state.field.nbytes + state.current.nbytes + state.data.nbytes
            )
            if not all(np.isfinite(value).all() for value in
                       (state.current, state.field, state.w, state.data)):
                raise NumericalFailure("CONFIRMATION_NONFINITE_RELATIVE_STATE")
        return state

    def _check(self, chi, state):
        if state is None:
            return self.forward(chi)
        if not np.array_equal(chi, state.chi) or state.extra.get("model_id") != id(self):
            raise ValueError("CONFIRMATION_STALE_STATE")
        return state

    def jvp(self, chi, delta_mass, state=None):
        state = self._check(chi, state)
        p = self.physics
        delta = mass_unpack(delta_mass, p.volume)
        if delta.shape != (p.N,) or not np.isfinite(delta).all():
            raise ValueError("CONFIRMATION_REAL_MASS_DIRECTION_REQUIRED")
        with self.book.span("confirmation_" + self.kind + "_jvp",
                            confirmation_material_tangent_directions=1,
                            confirmation_material_tangent_source_rhs=p.s):
            injection = np.repeat(state.da * delta, 3)[:, None] * state.field
            return pack(self.cache.db(self.solve_A(injection, state)))

    def adjoint(self, chi, real_load, state=None):
        state = self._check(chi, state)
        p = self.physics
        with self.book.span("confirmation_" + self.kind + "_adjoint",
                            confirmation_data_adjoint_directions=1,
                            confirmation_data_adjoint_source_rhs=p.s):
            data_load = unpack(real_load, p.q, p.s)
            z = self.solve_A(self.cache.db(data_load, adjoint=True), state, adjoint=True)
            return p.material_pullback(state.field, state.da, z)


def _prepare(cache, book):
    with book.span("confirmation_background_step_prepare"):
        J = cache.background_matrix()
        den = float(la.norm(cache.yb) ** 2)
        if den <= 0:
            raise NumericalFailure("CONFIRMATION_ZERO_BACKGROUND_DATA_SCALE")
        largest = float(la.eigh(J @ J.T, subset_by_index=(len(J) - 1, len(J) - 1),
                                eigvals_only=True)[0] / den)
        if not np.isfinite(largest) or largest <= 0:
            raise NumericalFailure("CONFIRMATION_ZERO_BACKGROUND_INFORMATION")
        return {"J": J, "data_norm2": den, "step": .8 / largest,
                "lambda_max_normalized_background_Hessian": largest}


def _invariants(cache, models, config, book):
    """Known background and a fixed legal candidate, before any label exists."""
    p = cache.physics
    rng = np.random.default_rng(np.random.SeedSequence([config["master_seed"], 340924]))
    direction = rng.standard_normal(2 * p.N)
    direction /= la.norm(direction)
    load = rng.standard_normal(2 * p.q * p.s)
    load /= la.norm(load)
    chi = cache.chi_b + .03 + .005j
    rows = []
    with book.span("confirmation_inline_primal_dual_identities"):
        for kind, model in models.items():
            at_background = model.forward(cache.chi_b)
            state = model.forward(chi)
            tangent = model.jvp(chi, direction, state)
            adjoint = model.adjoint(chi, load, state)
            left, right = float(tangent @ load), float(direction @ adjoint)
            dot_error = abs(left - right) / max(abs(left), abs(right), 1e-14)
            step = 1e-5
            dchi = mass_unpack(direction, p.volume)
            plus, minus = model.forward(chi + step * dchi), model.forward(chi - step * dchi)
            finite_difference = pack(plus.data - minus.data) / (2 * step)
            fd_error = relative_error(finite_difference, tangent)
            anchor_error = relative_error(at_background.data, cache.yb)
            anchor_source = float(la.norm(at_background.w))
            constitutive = relative_error(state.w, state.h[:, None] * state.field)
            row = {"method": kind, "anchor_data_error": anchor_error,
                   "anchor_source_norm": anchor_source, "real_adjoint_error": dot_error,
                   "finite_difference_error": fd_error, "finite_difference_step": step,
                   "relative_source_equation_error": constitutive}
            if kind == "F":
                native = state.extra["native"]
                row["full_relative_data_error"] = relative_error(state.data, native.data)
                row["full_relative_current_error"] = relative_error(
                    cache.solve_ref(state.w), native.current - cache.cb)
                native_jvp = p.adapter.full_tangent_action(chi, native.native, direction)
                native_vjp = p.adapter.full_adjoint_action(chi, native.native, load)
                row["original_adapter_jvp_error"] = relative_error(tangent, native_jvp)
                row["original_adapter_adjoint_error"] = relative_error(adjoint, native_vjp)
            if kind == "R16":
                rhs = rng.standard_normal((p.n, 2)) + 1j * rng.standard_normal((p.n, 2))
                cot = rng.standard_normal((p.n, 2)) + 1j * rng.standard_normal((p.n, 2))
                primal = model.solve_A(rhs, state)
                dual = model.solve_A(cot, state, adjoint=True)
                lhs, rhs_dot = np.vdot(primal, cot), np.vdot(rhs, dual)
                row["core_inverse_adjoint_error"] = float(
                    abs(lhs - rhs_dot) / max(abs(lhs), abs(rhs_dot), 1e-14))
            rows.append(row)
        background_tangent = models["F"].jvp(cache.chi_b, direction,
                                              models["F"].forward(cache.chi_b))
        J_error = relative_error(cache.background_matrix() @ direction, background_tangent)
        tolerance = float(config.get("identity_tolerance", 1e-10))
        identity_values = [J_error]
        for row in rows:
            identity_values.extend(value for key, value in row.items()
                                   if key.endswith("error") and key != "finite_difference_error")
            identity_values.append(row["anchor_source_norm"])
        if any(value is None or value > tolerance for value in identity_values):
            raise NumericalFailure("CONFIRMATION_INLINE_IDENTITY_FAILED:" + str(rows))
        if any(row["finite_difference_error"] is None or
               row["finite_difference_error"] > config.get("fd_platform_tolerance", 1e-6)
               for row in rows):
            raise NumericalFailure("CONFIRMATION_INLINE_FINITE_DIFFERENCE_FAILED:" + str(rows))
    return {"status": "PASS", "known_background_J_error": J_error,
            "rows": rows, "scope": "known background and fixed current candidate; no labels"}


def _initialization(cache, observation, prep, config, book):
    xb = mass_pack(cache.chi_b, cache.physics.volume)
    with book.span("confirmation_common_initialization"):
        gradient = prep["J"].T @ pack(cache.yb - observation.data) / prep["data_norm2"]
        x, meta = prox_tv_box(xb - prep["step"] * gradient, xb, prep["step"] * .01,
                              (6, 6, 6), cache.physics.volume, config, book=book)
    return x, meta


def _objective(model, state, observation, prep, x, xb):
    with model.book.span("confirmation_material_objective", confirmation_tv_objective_evaluations=1):
        residual = pack(state.data - observation.data)
        data = .5 * float(residual @ residual) / prep["data_norm2"]
        tv = tv_value(x - xb, (6, 6, 6), model.physics.volume)
    return data + .01 * tv, data, tv


def _reconstruct(model, observation, x0, prep, config, book):
    """Only online observation and fixed background; no evaluator arguments."""
    p = model.physics
    xb = mass_pack(model.cache.chi_b, p.volume)
    x, history = x0.copy(), []
    before, started = book.snapshot(), time.perf_counter()
    with book.span("confirmation_online_measurement_to_image"):
        state = model.forward(mass_unpack(x, p.volume))
        for block in range(3):
            book.check()
            old, old_data, old_tv = _objective(model, state, observation, prep, x, xb)
            gradient = model.adjoint(state.chi, pack(state.data - observation.data), state)
            gradient /= prep["data_norm2"]
            trials, accepted = [], False
            for retry in range(2):
                step = prep["step"] / 2 ** retry
                candidate, prox = prox_tv_box(x - step * gradient, xb, step * .01,
                                              (6, 6, 6), p.volume, config, book=book)
                trial = model.forward(mass_unpack(candidate, p.volume))
                new, data, tv = _objective(model, trial, observation, prep, candidate, xb)
                ok = new <= old + 1e-12 * max(1., abs(old))
                trials.append({"retry": retry, "step": step, "objective": new,
                               "data_loss": data, "tv": tv, "prox": prox,
                               "accepted": ok, "margins": trial.margins})
                if ok:
                    x, state, accepted = candidate, trial, True
                    break
            history.append({"block": block, "old_objective": old,
                            "old_data_loss": old_data, "old_tv": old_tv,
                            "gradient_mass_norm": float(la.norm(gradient)),
                            "accepted": accepted, "trials": trials})
        chi = p.validate_material(mass_unpack(x, p.volume)).copy()
    return {"chi": chi, "x": x, "state": state, "history": history,
            "online_s": time.perf_counter() - started, "cost": book.delta(before)}


def _patterns(points):
    centered = points - np.array([-.1, .05, 0.])
    radius = la.norm(centered, axis=1)
    shell = ((radius >= .18) & (radius <= .32)).astype(float)
    shell += .5 * (radius <= .12)
    box = ((points[:, 0] >= -.55) & (points[:, 0] <= -.05)
           & (points[:, 1] >= -.40) & (points[:, 1] <= .15)
           & (points[:, 2] >= -.35) & (points[:, 2] <= .20)).astype(float)
    box += .7 * (la.norm(points - np.array([.35, .20, .15]), axis=1) <= .20)
    phase = (1 + .2j) / np.sqrt(1.04)
    return {3401: ("spherical_shell", phase * shell),
            3402: ("asymmetric_box_ball", phase * box)}


def _evaluate(physics, cache, truth, clean, observation, got):
    """Full physics is evaluated only after the material image is frozen."""
    with physics.book.span("confirmation_offline_full_image_validation"):
        full = physics.full_state(got["chi"])
        linear_a, _ = physics.material(got["chi"])
        linear_data = cache.yb + cache.db(np.repeat(linear_a - cache.ab, 3)[:, None] * cache.eb)
        error = got["chi"] - truth
        delta = truth - cache.chi_b
        measured_delta_norm = float(la.norm(observation.data - cache.yb))
        signal = float(la.norm(full.data - linear_data))
        closure = float(la.norm(got["state"].data - full.data))
        floor = 1e-12 * float(la.norm(cache.yb))
        residual = float(la.norm(full.data - observation.data))
        forcing = np.repeat(full.a, 3)[:, None] * physics.incident
        with physics.book.span("confirmation_relative_current_physical_residual",
                               confirmation_physical_current_residual_rhs=physics.s):
            relative_current_residual = float(la.norm(full.L @ got["state"].current - forcing)
                                              / max(float(la.norm(forcing)), 1e-300))
        metrics = {
            "material_nrmse": float(la.norm(error) / la.norm(truth)),
            "delta_nrmse": float(la.norm(error) / la.norm(delta)) if la.norm(delta) else None,
            "real_nrmse": relative_error(got["chi"].real, truth.real),
            "imag_nrmse": relative_error(got["chi"].imag, truth.imag),
            "full_data_absolute_residual": residual,
            "full_data_relative_residual": residual / measured_delta_norm if measured_delta_norm else None,
            "clean_prediction_relative_error": relative_error(full.data, clean),
            "full_state_backward_residual": full.residual,
            "surrogate_current_full_equation_residual": relative_current_residual,
            "relative_feedback_signal": signal, "closure_absolute": closure,
            "rho_closure": closure / signal if signal > floor else None,
            "closure_status": "RESOLVABLE" if signal > floor else "NO_RESOLVABLE_FEEDBACK",
            "feasible": True,
        }
    return metrics, full


def _save_slices(out, case, background, truth, estimates, book):
    with book.span("confirmation_evaluator_slice_render", confirmation_slice_figures=1):
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
        figure, axes = plt.subplots(2, 4, figsize=(11, 5), constrained_layout=True)
        values = [("Truth", truth), ("L", estimates.get("L")),
                  ("F", estimates.get("F")), ("R16", estimates.get("R16"))]
        limits = []
        for channel in range(2):
            channel_values = [(value - background).real if channel == 0 else
                              (value - background).imag
                              for _, value in values if value is not None]
            limits.append(max(float(np.max(np.abs(value))) for value in channel_values))
        for column, (label, value) in enumerate(values):
            for channel in range(2):
                ax = axes[channel, column]
                if value is None:
                    ax.text(.5, .5, "FAILED", ha="center", va="center")
                    ax.set_axis_off()
                    continue
                image = (value - background).reshape(6, 6, 6)[:, :, 3]
                image = image.real if channel == 0 else image.imag
                limit = limits[channel] if limits[channel] > 0 else 1.
                artist = ax.imshow(image.T, origin="lower", cmap="coolwarm",
                                   vmin=-limit, vmax=limit, extent=(-.75, .75, -.75, .75))
                ax.set_title(label + (" Re(delta chi)" if channel == 0 else " Im(delta chi)"))
                figure.colorbar(artist, ax=ax, shrink=.8)
        figure.suptitle(case + "; z=0.125 slice; complete 3-D arrays in NPZ")
        figure.savefig(out / "images" / (case + "_slices.png"), dpi=140)
        plt.close(figure)


def confirm(config, out, book):
    """Run only after the caller establishes G1 and B0 F-headroom gates."""
    if config.get("training_enabled") or config.get("gpu_enabled"):
        raise ValueError("CONFIRMATION_REQUIRES_CPU_NO_TRAINING")
    if int(config.get("blocks", 3)) != 3 or int(config.get("max_half_step_retry", 1)) != 1:
        raise ValueError("CONFIRMATION_FROZEN_OPTIMIZER_CHANGED")
    if int(config.get("confirmation_states_max", 4)) != 4:
        raise ValueError("CONFIRMATION_FOUR_STATE_CAP_REQUIRED")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for directory in ("data/online", "data/offline", "images", "cache"):
        (out / directory).mkdir(parents=True, exist_ok=True)
    rows, failures = [], out / "FAILURE_LEDGER.jsonl"
    start, snapshot = time.perf_counter(), book.snapshot()
    prior_labels = book.reservations.get("new_clean_labels", 0)
    summary = {"status": "RUNNING", "conditional": True, "device": "cpu", "training": False}
    protocol = {
        "grid": [6, 6, 6], "side": 1.5, "cell_volume": .25 ** 3, "k": 2.,
        "sources": "+/- Cartesian axes, one transverse polarization each", "source_count": 6,
        "receiver_count": 16, "receiver_radius": 2., "receiver_rule": "Fibonacci sphere",
        "readouts_per_receiver": 2, "background_ring_radii": [.3, .55],
        "background_ring": [2., .1], "background_other": [.1, .04],
        "shell": {"center": [-.1, .05, 0.], "band": [.18, .32],
                  "inner_radius": .12, "inner_weight": .5},
        "asymmetry": {"box": [[-.55, -.05], [-.40, .15], [-.35, .20]],
                      "ball_center": [.35, .20, .15], "ball_radius": .20, "ball_weight": .7},
        "amplitudes": [.3, 1.2], "phase": "(1+.2i)/sqrt(1.04)", "noiseless": True,
        "methods": ["L", "F", "R16"], "return_rank": 16, "oversampling": 8,
        "power_iterations": 0, "local": False, "blocks": 3, "half_step_retries": 1,
        "tv_lambda": .01, "current_output": "cb + Rb*w, explicitly charged for L/R",
        "scientific_gate_owner": "parent Codex review",
    }
    write_json(out / "CONFIRMATION_PROTOCOL.json", protocol)
    try:
        runtime = online_config(config)
        runtime.update(grid=6, side=1.5, wavenumber=2., sources=6, receivers=16,
                       confirmation_grid=6, confirmation_k=2.,
                       confirmation_source_count=6, confirmation_receiver_count=16)
        begin = time.perf_counter()
        with book.scope("confirmation_background_preparation"):
            physics = Physics3D(runtime, book)
            cache = Reference3D(physics)
            prep = _prepare(cache, book)
            models = {kind: Relative3D(cache, kind, int(config["master_seed"]) + 340)
                      for kind in ("L", "F", "R16")}
            invariants = _invariants(cache, models, config, book)
        preparation_s = time.perf_counter() - begin
        write_json(out / "INVARIANTS.json", invariants)
        with book.span("confirmation_reference_cache_export", confirmation_cache_writes=1):
            np.savez_compressed(out / "cache" / "background.npz", chi_b=cache.chi_b,
                                points=physics.points, volume=physics.volume, eb=cache.eb,
                                yb=cache.yb, Db=cache.Db, J=prep["J"], step=prep["step"],
                                Ug=models["R16"].Ug, Vg=models["R16"].Vg,
                                dirs=physics.model.dirs, pols=physics.model.pols,
                                receivers=physics.model.receivers,
                                obs_basis=physics.model.obs_basis, k=physics.k)
        write_json(out / "PREPARATION.json", {"seconds": preparation_s, "step": prep["step"],
                   "lambda_max_normalized_background_Hessian": prep["lambda_max_normalized_background_Hessian"],
                   "reference_before_labels": True, "full_inverse_stored": False,
                   "actual_feedback_rank": 16, "power_iterations": 0})
        with book.scope("confirmation_offline_scene_definition"):
            with book.span("confirmation_fixed_material_patterns", confirmation_scene_definitions=2):
                patterns = _patterns(physics.points)
        for parent, (family, pattern) in patterns.items():
            for amplitude in (.3, 1.2):
                case = f"3d_ring_{parent}_{amplitude}_zero"
                book.reserve("new_clean_labels", 4)
                try:
                    with book.scope("confirmation_offline_clean_label"):
                        with book.span("confirmation_evaluator_material_scene"):
                            truth = cache.chi_b + amplitude * pattern
                        truth_state = physics.full_state(truth)
                    with book.span("confirmation_observation_export", confirmation_label_writes=1):
                        np.savez_compressed(out / "data/offline" / (case + ".npz"),
                                            truth=truth, clean=truth_state.data)
                        np.savez_compressed(out / "data/online" / (case + ".npz"),
                                            data=truth_state.data, sigma=0., chi_b=cache.chi_b, case_id=case)
                    observation = OnlineObservation(truth_state.data.copy(), 0., case)
                    begin = time.perf_counter()
                    with book.scope("confirmation_online_shared_initialization"):
                        initial, initial_meta = _initialization(cache, observation, prep, runtime, book)
                    initialization_s = time.perf_counter() - begin
                except BudgetExceeded:
                    raise
                except Exception as exc:
                    append_failure(failures, phase="label_or_initialization", case_id=case, error=repr(exc))
                    for method in models:
                        rows.append({"case_id": case, "parent_id": parent, "family": family,
                                     "amplitude": amplitude, "method": method, "status": "LABEL_OR_INIT_FAILED",
                                     "material_nrmse": None, "delta_nrmse": None,
                                     "full_data_relative_residual": None, "error": repr(exc)})
                    write_csv(out / "CASES.csv", rows)
                    continue
                estimates = {}
                for method, model in models.items():
                    row = {"case_id": case, "parent_id": parent, "family": family,
                           "background": "strong_spherical_ring", "amplitude": amplitude,
                           "noise_db": None, "sigma": 0., "method": method,
                           "status": "NOT_RUN", "material_nrmse": None, "delta_nrmse": None,
                           "full_data_relative_residual": None, "feasible": False}
                    try:
                        with book.scope("confirmation_online_imaging"):
                            got = _reconstruct(model, observation, initial, prep, runtime, book)
                        # Freeze/export the runtime result before evaluator access.
                        with book.span("confirmation_runtime_image_export", confirmation_image_writes=1):
                            np.savez_compressed(out / "images" / (case + "_" + method + ".npz"),
                                                chi=got["chi"], x=got["x"], predicted=got["state"].data,
                                                current=got["state"].current)
                        begin = time.perf_counter()
                        with book.scope("confirmation_offline_full_validation"):
                            metrics, physical = _evaluate(physics, cache, truth, truth_state.data,
                                                          observation, got)
                        row.update(metrics, status="OK", online_s=got["online_s"] + initialization_s,
                                   common_initialization_s=initialization_s, preparation_s=preparation_s,
                                   full_validation_s=time.perf_counter() - begin, online_cost=got["cost"],
                                   core_margins=got["state"].margins,
                                   accepted_blocks=sum(item["accepted"] for item in got["history"]),
                                   feedback_rank=16 if method == "R16" else 0)
                        with book.span("confirmation_evaluator_prediction_export"):
                            np.savez_compressed(out / "images" / (case + "_" + method + "_evaluation.npz"),
                                                full_prediction=physical.data)
                            write_json(out / "images" / (case + "_" + method + ".json"),
                                       {"history": got["history"], "initialization": initial_meta, "row": row})
                        estimates[method] = got["chi"]
                    except BudgetExceeded:
                        raise
                    except Exception as exc:
                        row.update(status="FAILED", error=repr(exc))
                        append_failure(failures, phase="online_or_evaluation", case_id=case,
                                       method=method, error=repr(exc))
                    rows.append(row)
                    write_csv(out / "CASES.csv", rows)
                _save_slices(out, case, cache.chi_b, truth, estimates, book)
        summary.update(status="COMPLETE" if len(rows) == 12 and all(r["status"] == "OK" for r in rows)
                       else "PARTIAL", cases=len(rows), successful_cases=sum(r["status"] == "OK" for r in rows),
                       inline_identity_status="PASS", preparation_s=preparation_s,
                       gate_decision="PARENT_REVIEW_REQUIRED", repeated_timing="NOT_RUN")
    except BaseException as exc:
        summary.update(status="BUDGET_STOP" if isinstance(exc, BudgetExceeded) else "FAILED",
                       error=repr(exc), cases=len(rows))
        append_failure(failures, phase="confirmation_stage", error=repr(exc))
        raise
    finally:
        summary.update(wall_seconds=time.perf_counter() - start,
                       clean_labels_reserved=book.reservations.get("new_clean_labels", 0) - prior_labels,
                       planned_clean_labels=4, cost={"counts": {
                           key: int(value - snapshot["counts"].get(key, 0))
                           for key, value in book.counts.items()},
                           "exclusive_walls": {key: float(value - snapshot["exclusive_walls"].get(key, 0.))
                                               for key, value in book.walls.items()}})
        write_csv(out / "CASES.csv", rows)
        write_json(out / "SUMMARY.json", summary)
        write_json(out / "COST_SUMMARY.json", book.receipt())
    return summary
