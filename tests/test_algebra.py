"""A0 assertions; run only inside the parent's charged active_ledger context."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
import numpy as np
from scipy import linalg as la

from a24.anatomy import (SchurAudit, degree_basis, norm_ratio, orth_basis,
                         source_seed_banks, tsom_spaces)
from a24.contracts import (BudgetExceeded, ForbiddenAccess, Ledger,
                           NumericalFailure, OnlineObservation, get_ledger,
                           guard_core, mass_pack, mass_unpack, pack, unpack)


class AlgebraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book = get_ledger()
        with cls.book.span('A0_fixture', evaluator_dense_oracles=1,
                           full_linear_rhs=18):
            cls.config = json.loads((Path(__file__).resolve().parents[1] /
                                     'configs/a24_frozen.json').read_text())
            cls.config.update(target_current_rank=10, seed_rank_M=2, seed_rank_O=2)
            rng = np.random.default_rng(241008)
            def random(*shape):
                return (rng.standard_normal(shape)+1j*rng.standard_normal(shape))/np.sqrt(2.)
            cls.n, cls.s, cls.q = 18, 3, 5
            cls.G = .35*random(cls.n, cls.n)/np.sqrt(cls.n)
            cls.chi_b = np.full(cls.n, .3+.08j, dtype=complex)
            cls.incident = random(cls.n, cls.s)
            cls.S = random(cls.q, cls.n)/np.sqrt(cls.n)
            cls.L = np.eye(cls.n)-cls.chi_b[:, None]*cls.G
            cls.forcing = cls.chi_b[:, None]*cls.incident
            cls.jb = la.solve(cls.L, cls.forcing)
            cls.eb = cls.incident+cls.G@cls.jb
            cls.U, _ = orth_basis(np.column_stack((cls.jb, cls.S.conj().T[:, :2])),
                                  book=cls.book)
            cls.nonU, _ = orth_basis(random(cls.n, 2), book=cls.book)
            cls.mp = rng.standard_normal((2*cls.n, 4))
            cls.op = rng.standard_normal((2*cls.q*cls.s, 4))

    def setUp(self):
        self.book.check()

    def test_source_anchor_and_same_U_P_removal(self):
        with self.book.span('A0_source_anchor_pair'):
            schur = SchurAudit(self.L, self.U, self.config, self.book)
            P = schur.K(self.forcing)
            self.assertLessEqual(norm_ratio(P, self.forcing), 1e-10)
            blocks, records, _ = source_seed_banks(
                schur, self.forcing, self.eb, self.S, 1., self.mp, self.op, self.config)
            self.assertEqual(blocks['P'].shape[1], 0)
            self.assertEqual(records['P']['zero_scale'], float(la.norm(self.forcing)))
            OPM, opm_record = degree_basis(schur, blocks, 'OPM', self.config)
            OM, om_record = degree_basis(schur, blocks, 'OM', self.config)
            self.assertEqual(OPM.shape, OM.shape)
            self.assertLessEqual(norm_ratio(OPM@OPM.conj().T-OM@OM.conj().T,
                                           OM@OM.conj().T), 1e-10)
            self.assertEqual(opm_record['padding'], 0)
            self.assertEqual(om_record['padding'], 0)
            # A global forcing scale prevents normalization of a roundoff seed.
            tiny = np.full((self.n, 3), 1e-15+2e-15j)
            zero, _ = orth_basis(tiny, absolute_zero_scale=la.norm(self.forcing),
                                 book=self.book)
            self.assertEqual(zero.shape[1], 0)

    def test_nonanchor_P_negative_control(self):
        with self.book.span('A0_nonanchor_negative'):
            schur = SchurAudit(self.L, self.nonU, self.config, self.book)
            self.assertGreater(norm_ratio(schur.K(self.forcing), self.forcing), 1e-4)

    def test_schur_inverse_and_retained_coupling(self):
        with self.book.span('A0_schur_feedback_certificate'):
            anchor = SchurAudit(self.L, self.U, self.config, self.book)
            record, _ = anchor.inverse_certificate()
            self.assertLessEqual(record['inverse_schur_error'], 1e-10)
            self.assertGreater(record['complement_core_not_identity_norm'], 1e-4)
            self.assertGreater(la.norm(anchor.K(self.eb*self.mp[:self.n, :1])), 1e-4)
            schur = SchurAudit(self.L, self.nonU, self.config, self.book)
            HU = schur.project((np.eye(self.n)-self.L)@self.nonU)
            a_star = schur.coarse(self.nonU.conj().T@self.jb)
            material = schur.K(self.jb)
            coupled = material-HU@a_star
            rhs = coupled-schur.feedback(coupled)
            target = schur.K(self.forcing)
            self.assertLessEqual(norm_ratio(rhs-target, target), 1e-10)
            omitted = material-schur.feedback(material)
            self.assertGreater(norm_ratio(omitted-target, target), 1e-5)

    def test_schur_actions_have_conjugate_adjoints(self):
        with self.book.span('A0_conjugate_schur_actions'):
            schur = SchurAudit(self.L, self.nonU, self.config, self.book)
            u = self.jb[:, 0]
            v = self.eb[:, 1]
            for name in ('K', 'T', 'feedback'):
                with self.subTest(action=name):
                    action = getattr(schur, name)
                    left = np.vdot(v, action(u))
                    right = np.vdot(action(v, adjoint=True), u)
                    scale = la.norm(u)*la.norm(v)
                    self.assertGreater(scale, 0.)
                    self.assertLessEqual(abs(left-right)/scale, 1e-10)

    def test_relative_identity_defect_and_receiver_error(self):
        with self.book.span('A0_relative_and_defect_identities',
                            evaluator_dense_oracles=1, full_linear_rhs=2*self.n+6):
            eye = np.eye(self.n)
            Rb = la.solve(self.L, eye)
            Gb, Db = self.G@Rb, self.S@Rb
            h = np.linspace(-.05, .1, self.n)-.02j
            chi = self.chi_b+h
            self.assertTrue(np.all(chi.imag >= 0.))
            current = la.solve(eye-chi[:, None]*self.G, chi[:, None]*self.incident)
            w = la.solve(eye-h[:, None]*Gb, h[:, None]*self.eb)
            self.assertLessEqual(norm_ratio(Rb@w-(current-self.jb), current-self.jb), 1e-10)
            u, singular, vh = la.svd(Gb, full_matrices=False)
            Ghat = (u[:, :3]*singular[:3])@vh[:3]
            what = la.solve(eye-h[:, None]*Ghat, h[:, None]*self.eb)
            defect = h[:, None]*(Gb-Ghat)@what
            jhat = self.jb+Rb@what
            residual = (eye-chi[:, None]*self.G)@jhat-chi[:, None]*self.incident
            self.assertLessEqual(norm_ratio(residual+defect, chi[:, None]*self.incident), 1e-10)
            self.assertLessEqual(norm_ratio(w-what-la.solve(eye-h[:, None]*Gb, defect), w), 1e-10)
            Dbhat = .93*Db
            exact_y = Db@w
            yhat = Dbhat@what
            decomposition = Db@(w-what)+(Db-Dbhat)@what
            self.assertLessEqual(norm_ratio(exact_y-yhat-decomposition, exact_y), 1e-10)

    def test_TSOM_intersection_projection_restricted_G(self):
        with self.book.span('A0_TSOM_counterexample'):
            e = np.eye(3, dtype=complex)
            O = e[:, :1]
            D = np.column_stack(((e[:, 0]+e[:, 1])/np.sqrt(2.), e[:, 2]))
            complement = (e[:, 0]-e[:, 1])/np.sqrt(2.)
            V = np.column_stack((D, complement))
            G = np.diag([3., 2., .5])@V.conj().T
            spaces, record = tsom_spaces(G, O, 2, book=self.book)
            self.assertEqual(record['intersection_rank'], 1)
            self.assertEqual(record['projected_rank'], 2)
            self.assertGreater(record['projected_not_in_D_norm'], .1)
            self.assertGreater(record['projector_commutator_norm'], .1)
            self.assertLessEqual(record['restricted_gram_identity_error'], 1e-10)
            self.assertLessEqual(la.norm(O.conj().T@spaces['restricted_G']), 1e-10)
            self.assertLessEqual(la.norm(O.conj().T@spaces['ideal_intersection']), 1e-10)

    def test_unsafe_retained_core_without_fallback(self):
        with self.book.span('A0_unsafe_core_failure'):
            L = np.array([[0., 1.], [1., 0.]], dtype=complex)
            U = np.array([[1.], [0.]], dtype=complex)
            self.assertNotEqual(la.det(L), 0.)
            with self.assertRaisesRegex(NumericalFailure, 'UNSAFE_CORE'):
                SchurAudit(L, U, self.config, self.book)
            with self.assertRaisesRegex(NumericalFailure, 'UNSAFE_CORE'):
                guard_core(np.diag([1., 1e-12]), self.config)

    def test_common_material_impossible_current_and_dark_field(self):
        with self.book.span('A0_common_material_counterexamples'):
            E = np.array([1., 1.], dtype=complex)
            J = np.array([1., 2.], dtype=complex)
            a = np.vdot(E, J)/np.vdot(E, E)
            self.assertEqual(a, 1.5)
            self.assertGreater(la.norm(J-a*E), .7)
            least_residual = la.norm(J)**2-abs(np.vdot(E, J))**2/np.vdot(E, E).real
            self.assertAlmostEqual(least_residual, la.norm(J-a*E)**2)
            self.assertIsNone(norm_ratio(J, np.zeros_like(E)))

    def test_packing_and_material_mass_coordinates(self):
        with self.book.span('A0_real_packing'):
            data = self.S@self.jb
            self.assertTrue(np.array_equal(unpack(pack(data), self.q, self.s), data))
            chi = self.chi_b+.01*self.mp[:self.n, 0]
            self.assertLessEqual(la.norm(mass_unpack(mass_pack(chi, .03125), .03125)-chi), 1e-14)
            perm = np.array([2, 0, 1])
            self.assertTrue(np.array_equal(pack(data[:, perm]).reshape(self.s, 2*self.q),
                                           pack(data).reshape(self.s, 2*self.q)[perm]))
            with self.assertRaises(ValueError):
                pack(np.ones((2, 3)))
            with self.assertRaises(ValueError):
                unpack(np.ones(2*self.q*self.s, dtype=complex), self.q, self.s)
            with self.assertRaises(ValueError):
                mass_unpack(np.ones(3), .1)

    def test_oracle_fields_and_paths_are_forbidden(self):
        from a24.contracts import deny_oracle_path, load_observation
        with self.book.span('A0_oracle_guard'):
            obs = OnlineObservation(np.zeros((2, 2), dtype=complex), 0., 'unit')
            for key in ('truth', 'teacher', 'truth_currents', 'full_J', 'full_H',
                        'reference_step', 'support_mask', 'oracle_currents'):
                with self.subTest(key=key), self.assertRaises(ForbiddenAccess):
                    getattr(obs, key)
            for path in ('offline/example.npz', 'offline_eval/state.npz',
                         'oracle/known.npz', 'teacher/state.npy', 'runtime/full_GN.npz'):
                with self.subTest(path=path), self.assertRaises(ForbiddenAccess):
                    deny_oracle_path(path)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)/'mixed.npz'
                np.savez(path, data=obs.data, sigma=0., truth=np.ones(4))
                with self.assertRaises(ForbiddenAccess):
                    load_observation(path)

    def test_budget_reservation_and_failed_actions_are_charged(self):
        with self.book.span('A0_budget_ledger_guards'):
            zero = Ledger(wall_limit=0.)
            with self.assertRaises(BudgetExceeded):
                zero.check()
            ledger = Ledger(wall_limit=120.)
            ledger.reserve('unit_action', 1)
            with self.assertRaisesRegex(BudgetExceeded, 'ACTION_CAP'):
                ledger.reserve('unit_action', 1)
            self.assertEqual(ledger.reservations['unit_action'], 1)
            with self.assertRaisesRegex(NumericalFailure, 'EXPECTED_FAILURE'):
                with ledger.span('failed_unit_action', linear_solve_rhs=3):
                    raise NumericalFailure('EXPECTED_FAILURE')
            self.assertEqual(ledger.receipt()['counts']['linear_solve_rhs'], 3)
            with ledger.span('parent'):
                with ledger.span('child'):
                    pass
            self.assertLessEqual(sum(ledger.receipt()['exclusive_walls'].values()),
                                 ledger.receipt()['wall_seconds']+1e-6)


if __name__ == '__main__':
    raise SystemExit('Use python -m a24.cli anatomy: standalone uncharged tests are disabled.')
