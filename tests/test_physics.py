"""A1 native 2-D and closure tests; fixtures use the active charged ledger."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import unittest
import numpy as np
from scipy import linalg as la

from a24.contracts import (NumericalFailure, get_ledger, mass_unpack,
                           pack, unpack)
from a24.physics import Physics2D
from a24.relative_feedback import LocalBlocks, ReferenceCache, RelativeFeedbackModel


class PhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = get_ledger()
        with cls.book.span('A1_fixture'):
            cls.config = json.loads((Path(__file__).resolve().parents[1] /
                                     'configs/a24_frozen.json').read_text())
            cls.physics = Physics2D(grid=8, book=cls.book, config=cls.config)
            p = cls.physics
            cls.chi_b = np.full(p.N, .1+.04j, dtype=complex)
            cls.cache = ReferenceCache(p, cls.chi_b, book=cls.book, config=cls.config)
            x, y = p.points.T
            cls.chi = .22+.06j+.035*np.sin(2*np.pi*x)*np.cos(2*np.pi*y)
            cls.models = {
                'L': RelativeFeedbackModel(cls.cache, 'L', config=cls.config),
                'F': RelativeFeedbackModel(cls.cache, 'F', config=cls.config),
                'R': RelativeFeedbackModel(cls.cache, 'R', rank=16, config=cls.config),
                'R_LOCAL': RelativeFeedbackModel(cls.cache, 'R', rank=16, local=True, config=cls.config),
                'ROM': RelativeFeedbackModel(cls.cache, 'ROM', config=cls.config)}
            cls.states = {name: model.forward(cls.chi) for name, model in cls.models.items()}
            rng = np.random.default_rng([241008, 7107])
            cls.direction = rng.standard_normal(2*p.N)
            cls.direction /= la.norm(cls.direction)
            cls.load = rng.standard_normal(2*p.q*p.s)
            cls.load /= la.norm(cls.load)
            cls.probes = (rng.standard_normal((p.n, 3))+1j*rng.standard_normal((p.n, 3)))/np.sqrt(2.)

    def setUp(self):
        self.book.check()

    def assertScaledClose(self, actual, expected, tolerance=1e-10):
        scale = float(la.norm(expected))
        self.assertGreater(scale, 0., 'Declared comparison scale is zero')
        self.assertLessEqual(la.norm(actual-expected)/scale, tolerance)

    def test_native_A2_dense_reference_and_mass_normalization(self):
        with self.book.span('A1_original_A2_dense_reference', evaluator_dense_oracles=1,
                            G_dense_assemblies=1, full_linear_rhs=self.physics.s):
            reference = self.physics.vie.dense_reference(self.chi)
            full = self.states['F'].extra['native']
            self.assertScaledClose(full.current, np.sqrt(self.physics.volume)*reference['current'])
            self.assertScaledClose(full.data, reference['scattered'])
            self.assertScaledClose(full.field, np.sqrt(self.physics.volume)*self.physics.vie.E+
                                   self.physics.G@full.current)
            self.assertLessEqual(full.residual, 1e-10)
            self.assertEqual(full.current.shape, (self.physics.n, self.physics.s))
            self.assertEqual(full.data.shape, (self.physics.q, self.physics.s))
            self.assertEqual(full.current.dtype, np.dtype('complex128'))

    def test_full_relative_source_identity_and_zero_h_nonzero_J(self):
        with self.book.span('A1_full_relative_identity', evaluator_dense_oracles=1,
                            full_linear_rhs=self.physics.n+self.physics.s):
            p, cache = self.physics, self.cache
            Rb = la.solve(cache.state_b.L, np.eye(p.n))
            h = self.chi-cache.chi_b
            w = la.solve(np.eye(p.n)-h[:, None]*(p.G@Rb), h[:, None]*cache.eb)
            exact = self.states['F']
            self.assertScaledClose(exact.w, w)
            self.assertScaledClose(cache.solve_ref(w), exact.extra['native'].current-cache.state_b.current)
            self.assertScaledClose(cache.yb+cache.Db@w, exact.extra['native'].data)
            for name, model in self.models.items():
                with self.subTest(model=name):
                    state = model.forward(cache.chi_b)
                    self.assertEqual(float(la.norm(state.w)), 0.)
                    self.assertTrue(np.array_equal(state.data, cache.yb))
                    tangent = model.jvp(cache.chi_b, self.direction, state)
                    self.assertGreater(la.norm(tangent), 1e-8)

    def test_G_S_and_background_conjugate_adjoints(self):
        with self.book.span('A1_native_conjugate_adjoints'):
            p, cache = self.physics, self.cache
            v, z = self.probes[:, 0], self.probes[:, 1]
            lhs = np.vdot(z, p.green(v))
            rhs = np.vdot(p.green(z, adjoint=True), v)
            self.assertLessEqual(abs(lhs-rhs)/(la.norm(v)*la.norm(z)), 1e-10)
            r = unpack(self.load, p.q, p.s)[:, 0]
            lhs = np.vdot(r, p.observe(v))
            rhs = np.vdot(p.observe(r, adjoint=True), v)
            self.assertLessEqual(abs(lhs-rhs)/(la.norm(v)*la.norm(r)), 1e-10)
            lhs = np.vdot(z, cache.gb(v))
            rhs = np.vdot(cache.gb(z, adjoint=True), v)
            self.assertLessEqual(abs(lhs-rhs)/(la.norm(v)*la.norm(z)), 1e-10)

    def test_real_JVP_VJP_dot_product_and_batched_source_shape(self):
        with self.book.span('A1_real_adjoint_dot'):
            for name, model in self.models.items():
                with self.subTest(model=name):
                    state = self.states[name]
                    jv = model.jvp(self.chi, self.direction, state)
                    g = model.adjoint(self.chi, self.load, state)
                    lhs = float(np.dot(self.load, jv))
                    rhs = float(np.dot(self.direction, g))
                    scale = float(la.norm(self.load)*la.norm(jv)+la.norm(self.direction)*la.norm(g))
                    self.assertGreater(scale, 0.)
                    self.assertLessEqual(abs(lhs-rhs)/scale, 1e-10)
                    batched = model.jvp(self.chi, np.column_stack((self.direction, -self.direction)), state)
                    self.assertEqual(batched.shape, (2*self.physics.q*self.physics.s, 2))
                    self.assertScaledClose(batched[:, 0], jv)
                    self.assertScaledClose(batched[:, 1], -jv)
                    batched_g = model.adjoint(self.chi, np.column_stack((self.load, -self.load)), state)
                    self.assertScaledClose(batched_g[:, 0], g)
                    self.assertScaledClose(batched_g[:, 1], -g)

    def test_four_finite_difference_steps_at_independent_passive_candidate(self):
        with self.book.span('A1_four_step_finite_difference'):
            delta = mass_unpack(self.direction, self.physics.volume)
            steps = self.config['fd_steps']
            self.assertEqual(steps, [1e-3, 3e-4, 1e-4, 3e-5])
            for name, model in self.models.items():
                with self.subTest(model=name):
                    tangent = model.jvp(self.chi, self.direction, self.states[name])
                    scale = float(la.norm(tangent))
                    self.assertGreater(scale, 0.)
                    errors = []
                    for epsilon in steps:
                        plus = model.forward(self.chi+epsilon*delta).data
                        minus = model.forward(self.chi-epsilon*delta).data
                        numerical = pack((plus-minus)/(2*epsilon))
                        errors.append(float(la.norm(numerical-tangent)/scale))
                    self.book.append({'event': 'finite_difference_platform', 'status': 'MEASURED',
                                      'method': name, 'steps': steps, 'relative_errors': errors,
                                      'threshold': self.config['fd_platform_tolerance']})
                    # The two smallest preregistered steps must both be on the platform.
                    self.assertLessEqual(max(errors[-2:]), self.config['fd_platform_tolerance'])

    def test_dense_surrogate_small_core_and_same_conjugate_adjoint(self):
        with self.book.span('A1_dense_lowrank_core_verification', evaluator_dense_oracles=2,
                            full_linear_rhs=2*(self.physics.s+6)):
            p = self.physics
            for name in ('R', 'R_LOCAL'):
                with self.subTest(model=name):
                    model, state = self.models[name], self.states[name]
                    Ghat = model.D.to_dense()+model.Ug@model.Vg.conj().T
                    Ahat = np.eye(p.n)-state.h[:, None]*Ghat
                    w = la.solve(Ahat, state.h[:, None]*self.cache.eb)
                    self.assertScaledClose(state.w, w)
                    self.assertScaledClose(model.solve_A(self.probes, state), la.solve(Ahat, self.probes))
                    self.assertScaledClose(model.solve_A_adjoint(self.probes, state),
                                           la.solve(Ahat.conj().T, self.probes))
                    lhs = np.vdot(self.probes[:, 1], model.solve_A(self.probes[:, 0], state))
                    rhs = np.vdot(model.solve_A_adjoint(self.probes[:, 1], state), self.probes[:, 0])
                    self.assertLessEqual(abs(lhs-rhs)/(la.norm(self.probes[:, 0])*la.norm(self.probes[:, 1])), 1e-10)

    def test_negative_Im_h_is_allowed_when_final_chi_is_passive(self):
        with self.book.span('A1_negative_relative_loss'):
            chi = self.cache.chi_b+.05-.02j
            self.assertTrue(np.all(chi.imag >= 0.))
            self.assertTrue(np.all((chi-self.cache.chi_b).imag < 0.))
            for name in ('L', 'F', 'R', 'R_LOCAL'):
                with self.subTest(model=name):
                    state = self.models[name].forward(chi)
                    self.assertTrue(np.isfinite(state.data).all())

    def test_no_feedback_matches_dressed_linear_and_linear_a_conversion(self):
        with self.book.span('A1_no_feedback_constitutive_control'):
            state = self.states['L']
            h = self.physics.material_to_a(self.chi)-self.cache.ab
            dressed = self.cache.yb+self.cache.apply_db(h[:, None]*self.cache.eb)
            self.assertScaledClose(state.data, dressed)
            # a=chi is the separately declared 2-D constitutive map.
            exact_conversion = self.physics.material_to_a(self.chi)
            self.assertTrue(np.array_equal(exact_conversion, self.chi))
            linear_a = self.cache.yb+self.cache.apply_db((exact_conversion-self.cache.ab)[:, None]*self.cache.eb)
            self.assertScaledClose(state.data, linear_a)
            before = dict(self.book.counts)
            model = self.models['L']
            model.forward(self.chi)
            model.jvp(self.chi, self.direction, state)
            model.adjoint(self.chi, self.load, state)
            self.assertEqual(self.book.counts['Green_kernel_rhs'], before.get('Green_kernel_rhs', 0))
            self.assertEqual(self.book.counts['full_forward_calls'], before.get('full_forward_calls', 0))

    def test_source_permutation_forward_equivariance_common_material_adjoint(self):
        with self.book.span('A1_source_permutation'):
            perm = np.array([6, 2, 0, 7, 3, 1, 5, 4])
            p = Physics2D(grid=8, book=self.book, config=self.config)
            p.incident = p.incident[:, perm].copy()
            p.vie.tx = p.vie.tx[perm].copy()
            cache = ReferenceCache(p, self.chi_b, book=self.book, config=self.config)
            load_permuted = pack(unpack(self.load, p.q, p.s)[:, perm])
            for name in ('L', 'F', 'R', 'R_LOCAL'):
                with self.subTest(model=name):
                    original = self.models[name]
                    model = RelativeFeedbackModel(cache, original.kind, rank=original.rank,
                                                  local=original.local, seed=original.seed, config=self.config)
                    state = model.forward(self.chi)
                    self.assertScaledClose(state.data, self.states[name].data[:, perm])
                    self.assertScaledClose(model.adjoint(self.chi, load_permuted, state),
                                           original.adjoint(self.chi, self.load, self.states[name]))

    def test_cache_keys_reject_frequency_geometry_background_and_precision_change(self):
        with self.book.span('A1_cache_dependency_validation'):
            self.assertTrue(self.cache.validate(self.cache.descriptor))
            for field in ('frequency_hz', 'geometry', 'background', 'precision'):
                altered = deepcopy(self.cache.descriptor)
                if field == 'frequency_hz':
                    altered[field] *= 1.01
                elif field == 'geometry':
                    altered[field]['radius_rx'] += .01
                elif field == 'background':
                    altered[field][0][0] += .01
                else:
                    altered[field] = 'complex64'
                with self.subTest(field=field), self.assertRaisesRegex(NumericalFailure, 'CACHE_DESCRIPTOR'):
                    self.cache.validate(altered)
            with self.assertRaises(ValueError):
                self.models['R'].jvp(self.chi+.001, self.direction, self.states['R'])
            with self.assertRaises(ValueError):
                self.models['R'].adjoint(self.chi, self.load, self.states['F'])

    def test_unsafe_local_P_is_explicit_failure_without_silent_fallback(self):
        with self.book.span('A1_unsafe_local_P_control'):
            model = RelativeFeedbackModel(self.cache, 'R', rank=0, config=self.config)
            model.D = LocalBlocks(self.physics.n, (np.array([0]),),
                                  (np.array([[1.]], dtype=complex),))
            chi = self.cache.chi_b.copy()
            chi[0] += 1.
            with self.assertRaisesRegex(NumericalFailure, 'UNSAFE_CORE:P'):
                model.forward(chi)

    def test_full_state_defect_identity_for_reduced_feedback(self):
        with self.book.span('A1_full_state_defect_evaluator'):
            p, cache = self.physics, self.cache
            for name in ('R', 'R_LOCAL'):
                with self.subTest(model=name):
                    model, state = self.models[name], self.states[name]
                    defect = state.h[:, None]*(cache.gb(state.w)-model.feedback_apply(state.w))
                    implied = cache.state_b.current+cache.solve_ref(state.w)
                    full_L = self.states['F'].extra['native'].L
                    residual = p.apply_matrix(full_L, implied, role='evaluator_residual')-self.chi[:, None]*p.incident
                    scale = la.norm(self.chi[:, None]*p.incident)
                    self.assertGreater(scale, 0.)
                    self.assertLessEqual(la.norm(residual+defect)/scale, 1e-10)


if __name__ == '__main__':
    raise SystemExit('Use python -m a24.cli anatomy: standalone uncharged tests are disabled.')
