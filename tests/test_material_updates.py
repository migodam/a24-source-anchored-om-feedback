"""Run only inside the parent A0/A1 active_ledger context; no import-time work."""
import unittest

import numpy as np

from a24 import contracts
from a24.contracts import NumericalFailure, mass_pack, mass_unpack
from a24.material_updates import (material_gradient, material_gradient_adjoint,
                                  normalized_backprojection, prox_tv_box, tv_value)


class MaterialUpdatesTests(unittest.TestCase):
    def setUp(self):
        self.book = contracts.get_ledger()
        self.book.check()
        self.book.counts['material_unit_test_cases'] += 1
        self.config = {'prox_tolerance': 1e-6, 'prox_max_iter': 1000,
                       'prox_check_every': 10, 'material_scale': 1.}
        self.addCleanup(self.book.check)

    def prox(self, v, background, weight, shape, volume=1., config=None):
        return prox_tv_box(v, background, weight, shape, volume,
                           self.config if config is None else config, book=self.book)

    def assert_certificate(self, meta):
        self.assertTrue(meta['converged'], meta)
        self.assertEqual(meta['status'], 'CONVERGED')
        self.assertLessEqual(meta['kkt_residual'], meta['tolerance'])
        self.assertLessEqual(meta['normalized_gap'], meta['tolerance'])
        self.assertLessEqual(meta['feasibility'], 1e-10)
        self.assertLessEqual(meta['dual_feasibility'], meta['tolerance'])
        self.assertGreaterEqual(meta['primal_dual_gap'], -1e-12)
        self.assertLess(meta['tau_sigma_norm_bound_squared'], 1.)

    def test_neumann_gradient_real_adjoint_in_two_and_three_dimensions(self):
        rng = np.random.default_rng(240081)
        for shape in ((3, 4), (2, 3, 2)):
            n = int(np.prod(shape))
            x = rng.normal(size=2*n)
            # Include loads on boundary rows: their D* contribution must vanish.
            p = rng.normal(size=shape+(len(shape), 2))
            lhs = float(np.sum(material_gradient(x, shape)*p))
            rhs = float(np.dot(x, material_gradient_adjoint(p, shape)))
            self.assertLessEqual(abs(lhs-rhs)/max(1., abs(lhs), abs(rhs)), 1e-13)

    def test_constant_complex_field_has_zero_tv(self):
        for shape in ((3, 2), (2, 2, 3)):
            chi = np.full(int(np.prod(shape)), 1.2+.3j)
            x = mass_pack(chi, .03125)
            self.assertEqual(tv_value(x, shape, .03125), 0.)
            self.assertEqual(float(np.linalg.norm(material_gradient(x, shape))), 0.)

    def test_joint_real_imag_tv_and_physical_cell_volume_scaling(self):
        chi = np.array([[0., 1.], [2., 3.]])+1j*np.array([[0., 2.], [1., 3.]])
        for volume in (.04, .25):
            expected = np.sqrt(volume)*(np.sqrt(10.)+2.*np.sqrt(5.))
            self.assertAlmostEqual(tv_value(mass_pack(chi.reshape(-1), volume),
                                          (2, 2), volume), expected, places=13)
        # A single physical edge in three dimensions has area volume**(2/3).
        chi3 = np.array([0., 1.+.25j])
        volume = .008
        expected3 = volume**(2./3.)*np.sqrt(1.+.25**2)
        self.assertAlmostEqual(tv_value(mass_pack(chi3, volume), (2, 1, 1), volume),
                               expected3, places=14)

    def test_zero_weight_is_exact_box_prox_and_is_counted(self):
        volume = .0625
        physical_v = np.array([-2.-.2j, 5.+.9j, .2+.25j, 3.+.1j])
        v = mass_pack(physical_v, volume)
        background = mass_pack(np.full(4, .1+.04j), volume)
        before = self.book.counts['material_box_projections']
        x, meta = self.prox(v, background, 0., (2, 2), volume)
        expected = np.array([-.5+0.j, 4.+.5j, .2+.25j, 3.+.1j])
        np.testing.assert_array_equal(x, mass_pack(expected, volume))
        self.assertEqual(meta['iterations'], 0)
        self.assertGreater(self.book.counts['material_box_projections'], before)
        self.assert_certificate(meta)

    def test_positive_tv_on_a_single_cell_is_analytic_box_prox(self):
        v = mass_pack(np.array([5.-.1j]), 1.)
        background = mass_pack(np.array([.2+.1j]), 1.)
        x, meta = self.prox(v, background, .4, (1, 1))
        np.testing.assert_array_equal(x, mass_pack(np.array([4.+0.j]), 1.))
        self.assertEqual(meta['iterations'], 0)
        self.assertEqual(meta['tv'], 0.)
        self.assert_certificate(meta)

    def test_two_cell_joint_prox_matches_closed_form(self):
        physical_v = np.array([0.+.1j, 1.+.3j])
        q = np.array([1., .2])
        alpha = .05
        mean = np.array([.5, .2])
        difference = (1.-2.*alpha/np.linalg.norm(q))*q
        low, high = mean-.5*difference, mean+.5*difference
        expected = np.array([low[0]+1j*low[1], high[0]+1j*high[1]])
        x, meta = self.prox(mass_pack(physical_v, 1.),
                            mass_pack(np.full(2, .1+.04j), 1.), alpha, (2,))
        np.testing.assert_allclose(mass_unpack(x, 1.), expected, atol=5e-6, rtol=0.)
        self.assert_certificate(meta)

    def test_fused_two_cell_solution_and_dual_complementarity(self):
        v = mass_pack(np.array([0.+.1j, 1.+.3j]), 1.)
        background = mass_pack(np.full(2, .1+.04j), 1.)
        x, meta = self.prox(v, background, 1., (2,))
        np.testing.assert_allclose(mass_unpack(x, 1.), np.full(2, .5+.2j),
                                   atol=5e-6, rtol=0.)
        self.assertLessEqual(meta['kkt_components']['tv_complementarity'], 1e-6)
        self.assert_certificate(meta)

    def test_joint_box_active_solution_has_known_kkt_certificate(self):
        # Construct v from an exact nonzero-TV solution, its TV subgradient
        # and a positive upper-box normal. Re/Im coupling matters here.
        expected = np.array([3.5+.1j, 4.+.3j])
        q = np.array([.5, .2])
        dual = .2*q/np.linalg.norm(q)
        dt_dual = np.array([-dual[0], dual[0], -dual[1], dual[1]])
        upper_normal = np.array([0., .4, 0., 0.])
        v = mass_pack(expected, 1.)+dt_dual+upper_normal
        background = mass_pack(np.full(2, .1+.04j), 1.)
        x, meta = self.prox(v, background, .2, (2,))
        np.testing.assert_allclose(mass_unpack(x, 1.), expected, atol=5e-6, rtol=0.)
        self.assertLessEqual(float(np.max(mass_unpack(x, 1.).real)), 4.)
        self.assertGreaterEqual(float(np.min(mass_unpack(x, 1.).imag)), 0.)
        self.assert_certificate(meta)

    def test_prox_physical_solution_is_consistent_under_mass_scaling(self):
        chi_v = np.array([0.+.1j, 1.+.3j])
        chi_b = np.full(2, .1+.04j)
        solutions = []
        for volume in (1., .125):
            # In 1D, weight proportional to cell volume makes both terms
            # in the physical-coordinate objective scale by volume.
            x, meta = self.prox(mass_pack(chi_v, volume), mass_pack(chi_b, volume),
                                .05*volume, (2,), volume)
            solutions.append(mass_unpack(x, volume))
            self.assertAlmostEqual(meta['physical_mass_scale'], np.sqrt(2.*volume))
            self.assert_certificate(meta)
        np.testing.assert_allclose(solutions[0], solutions[1], atol=5e-6, rtol=0.)

    def test_max_iteration_is_failure_with_metadata_and_optional_exception(self):
        v = mass_pack(np.array([0.+.05j, 1.+.1j, .5+.45j, 2.+.3j]), 1.)
        background = mass_pack(np.full(4, .1+.04j), 1.)
        config = {**self.config, 'prox_max_iter': 1, 'prox_raise_on_failure': False}
        _, meta = self.prox(v, background, .8, (2, 2), config=config)
        self.assertFalse(meta['converged'])
        self.assertEqual(meta['status'], 'NOT_CONVERGED')
        self.assertEqual(meta['iterations'], 1)
        self.assertGreater(meta['kkt_residual'], config['prox_tolerance'])
        config['prox_raise_on_failure'] = True
        with self.assertRaises(NumericalFailure) as caught:
            self.prox(v, background, .8, (2, 2), config=config)
        self.assertFalse(caught.exception.meta['converged'])
        self.assertEqual(caught.exception.meta['iterations'], 1)

    def test_normalized_backprojection_uses_standard_step_and_shared_prox(self):
        background = mass_pack(np.full(2, .1+.04j), 1.)
        residual = np.array([.4, 1.2, .12, .3])
        x, meta = normalized_backprojection(background, residual,
                                            lambda direction: 2.*direction,
                                            lambda load: 2.*load, weight=0.,
                                            grid_shape=(2,), volume=1.,
                                            config=self.config, book=self.book)
        np.testing.assert_allclose(x, background+.5*residual, atol=1e-14, rtol=0.)
        self.assertAlmostEqual(meta['step_size'], .25)
        self.assert_certificate(meta['prox'])

    def test_zero_backprojection_never_calls_forward(self):
        background = mass_pack(np.full(2, .1+.04j), 1.)

        def forbidden_forward(direction):
            raise AssertionError('Zero adjoint must not incur a forward action')

        x, meta = normalized_backprojection(background, np.zeros(4), forbidden_forward,
                                            lambda load: np.zeros(4), weight=.1,
                                            grid_shape=(2,), volume=1.,
                                            config=self.config, book=self.book)
        np.testing.assert_array_equal(x, background)
        self.assertTrue(meta['zero_adjoint'])
        self.assertIsNone(meta['response_norm_squared'])
        self.assert_certificate(meta['prox'])


if __name__ == '__main__':
    raise SystemExit('Run inside contracts.active_ledger(book) in the parent A0/A1 stage.')
